from .models import Category, Cart
from django.utils import translation


def categories(request):
    """Add categories to all templates"""
    return {
        'categories': Category.objects.filter(is_active=True).prefetch_related('subcategories')
    }


def cart(request):
    """Add cart information to all templates"""
    cart_items_count = 0
    cart_total = 0

    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_items_count = cart.total_items
            cart_total = cart.total_price_uzs
        except Cart.DoesNotExist:
            pass
    elif request.session.session_key:
        # Initialize cart session flag if not set
        if not request.session.get('cart_initialized', False):
            # Clean up any stale carts for this session
            Cart.objects.filter(session_key=request.session.session_key, user=None).delete()
            request.session['cart_initialized'] = True
            request.session.modified = True
        
        try:
            cart = Cart.objects.get(session_key=request.session.session_key, user=None)
            cart_items_count = cart.total_items
            cart_total = cart.total_price_uzs
        except Cart.DoesNotExist:
            pass

    # Add favorites count for guests
    favorites_count = 0
    if request.user.is_authenticated:
        try:
            from .models import Favorite
            favorites_count = Favorite.objects.filter(user=request.user).count()
        except:
            favorites_count = 0
    else:
        favorites_count = len(request.session.get('favorites', []))

    return {
        'cart_items_count': cart_items_count,
        'cart_total': cart_total,
        'favorites_count': favorites_count,
    }


def language(request):
    """Add current language to all templates"""
    return {
        'current_language': translation.get_language(),
        'available_languages': [
            {'code': 'uz', 'name': 'O\'zbekcha'},
            {'code': 'ru', 'name': 'Русский'},
        ]
    }