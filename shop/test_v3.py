"""Régressions V3 (exécuter: python manage.py test shop.test_v3)."""
from io import BytesIO
from tempfile import TemporaryDirectory
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from PIL import Image
from .models import Category,PhoneModel,Product,ProductVariant

class CatalogueSecurityTests(TestCase):
    def setUp(self):
        cat=Category.objects.create(slug='a-classer',name='À classer')
        self.product=Product.objects.create(name='Housse test <img>',slug='housse-test',category=cat,price=35000,price_confirmed=False,kind='non_classe',active=True)
        self.phone=PhoneModel.objects.create(brand='Test',name='Test Phone 1')
        self.variant=ProductVariant.objects.create(product=self.product,phone_model=self.phone,color='Selon photo')
        self.client=APIClient()

    def test_unconfirmed_product_is_visible_but_not_orderable(self):
        response=self.client.get('/api/v1/products/housse-test/')
        self.assertEqual(response.status_code,200)
        self.assertFalse(response.data['price_confirmed'])
        payload={'customer_name':'Client test','customer_phone':'0340000000','address':'Quartier','city':'Tana','zone':'tana',
                 'payment_method':'mvola','transaction_reference':'FAKE-REF-FOR-TEST','items':[{'product_id':self.product.pk,'variant_id':self.variant.pk,'quantity':1}]}
        response=self.client.post('/api/v1/orders/',payload,format='json')
        self.assertEqual(response.status_code,400)
        self.assertIn('Prix non confirmé',str(response.data))

    @override_settings(FRONTEND_ORIGIN='https://newarrivals.example')
    def test_crawler_html_has_server_rendered_escaped_og_tags(self):
        response=self.client.get('/produit/housse-test',HTTP_USER_AGENT='facebookexternalhit/1.1')
        self.assertEqual(response.status_code,200)
        page=response.content.decode('utf-8')
        self.assertIn('property="og:image"',page)
        self.assertIn('https://newarrivals.example/produit/housse-test',page)
        self.assertNotIn('<img>',page)
        self.assertIn('&lt;img&gt;',page)

    @override_settings(FRONTEND_ORIGIN='https://newarrivals.example')
    def test_dynamic_robots_sitemap(self):
        response=self.client.get('/robots.txt')
        self.assertEqual(response.status_code,200)
        self.assertIn('https://newarrivals.example/sitemap.xml',response.content.decode())

class AvatarSecurityTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='avataruser',email='avatar@example.invalid',password='Not-the-actual-secret-123')
        self.client=APIClient()

    def test_avatar_requires_authentication(self):
        self.assertIn(self.client.get('/api/v1/auth/avatar/').status_code,[401,403])

    def test_avatar_upload_and_private_read(self):
        with TemporaryDirectory() as directory,override_settings(MEDIA_ROOT=directory):
            self.client.force_authenticate(user=self.user)
            image=Image.new('RGB',(400,500),(210,180,150));stream=BytesIO();image.save(stream,'JPEG')
            data=SimpleUploadedFile('avatar.jpg',stream.getvalue(),content_type='image/jpeg')
            response=self.client.post('/api/v1/auth/avatar/',{'avatar':data},format='multipart')
            self.assertEqual(response.status_code,200,response.data)
            response=self.client.get('/api/v1/auth/avatar/')
            self.assertEqual(response.status_code,200)
            self.assertEqual(response['Cache-Control'],'private, no-store')
            self.assertTrue(b''.join(response.streaming_content).startswith(b'RIFF'))
            response=self.client.delete('/api/v1/auth/avatar/')
            self.assertEqual(response.status_code,200)
