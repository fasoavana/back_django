import json
import csv
import os
from django.conf import settings
from pathlib import Path
from django.core.management.base import BaseCommand
from shop.models import Product,ProductVariant,PhoneModel,Category,SiteConfig

class Command(BaseCommand):
    help='Ajoute un échantillon réel de photos issues des archives de housses (sans modifier les autres produits).'
    def handle(self,*args,**kwargs):
        data=json.loads((Path(os.environ.get('CATALOG_DATA_DIR',str(Path(settings.BASE_DIR).parent/'data')))/'produits_selection.json').read_text())
        cats={'luxe':'Luxe','bijoux':'Avec bracelet','diamant':'Diamant','simple':'Simples',
              'blinde':'Blindées','iphone':'iPhone','personnalisee':'Personnalisées','accessoire':'Accessoires'}
        for slug,name in cats.items():Category.objects.update_or_create(slug=slug,defaults={'name':name})
        for row in data:
            kind='bracelet' if row['kind']=='bijoux' else row['kind']
            cat=Category.objects.get(slug=row['kind'])
            product,_=Product.objects.get_or_create(slug=row['slug'],defaults={
                'name':row['name'],'price':row['price'],'kind':kind,'category':cat,
                'description':'Housse disponible sur commande. Compatibilité correspondant au modèle photographié ; demandez confirmation pour les autres téléphones.',
                'cover_url':row['cover_url'],'on_order':True,'source_ref':row['ref'],'active':True})
            phone=row['phone'];brand=phone.split(' ')[0].title()
            model,_=PhoneModel.objects.get_or_create(name=phone,defaults={'brand':brand})
            ProductVariant.objects.get_or_create(product=product,phone_model=model,color='Selon photo',defaults={'status':'sur_commande'})
        custom_cat=Category.objects.get(slug='personnalisee')
        custom,_=Product.objects.get_or_create(slug='personnalisee-effet-verre',defaults={
            'name':'Housse personnalisée — effet verre brillant','price':36000,'kind':'personnalisee',
            'category':custom_cat,'cover_url':'/catalog/personnalisee-ref-3.webp','on_order':True,
            'customizable':True,'active':True,
            'description':'Votre photo sur une housse à dos brillant aspect verre. Matériau exact à confirmer selon le modèle de téléphone.'})
        # Les noms proviennent des dossiers de photos. La disponibilité en version personnalisée
        # doit rester confirmée manuellement par le vendeur, même si la demande est acceptée.
        phones={'iPhone 13 Pro Max','iPhone 14','iPhone 15','Samsung Galaxy A15',
                'Samsung Galaxy S24','Redmi Note 13','Redmi Note 12','Oppo Reno 8',
                'Realme V20','Tecno Spark 10 Pro'}
        with (Path(os.environ.get('CATALOG_DATA_DIR',str(Path(settings.BASE_DIR).parent/'data')))/'index_photos_15_archives.csv').open(newline='',encoding='utf-8') as handle:
            for row in csv.DictReader(handle):
                phone_name=row['modele_telephone'].strip()
                if phone_name:phones.add(phone_name)
        for phone in sorted(phones):
            pm,_=PhoneModel.objects.get_or_create(name=phone,defaults={'brand':phone.split(' ')[0].title()})
            ProductVariant.objects.get_or_create(product=custom,phone_model=pm,color='Photo du client',defaults={'status':'sur_commande'})
        SiteConfig.current()
        self.stdout.write(self.style.SUCCESS(f'{len(data)} produits réels + 1 personnalisable ; {len(phones)} modèles proposés sous réserve de confirmation.'))
