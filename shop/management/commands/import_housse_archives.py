"""Importer les photos des 15 ZIP. Le prix reste à valider par le commerçant.

Usage:
  python manage.py import_housse_archives --archives-dir /archives --dry-run
  python manage.py import_housse_archives --archives-dir /archives

Chaque photo donne une fiche visible, identifiée par une référence stable.
price_confirmed=False empêche une vente au tarif de base si la finition
est blindée, diamant, etc. Classement manuel préalable à la vente.
"""
import csv
import hashlib
import io
import os
import zipfile
from collections import defaultdict
from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image, ImageOps, UnidentifiedImageError
from shop.models import Category, PhoneModel, Product, ProductVariant

class Command(BaseCommand):
    help='Importer les photos des archives comme fiches visibles, mais non commandables avant validation du tarif.'

    def add_arguments(self,parser):
        parser.add_argument('--archives-dir',required=True,help='Dossier des 15 fichiers housses_part*.zip')
        parser.add_argument('--index',default=None,help='Chemin de index_photos_15_archives.csv')
        parser.add_argument('--dry-run',action='store_true')
        parser.add_argument('--limit',type=int,default=0,help='Nombre maximal de lignes à traiter (tests)')
        parser.add_argument('--only-archive',action='append',default=[],help='Limiter à une archive ZIP précise ; répétable')

    def handle(self,*args,**options):
        data_dir=Path(os.environ.get('CATALOG_DATA_DIR',str(Path(settings.BASE_DIR).parent/'data')))
        index_path=Path(options['index'] or data_dir/'index_photos_15_archives.csv')
        archive_dir=Path(options['archives_dir'])
        if not index_path.is_file():raise CommandError(f'Index absent: {index_path}')
        if not archive_dir.is_dir():raise CommandError(f'Dossier absent: {archive_dir}')
        with index_path.open(newline='',encoding='utf-8-sig') as file:
            rows=list(csv.DictReader(file))
        if options['only_archive']:
            accepted=set(options['only_archive'])
            if any(Path(name).name != name for name in accepted):
                raise CommandError('--only-archive attend un nom de fichier uniquement.')
            rows=[row for row in rows if row['archive'] in accepted]
            if not rows:raise CommandError('Aucune référence trouvée pour ces archives.')
        if options['limit']>0:rows=rows[:options['limit']]
        grouped=defaultdict(list)
        for row in rows:
            grouped[row['archive']].append(row)
        missing=[name for name in grouped if not (archive_dir/name).is_file()]
        if missing:raise CommandError('Archives manquantes: '+', '.join(missing))
        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(f'{len(rows)} fichiers indexés, {len(grouped)} ZIP disponibles; aucun import effectué.'))
            return
        category,_=Category.objects.get_or_create(slug='a-classer',defaults={'name':'Collection à classifier','active':True,'order':99})
        imported=skipped=errors=0
        phones={}
        for archive_name,group in grouped.items():
            self.stdout.write(f'{archive_name}: {len(group)} entrées')
            with zipfile.ZipFile(archive_dir/archive_name,'r') as archive:
                infos={item.filename:item for item in archive.infolist()}
                for row in group:
                    path=row['chemin_dans_zip']
                    signature=hashlib.sha256((archive_name+'\n'+path).encode('utf-8')).hexdigest()[:24]
                    slug='housse-'+signature
                    if Product.objects.filter(slug=slug).exists():
                        skipped+=1;continue
                    entry=infos.get(path)
                    if not entry or entry.is_dir() or entry.file_size>14*1024*1024:
                        errors+=1;continue
                    phone_name=row['modele_telephone'].strip()[:150]
                    if not phone_name:
                        errors+=1;continue
                    try:
                        with archive.open(entry) as source:
                            content=source.read()
                        image=Image.open(io.BytesIO(content));image.verify()
                        image=ImageOps.exif_transpose(Image.open(io.BytesIO(content)))
                        if image.width*image.height>35_000_000:raise ValueError('Trop grande image')
                        image=image.convert('RGB');image.thumbnail((1300,1300),Image.Resampling.LANCZOS)
                        output=io.BytesIO();image.save(output,format='WEBP',quality=78,method=4)
                        asset='catalog/imported/'+signature+'.webp'
                        if not default_storage.exists(asset):default_storage.save(asset,ContentFile(output.getvalue()))
                    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError, zipfile.BadZipFile) as exc:
                        errors+=1
                        self.stderr.write(f'Image illisible: {archive_name} -> {path}: {exc}')
                        continue
                    if phone_name not in phones:
                        phones[phone_name],_=PhoneModel.objects.get_or_create(name=phone_name,defaults={'brand':phone_name.split(' ')[0].title()})
                    with transaction.atomic():
                        product,created=Product.objects.get_or_create(slug=slug,defaults={
                            'name':f'Housse pour {phone_name} · {signature[-6:].upper()}',
                            'category':category,'kind':'non_classe','price':35000,
                            'price_confirmed':False,'cover_url':settings.MEDIA_URL+asset,'active':True,
                            'on_order':True,'is_new':False,'source_ref':'CAT-'+signature[:12].upper(),
                            'description':'Visuel de référence sur commande. Prix à partir de 35 000 Ar : la finition et le tarif exact doivent être validés par New arrivals avant tout paiement.'})
                        ProductVariant.objects.get_or_create(product=product,phone_model=phones[phone_name],color='Selon photo',defaults={'status':'sur_commande'})
                        if created:imported+=1
                        else:skipped+=1
            self.stdout.write(f'Cumul: {imported} créées, {skipped} déjà présentes, {errors} erreurs')
        self.stdout.write(self.style.SUCCESS(f'Terminé: {imported} fiches visibles (prix à confirmer), {skipped} existantes, {errors} images ignorées.'))
