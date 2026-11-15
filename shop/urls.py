from django.urls import path,include
from rest_framework.routers import DefaultRouter
from . import views
router=DefaultRouter()
router.register('categories',views.CategoryViewSet,basename='categories')
router.register('phone-models',views.PhoneModelViewSet,basename='phone-models')
router.register('products',views.ProductViewSet,basename='products')
router.register('orders',views.OrderViewSet,basename='orders')
router.register('admin/variants',views.VariantAdminViewSet,basename='admin-variants')
router.register('admin/product-images',views.ProductImageAdminViewSet,basename='admin-product-images')
router.register('addresses',views.CustomerAddressViewSet,basename='addresses')
router.register('banners',views.BannerViewSet,basename='banners')
router.register('admin/reviews',views.ReviewAdminViewSet,basename='admin-reviews')
urlpatterns=[
    path('',include(router.urls)),
    path('site-config/',views.SiteConfigView.as_view()),
    path('customizations/upload/',views.ArtworkUploadView.as_view()),
    path('customizations/<uuid:token>/download/',views.AdminArtworkView.as_view()),
    path('track/<uuid:token>/',views.TrackingView.as_view()),
    path('auth/register/',views.RegisterView.as_view()),
    path('auth/me/',views.WhoAmIView.as_view()),
    path('auth/avatar/',views.MyAvatarView.as_view()),
    path('my-orders/',views.MyOrdersView.as_view()),
    path('admin/dashboard/',views.AdminDashboardView.as_view()),
    path('reviews/',views.PublicReviewsView.as_view()),
    path('reviews/submit/',views.ReviewSubmissionView.as_view()),
    path('auth/password-reset/',views.PasswordResetRequestView.as_view()),
    path('auth/password-reset/confirm/',views.PasswordResetConfirmView.as_view()),
    path('wishlist/',views.WishlistView.as_view()),
    path('cart/',views.CartView.as_view()),
    path('admin/customers/',views.AdminCustomersView.as_view()),
    path('admin/stock-movements/',views.StockMovementView.as_view()),
    path('orders/<int:pk>/invoice/',views.InvoiceView.as_view()),
]
