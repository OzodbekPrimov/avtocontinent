from .home_views import dashboard_login_required, is_staff_user
from django.contrib.auth.decorators import login_required, user_passes_test
from store.models import CarModel, Brand
from dashboard.forms import CarModelForm
from django.db.models import Count, Sum, Avg, Q
from django.core.paginator import Paginator
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages





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