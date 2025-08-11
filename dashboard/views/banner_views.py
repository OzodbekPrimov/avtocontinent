
from django.contrib.auth.decorators import login_required, user_passes_test
from store.models import Banner
from .home_views import dashboard_login_required, is_staff_user
from django.db.models import Count, Sum, Avg, Q
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from dashboard.forms import BannerForm
from django.contrib import messages



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