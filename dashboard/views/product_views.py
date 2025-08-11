from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import  user_passes_test
from django.contrib import messages
from django.db.models import  Q
from django.core.paginator import Paginator
from .home_views import dashboard_login_required, is_staff_user
from store.models import Product, Category, CarModel
from dashboard.forms import ProductForm



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
