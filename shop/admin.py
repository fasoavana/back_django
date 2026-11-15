from django.contrib import admin
from .models import (Category,PhoneModel,Product,ProductVariant,ProductImage,Order,OrderItem,
                     CustomerArtwork,StockMovement,Review,SiteConfig,Banner,Wishlist,SavedCart,CustomerAddress)
class VariantInline(admin.TabularInline):
    model=ProductVariant;extra=0
class ImageInline(admin.TabularInline):
    model=ProductImage;extra=0
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display=('name','kind','price','price_confirmed','active','on_order','customizable')
    list_filter=('category','kind','price_confirmed','active','on_order')
    search_fields=('name','slug','source_ref')
    prepopulated_fields={'slug':('name',)}
    inlines=[VariantInline,ImageInline]
class OrderItemInline(admin.TabularInline):
    model=OrderItem;extra=0;readonly_fields=('product_name','unit_price','quantity')
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display=('reference','source','customer_name','zone','total','required_payment','payment_status','status','created_at')
    search_fields=('reference','customer_name','customer_phone','transaction_reference')
    list_filter=('source','status','payment_status','zone','created_at')
    readonly_fields=('reference','tracking_token','created_at','updated_at','required_payment','total')
    inlines=[OrderItemInline]
for cls in (Category,PhoneModel,CustomerArtwork,StockMovement,Review,SiteConfig,Banner,Wishlist,SavedCart,CustomerAddress):admin.site.register(cls)
admin.site.site_header='NEW ARRIVALS — Gestion'
