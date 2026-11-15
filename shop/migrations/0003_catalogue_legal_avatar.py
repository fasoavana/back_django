from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):
    dependencies=[('shop','0002_customer_features'),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
        migrations.AlterField(model_name='product',name='kind',field=models.CharField(max_length=25,default='simple',choices=[('simple','Simple'),('iphone','iPhone'),('bracelet','Bracelet / cordon'),('diamant','Cristaux / diamant'),('blinde','Blindée'),('luxe','Luxe'),('personnalisee','Personnalisée'),('accessoire','Accessoire'),('non_classe','À classer')])),
        migrations.AddField(model_name='product',name='price_confirmed',field=models.BooleanField(default=True,help_text='False: photo visible, commande désactivée tant que le prix n’est pas validé.')),
        migrations.AddField(model_name='siteconfig',name='legal_business_name',field=models.CharField(max_length=180,blank=True)),
        migrations.AddField(model_name='siteconfig',name='legal_address',field=models.TextField(blank=True)),
        migrations.AddField(model_name='siteconfig',name='legal_registration',field=models.CharField(max_length=180,blank=True)),
        migrations.AddField(model_name='siteconfig',name='hosting_provider',field=models.CharField(max_length=250,blank=True)),
        migrations.AddField(model_name='siteconfig',name='legal_contact_phone',field=models.CharField(max_length=30,blank=True)),
        migrations.AddField(model_name='siteconfig',name='legal_contact_email',field=models.EmailField(max_length=254,blank=True)),
        migrations.AddField(model_name='siteconfig',name='privacy_contact_email',field=models.EmailField(max_length=254,blank=True)),
        migrations.AddField(model_name='siteconfig',name='legal_updated_at',field=models.DateField(null=True,blank=True)),
        migrations.AddField(model_name='siteconfig',name='data_retention_months',field=models.PositiveSmallIntegerField(default=24)),
        migrations.CreateModel(name='CustomerProfile',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('avatar',models.ImageField(upload_to='private/avatars/%Y/%m/',blank=True)),('user',models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,related_name='new_arrivals_profile',to=settings.AUTH_USER_MODEL))]),
    ]
