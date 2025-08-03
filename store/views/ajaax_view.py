import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from functools import wraps

from store.models import Product, ProductLike, Cart, CartItem, Favorite


def store_login_required(view_func):
    """Custom login_required decorator for store that redirects to store login"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('store:login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def ajax_like_product(request):
    """AJAX endpoint to like/unlike a product"""
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        try:
            product = Product.objects.get(pk=product_id)

            if request.user.is_authenticated:
                like, created = ProductLike.objects.get_or_create(
                    user=request.user,
                    product=product
                )

                if not created:
                    like.delete()
                    liked = False
                else:
                    liked = True
            else:
                # For guest users, store in session
                if not request.session.session_key:
                    request.session.create()

                likes = request.session.get('likes', [])
                if product_id in likes:
                    likes.remove(product_id)
                    liked = False
                else:
                    likes.append(product_id)
                    liked = True

                request.session['likes'] = likes
                request.session.modified = True

            return JsonResponse({
                'success': True,
                'liked': liked,
                'like_count': product.like_count
            })
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Product not found'})

    return JsonResponse({'success': False, 'message': 'Invalid request'})


def ajax_favorite_product(request):
    """AJAX endpoint to add/remove product from favorites (guest or authenticated)"""
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        try:
            product = Product.objects.get(pk=product_id)
            if request.user.is_authenticated:
                favorite, created = Favorite.objects.get_or_create(
                    user=request.user,
                    product=product
                )

                if not created:
                    favorite.delete()
                    favorited = False
                else:
                    favorited = True

                # Get updated favorites count
                favorites_count = Favorite.objects.filter(user=request.user).count()
            else:
                # For guest users, store in session
                if not request.session.session_key:
                    request.session.create()

                favorites = request.session.get('favorites', [])
                if str(product_id) in favorites:
                    favorites.remove(str(product_id))
                    favorited = False
                else:
                    favorites.append(str(product_id))
                    favorited = True

                request.session['favorites'] = favorites
                request.session.modified = True

                # Get updated favorites count
                favorites_count = len(favorites)

            return JsonResponse({
                'success': True,
                'favorited': favorited,
                'favorites_count': favorites_count
            })
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Product not found'})

    return JsonResponse({'success': False, 'message': 'Invalid request'})


@csrf_exempt
@require_POST
def ajax_add_to_cart(request):
    try:
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 1))

        product = get_object_or_404(Product, pk=product_id, is_active=True)

        if product.stock_quantity < quantity:
            return JsonResponse({
                'success': False,
                'message': f'Only {product.stock_quantity} items available'
            })

        cart = None
        if request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=request.user)
        else:
            # MUHIM: session_key mavjudligini tekshirish va saqlash
            if not request.session.session_key:
                request.session.create()  # Yangi session yaratish
            session_key = request.session.session_key
            cart, created = Cart.objects.get_or_create(
                session_key=session_key,
                defaults={'session_key': session_key}
            )

        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )

        if not item_created:
            new_quantity = cart_item.quantity + quantity
            if new_quantity > product.stock_quantity:
                return JsonResponse({
                    'success': False,
                    'message': f'Only {product.stock_quantity - cart_item.quantity} more items can be added'
                })
            cart_item.quantity = new_quantity
            cart_item.save()

        return JsonResponse({
            'success': True,
            'message': 'Product added to cart',
            'cart_total': cart.total_items
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Server error'
        }, status=400)


@csrf_exempt
@store_login_required
def ajax_sync_cart(request):
    try:
        cart_data = json.loads(request.POST.get('cart', '{}'))
        cart, created = Cart.objects.get_or_create(user=request.user)

        for product_id_str, quantity in cart_data.items():
            product_id = int(product_id_str)
            product = Product.objects.get(id=product_id)

            cart_item, item_created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': 0}
            )
            # Zaxirani tekshirish
            new_quantity = cart_item.quantity + quantity
            if new_quantity > product.stock_quantity:
                new_quantity = product.stock_quantity
            cart_item.quantity = new_quantity
            if cart_item.quantity > 0:
                cart_item.save()
            elif not item_created:
                cart_item.delete()

        return JsonResponse({
            'success': True,
            'cart_total': cart.total_items
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@csrf_exempt
@store_login_required
def ajax_sync_favorites(request):
    try:
        favorites_data = json.loads(request.POST.get('favorites', '[]'))
        for product_id in favorites_data:
            product = Product.objects.get(id=product_id)
            Favorite.objects.get_or_create(user=request.user, product=product)

        return JsonResponse({
            'success': True,
            'favorites_count': request.user.favorites.count()
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

def ajax_update_cart_quantity(request):
    """AJAX endpoint to update cart item quantity"""
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        quantity = int(request.POST.get('quantity', 1))

        try:
            if request.user.is_authenticated:
                cart_item = CartItem.objects.get(id=item_id, cart__user=request.user)
            else:
                cart_item = CartItem.objects.get(id=item_id, cart__session_key=request.session.session_key)

            cart_item.quantity = quantity
            cart_item.save()

            return JsonResponse({
                'success': True,
                'message': 'Cart updated'
            })

        except CartItem.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Cart item not found'})

    return JsonResponse({'success': False, 'message': 'Invalid request'})


def ajax_remove_from_cart(request):
    """AJAX endpoint to remove item from cart"""
    if request.method == 'POST':
        item_id = request.POST.get('item_id')

        try:
            if request.user.is_authenticated:
                cart_item = CartItem.objects.get(id=item_id, cart__user=request.user)
            else:
                cart_item = CartItem.objects.get(id=item_id, cart__session_key=request.session.session_key)

            cart = cart_item.cart
            cart_item.delete()

            return JsonResponse({
                'success': True,
                'message': 'Item removed from cart',
                'cart_total': cart.total_items
            })

        except CartItem.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Cart item not found'})

    return JsonResponse({'success': False, 'message': 'Invalid request'})
