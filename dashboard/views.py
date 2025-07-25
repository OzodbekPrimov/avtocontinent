from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.paginator import Paginator
import json

from store.models import (
    Product, Category, Brand, CarModel, Order, OrderItem,
    ProductLike, ProductComment, Favorite, Cart, CartItem,
    UserProfile, ExchangeRate, Banner, PaymentSettings
)
from django.contrib.auth.models import User


def is_staff_user(user):
    """Check if user is staff"""
    return user.is_staff


@login_required
@user_passes_test(is_staff_user)
def dashboard_home(request):
    """Dashboard home with analytics"""
    # Date range for analytics
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Basic stats
    total_products = Product.objects.filter(is_active=True).count()
    total_orders = Order.objects.count()
    total_users = User.objects.count()
    total_revenue = Order.objects.filter(payment_confirmed=True).aggregate(
        total=Sum('total_amount_uzs')
    )['total'] or 0
    
    # Recent stats
    recent_orders = Order.objects.filter(created_at__gte=week_ago).count()
    recent_users = User.objects.filter(date_joined__gte=week_ago).count()
    recent_revenue = Order.objects.filter(
        created_at__gte=week_ago,
        payment_confirmed=True
    ).aggregate(total=Sum('total_amount_uzs'))['total'] or 0
    
    # Order status distribution
    order_status_data = Order.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # Top selling products
    top_products = Product.objects.annotate(
        order_count=Count('orderitem')
    ).filter(order_count__gt=0).order_by('-order_count')[:5]
    
    # Most liked products
    most_liked = Product.objects.annotate(
        likes_count=Count('likes')
    ).filter(likes_count__gt=0).order_by('-likes_count')[:5]
    
    # Recent orders
    recent_orders_list = Order.objects.select_related('user').order_by('-created_at')[:10]
    
    # Monthly revenue chart data
    monthly_revenue = []
    for i in range(12):
        month_start = today.replace(day=1) - timedelta(days=30*i)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        revenue = Order.objects.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=month_end,
            payment_confirmed=True
        ).aggregate(total=Sum('total_amount_uzs'))['total'] or 0
        monthly_revenue.append({
            'month': month_start.strftime('%b %Y'),
            'revenue': float(revenue)
        })
    
    monthly_revenue.reverse()
    
    # Category distribution
    category_data = Category.objects.annotate(
        product_count=Count('product')
    ).filter(product_count__gt=0)
    
    context = {
        'total_products': total_products,
        'total_orders': total_orders,
        'total_users': total_users,
        'total_revenue': total_revenue,
        'recent_orders': recent_orders,
        'recent_users': recent_users,
        'recent_revenue': recent_revenue,
        'order_status_data': order_status_data,
        'top_products': top_products,
        'most_liked': most_liked,
        'recent_orders_list': recent_orders_list,
        'monthly_revenue': json.dumps(monthly_revenue),
        'category_data': category_data,
    }
    
    return render(request, 'dashboard/home.html', context)


@login_required
@user_passes_test(is_staff_user)
def products_management(request):
    """Products management page"""
    products = Product.objects.select_related('category').order_by('-created_at')
    
    # Search and filter
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    if category_filter:
        products = products.filter(category_id=category_filter)
    
    if status_filter == 'active':
        products = products.filter(is_active=True)
    elif status_filter == 'inactive':
        products = products.filter(is_active=False)
    elif status_filter == 'featured':
        products = products.filter(is_featured=True)
    elif status_filter == 'out_of_stock':
        products = products.filter(stock_quantity=0)
    
    # Pagination
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categories = Category.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'search_query': search_query,
        'category_filter': category_filter,
        'status_filter': status_filter,
    }
    
    return render(request, 'dashboard/products.html', context)


@login_required
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


@login_required
@user_passes_test(is_staff_user)
def order_detail(request, order_id):
    """Order detail page"""
    order = get_object_or_404(Order, order_id=order_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_status':
            new_status = request.POST.get('status')
            if new_status in dict(Order.STATUS_CHOICES):
                order.status = new_status
                order.save()
                messages.success(request, f'Order status updated to {order.get_status_display()}')
        
        elif action == 'confirm_payment':
            order.payment_confirmed = True
            order.payment_confirmed_at = timezone.now()
            order.save()
            messages.success(request, 'Payment confirmed successfully')
        
        elif action == 'reject_payment':
            order.payment_confirmed = False
            order.payment_confirmed_at = None
            order.save()
            messages.success(request, 'Payment rejected')
        
        return redirect('dashboard:order_detail', order_id=order_id)
    
    context = {
        'order': order,
        'status_choices': Order.STATUS_CHOICES,
    }
    
    return render(request, 'dashboard/order_detail.html', context)


@login_required
@user_passes_test(is_staff_user)
def users_management(request):
    """Users management page"""
    users = User.objects.select_related('userprofile').order_by('-date_joined')
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(userprofile__phone_number__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'dashboard/users.html', context)


@login_required
@user_passes_test(is_staff_user)
def analytics(request):
    """Analytics page"""
    # Date range
    today = timezone.now().date()
    
    # Sales analytics
    daily_sales = []
    for i in range(30):
        date = today - timedelta(days=i)
        sales = Order.objects.filter(
            created_at__date=date,
            payment_confirmed=True
        ).aggregate(
            total=Sum('total_amount_uzs'),
            count=Count('id')
        )
        daily_sales.append({
            'date': date.strftime('%Y-%m-%d'),
            'sales': float(sales['total'] or 0),
            'orders': sales['count']
        })
    
    daily_sales.reverse()
    
    # Product performance
    product_performance = Product.objects.annotate(
        order_count=Count('orderitem'),
        like_count=Count('likes'),
        comment_count=Count('comments'),
        revenue=Sum('orderitem__price_uzs')
    ).filter(order_count__gt=0).order_by('-revenue')[:10]
    
    # Category performance
    category_performance = Category.objects.annotate(
        product_count=Count('product'),
        order_count=Count('product__orderitem'),
        revenue=Sum('product__orderitem__price_uzs')
    ).filter(order_count__gt=0).order_by('-revenue')
    
    # User engagement
    user_stats = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(last_login__gte=today - timedelta(days=30)).count(),
        'new_users_this_month': User.objects.filter(date_joined__gte=today - timedelta(days=30)).count(),
        'users_with_orders': User.objects.filter(orders__isnull=False).distinct().count(),
    }
    
    context = {
        'daily_sales': json.dumps(daily_sales),
        'product_performance': product_performance,
        'category_performance': category_performance,
        'user_stats': user_stats,
    }
    
    return render(request, 'dashboard/analytics.html', context)


@login_required
@user_passes_test(is_staff_user)
def settings_management(request):
    """Settings management page"""
    exchange_rate = ExchangeRate.objects.filter(is_active=True).first()
    payment_settings = PaymentSettings.objects.filter(is_active=True).first()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_exchange_rate':
            new_rate = request.POST.get('exchange_rate')
            try:
                rate = float(new_rate)
                if exchange_rate:
                    exchange_rate.is_active = False
                    exchange_rate.save()
                
                ExchangeRate.objects.create(
                    usd_to_uzs=rate,
                    is_active=True,
                    created_by=request.user
                )
                messages.success(request, 'Exchange rate updated successfully')
            except ValueError:
                messages.error(request, 'Invalid exchange rate value')
        
        elif action == 'update_payment_settings':
            card_number = request.POST.get('card_number')
            card_holder = request.POST.get('card_holder')
            bank_name = request.POST.get('bank_name')
            
            if payment_settings:
                payment_settings.is_active = False
                payment_settings.save()
            
            PaymentSettings.objects.create(
                card_number=card_number,
                card_holder_name=card_holder,
                bank_name=bank_name,
                is_active=True
            )
            messages.success(request, 'Payment settings updated successfully')
        
        return redirect('dashboard:settings')
    
    context = {
        'exchange_rate': exchange_rate,
        'payment_settings': payment_settings,
    }
    
    return render(request, 'dashboard/settings.html', context)


@login_required
@user_passes_test(is_staff_user)
def ajax_toggle_product_status(request):
    """AJAX endpoint to toggle product status"""
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        try:
            product = Product.objects.get(pk=product_id)
            product.is_active = not product.is_active
            product.save()
            
            return JsonResponse({
                'success': True,
                'is_active': product.is_active
            })
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Product not found'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


@login_required
@user_passes_test(is_staff_user)
def ajax_toggle_product_featured(request):
    """AJAX endpoint to toggle product featured status"""
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        try:
            product = Product.objects.get(pk=product_id)
            product.is_featured = not product.is_featured
            product.save()
            
            return JsonResponse({
                'success': True,
                'is_featured': product.is_featured
            })
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Product not found'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})