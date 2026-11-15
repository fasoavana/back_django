from rest_framework import serializers
from .models import Category,PhoneModel,Product,ProductImage,ProductVariant,Order,OrderItem,Review,SiteConfig,Wishlist,CustomerAddress,Banner

class CategorySerializer(serializers.ModelSerializer):
    class Meta: model=Category;fields=['id','name','slug']

class PhoneModelSerializer(serializers.ModelSerializer):
    class Meta: model=PhoneModel;fields=['id','brand','name']

class VariantSerializer(serializers.ModelSerializer):
    phone_model_name=serializers.CharField(source='phone_model.name',read_only=True,default='')
    class Meta: model=ProductVariant;fields=['id','product','phone_model','phone_model_name','color','status','stock_count']

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta: model=ProductImage;fields=['id','product','image','order']

class ProductSerializer(serializers.ModelSerializer):
    category_name=serializers.CharField(source='category.name',read_only=True)
    variants=VariantSerializer(many=True,read_only=True)
    images=ProductImageSerializer(many=True,read_only=True)
    class Meta:
        model=Product
        fields=['id','name','slug','description','category','category_name','kind','price','cover_url',
                'active','is_new','is_bestseller','on_order','price_confirmed','customizable','source_ref','variants','images']
        read_only_fields=['source_ref']

class OrderItemInputSerializer(serializers.Serializer):
    product_id=serializers.IntegerField(min_value=1)
    variant_id=serializers.IntegerField(required=False,allow_null=True)
    quantity=serializers.IntegerField(min_value=1,max_value=20)
    color=serializers.CharField(required=False,allow_blank=True,max_length=50)
    artwork_token=serializers.UUIDField(required=False)
    negotiated_unit_price=serializers.IntegerField(required=False,min_value=1)

class OrderCreateSerializer(serializers.Serializer):
    customer_name=serializers.CharField(max_length=130)
    customer_phone=serializers.CharField(max_length=30)
    customer_email=serializers.EmailField(required=False,allow_blank=True)
    address=serializers.CharField(max_length=500)
    city=serializers.CharField(max_length=100)
    zone=serializers.ChoiceField(choices=['tana','province'])
    payment_method=serializers.ChoiceField(choices=['orange','mvola'])
    transaction_reference=serializers.CharField(max_length=120,required=False,allow_blank=True)
    payment_phone=serializers.CharField(max_length=30,required=False,allow_blank=True)
    notes=serializers.CharField(max_length=1000,required=False,allow_blank=True)
    source=serializers.ChoiceField(choices=['web','facebook'],default='web')
    paid_amount=serializers.IntegerField(required=False,min_value=0)
    items=OrderItemInputSerializer(many=True)
    def validate(self,attrs):
        staff=self.context['request'].user.is_staff
        if attrs.get('source')=='facebook' and not staff:
            raise serializers.ValidationError('Canal Facebook réservé à l’administration.')
        if not attrs.get('items') or len(attrs['items'])>25:
            raise serializers.ValidationError('Entre 1 et 25 lignes de commande requises.')
        if not staff and not attrs.get('transaction_reference','').strip():
            raise serializers.ValidationError({'transaction_reference':'Saisissez une référence de paiement. La vérification sera manuelle.'})
        if not staff and any('negotiated_unit_price' in x for x in attrs['items']):
            raise serializers.ValidationError('Les prix doivent être calculés par le serveur.')
        return attrs

class OrderItemSerializer(serializers.ModelSerializer):
    has_artwork=serializers.SerializerMethodField()
    class Meta:model=OrderItem;fields=['id','product_name','phone_model_name','color','unit_price','quantity','has_artwork']
    def get_has_artwork(self,obj):return bool(obj.artwork_id)

class OrderSerializer(serializers.ModelSerializer):
    items=OrderItemSerializer(many=True,read_only=True)
    remaining=serializers.SerializerMethodField()
    class Meta:
        model=Order
        fields=['id','reference','tracking_token','source','customer_name','customer_phone','customer_email',
                'address','city','zone','total','required_payment','paid_amount','remaining','payment_method',
                'payment_phone','transaction_reference','payment_status','status','notes','created_at','updated_at','items']
    def get_remaining(self,obj):return max(0,obj.total-obj.paid_amount)

class PublicTrackSerializer(serializers.ModelSerializer):
    items=OrderItemSerializer(many=True,read_only=True)
    remaining=serializers.SerializerMethodField()
    class Meta:
        model=Order; fields=['reference','status','payment_status','created_at','updated_at','total','required_payment','paid_amount','remaining','zone','items']
    def get_remaining(self,obj):return max(0,obj.total-obj.paid_amount)

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:model=Review;fields=['id','product','display_name','rating','body','created_at']

class SiteConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model=SiteConfig
        fields=['site_name','orange_number','mvola_number','min_delivery_days','max_delivery_days','hero_title','hero_subtitle','legal_business_name','legal_address', 'legal_registration', 'hosting_provider', 'legal_contact_phone', 'legal_contact_email', 'privacy_contact_email', 'legal_updated_at', 'data_retention_months']


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ['id','title','subtitle','url','active','starts_at','ends_at']

class CustomerAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAddress
        fields = ['id','label','address','city','zone','phone','is_default']
