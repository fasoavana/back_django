"""Regression tests for v2 capabilities; run with: python manage.py test shop"""
from django.contrib.auth.models import User
from django.core import mail
from django.test import override_settings
from rest_framework.test import APITestCase
from shop.models import Category, PhoneModel, Product, ProductVariant, Order, Wishlist, SavedCart, Banner


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class NewArrivalsFeatureTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='client@example.test', email='client@example.test', password='strong-client-password-123', first_name='Client')
        self.staff = User.objects.create_superuser(username='admin@example.test', email='admin@example.test', password='strong-admin-password-123')
        self.category = Category.objects.create(name='Housses', slug='housses')
        self.phone = PhoneModel.objects.create(name='Samsung Galaxy A15', brand='Samsung')
        self.product = Product.objects.create(name='Housse personnalisée — effet verre',slug='personnalisee-effet-verre-test',price=36000,
            category=self.category, kind='personnalisee',customizable=True)
        self.variant = ProductVariant.objects.create(product=self.product,phone_model=self.phone,color='Noir brillant')

    def test_wishlist_requires_authentication_and_saves_product(self):
        self.assertEqual(self.client.get('/api/v1/wishlist/').status_code, 401)
        self.client.force_authenticate(self.user)
        r = self.client.post('/api/v1/wishlist/',{'product_id':self.product.id}, format='json')
        self.assertEqual(r.status_code, 201,r.data)
        self.assertTrue(Wishlist.objects.filter(user=self.user,product=self.product).exists())
        self.assertEqual(len(self.client.get('/api/v1/wishlist/').data),1)
        self.assertEqual(self.client.delete('/api/v1/wishlist/',{'product_id':self.product.id}, format='json').status_code,204)

    def test_saved_cart_recalculates_server_price_and_cannot_inject_other_data(self):
        self.client.force_authenticate(self.user)
        payload={'items':[{'key':'line-1','product_id':self.product.id,'variant_id':self.variant.id,'quantity':2,
            'name':'faux','price':1,'image':'https://example.invalid'}]}
        r=self.client.put('/api/v1/cart/',payload,format='json')
        self.assertEqual(r.status_code,200,r.data)
        self.assertEqual(r.data[0]['price'],36000)
        self.assertEqual(r.data[0]['name'],self.product.name)
        self.assertEqual(SavedCart.objects.get(user=self.user).items[0]['quantity'],2)

    def test_advanced_product_filters(self):
        r=self.client.get('/api/v1/products/?color=Noir&phone=Galaxy%20A15&min_price=35000&max_price=50000')
        self.assertEqual(r.status_code,200,r.data)
        self.assertEqual(r.data['count'],1)
        r=self.client.get('/api/v1/products/?color=Rose')
        self.assertEqual(r.data['count'],0)

    def test_staff_only_controls_banners_and_duplicates_products(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post('/api/v1/banners/',{'title':'Promotion'},format='json').status_code,403)
        self.assertEqual(self.client.post(f'/api/v1/products/{self.product.slug}/duplicate/',format='json').status_code,403)
        self.client.force_authenticate(self.staff)
        banner=self.client.post('/api/v1/banners/',{'title':'Promotion','active':True,'url':'/boutique'},format='json')
        self.assertEqual(banner.status_code,201,banner.data)
        duplicated=self.client.post(f'/api/v1/products/{self.product.slug}/duplicate/',format='json')
        self.assertEqual(duplicated.status_code,201,duplicated.data)
        self.assertFalse(duplicated.data['active'])
        self.assertNotEqual(duplicated.data['slug'],self.product.slug)

    def test_profile_and_addresses(self):
        self.client.force_authenticate(self.user)
        r=self.client.patch('/api/v1/auth/me/',{'name':'Nouvelle cliente'},format='json')
        self.assertEqual(r.status_code,200,r.data)
        self.assertEqual(r.data['name'],'Nouvelle cliente')
        address=self.client.post('/api/v1/addresses/',{'label':'Maison','address':'67 Sud','city':'Antananarivo','zone':'tana','phone':'0340000000'},format='json')
        self.assertEqual(address.status_code,201,address.data)
        self.assertEqual(len(self.client.get('/api/v1/addresses/').data),1)

    def test_password_reset_does_not_disclose_existing_accounts(self):
        # Empty/non-existent emails receive identical public response.
        a=self.client.post('/api/v1/auth/password-reset/',{'email':'nobody@example.test'},format='json')
        b=self.client.post('/api/v1/auth/password-reset/',{'email':self.user.email},format='json')
        self.assertEqual(a.status_code,200)
        self.assertEqual(b.status_code,200)
        self.assertEqual(a.data,b.data)
        self.assertEqual(self.client.post('/api/v1/auth/password-reset/confirm/',{'uid':'no','token':'incorrect','password':'anypass'},format='json').status_code,400)

    def test_invoice_only_owner_and_staff_can_download(self):
        simple=Product.objects.create(name='Housse simple test',slug='housse-simple-pdf-test',price=35000,
            category=self.category,kind='simple')
        variant=ProductVariant.objects.create(product=simple,phone_model=self.phone,color='Noir')
        payload={'customer_name':'Client PDF','customer_phone':'0340000000','address':'Quartier',
            'city':'Antananarivo','zone':'tana','payment_method':'orange','transaction_reference':'test-pdf-transaction',
            'items':[{'product_id':simple.id,'variant_id':variant.id,'quantity':1}]}
        self.client.force_authenticate(self.user)
        r=self.client.post('/api/v1/orders/',payload,format='json')
        self.assertEqual(r.status_code,201,r.data)
        order_id=r.data['id']
        doc=self.client.get(f'/api/v1/orders/{order_id}/invoice/')
        self.assertEqual(doc.status_code,200)
        self.assertIn('application/pdf',doc['Content-Type'])
        stranger=User.objects.create_user(username='other@example.test',password='other-password-123')
        self.client.force_authenticate(stranger)
        self.assertEqual(self.client.get(f'/api/v1/orders/{order_id}/invoice/').status_code,404)
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get(f'/api/v1/orders/{order_id}/invoice/').status_code,200)

    def test_photo_upload_webp_and_reorder_staff_only(self):
        import io,tempfile
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings
        from shop.models import ProductImage
        self.client.force_authenticate(self.staff)
        buff=io.BytesIO();Image.new('RGB',(64,96),'blue').save(buff,format='PNG')
        with tempfile.TemporaryDirectory() as folder, override_settings(MEDIA_ROOT=folder):
            upload=SimpleUploadedFile('coque.png',buff.getvalue(),content_type='image/png')
            r=self.client.post('/api/v1/admin/product-images/',{'product':self.product.pk,'image':upload,'order':'0'},format='multipart')
            self.assertEqual(r.status_code,201,r.data)
            img=ProductImage.objects.get(pk=r.data['id'])
            self.assertTrue(img.image.name.endswith('.webp'),img.image.name)
            move=self.client.post('/api/v1/admin/product-images/reorder/',{'product':self.product.pk,'ids':[img.id]},format='json')
            self.assertEqual(move.status_code,200,move.data)
