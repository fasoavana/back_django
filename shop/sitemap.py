from xml.sax.saxutils import escape
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.http import require_GET
from .models import Product
@require_GET
def sitemap(request):
    base=settings.FRONTEND_ORIGIN.rstrip('/')
    paths=['/','/boutique','/informations/conditions','/informations/mentions','/informations/confidentialite']
    paths += [f'/produit/{slug}' for slug in Product.objects.filter(active=True).values_list('slug',flat=True).iterator()]
    xml='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join('<url><loc>'+escape(base+p)+'</loc></url>' for p in paths) + '</urlset>'
    return HttpResponse(xml,content_type='application/xml; charset=utf-8')
