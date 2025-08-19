from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import  user_passes_test
from django.contrib import messages
from django.db.models import  Q, Count, F
from django.core.paginator import Paginator
from .home_views import dashboard_login_required, is_staff_user
from store.models import Product, Category, CarModel, ProductImage
from dashboard.forms import ProductForm



@dashboard_login_required
@user_passes_test(is_staff_user)
def products_management(request):
    """Products management page"""
    products = (Product.objects
                .select_related('category')
                .annotate(
                    cart_count=Count('cartitem__cart__user', filter=Q(cartitem__cart__user__isnull=False), distinct=True)
                )
                .order_by('-created_at'))

    # Search and filter
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')
    cart_filter = request.GET.get('cart_filter', '')

    if search_query:
        products = products.filter(
            Q(name_uz__icontains=search_query) |
            Q(name_cyrl__icontains=search_query) |
            Q(name_ru__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(description_uz__icontains=search_query) |
            Q(description_cyrl__icontains=search_query) |
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

    # Cart analytics filters
    if cart_filter == 'critical':
        # stock < people in carts and carts > 0
        products = products.filter(
            Q(cart_count__gt=F('stock_quantity')) & Q(cart_count__gt=0)
        )
    elif cart_filter == 'popular':
        products = products.filter(cart_count__gte=5)
    elif cart_filter == 'zero':
        products = products.filter(cart_count=0)

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
        'cart_filter': cart_filter,
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
            product = form.save()

            # Validate and save all additional images (no limit)
            extra_files = request.FILES.getlist('extra_images')
            if extra_files:
                errors = []
                saved = 0
                valid_ext = {"jpg", "jpeg", "png", "gif", "webp"}
                max_size = 5 * 1024 * 1024

                for f in extra_files:
                    if getattr(f, 'size', 0) > max_size:
                        errors.append("Каждое изображение должно быть не более 5MB.")
                        continue
                    ext = f.name.rsplit('.', 1)[-1].lower() if hasattr(f, 'name') and '.' in f.name else ''
                    if ext not in valid_ext:
                        errors.append("Допустимые форматы: jpg, jpeg, png, gif, webp.")
                        continue
                    ProductImage.objects.create(product=product, image=f)
                    saved += 1

                if saved:
                    messages.success(request, f"Добавлено дополнительных изображений: {saved}.")
                if errors:
                    for e in set(errors):
                        messages.warning(request, e)

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
            product = form.save()

            # Validate and save all additional images (no limit)
            extra_files = request.FILES.getlist('extra_images')
            if extra_files:
                errors = []
                saved = 0
                valid_ext = {"jpg", "jpeg", "png", "gif", "webp"}
                max_size = 5 * 1024 * 1024

                for f in extra_files:
                    if getattr(f, 'size', 0) > max_size:
                        errors.append("Каждое изображение должно быть не более 5MB.")
                        continue
                    ext = f.name.rsplit('.', 1)[-1].lower() if hasattr(f, 'name') and '.' in f.name else ''
                    if ext not in valid_ext:
                        errors.append("Допустимые форматы: jpg, jpeg, png, gif, webp.")
                        continue
                    ProductImage.objects.create(product=product, image=f, is_primary=False)
                    saved += 1

                if saved:
                    messages.success(request, f"Добавлено дополнительных изображений: {saved}.")
                if errors:
                    for e in set(errors):
                        messages.warning(request, e)

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
