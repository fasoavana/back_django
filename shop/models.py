import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

class Category(models.Model):
    name = models.CharField(max_length=90)
    slug = models.SlugField(unique=True)
    order = models.PositiveSmallIntegerField(default=0)
    active = models.BooleanField(default=True)
    def __str__(self): return self.name
    class Meta: ordering = ['order','name']

class PhoneModel(models.Model):
    brand = models.CharField(max_length=80)
    name = models.CharField(max_length=150, unique=True)
    active = models.BooleanField(default=True)
    def __str__(self): return self.name
    class Meta: ordering = ['brand','name']

class Product(models.Model):
    KINDS = [('simple','Simple'), ('iphone','iPhone'), ('bracelet','Bracelet / cordon'),
             ('diamant','Cristaux / diamant'), ('blinde','Blindée'), ('luxe','Luxe'),
             ('personnalisee','Personnalisée'), ('accessoire','Accessoire'), ('non_classe','À classer')]
    name = models.CharField(max_length=180)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    kind = models.CharField(max_length=25, choices=KINDS, default='simple')
    price = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    cover_url = models.CharField(max_length=500, blank=True)
    active = models.BooleanField(default=True)
    is_new = models.BooleanField(default=True)
    is_bestseller = models.BooleanField(default=False)
    on_order = models.BooleanField(default=True)
    price_confirmed = models.BooleanField(default=True, help_text="False: photo visible, commande désactivée tant que le prix n’est pas validé.")
    customizable = models.BooleanField(default=False)
    source_ref = models.CharField(max_length=70, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):return self.name
    class Meta: ordering = ['-created_at','id']

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='catalog/')
    order = models.PositiveSmallIntegerField(default=0)
    class Meta: ordering = ['order','id']
    def save(self,*args,**kwargs):
        # The same optimization applies to Django Admin inline uploads and the React admin panel.
        if self.image and not self.image._committed:
            from .media_utils import optimize_image
            self.image = optimize_image(self.image)
        result = super().save(*args,**kwargs)
        # First uploaded image becomes the card image when the product has no cover.
        if self.image and self.product_id and not self.product.cover_url:
            url=settings.MEDIA_URL + self.image.name
            Product.objects.filter(pk=self.product_id,cover_url='').update(cover_url=url)
            self.product.cover_url=url
        return result

class ProductVariant(models.Model):
    STATUS_CHOICES = [('sur_commande','Sur commande'),('en_stock','En stock'),('indisponible','Indisponible')]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    phone_model = models.ForeignKey(PhoneModel, on_delete=models.PROTECT, null=True, blank=True)
    color = models.CharField(max_length=50, default='Selon photo')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='sur_commande')
    stock_count = models.PositiveIntegerField(default=0)
    class Meta: constraints = [models.UniqueConstraint(fields=['product','phone_model','color'],name='unique_phone_color_variant')]
    def __str__(self):return f'{self.product} — {self.phone_model or "Sans téléphone"}'

class CustomerArtwork(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    image = models.ImageField(upload_to='private/artworks/%Y/%m/')
    created_at = models.DateTimeField(auto_now_add=True)
    consumed = models.BooleanField(default=False)
    def __str__(self):return str(self.token)

class Order(models.Model):
    SOURCES = [('web','Site web'),('facebook','Facebook')]
    ZONES = [('tana','Antananarivo'),('province','Province')]
    STATUS_CHOICES = [('attente_acompte','En attente du paiement'),('acompte_recu','Paiement confirmé'),
              ('preparation','En préparation'),('prete','Prête'),('expediee','Expédiée'),
              ('livree','Livrée'),('annulee','Annulée')]
    PAYMENTS = [('en_attente','En attente'),('declare','Déclaré par le client'),('verifie','Vérifié'),('rejete','Rejeté')]
    METHODS = [('orange','Orange Money'),('mvola','MVola')]
    reference = models.CharField(max_length=24, unique=True, editable=False)
    tracking_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    source = models.CharField(max_length=10, choices=SOURCES, default='web')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    customer_name = models.CharField(max_length=130)
    customer_phone = models.CharField(max_length=30)
    customer_email = models.EmailField(blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    zone = models.CharField(max_length=12, choices=ZONES, default='tana')
    total = models.PositiveIntegerField()
    required_payment = models.PositiveIntegerField()
    paid_amount = models.PositiveIntegerField(default=0)
    payment_method = models.CharField(max_length=12, choices=METHODS)
    payment_phone = models.CharField(max_length=30, blank=True)
    transaction_reference = models.CharField(max_length=120, blank=True)
    payment_status = models.CharField(max_length=12, choices=PAYMENTS, default='en_attente')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='attente_acompte')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: ordering = ['-created_at']
    def save(self,*args,**kwargs):
        if not self.reference: self.reference = 'NA-' + uuid.uuid4().hex[:10].upper()
        super().save(*args,**kwargs)
    def __str__(self):return self.reference

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, null=True, on_delete=models.SET_NULL)
    variant = models.ForeignKey(ProductVariant, null=True, on_delete=models.SET_NULL)
    product_name = models.CharField(max_length=180)
    phone_model_name = models.CharField(max_length=150, blank=True)
    color = models.CharField(max_length=50, blank=True)
    unit_price = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(20)])
    artwork = models.ForeignKey(CustomerArtwork, null=True, blank=True, on_delete=models.PROTECT)
    @property
    def line_total(self):return self.unit_price*self.quantity

class StockMovement(models.Model):
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, related_name='movements')
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL)
    delta = models.IntegerField()
    reason = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

class Review(models.Model):
    product = models.ForeignKey(Product,on_delete=models.CASCADE,related_name='reviews')
    order_item = models.OneToOneField(OrderItem,on_delete=models.PROTECT, related_name='review')
    display_name = models.CharField(max_length=70)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    body = models.TextField(max_length=2000)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class SiteConfig(models.Model):
    site_name = models.CharField(max_length=100, default='NEW ARRIVALS')
    orange_number = models.CharField(max_length=25, default='0375578480')
    mvola_number = models.CharField(max_length=25, default='0348595149')
    min_delivery_days = models.PositiveSmallIntegerField(default=9)
    max_delivery_days = models.PositiveSmallIntegerField(default=15)
    hero_title = models.CharField(max_length=200, default='Chaque arrivée, une nouvelle envie.')
    hero_subtitle = models.CharField(max_length=350, default='Des housses qui vous ressemblent. Commandez partout à Madagascar.')
    legal_business_name = models.CharField(max_length=180, blank=True)
    legal_address = models.TextField(blank=True)
    legal_registration = models.CharField(max_length=180, blank=True)
    hosting_provider = models.CharField(max_length=250, blank=True)
    legal_contact_phone = models.CharField(max_length=30, blank=True)
    legal_contact_email = models.EmailField(blank=True)
    privacy_contact_email = models.EmailField(blank=True)
    legal_updated_at = models.DateField(null=True, blank=True)
    data_retention_months = models.PositiveSmallIntegerField(default=24)
    def save(self,*args,**kwargs):self.pk=1;super().save(*args,**kwargs)
    @classmethod
    def current(cls):return cls.objects.get_or_create(pk=1)[0]

class Banner(models.Model):
    title = models.CharField(max_length=150)
    subtitle = models.CharField(max_length=200, blank=True)
    url = models.CharField(max_length=300, default='/boutique')
    active = models.BooleanField(default=False)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)


class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist_entries')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'product'], name='unique_wishlist_user_product')]

class SavedCart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_cart')
    items = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)

class CustomerAddress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_addresses')
    label = models.CharField(max_length=50, default='Domicile')
    address = models.CharField(max_length=500)
    city = models.CharField(max_length=100)
    zone = models.CharField(max_length=12, choices=Order.ZONES, default='tana')
    phone = models.CharField(max_length=30)
    is_default = models.BooleanField(default=False)


class CustomerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='new_arrivals_profile')
    avatar = models.ImageField(upload_to='private/avatars/%Y/%m/',blank=True)
    def __str__(self):return str(self.user_id)
