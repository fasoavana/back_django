"""Server-side catalogue photo validation + optimization."""
import io
from django.core.files.base import ContentFile
from rest_framework.exceptions import ValidationError
from PIL import Image, ImageOps, UnidentifiedImageError

def optimize_image(file):
    if not file or file.size > 8*1024*1024:
        raise ValidationError({'image':'Image obligatoire, 8 Mo maximum.'})
    try:
        src = Image.open(file)
        src.verify()
        file.seek(0)
        img = ImageOps.exif_transpose(Image.open(file))
        if img.width * img.height > 20_000_000:
            raise ValidationError({'image':'Dimensions trop grandes.'})
        if img.mode not in ('RGB','RGBA'):
            img = img.convert('RGB')
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, 'white');background.paste(img, mask=img.getchannel('A'));img=background
        img.thumbnail((1800,1800), Image.Resampling.LANCZOS)
        out = io.BytesIO();img.save(out, format='WEBP', quality=83, method=5)
        return ContentFile(out.getvalue(), name='catalogue.webp')
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
        raise ValidationError({'image':'Fichier image invalide.'})
