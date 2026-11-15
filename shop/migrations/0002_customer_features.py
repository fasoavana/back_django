from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('shop', '0001_initial'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name='Wishlist', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wishlisted_by', to='shop.product')),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wishlist_entries', to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.AddConstraint(model_name='wishlist',constraint=models.UniqueConstraint(fields=('user','product'),name='unique_wishlist_user_product')),
        migrations.CreateModel(name='SavedCart',fields=[
            ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
            ('items',models.JSONField(default=list)),('updated_at',models.DateTimeField(auto_now=True)),
            ('user',models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,related_name='saved_cart',to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name='CustomerAddress',fields=[
            ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
            ('label',models.CharField(default='Domicile',max_length=50)),
            ('address',models.CharField(max_length=500)),('city',models.CharField(max_length=100)),
            ('zone',models.CharField(choices=[('tana','Antananarivo'),('province','Province')],default='tana',max_length=12)),
            ('phone',models.CharField(max_length=30)),('is_default',models.BooleanField(default=False)),
            ('user',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='saved_addresses',to=settings.AUTH_USER_MODEL)),
        ]),
    ]
