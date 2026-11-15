"""Crawler-visible, server-rendered OpenGraph pages for catalogue products."""
from html import escape
from urllib.parse import urljoin
from django.conf import settings
from django.http import HttpResponse, Http404
from django.views.decorators.http import require_GET
from django.utils.html import strip_tags
from .models import Product

@require_GET
def social_product_page(request, slug):
    product=Product.objects.filter(slug=slug,active=True).first()
    if not product:
        raise Http404('Produit inconnu')
    base=settings.FRONTEND_ORIGIN.rstrip('/')+'/'
    url=urljoin(base,'produit/'+product.slug)
    title=f'{product.name} | NEW ARRIVALS'
    description=(strip_tags(product.description).strip() or 'Housses sur commande à Madagascar.')[:230]
    photo=urljoin(base,product.cover_url.lstrip('/')) if product.cover_url else urljoin(base,'favicon.svg')
    price=(f'À partir de {product.price:,} Ar' if not product.price_confirmed else f'{product.price:,} Ar').replace(',',' ')
    def meta(name,value):
        return f'<meta property="{escape(name,quote=True)}" content="{escape(str(value),quote=True)}">'
    tags=''.join([meta('og:type','product'),meta('og:site_name','NEW ARRIVALS'),meta('og:title',title),meta('og:description',description),meta('og:url',url),meta('og:image',photo),meta('og:locale','fr_MG')])
    html=f'''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{escape(title)}</title><meta name="description" content="{escape(description,quote=True)}"><link rel="canonical" href="{escape(url,quote=True)}">{tags}<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{escape(photo,quote=True)}"></head><body><main><h1>{escape(product.name)}</h1><p>{escape(description)}</p><p>{escape(price)} — Sur commande</p><img src="{escape(photo,quote=True)}" alt="{escape(product.name,quote=True)}"><p><a href="{escape(url,quote=True)}">Découvrir ce produit sur NEW ARRIVALS</a></p></main></body></html>'''
    response=HttpResponse(html,content_type='text/html; charset=utf-8')
    response['Cache-Control']='public, max-age=300'
    return response

@require_GET
def robots_txt(request):
    base=settings.FRONTEND_ORIGIN.rstrip('/')
    body=f'User-agent: *\nDisallow: /admin-panel\nDisallow: /mon-compte\nDisallow: /commande\nDisallow: /suivi/\nDisallow: /django-admin/\nDisallow: /api/\nSitemap: {base}/sitemap.xml\n'
    return HttpResponse(body,content_type='text/plain; charset=utf-8')
