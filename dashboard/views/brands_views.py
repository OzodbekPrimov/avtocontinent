from .home_views import dashboard_login_required, is_staff_user
from django.contrib.auth.decorators import  user_passes_test
from store.models import Brand
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.shortcuts import redirect, render, get_object_or_404
from dashboard.forms import BrandForm
from django.contrib import messages




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
            Q(name_cyrl__icontains=search_query) |
            Q(name_ru__icontains=search_query) |
            Q(description_uz__icontains=search_query) |
            Q(description_cyrl__icontains=search_query) |
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