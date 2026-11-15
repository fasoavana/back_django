from django.contrib import admin
from shop.sitemap import sitemap
from shop.social import social_product_page,robots_txt
from django.urls import path, include
from django.http import JsonResponse
from shop.public_media import public_catalog_image
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("sitemap.xml", sitemap),
    path("robots.txt", robots_txt),
    path("produit/<slug:slug>", social_product_page),
    path("produit/<slug:slug>/", social_product_page),
    path('api/v1/health', lambda request: JsonResponse({'status':'ok','shop':'NEW ARRIVALS'})),
    path('api/v1/auth/token/', TokenObtainPairView.as_view()),
    path('api/v1/auth/refresh/', TokenRefreshView.as_view()),
    path('api/v1/', include('shop.urls')),
    path('django-admin/', admin.site.urls),
    path('media/catalog/<path:image_path>', public_catalog_image),
]
