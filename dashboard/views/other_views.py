from django.shortcuts import render, redirect
from django.contrib.auth.decorators import user_passes_test

from django.db.models import Count, Sum,  Q
from django.utils import timezone
from datetime import  timedelta
from django.core.paginator import Paginator
from .home_views import dashboard_login_required, is_staff_user
import json
from django.contrib.auth.models import User
from store.models import Order, Product, Category




@dashboard_login_required
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


@dashboard_login_required
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
            count=Count('order_id')
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
        likes_count=Count('likes'),
        comments_count=Count('comments'),
        revenue=Sum('orderitem__price_uzs')
    ).filter(order_count__gt=0).order_by('-revenue')[:10]

    # Category performance
    category_performance = Category.objects.annotate(
        products_count=Count('product'),
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


