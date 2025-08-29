from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Product, Brand, Category

class StaticViewSitemap(Sitemap):
    """Sitemap for static pages"""
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return ["home", "product_list"]

    def location(self, item):
        return reverse(item)


class ProductSitemap(Sitemap):
    """Sitemap for products"""
    changefreq = "weekly"
    priority = 0.7
    protocol = 'https'

    def items(self):
        return Product.objects.filter(is_active=True).select_related('category')

    def lastmod(self, obj):
        return getattr(obj, 'updated_at', None)

    def location(self, obj):
        return obj.get_absolute_url()


class BrandSitemap(Sitemap):
    """Sitemap for brands"""
    changefreq = "monthly"
    priority = 0.6
    protocol = 'https'

    def items(self):
        return Brand.objects.filter(is_active=True)

    def location(self, obj):
        return reverse("brand_models", args=[obj.slug])


class CategorySitemap(Sitemap):
    """Sitemap for categories"""
    changefreq = "weekly"
    priority = 0.6
    protocol = 'https'

    def items(self):
        return Category.objects.filter(is_active=True)

    def location(self, obj):
        return f"/products/?category={obj.slug}"