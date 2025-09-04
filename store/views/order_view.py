
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from store.models import Cart, Order, OrderItem, PaymentSettings, ExchangeRate, Category
from store.utils import get_branch_by_id
from functools import wraps


def store_login_required(view_func):
    """Custom login_required decorator for store that redirects to store login"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@store_login_required
def checkout(request):
    """Checkout view"""
    categories = Category.objects.filter(is_active=True)[:6]
    try:

        cart = Cart.objects.get(user=request.user)
        if not cart.items.exists():
            messages.error(request, 'Your cart is empty.')
            return redirect('cart')
    except Cart.DoesNotExist:
        messages.error(request, 'Your cart is empty.')
        return redirect('cart')

    # Get payment settings
    payment_settings = PaymentSettings.objects.filter(is_active=True).first()

    if request.method == 'POST':
        # Create order
        exchange_rate = ExchangeRate.objects.filter(is_active=True).first()
        if not exchange_rate:
            messages.error(request, 'Exchange rate not set. Please contact support.')
            return redirect('checkout')

        # Get delivery information - only branch delivery
        delivery_branch_id = request.POST.get('delivery_branch_id')
        additional_instructions = request.POST.get('additional_instructions', '').strip()
        
        # Validate branch selection
        if delivery_branch_id:
            branch_info = get_branch_by_id(delivery_branch_id)
            if not branch_info:
                messages.error(request, 'Selected branch is not available.')
                return redirect('checkout')
        else:
            messages.error(request, 'Please select a delivery branch.')
            return redirect('checkout')

        order = Order.objects.create(
            user=request.user,
            total_amount_usd=cart.total_price_usd,
            total_amount_uzs=cart.total_price_uzs,
            exchange_rate_used=exchange_rate.usd_to_uzs,
            customer_name=request.POST.get('customer_name'),
            customer_phone=request.POST.get('customer_phone'),
            delivery_branch_id=delivery_branch_id,
            additional_instructions=additional_instructions,
        )

        # Create order items
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price_usd=cart_item.product.price_usd,
                price_uzs=cart_item.product.price_uzs
            )

        # Clear cart
        cart.items.all().delete()

        messages.success(request, 'Order created successfully!')
        return redirect('order_payment', order_id=order.order_id)

    context = {
        'cart': cart,
        'payment_settings': payment_settings,
        'categories':categories
    }

    return render(request, 'store/checkout.html', context)


@store_login_required
def order_payment(request, order_id):
    """Order payment view"""
    categories = Category.objects.filter(is_active=True)[:4]
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    payment_settings = PaymentSettings.objects.filter(is_active=True).first()

    if request.method == 'POST':
        if request.FILES.get('payment_screenshot'):
            order.payment_screenshot = request.FILES['payment_screenshot']

            # Mahsulot sonini kamaytirish
            for order_item in order.items.all():
                product = order_item.product
                if product.stock_quantity >= order_item.quantity:
                    product.stock_quantity -= order_item.quantity
                    product.save(update_fields=['stock_quantity'])
                else:
                    messages.error(request,
                                   f'{product.name} mahsulotidan yetarli miqdor yo\'q. Mavjud: {product.stock_quantity}')
                    return redirect('order_payment', order_id=order.order_id)

            order.save(update_fields=['payment_screenshot'])
            messages.success(request, 'Payment screenshot uploaded successfully!')
            return redirect('order_detail', order_id=order.order_id)

    context = {
        'order': order,
        'payment_settings': payment_settings,
        'categories': categories
    }

    return render(request, 'store/order_payment.html', context)


@store_login_required
def order_detail(request, order_id):
    """Order detail view"""
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    categories = Category.objects.filter(is_active=True)[:4]

    context = {
        'order': order,
        'categories':categories
    }

    return render(request, 'store/order_detail.html', context)


@store_login_required
def order_history(request):
    """Order history view"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    categories = Category.objects.filter(is_active=True)[:4]

    context = {
        'orders': orders,
        'categories':categories
    }

    return render(request, 'store/order_history.html', context)