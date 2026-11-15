from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from shop.models import Category,Product,ProductVariant,PhoneModel,Order

class StoreOrderTests(APITestCase):
    def setUp(self):
        cat=Category.objects.create(name='Housses simples',slug='simple')
        self.product=Product.objects.create(name='Housse test',slug='housse-test',category=cat,price=35000,on_order=True)
        phone=PhoneModel.objects.create(brand='Xiaomi',name='Redmi Note Test')
        self.variant=ProductVariant.objects.create(product=self.product,phone_model=phone)
        self.payload={'customer_name':'Client test','customer_phone':'0340000000',
            'address':'Quartier test','city':'Antananarivo','zone':'tana',
            'payment_method':'mvola','transaction_reference':'REF-TEST-123',
            'items':[{'product_id':self.product.id,'variant_id':self.variant.id,'quantity':2}]}

    def test_real_order_and_manual_payment_confirmation(self):
        r=self.client.post('/api/v1/orders/',self.payload,format='json')
        self.assertEqual(r.status_code,201,r.data)
        self.assertEqual(r.data['total'],70000)
        self.assertEqual(r.data['required_payment'],35000)
        self.assertEqual(r.data['payment_status'],'declare')
        self.assertEqual(r.data['status'],'attente_acompte')
        tracking=r.data['tracking_token']
        self.assertEqual(self.client.get(f'/api/v1/track/{tracking}/').status_code,200)
        self.assertEqual(self.client.get('/api/v1/orders/').status_code,401)

        # Un utilisateur authentifié non administrateur doit être refusé.
        regular_user = User.objects.create_user(
            username='client@test.test',
            password='client-test-password'
        )
        self.client.force_authenticate(regular_user)

        self.assertEqual(
            self.client.get('/api/v1/orders/').status_code,
            403
        )

        # Réinitialiser l'authentification avant le test administrateur.
        self.client.force_authenticate(user=None)

        staff=User.objects.create_user(username='admin@test.test',password='strong-pass',is_staff=True)
        self.client.force_authenticate(staff)
        order=Order.objects.get(reference=r.data['reference'])
        confirm=self.client.patch(f'/api/v1/orders/{order.id}/manage/',{'payment_status':'verifie'},format='json')
        self.assertEqual(confirm.status_code,200,confirm.data)
        self.assertEqual(confirm.data['status'],'acompte_recu')
        self.assertEqual(confirm.data['paid_amount'],35000)

    def test_province_requires_full_payment(self):
        data={**self.payload,'zone':'province'}
        r=self.client.post('/api/v1/orders/',data,format='json')
        self.assertEqual(r.status_code,201,r.data)
        self.assertEqual(r.data['required_payment'],70000)

    def test_browser_cannot_set_its_own_price(self):
        data={**self.payload,'items':[{**self.payload['items'][0],'negotiated_unit_price':1}]}
        r=self.client.post('/api/v1/orders/',data,format='json')
        self.assertEqual(r.status_code,400)

    def test_ref_is_not_proof_of_payment(self):
        r=self.client.post('/api/v1/orders/',self.payload,format='json')
        self.assertEqual(r.data['paid_amount'],0)
        self.assertEqual(r.data['payment_status'],'declare')
