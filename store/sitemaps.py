from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Product, Brand  # mahsulot modeli bo'lsa, bo'lmasa hozircha olib tashla

class StaticViewSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        # bu yerda asosiy statik sahifalaringni url name'larini yoz
        return ["home", "product_list", "brands"]

    def location(self, item):
        return reverse(item)


# Agar mahsulotlar bo'lsa
class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Product.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at


class BrandSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return Brand.objects.all()

    def location(self, obj):
        return reverse("brand_models", args=[obj.slug])