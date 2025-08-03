from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from functools import wraps
from django.urls import reverse
from django.http import JsonResponse
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json

from store.models import (
    Product, Category, Brand, CarModel, Order, OrderItem,
    ProductLike, ProductComment, Favorite, Cart, CartItem,
    UserProfile, ExchangeRate, Banner, PaymentSettings
)
from django.contrib.auth.models import User
from .forms import (
    BannerForm, CarModelForm, ProductForm, CategoryForm, BrandForm,
    OrderForm, ExchangeRateForm, PaymentSettingsForm
)


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


# Form classes are now imported from forms.py


@dashboard_login_required
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


# Banner CRUD Operations
@dashboard_login_required
@user_passes_test(is_staff_user)
def banners_management(request):
    """Banners management page"""
    banners = Banner.objects.order_by('order', '-created_at')

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        banners = banners.filter(
            Q(title_uz__icontains=search_query) |
            Q(title_en__icontains=search_query) |
            Q(title_ru__icontains=search_query)

        )

    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        banners = banners.filter(is_active=True)
    elif status_filter == 'inactive':
        banners = banners.filter(is_active=False)

    # Pagination
    paginator = Paginator(banners, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
    }

    return render(request, 'dashboard/banners.html', context)


@dashboard_login_required
@user_passes_test(is_staff_user)
def banner_create(request):
    """Create new banner"""
    if request.method == 'POST':
        form = BannerForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Banner created successfully!')
            return redirect('dashboard:banners')
        else:
            # Form is invalid, render with errors
            context = {
                'form': form,
                'title': 'Create Banner',
                'action': 'Create'
            }
            return render(request, 'dashboard/banner_form.html', context)
    else:
        form = BannerForm()

    context = {
        'form': form,
        'title': 'Create Banner',
        'action': 'Create'
    }
    return render(request, 'dashboard/banner_form.html', context)


@dashboard_login_required
@user_passes_test(is_staff_user)
def banner_edit(request, banner_id):
    """Edit banner"""
    banner = get_object_or_404(Banner, pk=banner_id)

    if request.method == 'POST':
        form = BannerForm(request.POST, request.FILES, instance=banner)
        if form.is_valid():
            form.save()
            messages.success(request, 'Banner updated successfully!')
            return redirect('dashboard:banners')
        else:
            # Form is invalid, render with errors
            context = {
                'form': form,
                'banner': banner,
                'title': 'Edit Banner',
                'action': 'Update'
            }
            return render(request, 'dashboard/banner_form.html', context)
    else:
        form = BannerForm(instance=banner)

    context = {
        'form': form,
        'banner': banner,
        'title': 'Edit Banner',
        'action': 'Update'
    }
    return render(request, 'dashboard/banner_form.html', context)


@dashboard_login_required
@user_passes_test(is_staff_user)
def banner_delete(request, banner_id):
    """Delete banner"""
    banner = get_object_or_404(Banner, pk=banner_id)

    if request.method == 'POST':
        banner.delete()
        messages.success(request, 'Banner deleted successfully!')
        return redirect('dashboard:banners')

    context = {
        'banner': banner,
        'title': 'Delete Banner'
    }
    return render(request, 'dashboard/banner_confirm_delete.html', context)


# Brand CRUD Operations
@dashboard_login_required
@user_passes_test(is_staff_user)
def brands_management(request):
    """Brands management page"""
    brands = Brand.objects.annotate(
        model_count=Count('models'),
        product_count=Count('models__products')
    ).order_by('name_uz')

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        brands = brands.filter(
            Q(name_uz__icontains=search_query) |
            Q(name_en__icontains=search_query) |
            Q(name_ru__icontains=search_query) |
            Q(description_uz__icontains=search_query) |
            Q(description_en__icontains=search_query) |
            Q(description_ru__icontains=search_query)
        )

    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        brands = brands.filter(is_active=True)
    elif status_filter == 'inactive':
        brands = brands.filter(is_active=False)

    # Pagination
    paginator = Paginator(brands, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
    }

    return render(request, 'dashboard/brands.html', context)


@dashboard_login_required
@user_passes_test(is_staff_user)
def brand_create(request):
    """Create new brand"""
    if request.method == 'POST':
        form = BrandForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Brand created successfully!')
            return redirect('dashboard:brands')
        else:
            # Form is invalid, render with errors
            context = {
                'form': form,
                'title': 'Create Brand',
                'action': 'Create'
            }
            return render(request, 'dashboard/brand_form.html', context)
    else:
        form = BrandForm()

    context = {
        'form': form,
        'title': 'Create Brand',
        'action': 'Create'
    }
    return render(request, 'dashboard/brand_form.html', context)


@dashboard_login_required
@user_passes_test(is_staff_user)
def brand_edit(request, brand_id):
    """Edit brand"""
    brand = get_object_or_404(Brand, pk=brand_id)

    if request.method == 'POST':
        form = BrandForm(request.POST, request.FILES, instance=brand)
        if form.is_valid():
            form.save()
            messages.success(request, 'Brand updated successfully!')
            return redirect('dashboard:brands')
        else:
            # Form is invalid, render with errors
            context = {
                'form': form,
                'brand': brand,
                'title': 'Edit Brand',
                'action': 'Update'
            }
            return render(request, 'dashboard/brand_form.html', context)
    else:
        form = BrandForm(instance=brand)

    context = {
        'form': form,
        'brand': brand,
        'title': 'Edit Brand',
        'action': 'Update'
    }
    return render(request, 'dashboard/brand_form.html', context)


@dashboard_login_required
@user_passes_test(is_staff_user)
def brand_delete(request, brand_id):
    """Delete brand"""
    brand = get_object_or_404(Brand, pk=brand_id)

    if request.method == 'POST':
        brand.delete()
        messages.success(request, 'Brand deleted successfully!')
        return redirect('dashboard:brands')

    context = {
        'brand': brand,
        'title': 'Delete Brand'
    }
    return render(request, 'dashboard/brand_confirm_delete.html', context)


# Car Model CRUD Operations
@dashboard_login_required
@user_passes_test(is_staff_user)
def models_management(request):
    """Car models management page"""
    models = CarModel.objects.select_related('brand').annotate(
        product_count=Count('products')
    ).order_by('brand__name_uz', 'name_uz')

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        models = models.filter(
            Q(name_uz__icontains=search_query) |
            Q(name_en__icontains=search_query) |
            Q(name_ru__icontains=search_query) |
            Q(brand__name_uz__icontains=search_query) |
            Q(brand__name_en__icontains=search_query) |
            Q(brand__name_ru__icontains=search_query) |
            Q(description_uz__icontains=search_query) |
            Q(description_en__icontains=search_query) |
            Q(description_ru__icontains=search_query)
        )

    # Filter by brand
    brand_filter = request.GET.get('brand', '')
    if brand_filter:
        models = models.filter(brand_id=brand_filter)

    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        models = models.filter(is_active=True)
    elif status_filter == 'inactive':
        models = models.filter(is_active=False)

    # Pagination
    paginator = Paginator(models, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    brands = Brand.objects.filter(is_active=True)

    context = {
        'page_obj': page_obj,
        'brands': brands,
        'search_query': search_query,
        'brand_filter': brand_filter,
        'status_filter': status_filter,
    }

    return render(request, 'dashboard/models.html', context)


@dashboard_login_required
@user_passes_test(is_staff_user)
def model_create(request):
    """Create new car model"""
    brands = Brand.objects.filter(is_active=True)
    
    if request.method == 'POST':
        form = CarModelForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Car model created successfully!')
            return redirect('dashboard:models')
        else:
            # Form is invalid, render with errors
            context = {
                'form': form,
                'brands': brands,
                'title': 'Create Car Model',
                'action': 'Create'
            }
            return render(request, 'dashboard/model_form.html', context)
    else:
        form = CarModelForm()

    context = {
        'form': form,
        'brands': brands,
        'title': 'Create Car Model',
        'action': 'Create'
    }
    return render(request, 'dashboard/model_form.html', context)


@dashboard_login_required
@user_passes_test(is_staff_user)
def model_edit(request, model_id):
    """Edit car model"""
    model = get_object_or_404(CarModel, pk=model_id)
    brands = Brand.objects.filter(is_active=True)

    if request.method == 'POST':
        form = CarModelForm(request.POST, request.FILES, instance=model)
        if form.is_valid():
            form.save()
            messages.success(request, 'Car model updated successfully!')
            return redirect('dashboard:models')
        else:
            # Form is invalid, render with errors
            context = {
                'form': form,
                'model': model,
                'brands': brands,
                'title': 'Edit Car Model',
                'action': 'Update'
            }
            return render(request, 'dashboard/model_form.html', context)
    else:
        form = CarModelForm(instance=model)

    context = {
        'form': form,
        'model': model,
        'brands': brands,
        'title': 'Edit Car Model',
        'action': 'Update'
    }
    return render(request, 'dashboard/model_form.html', context)


@dashboard_login_required
@user_passes_test(is_staff_user)
def model_delete(request, model_id):
    """Delete car model"""
    model = get_object_or_404(CarModel, pk=model_id)

    if request.method == 'POST':
        model.delete()
        messages.success(request, 'Car model deleted successfully!')
        return redirect('dashboard:models')

    context = {
        'model': model,
        'title': 'Delete Car Model'
    }
    return render(request, 'dashboard/model_confirm_delete.html', context)


# Category CRUD Operations
@dashboard_login_required
@user_passes_test(is_staff_user)
def categories_management(request):
    """Categories management page"""
    categories = Category.objects.annotate(
        product_count=Count('product'),
    ).order_by('name_uz')

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        categories = categories.filter(
            Q(name_uz__icontains=search_query) |
            Q(name_en__icontains=search_query) |
            Q(name_ru__icontains=search_query) |
            Q(description_uz__icontains=search_query) |
            Q(description_en__icontains=search_query) |
            Q(description_ru__icontains=search_query)
        )

    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        categories = categories.filter(is_active=True)
    elif status_filter == 'inactive':
        categories = categories.filter(is_active=False)

    # Pagination
    paginator = Paginator(categories, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
    }

    return render(request, 'dashboard/categories.html', context)


@dashboard_login_required
@user_passes_test(is_staff_user)
def category_create(request):
    """Create new category"""
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category created successfully!')
            return redirect('dashboard:categories')
        else:
            # Form is invalid, render with errors
            context = {
                'form': form,
                'title': 'Create Category',
                'action': 'Create'
            }
            return render(request, 'dashboard/category_form.html', context)
    else:
        form = CategoryForm()

    context = {
        'form': form,
        'title': 'Create Category',
        'action': 'Create'
    }
    return render(request, 'dashboard/category_form.html', context)

# from django import forms
from modeltranslation import forms

@dashboard_login_required
@user_passes_test(is_staff_user)
def category_edit(request, category_id):
    category = get_object_or_404(Category, pk=category_id)

    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Kategoriya muvaffaqiyatli tahrirlandi!")
            return redirect('dashboard:categories')
        else:
            # Form is invalid, render with errors
            return render(request, 'dashboard/category_form.html', {
                'form': form,
                'category': category,
                'title': "Kategoriyani Tahrirlash",
                'action': "Saqlash"
            })
    else:
        form = CategoryForm(instance=category)

    return render(request, 'dashboard/category_form.html', {
        'form': form,
        'category': category,
        'title': "Kategoriyani Tahrirlash",
        'action': "Saqlash"
    })


@dashboard_login_required
@user_passes_test(is_staff_user)
def category_delete(request, category_id):
    """Delete category"""
    category = get_object_or_404(Category, pk=category_id)

    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Category deleted successfully!')
        return redirect('dashboard:categories')

    context = {
        'category': category,
        'title': 'Delete Category'
    }
    return render(request, 'dashboard/category_confirm_delete.html', context)


# Product CRUD Operations
@dashboard_login_required
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
            Q(name_uz__icontains=search_query) |
            Q(name_en__icontains=search_query) |
            Q(name_ru__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(description_uz__icontains=search_query) |
            Q(description_en__icontains=search_query) |
            Q(description_ru__icontains=search_query)
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


@dashboard_login_required
@user_passes_test(is_staff_user)
def product_create(request):
    """Create new product"""
    categories = Category.objects.filter(is_active=True)
    car_models = CarModel.objects.filter(is_active=True).select_related('brand')
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product created successfully!')
            return redirect('dashboard:products')
        else:
            # Form is invalid, render with errors
            context = {
                'form': form,
                'categories': categories,
                'car_models': car_models,
                'title': 'Create Product',
                'action': 'Create'
            }
            return render(request, 'dashboard/product_form.html', context)
    else:
        form = ProductForm()

    context = {
        'form': form,
        'categories': categories,
        'car_models': car_models,
        'title': 'Create Product',
        'action': 'Create'
    }
    return render(request, 'dashboard/product_form.html', context)


@dashboard_login_required
@user_passes_test(is_staff_user)
def product_edit(request, product_id):
    """Edit product"""
    product = get_object_or_404(Product, pk=product_id)
    categories = Category.objects.filter(is_active=True)
    car_models = CarModel.objects.filter(is_active=True).select_related('brand')

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('dashboard:products')
        else:
            # Form is invalid, render with errors
            context = {
                'form': form,
                'product': product,
                'categories': categories,
                'car_models': car_models,
                'title': 'Edit Product',
                'action': 'Update'
            }
            return render(request, 'dashboard/product_form.html', context)
    else:
        form = ProductForm(instance=product)

    context = {
        'form': form,
        'product': product,
        'categories': categories,
        'car_models': car_models,
        'title': 'Edit Product',
        'action': 'Update'
    }
    return render(request, 'dashboard/product_form.html', context)


@dashboard_login_required
@user_passes_test(is_staff_user)
def product_delete(request, product_id):
    """Delete product"""
    product = get_object_or_404(Product, pk=product_id)

    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully!')
        return redirect('dashboard:products')

    context = {
        'product': product,
        'title': 'Delete Product'
    }
    return render(request, 'dashboard/product_confirm_delete.html', context)


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


@dashboard_login_required
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


# AJAX Endpoints
@dashboard_login_required
@user_passes_test(is_staff_user)
@require_POST
def ajax_toggle_product_status(request):
    """AJAX endpoint to toggle product status"""
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


@dashboard_login_required
@user_passes_test(is_staff_user)
@require_POST
def ajax_toggle_product_featured(request):
    """AJAX endpoint to toggle product featured status"""
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


@dashboard_login_required
@user_passes_test(is_staff_user)
@require_POST
def ajax_toggle_banner_status(request):
    try:
        banner_id = request.POST.get('banner_id')
        is_active = request.POST.get('is_active') == 'true'

        # Ma'lumotlar bazasida banner borligini tekshirish
        banner = Banner.objects.get(id=banner_id)
        print(f"Oldingi holat: {banner.is_active}, Yangi holat: {is_active}")  # Debug uchun

        # Statusni yangilash
        banner.is_active = is_active
        banner.save()

        # Yangilangan holatni tekshirish
        updated_banner = Banner.objects.get(id=banner_id)
        print(f"Yangilangan holat: {updated_banner.is_active}")  # Debug uchun

        return JsonResponse({'success': True, 'new_status': updated_banner.is_active})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@dashboard_login_required
@user_passes_test(is_staff_user)
@require_POST
def ajax_toggle_brand_status(request):
    try:
        brand_id = request.POST.get('brand_id')
        if not brand_id:
            return JsonResponse({'success': False, 'message': 'Brand ID required'})

        brand = get_object_or_404(Brand, id=brand_id)
        brand.is_active = not brand.is_active
        brand.save()

        return JsonResponse({
            'success': True,
            'message': 'Status updated successfully',
            'new_status': brand.is_active
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@dashboard_login_required
@require_POST
def ajax_delete_brand(request):
    try:
        brand_id = request.POST.get('brand_id')
        if not brand_id:
            return JsonResponse({'success': False, 'message': 'Brand ID required'})

        brand = get_object_or_404(Brand, id=brand_id)
        brand.delete()

        return JsonResponse({'success': True, 'message': 'Brand deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@dashboard_login_required
@user_passes_test(is_staff_user)
@require_POST
def ajax_toggle_model_status(request):
    try:
        model_id = request.POST.get('model_id')
        if not model_id:
            return JsonResponse({'success': False, 'message': 'Model ID required'})

        model = get_object_or_404(CarModel, id=model_id)  # CarModel yoki sizning model nomingiz
        model.is_active = not model.is_active
        model.save()

        return JsonResponse({
            'success': True,
            'message': 'Model status updated successfully',
            'new_status': model.is_active
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@dashboard_login_required
@require_POST
def ajax_delete_model(request):
    try:
        model_id = request.POST.get('model_id')
        if not model_id:
            return JsonResponse({'success': False, 'message': 'Model ID required'})

        model = get_object_or_404(CarModel, id=model_id)
        model.delete()

        return JsonResponse({'success': True, 'message': 'Model deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@dashboard_login_required
@user_passes_test(is_staff_user)
@require_POST
def ajax_toggle_category_status(request):
    category_id = request.POST.get('category_id')
    is_active = request.POST.get('is_active') == 'true'

    try:
        category = Category.objects.get(id=category_id)
        category.is_active = is_active
        category.save()  # 👉 MUHIM!
        return JsonResponse({'success': True, 'new_status': category.is_active})
    except Category.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Category not found'})


@dashboard_login_required
@user_passes_test(is_staff_user)
@require_POST
def ajax_update_order_status(request):
    """AJAX endpoint to update order status"""
    order_id = request.POST.get('order_id')
    new_status = request.POST.get('status')

    try:
        order = Order.objects.get(order_id=order_id)
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()

            return JsonResponse({
                'success': True,
                'status': order.status,
                'status_display': order.get_status_display()
            })
        else:
            return JsonResponse({'success': False, 'message': 'Invalid status'})
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'})


@dashboard_login_required
@user_passes_test(is_staff_user)
@require_POST
def ajax_confirm_payment(request):
    """AJAX endpoint to confirm payment"""
    order_id = request.POST.get('order_id')

    try:
        order = Order.objects.get(order_id=order_id)
        order.payment_confirmed = True
        order.payment_confirmed_at = timezone.now()
        order.save()

        return JsonResponse({
            'success': True,
            'payment_confirmed': order.payment_confirmed
        })
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'})


@dashboard_login_required
@user_passes_test(is_staff_user)
@require_POST
def ajax_reject_payment(request):
    """AJAX endpoint to reject payment"""
    order_id = request.POST.get('order_id')

    try:
        order = Order.objects.get(order_id=order_id)
        order.payment_confirmed = False
        order.payment_confirmed_at = None
        order.save()

        return JsonResponse({
            'success': True,
            'payment_confirmed': order.payment_confirmed
        })
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'})