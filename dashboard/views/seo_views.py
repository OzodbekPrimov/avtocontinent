from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from store.models import Product, Brand, Category
from store.seo_utils import get_seo_keywords, get_meta_description, get_page_title
import requests
from urllib.parse import quote

@staff_member_required
def seo_dashboard(request):
    """SEO monitoring dashboard"""
    context = {
        'seo_keywords': get_seo_keywords(),
        'total_products': Product.objects.filter(is_active=True).count(),
        'total_brands': Brand.objects.filter(is_active=True).count(),
        'total_categories': Category.objects.filter(is_active=True).count(),
        'meta_descriptions': {
            'uz': get_meta_description('uz'),
            'ru': get_meta_description('ru'),
            'cyrl': get_meta_description('cyrl')
        },
        'page_titles': {
            'home_uz': get_page_title('home', 'uz'),
            'home_ru': get_page_title('home', 'ru'),
            'products_uz': get_page_title('products', 'uz'),
            'products_ru': get_page_title('products', 'ru')
        }
    }
    return render(request, 'dashboard/seo_dashboard.html', context)

@staff_member_required
@require_http_methods(["POST"])
def check_search_rankings(request):
    """Check search rankings for key terms"""
    search_terms = [
        'avtokontinent',
        'автоконтинент',
        'avtokontinent.uz',
        'автоконтинент.уз',
        'avto kontinent',
        'авто континент'
    ]
    
    results = {}
    for term in search_terms:
        # This is a placeholder - in production you'd use proper SEO tools
        results[term] = {
            'term': term,
            'status': 'monitoring',
            'notes': f'Track ranking for: {term}'
        }
    
    return JsonResponse({'results': results})

@staff_member_required
def sitemap_status(request):
    """Check sitemap status and indexing"""
    sitemaps = [
        '/sitemap.xml',
        '/sitemap-products.xml', 
        '/sitemap-brands.xml',
        '/sitemap-categories.xml'
    ]
    
    context = {
        'sitemaps': sitemaps,
        'robots_txt_url': '/robots.txt',
        'google_verification_url': '/google-verification.html'
    }
    
    return render(request, 'dashboard/sitemap_status.html', context)
