from .home_views import dashboard_login_required, is_staff_user
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from store.models import Category
from dashboard.forms import CategoryForm
from django.db.models import Count, Sum, Avg, Q
from django.core.paginator import Paginator



# Category CRUD Operations
@dashboard_login_required
@user_passes_test(is_staff_user)
def categories_management(request):
    """Categories management page"""
    categories = Category.objects.annotate(
        products_count=Count('product'),
    ).order_by('name_uz')

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        categories = categories.filter(
            Q(name_uz__icontains=search_query) |
            Q(name_uz_Cyrl__icontains=search_query) |
            Q(name_ru__icontains=search_query) |
            Q(description_uz__icontains=search_query) |
            Q(description_uz_Cyrl__icontains=search_query) |
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