import io, csv, secrets, logging, hashlib
from datetime import timedelta
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.urls import reverse
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.db.models import Sum, Count, Q, F
from django.db import connection
from django.http import HttpResponse, FileResponse
from django.utils import timezone
from django.utils.text import slugify
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework import viewsets, generics, status, filters, permissions
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied
from django.core.files.base import ContentFile
from .models import (Category,PhoneModel,Product,ProductVariant,Order,OrderItem,Wishlist,SavedCart,CustomerAddress,
                     CustomerArtwork,StockMovement,Review,SiteConfig,ProductImage,Banner,CustomerProfile)
from .serializers import (CategorySerializer,PhoneModelSerializer,ProductSerializer,OrderCreateSerializer,
                          OrderSerializer,PublicTrackSerializer,SiteConfigSerializer,ReviewSerializer,VariantSerializer,ProductImageSerializer,BannerSerializer,CustomerAddressSerializer)

class StaffWritePublicRead(permissions.BasePermission):
    def has_permission(self,request,view):return request.method in permissions.SAFE_METHODS or bool(request.user and request.user.is_staff)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset=Category.objects.all();serializer_class=CategorySerializer;permission_classes=[StaffWritePublicRead]
    def get_queryset(self):
        return Category.objects.all() if self.request.user.is_staff else Category.objects.filter(active=True)

class PhoneModelViewSet(viewsets.ModelViewSet):
    queryset=PhoneModel.objects.all();serializer_class=PhoneModelSerializer;permission_classes=[StaffWritePublicRead]
    pagination_class=None
    def get_queryset(self):return PhoneModel.objects.all() if self.request.user.is_staff else PhoneModel.objects.filter(active=True)

class ProductViewSet(viewsets.ModelViewSet):
    queryset=Product.objects.select_related('category').prefetch_related('variants__phone_model','images')
    serializer_class=ProductSerializer;permission_classes=[StaffWritePublicRead]
    lookup_field='slug'
    def list(self,request,*args,**kwargs):
        # Cache only public catalogue responses. Staff may see inactive products.
        if request.user.is_authenticated:return super().list(request,*args,**kwargs)
        key='na:public:catalogue:'+hashlib.sha256(request.get_full_path().encode()).hexdigest()
        payload=cache.get(key)
        if payload is not None:return Response(payload)
        result=super().list(request,*args,**kwargs)
        if result.status_code==200:cache.set(key,result.data,45)
        return result
    def get_queryset(self):
        qs=self.queryset
        if not self.request.user.is_staff:qs=qs.filter(active=True)
        search=self.request.query_params.get('search','').strip()
        cat=self.request.query_params.get('category','')
        model=self.request.query_params.get('phone','')
        kind=self.request.query_params.get('kind','')
        if search:
            if len(search) > 100:raise ValidationError({'search':'Recherche trop longue.'})
            if connection.vendor=='postgresql':
                from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
                vector=SearchVector('name',weight='A')+SearchVector('description',weight='B')
                qs=qs.annotate(_rank=SearchRank(vector,SearchQuery(search,search_type='websearch'))).filter(
                    Q(_rank__gt=0)|Q(variants__phone_model__name__icontains=search)).distinct().order_by('-_rank','-created_at')
            else:qs=qs.filter(Q(name__icontains=search)|Q(description__icontains=search)|Q(variants__phone_model__name__icontains=search)).distinct()
        if cat:qs=qs.filter(category__slug=cat)
        if kind:qs=qs.filter(kind=kind)
        if self.request.query_params.get('price_confirmed')=='true':qs=qs.filter(price_confirmed=True)
        if model:qs=qs.filter(variants__phone_model__name__icontains=model).distinct()
        color=self.request.query_params.get('color','').strip()
        if color:qs=qs.filter(variants__color__icontains=color).distinct()
        min_price=self.request.query_params.get('min_price')
        max_price=self.request.query_params.get('max_price')
        if min_price and min_price.isdigit():qs=qs.filter(price__gte=int(min_price))
        if max_price and max_price.isdigit():qs=qs.filter(price__lte=int(max_price))
        if self.request.query_params.get('new')=='1':qs=qs.filter(is_new=True)
        ordering=self.request.query_params.get('sort','new')
        if ordering=='price_asc':qs=qs.order_by('price','id')
        elif ordering=='price_desc':qs=qs.order_by('-price','id')
        elif ordering=='popular':qs=qs.order_by('-is_bestseller','id')
        return qs

    @action(detail=True,methods=['post'],permission_classes=[IsAdminUser],url_path='duplicate')
    def duplicate(self,request,slug=None):
        original=self.get_object()
        with transaction.atomic():
            import copy
            clone=copy.copy(original);clone.pk=None
            clone.slug=f'{original.slug}-copie-{secrets.token_hex(3)}';clone.name=f'{original.name} (copie)'
            clone.active=False;clone.is_bestseller=False;clone.source_ref='';clone.save()
            for var in original.variants.all():
                var.pk=None;var.product=clone;var.stock_count=0;var.save()
            for img in original.images.all():
                img.pk=None;img.product=clone;img.save()
        return Response(ProductSerializer(clone).data,status=201)

class VariantAdminViewSet(viewsets.ModelViewSet):
    queryset=ProductVariant.objects.select_related('product','phone_model')
    serializer_class=VariantSerializer
    permission_classes=[IsAdminUser]
    pagination_class=None
    def get_queryset(self):
        qs=self.queryset
        if self.request.query_params.get('product'):qs=qs.filter(product_id=self.request.query_params['product'])
        return qs
    def perform_update(self, serializer):
        before=serializer.instance.stock_count
        with transaction.atomic():
            updated=serializer.save()
            delta=updated.stock_count-before
            if delta:StockMovement.objects.create(variant=updated,delta=delta,reason='Ajustement manuel de stock')

class ProductImageAdminViewSet(viewsets.ModelViewSet):
    queryset=ProductImage.objects.select_related('product')
    serializer_class=ProductImageSerializer
    permission_classes=[IsAdminUser]
    parser_classes=[MultiPartParser,FormParser,JSONParser]
    pagination_class=None
    def get_queryset(self):
        qs=self.queryset
        product=self.request.query_params.get('product')
        if product and product.isdigit():qs=qs.filter(product_id=int(product))
        return qs
    def perform_create(self,serializer):
        serializer.save()  # ProductImage.save optimizes images for API and Django Admin
    def perform_update(self,serializer):
        serializer.save()
    def perform_destroy(self,instance):
        product=instance.product
        image_url=instance.image.url
        instance.delete()
        if product.cover_url==image_url:
            next_photo=ProductImage.objects.filter(product=product).order_by('order','id').first()
            Product.objects.filter(pk=product.pk).update(cover_url=next_photo.image.url if next_photo else '')
    @action(detail=False,methods=['post'],url_path='reorder')
    def reorder(self,request):
        ids=request.data.get('ids')
        product=request.data.get('product')
        if not isinstance(ids,list) or not all(isinstance(i,int) for i in ids) or len(ids)>100:
            raise ValidationError({'ids':'Liste d’identifiants requise.'})
        existing=list(ProductImage.objects.filter(product_id=product,id__in=ids).values_list('id',flat=True))
        if len(existing)!=len(ids) or len(ids)!=ProductImage.objects.filter(product_id=product).count():
            raise ValidationError({'ids':'Les images doivent toutes appartenir au même produit.'})
        with transaction.atomic():
            for idx,image_id in enumerate(ids):ProductImage.objects.filter(pk=image_id).update(order=idx)
            if ids:
                first=ProductImage.objects.get(pk=ids[0])
                Product.objects.filter(pk=product).update(cover_url=settings.MEDIA_URL + first.image.name)
        return Response({'reordered':True})

class SiteConfigView(APIView):
    permission_classes=[AllowAny]
    def get(self,request):return Response(SiteConfigSerializer(SiteConfig.current()).data)
    def patch(self,request):
        if not request.user.is_staff:raise PermissionDenied()
        cfg=SiteConfig.current();serializer=SiteConfigSerializer(cfg,data=request.data,partial=True)
        serializer.is_valid(raise_exception=True);serializer.save();return Response(serializer.data)

class ArtworkUploadView(APIView):
    parser_classes=[MultiPartParser,FormParser]
    permission_classes=[AllowAny]
    throttle_classes=[ScopedRateThrottle]
    throttle_scope='uploads'
    def post(self,request):
        file=request.FILES.get('image')
        if not file or file.size>8*1024*1024:
            raise ValidationError({'image':'Image obligatoire, taille maximale 8 Mo.'})
        try:
            image=Image.open(file)
            image.verify();file.seek(0)
            image=Image.open(file)
            image=ImageOps.exif_transpose(image)
            if image.width*image.height>20_000_000:raise ValidationError({'image':'Image trop grande.'})
            image=image.convert('RGB')
            image.thumbnail((2500,2500),Image.Resampling.LANCZOS)
            output=io.BytesIO();image.save(output,format='JPEG',quality=90,optimize=True)
        except (OSError,UnidentifiedImageError,ValueError,Image.DecompressionBombError):
            raise ValidationError({'image':'Fichier image non valide.'})
        artwork=CustomerArtwork()
        artwork.image.save('photo-client.jpg',ContentFile(output.getvalue()),save=True)
        return Response({'token':str(artwork.token),'message':'Photo reçue. Elle ne sera pas affichée publiquement.'},status=201)

class AdminArtworkView(APIView):
    permission_classes=[IsAdminUser]
    def get(self,request,token):
        artwork=CustomerArtwork.objects.filter(token=token).first()
        if not artwork:raise NotFound()
        return FileResponse(artwork.image.open('rb'),content_type='image/jpeg',as_attachment=True,filename='personnalisation.jpg')

class OrderViewSet(viewsets.GenericViewSet):
    queryset=Order.objects.prefetch_related('items')
    serializer_class=OrderSerializer
    def get_permissions(self):
        if self.action=='create':return [AllowAny()]
        return [IsAdminUser()]
    def get_throttles(self):
        if self.action=='create':self.throttle_scope='orders';return [ScopedRateThrottle()]
        return super().get_throttles()
    def list(self,request):
        qs=self.queryset
        for key in ['source','status','payment_status','zone']:
            value=request.query_params.get(key)
            if value:qs=qs.filter(**{key:value})
        page=self.paginate_queryset(qs)
        if page is not None:return self.get_paginated_response(OrderSerializer(page,many=True).data)
        return Response(OrderSerializer(qs,many=True).data)
    def retrieve(self,request,pk=None):
        obj=self.get_object();return Response(OrderSerializer(obj).data)
    def create(self,request):
        s=OrderCreateSerializer(data=request.data,context={'request':request});s.is_valid(raise_exception=True)
        data=s.validated_data
        with transaction.atomic():
            lines=[];total=0
            for line in data['items']:
                product=Product.objects.select_for_update().filter(id=line['product_id'],active=True).first()
                if product is None:raise ValidationError({'items':'Un produit est indisponible.'})
                if not product.price_confirmed:raise ValidationError({'items':f'Prix non confirmé pour {product.name} : contactez New arrivals.'})
                variant=None
                if 'variant_id' in line and line['variant_id'] is not None:
                    variant=ProductVariant.objects.select_for_update().filter(pk=line['variant_id'],product=product).first()
                    if not variant or variant.status=='indisponible':raise ValidationError({'items':f'Variante indisponible : {product.name}'})
                    if variant.status=='en_stock' and variant.stock_count<line['quantity']:
                        raise ValidationError({'items':f'Stock insuffisant : {product.name}'})
                elif product.kind!='accessoire':
                    raise ValidationError({'items':f'Sélectionnez le modèle de téléphone pour {product.name}.'})
                price=line.get('negotiated_unit_price',product.price)
                if 'negotiated_unit_price' in line and not request.user.is_staff:raise PermissionDenied()
                artwork=None
                if product.customizable:
                    token=line.get('artwork_token')
                    if not token:raise ValidationError({'items':'Une photo est requise pour une housse personnalisée.'})
                    artwork=CustomerArtwork.objects.select_for_update().filter(token=token,consumed=False,created_at__gte=timezone.now()-timedelta(days=1)).first()
                    if not artwork:raise ValidationError({'items':'Photo expirée ou déjà utilisée. Envoyez-la à nouveau.'})
                elif line.get('artwork_token'):
                    raise ValidationError({'items':'Ce produit ne peut pas être personnalisé.'})
                total+=price*line['quantity']
                lines.append((product,variant,line,price,artwork))
            if total>30_000_000:raise ValidationError('Montant trop élevé pour une commande web.')
            required=(total+1)//2 if data['zone']=='tana' else total
            declared = data.get('paid_amount',0) if request.user.is_staff else 0
            if declared > total:raise ValidationError({'paid_amount':'Le paiement déclaré dépasse le montant de la commande.'})
            order=Order.objects.create(source=data.get('source','web'),
                user=request.user if request.user.is_authenticated else None,
                customer_name=data['customer_name'], customer_phone=data['customer_phone'],
                customer_email=data.get('customer_email',''),address=data['address'],city=data['city'],zone=data['zone'],
                total=total,required_payment=required,paid_amount=declared,payment_method=data['payment_method'],
                transaction_reference=data.get('transaction_reference','').strip(),payment_phone=data.get('payment_phone',''),
                notes=data.get('notes','') if request.user.is_staff else '',
                payment_status='declare' if data.get('transaction_reference') or declared else 'en_attente')
            for product,variant,line,price,artwork in lines:
                OrderItem.objects.create(order=order,product=product,variant=variant,product_name=product.name,
                    phone_model_name=variant.phone_model.name if variant and variant.phone_model else '',
                    color=line.get('color',variant.color if variant else ''),unit_price=price,
                    quantity=line['quantity'],artwork=artwork)
                if artwork:artwork.consumed=True;artwork.save(update_fields=['consumed'])
        from .tasks import queue_email
        if order.customer_email:
            queue_email(f'NEW ARRIVALS — Demande {order.reference}',
                f'Nous avons reçu votre demande {order.reference}. Paiement en attente de vérification. Montant requis : {required:,} Ar.',
                [order.customer_email])
        if settings.ADMIN_EMAIL:
            queue_email('Nouvelle commande NEW ARRIVALS',f'{order.reference} ({order.source})',[settings.ADMIN_EMAIL])
        return Response(OrderSerializer(order).data,status=201)

    @action(detail=True,methods=['patch'],permission_classes=[IsAdminUser],url_path='manage')
    def manage(self,request,pk=None):
        with transaction.atomic():
            order=Order.objects.select_for_update().get(pk=self.get_object().pk)
            new_payment=request.data.get('payment_status')
            new_status=request.data.get('status')
            if new_payment is not None:
                if new_payment not in dict(Order.PAYMENTS):raise ValidationError({'payment_status':'Statut invalide.'})
                if order.payment_status=='verifie' and new_payment!='verifie':
                    raise ValidationError('Un paiement vérifié ne peut pas être annulé sans procédure de remboursement/réconciliation.')
                if new_payment=='verifie':
                    paid=request.data.get('paid_amount',order.required_payment)
                    try:paid=int(paid)
                    except (ValueError,TypeError):raise ValidationError({'paid_amount':'Montant invalide.'})
                    if paid<order.required_payment or paid>order.total:
                        raise ValidationError({'paid_amount':'Le montant vérifié doit couvrir le paiement requis sans dépasser le total.'})
                    order.paid_amount=paid
                    if order.payment_status!='verifie':
                        for item in order.items.select_related('variant','product'):
                            if item.variant_id and item.variant.status=='en_stock':
                                variant=ProductVariant.objects.select_for_update().get(pk=item.variant_id)
                                if variant.stock_count<item.quantity:raise ValidationError('Stock insuffisant lors de la confirmation.')
                                variant.stock_count-=item.quantity;variant.save(update_fields=['stock_count'])
                                StockMovement.objects.create(variant=variant,order=order,delta=-item.quantity,reason='Confirmation commande')
                    if order.status=='attente_acompte':order.status='acompte_recu'
                order.payment_status=new_payment
            if new_status is not None:
                if new_status not in dict(Order.STATUS_CHOICES):raise ValidationError({'status':'Statut invalide.'})
                if new_status not in ['attente_acompte','annulee'] and order.payment_status!='verifie':
                    raise ValidationError('Le paiement doit être vérifié avant la préparation.')
                order.status=new_status
            if 'notes' in request.data:order.notes=str(request.data['notes'])[:3000]
            order.save()
        if order.customer_email:
            from .tasks import queue_email
            queue_email(f'NEW ARRIVALS — Suivi {order.reference}',
                f'Le statut de votre commande est maintenant : {order.get_status_display()}.', [order.customer_email])
        return Response(OrderSerializer(order).data)

    @action(detail=False,methods=['get'],permission_classes=[IsAdminUser],url_path='export-csv')
    def export_csv(self,request):
        response=HttpResponse(content_type='text/csv; charset=utf-8');response['Content-Disposition']='attachment; filename="commandes_new_arrivals.csv"'
        writer=csv.writer(response);writer.writerow(['Référence','Canal','Client','Téléphone','Zone','Total Ar','Paiement vérifié Ar','Paiement','Statut','Date'])
        for x in Order.objects.all().iterator():writer.writerow([x.reference,x.source,x.customer_name,x.customer_phone,x.zone,x.total,x.paid_amount,x.payment_status,x.status,x.created_at.isoformat()])
        return response

class TrackingView(APIView):
    permission_classes=[AllowAny]
    throttle_classes=[ScopedRateThrottle]
    throttle_scope='orders'
    def get(self,request,token):
        order=Order.objects.prefetch_related('items').filter(tracking_token=token).first()
        if not order:raise NotFound('Commande introuvable.')
        return Response(PublicTrackSerializer(order).data)

class MyOrdersView(generics.ListAPIView):
    permission_classes=[IsAuthenticated]
    serializer_class=OrderSerializer
    def get_queryset(self):return Order.objects.filter(user=self.request.user).prefetch_related('items')

class RegisterView(APIView):
    permission_classes=[AllowAny]
    throttle_classes=[ScopedRateThrottle]
    throttle_scope='auth'
    def post(self,request):
        email=str(request.data.get('email','')).strip().lower()
        password=str(request.data.get('password',''))
        first_name=str(request.data.get('name','')).strip()
        if '@' not in email or User.objects.filter(username=email).exists():raise ValidationError({'email':'Adresse invalide ou déjà utilisée.'})
        from django.contrib.auth.password_validation import validate_password
        validate_password(password)
        user=User.objects.create_user(username=email,email=email,password=password,first_name=first_name)
        return Response({'id':user.id,'email':user.email},status=201)

class AdminDashboardView(APIView):
    permission_classes=[IsAdminUser]
    def get(self,request):
        confirmed=Order.objects.filter(payment_status='verifie')
        all_orders=Order.objects.all()
        def rollup(days):
            qs=confirmed.filter(created_at__gte=timezone.now()-timedelta(days=days))
            return qs.aggregate(total=Sum('total'),paid=Sum('paid_amount'),count=Count('id'))
        from django.db.models.functions import TruncDate
        thirty = timezone.now()-timedelta(days=30)
        daily=list(confirmed.filter(created_at__gte=thirty).annotate(day=TruncDate('created_at')).values('day').annotate(total=Sum('total'),count=Count('id')).order_by('day'))
        alerts=list(ProductVariant.objects.filter(status='en_stock',stock_count__lte=3).select_related('product','phone_model').values('id','product__name','stock_count','phone_model__name')[:30])
        return Response({'daily':daily,'low_stock':alerts,'day':rollup(1),'week':rollup(7),'month':rollup(30),
                         'by_source':list(all_orders.values('source').annotate(count=Count('id'))),
                         'by_status':list(all_orders.values('status').annotate(count=Count('id'))),
                         'pending_payment':all_orders.exclude(payment_status='verifie').count(),
                         'recent':OrderSerializer(all_orders[:6],many=True).data})

class WhoAmIView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):return Response({'id':request.user.id,'email':request.user.email,'name':request.user.first_name,'is_staff':request.user.is_staff,'has_avatar':CustomerProfile.objects.filter(user=request.user).exclude(avatar='').exists()})
    def patch(self,request):
        name=str(request.data.get('name',request.user.first_name)).strip()
        if len(name)>100:raise ValidationError({'name':'Nom trop long.'})
        request.user.first_name=name;request.user.save(update_fields=['first_name'])
        return self.get(request)



class MyAvatarView(APIView):
    """Avatar privé : ne pas exposer l'image utilisateur via /media/ public."""
    permission_classes=[IsAuthenticated]
    parser_classes=[MultiPartParser,FormParser]
    def get(self,request):
        profile=CustomerProfile.objects.filter(user=request.user).first()
        if not profile or not profile.avatar:raise NotFound('Photo non définie.')
        response=FileResponse(profile.avatar.open('rb'),content_type='image/webp')
        response['Cache-Control']='private, no-store'
        response['X-Content-Type-Options']='nosniff'
        return response
    def post(self,request):
        file=request.FILES.get('avatar')
        if not file or file.size>3*1024*1024:raise ValidationError({'avatar':'Image de 3 Mo maximum requise.'})
        try:
            image=Image.open(file);image.verify();file.seek(0)
            image=ImageOps.exif_transpose(Image.open(file))
            if image.width*image.height>12_000_000:raise ValidationError({'avatar':'Image trop grande.'})
            image=ImageOps.fit(image.convert('RGB'),(320,320),method=Image.Resampling.LANCZOS)
            output=io.BytesIO();image.save(output,'WEBP',quality=82,method=5)
        except (OSError,UnidentifiedImageError,ValueError,Image.DecompressionBombError):
            raise ValidationError({'avatar':'Format image invalide.'})
        profile,_=CustomerProfile.objects.get_or_create(user=request.user)
        old=profile.avatar.name if profile.avatar else None
        profile.avatar.save('avatar.webp',ContentFile(output.getvalue()),save=True)
        if old and old!=profile.avatar.name:profile.avatar.storage.delete(old)
        return Response({'has_avatar':True})
    def delete(self,request):
        profile=CustomerProfile.objects.filter(user=request.user).first()
        if profile and profile.avatar:
            name=profile.avatar.name;profile.avatar='';profile.save(update_fields=['avatar']);profile.avatar.storage.delete(name)
        return Response({'has_avatar':False})

class PublicReviewsView(generics.ListAPIView):
    permission_classes=[AllowAny]
    serializer_class=ReviewSerializer
    def get_queryset(self):return Review.objects.filter(approved=True,order_item__order__status='livree')


class PasswordResetRequestView(APIView):
    permission_classes=[AllowAny]
    throttle_classes=[ScopedRateThrottle]
    throttle_scope='auth'
    def post(self,request):
        email=str(request.data.get('email','')).strip().lower()
        user=User.objects.filter(email__iexact=email,is_active=True).first()
        if user:
            uid=urlsafe_base64_encode(force_bytes(user.pk))
            token=default_token_generator.make_token(user)
            # FRONTEND_ORIGIN must be configured to the real customer-facing site.
            base=settings.FRONTEND_ORIGIN.rstrip('/')
            url=f'{base}/reinitialiser?uid={uid}&token={token}'
            from .tasks import queue_email
            queue_email('NEW ARRIVALS — Réinitialisation du mot de passe',
                f'Pour modifier votre mot de passe, ouvrez ce lien : {url}\nSi vous ne l’avez pas demandé, ignorez ce message.',[user.email])
        return Response({'detail':'Si un compte existe, un e-mail sera envoyé.'})

class PasswordResetConfirmView(APIView):
    permission_classes=[AllowAny]
    throttle_classes=[ScopedRateThrottle]
    throttle_scope='auth'
    def post(self,request):
        try:user=User.objects.get(pk=urlsafe_base64_decode(request.data.get('uid','')).decode())
        except (User.DoesNotExist,TypeError,ValueError,UnicodeError,OverflowError):raise ValidationError({'token':'Lien invalide.'})
        if not default_token_generator.check_token(user,str(request.data.get('token',''))):
            raise ValidationError({'token':'Lien invalide ou expiré.'})
        password=request.data.get('password','')
        from django.contrib.auth.password_validation import validate_password
        validate_password(password,user)
        user.set_password(password);user.save(update_fields=['password'])
        return Response({'detail':'Mot de passe modifié.'})

class WishlistView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        ids=Wishlist.objects.filter(user=request.user).values_list('product_id',flat=True)
        return Response(ProductSerializer(Product.objects.filter(pk__in=ids,active=True).prefetch_related('variants__phone_model','images').select_related('category'),many=True).data)
    def post(self,request):
        product=Product.objects.filter(pk=request.data.get('product_id'),active=True).first()
        if not product:raise NotFound('Produit introuvable')
        Wishlist.objects.get_or_create(user=request.user,product=product)
        return Response({'saved':True},status=201)
    def delete(self,request):
        Wishlist.objects.filter(user=request.user,product_id=request.data.get('product_id')).delete()
        return Response(status=204)

class CartView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):return Response(SavedCart.objects.get_or_create(user=request.user)[0].items)
    def put(self,request):
        rows=request.data.get('items',[])
        if not isinstance(rows,list) or len(rows)>50:raise ValidationError({'items':'Panier invalide.'})
        cleaned=[]
        for row in rows:
            if not isinstance(row,dict):raise ValidationError({'items':'Ligne invalide.'})
            try:
                product_id=int(row['product_id']);qty=int(row['quantity'])
                variant_id=int(row['variant_id']) if row.get('variant_id') else None
            except (KeyError,TypeError,ValueError):raise ValidationError({'items':'Produit invalide.'})
            if qty<1 or qty>20:raise ValidationError({'items':'Quantité invalide.'})
            product=Product.objects.filter(id=product_id,active=True).first()
            if not product or not product.price_confirmed:continue
            variant=ProductVariant.objects.filter(pk=variant_id,product=product).select_related('phone_model').first() if variant_id else None
            if product.kind!='accessoire' and not variant:continue
            cleaned.append({'key':str(row.get('key',''))[:120], 'product_id':product_id,'variant_id':variant_id,
                'name':product.name,'price':product.price,'image':product.cover_url,'phone':variant.phone_model.name if variant and variant.phone_model else '',
                'color':variant.color if variant else '', 'quantity':qty,
                'artwork_token':str(row.get('artwork_token') or '')[:40] or None})
        cart,_=SavedCart.objects.update_or_create(user=request.user,defaults={'items':cleaned})
        return Response(cart.items)

class CustomerAddressViewSet(viewsets.ModelViewSet):
    serializer_class=CustomerAddressSerializer
    permission_classes=[IsAuthenticated]
    pagination_class=None
    def get_queryset(self):return CustomerAddress.objects.filter(user=self.request.user)
    def perform_create(self,serializer):serializer.save(user=self.request.user)

class BannerViewSet(viewsets.ModelViewSet):
    serializer_class=BannerSerializer
    pagination_class=None
    def get_permissions(self):return [AllowAny()] if self.action=='list' else [IsAdminUser()]
    def get_queryset(self):
        qs=Banner.objects.all().order_by('-id')
        if not (self.request.user and self.request.user.is_staff):
            now=timezone.now();qs=qs.filter(active=True).filter(Q(starts_at__lte=now)|Q(starts_at__isnull=True)).filter(Q(ends_at__gte=now)|Q(ends_at__isnull=True))
        return qs

class ReviewAdminViewSet(viewsets.ModelViewSet):
    queryset=Review.objects.select_related('product','order_item')
    serializer_class=ReviewSerializer
    permission_classes=[IsAdminUser]
    pagination_class=None
    def partial_update(self,request,*args,**kwargs):
        review=self.get_object()
        if 'approved' in request.data:review.approved=bool(request.data['approved']);review.save(update_fields=['approved'])
        return Response({**ReviewSerializer(review).data,'approved':review.approved})
    def list(self,request,*args,**kwargs):
        return Response([{**ReviewSerializer(r).data,'approved':r.approved} for r in self.get_queryset()[:200]])

class ReviewSubmissionView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request):
        try: item=OrderItem.objects.select_related('order').get(pk=request.data.get('order_item_id'),order__user=request.user,order__status='livree')
        except OrderItem.DoesNotExist:raise ValidationError('Vous pouvez évaluer uniquement une commande livrée de votre compte.')
        if Review.objects.filter(order_item=item).exists():raise ValidationError('Ce produit a déjà été évalué.')
        try:rating=int(request.data.get('rating',0))
        except (TypeError,ValueError):rating=0
        if not 1<=rating<=5:raise ValidationError({'rating':'Note de 1 à 5 requise.'})
        obj=Review.objects.create(product=item.product,order_item=item,display_name=request.user.first_name or 'Client',rating=rating,body=str(request.data.get('body',''))[:2000])
        return Response(ReviewSerializer(obj).data,status=201)

class AdminCustomersView(APIView):
    permission_classes=[IsAdminUser]
    def get(self,request):
        users=list(User.objects.filter(is_staff=False).values('id','first_name','email','is_active','date_joined').order_by('-date_joined')[:200])
        guests=list(Order.objects.exclude(customer_phone='').values('customer_name','customer_phone','customer_email').annotate(orders=Count('id')).order_by('-orders')[:200])
        return Response({'users':users,'customers':guests})
    def patch(self,request):
        user=User.objects.filter(pk=request.data.get('user_id'),is_staff=False).first()
        if not user:raise NotFound('Client introuvable')
        if not isinstance(request.data.get('is_active'),bool):raise ValidationError({'is_active':'Booléen requis.'})
        user.is_active=request.data['is_active'];user.save(update_fields=['is_active'])
        return Response({'id':user.id,'is_active':user.is_active})

class StockMovementView(generics.ListAPIView):
    permission_classes=[IsAdminUser]
    def get(self,request):
        qs=StockMovement.objects.select_related('variant__product','order').order_by('-created_at')[:150]
        return Response([{'id':m.id,'product':m.variant.product.name,'variant':str(m.variant),'delta':m.delta,'reason':m.reason,'order':m.order.reference if m.order_id else None,'created_at':m.created_at} for m in qs])

class InvoiceView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request,pk):
        order=Order.objects.prefetch_related('items').filter(pk=pk).first()
        if not order or not (request.user.is_staff or order.user_id==request.user.pk):raise NotFound('Facture introuvable')
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.utils import simpleSplit
        buff=io.BytesIO();pdf=canvas.Canvas(buff,pagesize=A4)
        pdf.setTitle(f'NEW ARRIVALS - {order.reference}')
        y=800
        def row(label,value,size=10):
            nonlocal y
            pdf.setFont('Helvetica',size)
            for line in simpleSplit(f'{label}: {value}', 'Helvetica',size,500):
                if y<60:pdf.showPage();y=800
                pdf.drawString(45,y,line);y-=17
        row('NEW ARRIVALS','Releve de commande / facture',16);y-=15
        for label,value in [('Reference',order.reference),('Client',order.customer_name),('Telephone',order.customer_phone),('Date',order.created_at.strftime('%d/%m/%Y')),('Zone',order.zone),('Adresse',order.address)]:row(label,value)
        y-=20
        for item in order.items.all():row(item.product_name,f'{item.quantity} x {item.unit_price} Ar = {item.line_total} Ar')
        y-=12;row('Total produits',f'{order.total} Ar');row('Paiement verifie',f'{order.paid_amount} Ar')
        row('Reste a payer',f'{max(0,order.total-order.paid_amount)} Ar')
        row('Statut',order.get_status_display())
        y-=15;row('Note','Document de commande; le statut du paiement doit etre verifie.')
        pdf.showPage();pdf.save();buff.seek(0)
        response=FileResponse(buff,content_type='application/pdf',as_attachment=True,filename=f'{order.reference}.pdf')
        response['Cache-Control']='private, no-store'
        return response
