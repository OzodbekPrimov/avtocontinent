from django.contrib import admin
from django.utils.html import format_html
from admin_thumbnails import thumbnail
from .models import (
    Category, Brand, CarModel, Product, ProductImage,
    ExchangeRate, Banner, UserProfile, TelegramAuth, ProductLike,
    ProductComment, Favorite, PaymentSettings, Order, OrderItem,
    Cart, CartItem
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    
    def save_model(self, request, obj, form, change):
        # Generate slug from name_uz if slug is empty
        if not obj.slug and obj.name_uz:
            from django.utils.text import slugify
            base_slug = slugify(obj.name_uz)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(pk=obj.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            obj.slug = slug
        super().save_model(request, obj, form, change)

# @admin.register(SubCategory)
# class SubCategoryAdmin(admin.ModelAdmin):
#     list_display = ['name', 'category', 'slug', 'is_active', 'created_at']
#     list_filter = ['category', 'is_active', 'created_at']
#     search_fields = ['name', 'description']
#     prepopulated_fields = {'slug': ('name',)}
#     list_editable = ['is_active']

from django.contrib import admin
from django.utils.html import format_html
from .models import Brand

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'logo_thumbnail', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    
    def save_model(self, request, obj, form, change):
        # Generate slug from name_uz if slug is empty
        if not obj.slug and obj.name_uz:
            from django.utils.text import slugify
            base_slug = slugify(obj.name_uz)
            slug = base_slug
            counter = 1
            while Brand.objects.filter(slug=slug).exclude(pk=obj.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            obj.slug = slug
        super().save_model(request, obj, form, change)

    def logo_thumbnail(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="max-height:50px;"/>', obj.logo.url)
        return "-"
    logo_thumbnail.short_description = 'Logo'

@admin.register(CarModel)
class CarModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand',  'is_active', 'created_at']
    list_filter = ['brand', 'is_active', 'created_at']
    search_fields = ['name', 'brand__name']
    list_editable = ['is_active']
    
    def save_model(self, request, obj, form, change):
        # Generate slug from name_uz if slug is empty
        if not obj.slug and obj.name_uz:
            from django.utils.text import slugify
            base_slug = slugify(obj.name_uz)
            slug = base_slug
            counter = 1
            while CarModel.objects.filter(brand=obj.brand, slug=slug).exclude(pk=obj.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            obj.slug = slug
        super().save_model(request, obj, form, change)

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'category', 'price_usd', 'price_uzs_display', 'stock_quantity', 'is_active', 'is_featured']
    list_filter = ['category',  'is_active', 'is_featured', 'created_at']
    search_fields = ['name', 'sku', 'description']
    list_editable = ['is_active', 'is_featured']
    filter_horizontal = ['compatible_models']
    inlines = [ProductImageInline]
    
    def save_model(self, request, obj, form, change):
        # Generate slug from name_uz if slug is empty
        if not obj.slug and obj.name_uz:
            from django.utils.text import slugify
            base_slug = slugify(obj.name_uz)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=obj.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            obj.slug = slug
        super().save_model(request, obj, form, change)

    def price_uzs_display(self, obj):
        return f"{obj.price_uzs:,.0f} UZS"
    price_uzs_display.short_description = 'Price (UZS)'

@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ['usd_to_uzs', 'is_active', 'created_at', 'created_by']
    list_filter = ['is_active', 'created_at']
    readonly_fields = ['created_by']

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'image_thumbnail', 'is_active', 'order', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title',]
    list_editable = ['is_active', 'order']

    def image_thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:50px;"/>', obj.image.url)
        return "-"
    image_thumbnail.short_description = 'Image'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'is_phone_verified', 'created_at']
    list_filter = ['is_phone_verified', 'created_at']
    search_fields = ['user__username', 'phone_number']
    readonly_fields = ['created_at']

@admin.register(TelegramAuth)
class TelegramAuthAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'code', 'is_used', 'created_at', 'expires_at']
    list_filter = ['is_used', 'created_at']
    search_fields = ['phone_number']
    readonly_fields = ['created_at']

@admin.register(ProductComment)
class ProductCommentAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'rating', 'created_at']
    search_fields = ['product__name', 'user__username', 'comment']
    list_editable = ['is_approved']

@admin.register(PaymentSettings)
class PaymentSettingsAdmin(admin.ModelAdmin):
    list_display = ['card_number', 'card_holder_name', 'bank_name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    list_editable = ['is_active']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['total_price_usd', 'total_price_uzs']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'user', 'status', 'total_amount_uzs', 'payment_confirmed', 'created_at']
    list_filter = ['status', 'payment_confirmed', 'created_at']
    search_fields = ['order_id', 'user__username', 'customer_name', 'customer_phone']
    readonly_fields = ['order_id', 'created_at', 'updated_at']
    inlines = [OrderItemInline]

    def total_amount_uzs(self, obj):
        return f"{obj.total_amount_uzs:,.0f} UZS"
    total_amount_uzs.short_description = 'Total Amount (UZS)'

# Register other models without custom admin
admin.site.register(ProductLike)
admin.site.register(Favorite)
admin.site.register(Cart)
admin.site.register(CartItem)