from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone
from .models import Product, Brand, Category

class StaticViewSitemap(Sitemap):
    """Sitemap for static pages with multilingual support"""
    changefreq = "daily"
    priority = 0.9
    protocol = 'https'

    def items(self):
        # Include key pages that should rank for brand searches
        return ["home", "product_list", "brand_list", "category_list"]

    def location(self, item):
        try:
            return reverse(item)
        except:
            # Fallback for URLs that might not exist
            if item == "brand_list":
                return "/brands/"
            elif item == "category_list":
                return "/categories/"
            return reverse("home")
    
    def lastmod(self, item):
        return timezone.now()


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