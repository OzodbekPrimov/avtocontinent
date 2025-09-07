
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Avg, F, Func
from django.core.paginator import Paginator
from functools import wraps
from django.contrib import messages


from store.models import (
    Product, Category, Brand, CarModel, Banner,
    ProductLike, ProductComment, Favorite, Cart, CartItem,
    Order, OrderItem, UserProfile, TelegramAuth, ExchangeRate,
    PaymentSettings
)


def store_login_required(view_func):
    """Custom login_required decorator for store that redirects to store login"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def home(request):
    """Home page view"""
    # Get banners
    banners = Banner.objects.filter(is_active=True)
    # Get brands
    brands = Brand.objects.filter(is_active=True)[:8]
    # Get featured products
    featured_products = Product.objects.filter(is_active=True, is_featured=True)[:8]
    # Get best selling products
    best_selling = Product.objects.filter(is_active=True).annotate(
        order_count=Count('orderitem')
    ).order_by('-order_count')[:10]
    # Get most liked products
    most_liked = Product.objects.annotate(
        total_likes=Count('likes')
    ).order_by('-total_likes')[:8]
    # Get latest products
    latest_products = Product.objects.filter(is_active=True).order_by('-created_at')[:8]
    # Get categories (only top-level)
    categories = Category.objects.filter(is_active=True)  # prefetch_related olib tashlandi

    context = {
        'banners': banners,
        'brands': brands,
        'featured_products': featured_products,
        'best_selling': best_selling,
        'most_liked': most_liked,
        'latest_products': latest_products,
        'categories': categories,
    }
    return render(request, 'store/home.html', context)


@store_login_required
def profile_view(request):
    """Foydalanuvchi profilinga ko'rish"""
    user = request.user
    # Agar UserProfile modeli bo'lsa, uni ham oling
    try:
        profile = user.userprofile
    except:
        profile = None

    context = {
        'user': user,
        'profile': profile,
    }


def product_list(request):
    """Product list view with filtering and search"""
    products = Product.objects.filter(is_active=True)

    # Get filter parameters
    category_slug = request.GET.get('category')
    # subcategory_slug = request.GET.get('subcategory')
    brand_slug = request.GET.get('brand')
    model_slug = request.GET.get('model')
    search_query = request.GET.get('search', '').strip()

    # Apply filters
    if category_slug:
        products = products.filter(category__slug=category_slug)

    # if subcategory_slug:
    #     products = products.filter(subcategory__slug=subcategory_slug)

    if brand_slug:
        products = products.filter(compatible_models__brand__slug=brand_slug).distinct()

    if model_slug:
        products = products.filter(compatible_models__slug=model_slug)

    # Advanced search with spelling mistakes handling
    if search_query:
        products = advanced_search(products, search_query, current_lang=translation.get_language()[:2])

    # Sorting
    sort_by = request.GET.get('sort', 'name')
    if sort_by == 'price_low':
        products = products.order_by('price_usd')
    elif sort_by == 'price_high':
        products = products.order_by('-price_usd')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    elif sort_by == 'popular':
        products = products.annotate(likes_count=Count('likes')).order_by('-likes_count')
    else:
        products = products.order_by('name')

    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get filter options
    categories = Category.objects.filter(is_active=True)
    brands = Brand.objects.filter(is_active=True)

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'brands': brands,
        'current_category': category_slug,
        'current_brand': brand_slug,
        'current_model': model_slug,
        'search_query': search_query,
        'sort_by': sort_by,
    }

    return render(request, 'store/product_list.html', context)

from   django.db import models

class SearchQuery(Func):
    function = 'to_tsquery'
    template = '%(function)s(%(expressions)s)'
    output_field = models.TextField()

from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.utils import translation
from difflib import SequenceMatcher
from store.models import Product

def advanced_search(products, query, current_lang='uz'):
    languages = ['uz', 'ru', 'cyrl']
    query_str = query.strip()

    # Full-text search vector for all language fields
    search_vector = (
        SearchVector('name_uz', weight='A') +
        SearchVector('name_ru', weight='A') +
        SearchVector('name_cyrl', weight='A') +
        SearchVector('description_uz', weight='B') +
        SearchVector('description_ru', weight='B') +
        SearchVector('description_cyrl', weight='B')
    )

    # Create search query with proper syntax
    search_query = SearchQuery(query_str, config='simple')  # 'simple' config for basic matching

    # Apply full-text search with ranking
    results = products.annotate(
        search=search_vector,
        rank=SearchRank(search_vector, search_query)
    ).filter(search=search_query).order_by('-rank').distinct()

    # Fuzzy matching if no results
    if not results.exists():
        all_products = products.all()
        fuzzy_results = set()
        for product in all_products:
            name_str = getattr(product, f'name_{current_lang}', '').lower().replace(' ', '').strip()
            similarity = SequenceMatcher(None, query_str.lower().replace(' ', ''), name_str).ratio()
            if similarity > 0.6:
                fuzzy_results.add(product.pk)
                continue
            for lang in languages:
                if lang != current_lang:
                    name_str_other = getattr(product, f'name_{lang}', '').lower().replace(' ', '').strip()
                    if SequenceMatcher(None, query_str.lower().replace(' ', ''), name_str_other).ratio() > 0.6:
                        fuzzy_results.add(product.pk)
                        break
        if fuzzy_results:
            results = products.filter(pk__in=fuzzy_results)

    results = results.filter(is_active=True, stock_quantity__gt=0)
    return results




def product_detail(request, slug):
    """Product detail view"""
    product = get_object_or_404(Product, slug=slug, is_active=True)
    # Get related products
    related_products = Product.objects.filter(
        category=product.category, is_active=True
    ).exclude(pk=product.pk)[:4]
    # Get comments
    comments = ProductComment.objects.filter(
        product=product, is_approved=True, parent__isnull=True
    ).order_by('-created_at')[:4]
    # Get categories
    categories = Category.objects.filter(is_active=True)[:4]  # prefetch_related olib tashlandi
    # Check if user has liked this product
    user_liked = False
    user_favorited = False
    if request.user.is_authenticated:
        user_liked = ProductLike.objects.filter(user=request.user, product=product).exists()
        user_favorited = Favorite.objects.filter(user=request.user, product=product).exists()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, "Koment yozish uchun tizimga kirishingiz kerak!")
            return redirect('login')
        rating = request.POST.get('rating')
        comment_text = request.POST.get('comment')
        if rating and comment_text:
            try:
                rating = int(rating)
                if rating < 1 or rating > 5:
                    messages.error(request, "Reyting 1 dan 5 gacha bo‘lishi kerak!")
                    return redirect('product_detail', slug=product.slug)
                ProductComment.objects.create(
                    product=product,
                    user=request.user,
                    rating=rating,
                    comment=comment_text,
                    is_approved=True
                )
                messages.success(request, "Koment muvaffaqiyatli yuborildi!")
            except ValueError:
                messages.error(request, "Noto‘g‘ri reyting formati!")
        else:
            messages.error(request, "Reyting va koment kiritish shart!")
        return redirect('product_detail', slug=product.slug)

    context = {
        'product': product,
        'related_products': related_products,
        'comments': comments,
        'user_liked': user_liked,
        'user_favorited': user_favorited,
        'categories': categories,
    }
    return render(request, 'store/product_detail.html', context)

def brands(request):
    """Brands listing page"""
    brands = Brand.objects.filter(is_active=True).order_by('name')

    context = {
        'brands': brands,
    }

    return render(request, 'store/brands.html', context)


def brand_models(request, brand_slug):
    """Brand models listing page with filters and products"""
    brand = get_object_or_404(Brand, slug=brand_slug, is_active=True)
    models = CarModel.objects.filter(brand=brand, is_active=True).order_by('name')

    # Get products for this brand
    products = Product.objects.filter(
        compatible_models__brand=brand,
        is_active=True
    ).distinct()

    # Filter by specific model if selected
    selected_model = request.GET.get('model')
    if selected_model:
        try:
            model = CarModel.objects.get(slug=selected_model, brand=brand)
            products = products.filter(compatible_models=model)
        except CarModel.DoesNotExist:
            pass

    # Search filter
    search_query = request.GET.get('search', '').strip()
    if search_query:
        products = advanced_search(products, search_query)

    # Category filter
    category_slug = request.GET.get('category')
    if category_slug:
        products = products.filter(category__slug=category_slug)

    # Sorting
    sort_by = request.GET.get('sort', 'name')
    if sort_by == 'price_low':
        products = products.order_by('price_usd')
    elif sort_by == 'price_high':
        products = products.order_by('-price_usd')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    elif sort_by == 'popular':
        products = products.annotate(likes_count=Count('likes')).order_by('-likes_count')
    else:
        products = products.order_by('name')

    # Pagination - 15 products per page
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get categories for filtering
    categories = Category.objects.filter(is_active=True)

    context = {
        'brand': brand,
        'models': models,
        'page_obj': page_obj,
        'categories': categories,
        'selected_model': selected_model,
        'search_query': search_query,
        'sort_by': sort_by,
    }

    return render(request, 'store/brand_models.html', context)


def cart_view(request):
    cart = None
    cart_items = []
    categories = Category.objects.filter(is_active=True)

    if request.user.is_authenticated:
        # 1. Foydalanuvchi uchun savatni olish yoki yaratish
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.all()
    else:
        # 2. Session orqali mijoz uchun
        session_key = request.session.session_key
        if session_key:
            try:
                cart = Cart.objects.get(session_key=session_key)
                cart_items = cart.items.all()
            except Cart.DoesNotExist:
                pass

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'categories':categories
    }
    return render(request, 'store/cart.html', context)


def favorites(request):
    """User favorites view"""
    favorites = []
    categories = Category.objects.filter(is_active=True)[:6]

    if request.user.is_authenticated:
        favorites = Favorite.objects.filter(user=request.user).order_by('-created_at')
    else:
        # Guest favorites from session
        favorite_ids = request.session.get('favorites', [])
        if favorite_ids:
            products = Product.objects.filter(id__in=favorite_ids, is_active=True)
            # Create fake favorite objects for template compatibility
            favorites = [type('obj', (object,), {'product': product, 'created_at': None}) for product in products]

    context = {
        'favorites': favorites,
        'categories':categories
    }

    return render(request, 'store/favorites.html', context)
