# Migration initiale de NEW ARRIVALS. Créée pour exécuter migrate sans makemigrations au démarrage.
import uuid
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):
    initial=True
    dependencies=[migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
        migrations.CreateModel(name='Category',fields=[
            ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
            ('name',models.CharField(max_length=90)),('slug',models.SlugField(unique=True)),
            ('order',models.PositiveSmallIntegerField(default=0)),('active',models.BooleanField(default=True)),
        ],options={'ordering':['order','name']}),
        migrations.CreateModel(name='PhoneModel',fields=[
            ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
            ('brand',models.CharField(max_length=80)),('name',models.CharField(max_length=150,unique=True)),
            ('active',models.BooleanField(default=True)),
        ],options={'ordering':['brand','name']}),
        migrations.CreateModel(name='Product',fields=[
            ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
            ('name',models.CharField(max_length=180)),('slug',models.SlugField(unique=True)),
            ('description',models.TextField(blank=True)),
            ('kind',models.CharField(choices=[('simple','Simple'),('iphone','iPhone'),('bracelet','Bracelet / cordon'),('diamant','Cristaux / diamant'),('blinde','Blindée'),('luxe','Luxe'),('personnalisee','Personnalisée'),('accessoire','Accessoire')],default='simple',max_length=25)),
            ('price',models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
            ('cover_url',models.CharField(blank=True,max_length=500)),
            ('active',models.BooleanField(default=True)),('is_new',models.BooleanField(default=True)),
            ('is_bestseller',models.BooleanField(default=False)),('on_order',models.BooleanField(default=True)),
            ('customizable',models.BooleanField(default=False)),('source_ref',models.CharField(blank=True,max_length=70)),
            ('created_at',models.DateTimeField(auto_now_add=True)),('updated_at',models.DateTimeField(auto_now=True)),
            ('category',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='products',to='shop.category')),
        ],options={'ordering':['-created_at','id']}),
        migrations.CreateModel(name='ProductImage',fields=[
            ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
            ('image',models.ImageField(upload_to='catalog/')),('order',models.PositiveSmallIntegerField(default=0)),
            ('product',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='images',to='shop.product')),
        ],options={'ordering':['order','id']}),
        migrations.CreateModel(name='ProductVariant',fields=[
            ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
            ('color',models.CharField(default='Selon photo',max_length=50)),
            ('status',models.CharField(choices=[('sur_commande','Sur commande'),('en_stock','En stock'),('indisponible','Indisponible')],default='sur_commande',max_length=16)),
            ('stock_count',models.PositiveIntegerField(default=0)),
            ('phone_model',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,to='shop.phonemodel')),
            ('product',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='variants',to='shop.product')),
        ]),
        migrations.CreateModel(name='CustomerArtwork',fields=[
            ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
            ('token',models.UUIDField(default=uuid.uuid4,editable=False,unique=True)),
            ('image',models.ImageField(upload_to='private/artworks/%Y/%m/')),
            ('created_at',models.DateTimeField(auto_now_add=True)),('consumed',models.BooleanField(default=False)),
        ]),
        migrations.CreateModel(name='Order',fields=[
            ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
            ('reference',models.CharField(editable=False,max_length=24,unique=True)),
            ('tracking_token',models.UUIDField(default=uuid.uuid4,editable=False,unique=True)),
            ('source',models.CharField(choices=[('web','Site web'),('facebook','Facebook')],default='web',max_length=10)),
            ('customer_name',models.CharField(max_length=130)),('customer_phone',models.CharField(max_length=30)),
            ('customer_email',models.EmailField(blank=True,max_length=254)),('address',models.TextField()),
            ('city',models.CharField(max_length=100)),
            ('zone',models.CharField(choices=[('tana','Antananarivo'),('province','Province')],default='tana',max_length=12)),
            ('total',models.PositiveIntegerField()),('required_payment',models.PositiveIntegerField()),
            ('paid_amount',models.PositiveIntegerField(default=0)),
            ('payment_method',models.CharField(choices=[('orange','Orange Money'),('mvola','MVola')],max_length=12)),
            ('payment_phone',models.CharField(blank=True,max_length=30)),('transaction_reference',models.CharField(blank=True,max_length=120)),
            ('payment_status',models.CharField(choices=[('en_attente','En attente'),('declare','Déclaré par le client'),('verifie','Vérifié'),('rejete','Rejeté')],default='en_attente',max_length=12)),
            ('status',models.CharField(choices=[('attente_acompte','En attente du paiement'),('acompte_recu','Paiement confirmé'),('preparation','En préparation'),('prete','Prête'),('expediee','Expédiée'),('livree','Livrée'),('annulee','Annulée')],default='attente_acompte',max_length=20)),
            ('notes',models.TextField(blank=True)),('created_at',models.DateTimeField(auto_now_add=True)),('updated_at',models.DateTimeField(auto_now=True)),
            ('user',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,to=settings.AUTH_USER_MODEL)),
        ],options={'ordering':['-created_at']}),
        migrations.CreateModel(name='OrderItem',fields=[
            ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
            ('product_name',models.CharField(max_length=180)),('phone_model_name',models.CharField(blank=True,max_length=150)),
            ('color',models.CharField(blank=True,max_length=50)),('unit_price',models.PositiveIntegerField()),
            ('quantity',models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1),django.core.validators.MaxValueValidator(20)])),
            ('artwork',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,to='shop.customerartwork')),
            ('order',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='items',to='shop.order')),
            ('product',models.ForeignKey(null=True,on_delete=django.db.models.deletion.SET_NULL,to='shop.product')),
            ('variant',models.ForeignKey(null=True,on_delete=django.db.models.deletion.SET_NULL,to='shop.productvariant')),
        ]),
        migrations.CreateModel(name='StockMovement',fields=[
            ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
            ('delta',models.IntegerField()),('reason',models.CharField(max_length=120)),('created_at',models.DateTimeField(auto_now_add=True)),
            ('order',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,to='shop.order')),
            ('variant',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='movements',to='shop.productvariant')),
        ]),
        migrations.CreateModel(name='Review',fields=[
            ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
            ('display_name',models.CharField(max_length=70)),('rating',models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1),django.core.validators.MaxValueValidator(5)])),
            ('body',models.TextField(max_length=2000)),('approved',models.BooleanField(default=False)),('created_at',models.DateTimeField(auto_now_add=True)),
            ('order_item',models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,related_name='review',to='shop.orderitem')),
            ('product',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='reviews',to='shop.product')),
        ]),
        migrations.CreateModel(name='SiteConfig',fields=[
            ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
            ('site_name',models.CharField(default='NEW ARRIVALS',max_length=100)),
            ('orange_number',models.CharField(default='0375578480',max_length=25)),
            ('mvola_number',models.CharField(default='0348595149',max_length=25)),
            ('min_delivery_days',models.PositiveSmallIntegerField(default=9)),('max_delivery_days',models.PositiveSmallIntegerField(default=15)),
            ('hero_title',models.CharField(default='Chaque arrivée, une nouvelle envie.',max_length=200)),
            ('hero_subtitle',models.CharField(default='Des housses qui vous ressemblent. Commandez partout à Madagascar.',max_length=350)),
        ]),
        migrations.CreateModel(name='Banner',fields=[
            ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
            ('title',models.CharField(max_length=150)),('subtitle',models.CharField(blank=True,max_length=200)),
            ('url',models.CharField(default='/boutique',max_length=300)),('active',models.BooleanField(default=False)),
            ('starts_at',models.DateTimeField(blank=True,null=True)),('ends_at',models.DateTimeField(blank=True,null=True)),
        ]),
        migrations.AddConstraint(model_name='productvariant',constraint=models.UniqueConstraint(fields=('product','phone_model','color'),name='unique_phone_color_variant')),
    ]
