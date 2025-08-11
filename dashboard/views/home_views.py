from django.shortcuts import render, get_object_or_404, redirect
from functools import wraps
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from datetime import datetime, timedelta
from store.models import Product, Order, Category
from django.db.models import Count, Sum, Avg, Q
import json
from django.contrib.auth.models import User






def is_staff_user(user):
    """Check if user is staff"""
    return user.is_staff


def dashboard_login_required(view_func):
    """Custom login_required decorator for dashboard that redirects to dashboard login"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('dashboard:login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def dashboard_login(request):
    """Dashboard login view"""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('dashboard:home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_staff:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            return redirect('dashboard:home')
        else:
            messages.error(request, 'Invalid username or password, or insufficient permissions.')

    return render(request, 'dashboard/login.html')


def dashboard_logout(request):
    """Dashboard logout view"""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('dashboard:login')


@dashboard_login_required
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
        count=Count('order_id')
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
    ).filter(product_count__gt=0).values('name_uz', 'product_count')

    context = {
        'total_products': total_products,
        'total_orders': total_orders,
        'total_users': total_users,
        'total_revenue': total_revenue,
        'recent_orders': recent_orders,
        'recent_users': recent_users,
        'recent_revenue': recent_revenue,
        'order_status_data': json.dumps(list(order_status_data)),
        'top_products': top_products,
        'most_liked': most_liked,
        'recent_orders_list': recent_orders_list,
        'monthly_revenue': json.dumps(monthly_revenue),
        'category_data': category_data,
    }

    return render(request, 'dashboard/home.html', context)