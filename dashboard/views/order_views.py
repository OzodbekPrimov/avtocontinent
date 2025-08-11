from .home_views import dashboard_login_required, is_staff_user
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from store.models import Order
from django.db.models import  Q
from dashboard.forms import OrderForm
from django.core.paginator import Paginator




# Order Management
@dashboard_login_required
@user_passes_test(is_staff_user)
def orders_management(request):
    """Orders management page"""
    orders = Order.objects.select_related('user').order_by('-created_at')

    # Search and filter
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    payment_filter = request.GET.get('payment', '')

    if search_query:
        orders = orders.filter(
            Q(order_id__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(customer_phone__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )

    if status_filter:
        orders = orders.filter(status=status_filter)

    if payment_filter == 'confirmed':
        orders = orders.filter(payment_confirmed=True)
    elif payment_filter == 'pending':
        orders = orders.filter(payment_confirmed=False)

    # Pagination
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'payment_filter': payment_filter,
        'order_status_choices': Order.STATUS_CHOICES,
    }

    return render(request, 'dashboard/orders.html', context)


@dashboard_login_required
@user_passes_test(is_staff_user)
def order_detail(request, order_id):
    """Order detail page"""
    order = get_object_or_404(Order, order_id=order_id)

    if request.method == 'POST':
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, 'Order updated successfully!')
            return redirect('dashboard:order_detail', order_id=order_id)
    else:
        form = OrderForm(instance=order)

    context = {
        'order': order,
        'form': form,
        'status_choices': Order.STATUS_CHOICES,
    }

    return render(request, 'dashboard/order_detail.html', context)