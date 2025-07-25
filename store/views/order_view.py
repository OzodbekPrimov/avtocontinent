
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from store.models import Cart, Order, OrderItem, PaymentSettings, ExchangeRate


@login_required
def checkout(request):
    """Checkout view"""
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

        order = Order.objects.create(
            user=request.user,
            total_amount_usd=cart.total_price_usd,
            total_amount_uzs=cart.total_price_uzs,
            exchange_rate_used=exchange_rate.usd_to_uzs,
            customer_name=request.POST.get('customer_name'),
            customer_phone=request.POST.get('customer_phone'),
            customer_address=request.POST.get('customer_address'),
            delivery_address=request.POST.get('delivery_address'),
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
    }

    return render(request, 'store/checkout.html', context)

@login_required
def order_payment(request, order_id):
    """Order payment view"""
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    payment_settings = PaymentSettings.objects.filter(is_active=True).first()

    if request.method == 'POST':
        if request.FILES.get('payment_screenshot'):
            order.payment_screenshot = request.FILES['payment_screenshot']
            order.save(update_fields=['payment_screenshot'])  # update_fields qo'shildi
            messages.success(request, 'Payment screenshot uploaded successfully!')
            return redirect('order_detail', order_id=order.order_id)

    context = {
        'order': order,
        'payment_settings': payment_settings,
    }

    return render(request, 'store/order_payment.html', context)


@login_required
def order_detail(request, order_id):
    """Order detail view"""
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    context = {
        'order': order,
    }

    return render(request, 'store/order_detail.html', context)


@login_required
def order_history(request):
    """Order history view"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    context = {
        'orders': orders,
    }

    return render(request, 'store/order_history.html', context)