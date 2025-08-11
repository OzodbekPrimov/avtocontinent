from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import  user_passes_test
from django.contrib import messages
from .home_views import dashboard_login_required
from django.db.models import  Q
from store.models import AdminProfile, ExchangeRate, PaymentSettings
from dashboard.forms import AdminCreateForm, AdminEditForm, PaymentSettingsForm
from django.core.paginator import Paginator
from django.contrib.auth.models import User


def can_access_settings(user):
    """Check if user can access settings section"""
    if not user.is_staff:
        return False
    if user.is_superuser:
        return True
    try:
        admin_profile = user.admin_profile
        return admin_profile.can_access_settings
    except AdminProfile.DoesNotExist:
        # If no admin profile exists, assume it's a legacy admin with full access
        return True


def can_access_users(user):
    """Check if user can access users management"""
    if not user.is_staff:
        return False
    if user.is_superuser:
        return True
    try:
        admin_profile = user.admin_profile
        return admin_profile.can_access_users
    except AdminProfile.DoesNotExist:
        # If no admin profile exists, assume it's a legacy admin with full access
        return True


def can_access_admins(user):
    """Check if user can access admin management"""
    if not user.is_staff:
        return False
    if user.is_superuser:
        return True
    try:
        admin_profile = user.admin_profile
        return admin_profile.can_access_admins
    except AdminProfile.DoesNotExist:
        # If no admin profile exists, assume it's a legacy admin with full access
        return True



@dashboard_login_required
@user_passes_test(can_access_admins)
def admins_management(request):
    """Admins management page"""
    search_query = request.GET.get('search', '')

    # Get all staff users with their admin profiles
    admins_query = User.objects.filter(is_staff=True).select_related('admin_profile')

    if search_query:
        admins_query = admins_query.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(admin_profile__full_name__icontains=search_query)
        )

    admins = admins_query.order_by('-date_joined')

    # Pagination
    paginator = Paginator(admins, 20)
    page_number = request.GET.get('page')
    admins_page = paginator.get_page(page_number)

    context = {
        'admins': admins_page,
        'search_query': search_query,
        'total_admins': admins_query.count(),
    }

    return render(request, 'dashboard/admins_management.html', context)


@dashboard_login_required
@user_passes_test(can_access_admins)
def admin_create(request):
    """Create new admin"""
    if request.method == 'POST':
        form = AdminCreateForm(request.POST)
        if form.is_valid():
            try:
                # Create the user
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    password=form.cleaned_data['password'],
                    email=form.cleaned_data.get('email', ''),
                    is_staff=True,  # Always set to True for admins
                    is_active=True
                )

                # Create admin profile
                AdminProfile.objects.create(
                    user=user,
                    full_name=form.cleaned_data.get('full_name', ''),
                    phone_number=form.cleaned_data.get('phone_number', ''),
                    can_access_settings=form.cleaned_data.get('can_access_settings', False),
                    can_access_users=form.cleaned_data.get('can_access_users', False),
                    can_access_admins=form.cleaned_data.get('can_access_admins', False)
                )

                messages.success(request, f'Admin "{user.username}" created successfully!')
                return redirect('dashboard:admins')

            except Exception as e:
                messages.error(request, f'Error creating admin: {str(e)}')
    else:
        form = AdminCreateForm()

    context = {
        'form': form,
        'title': 'Create New Admin'
    }

    return render(request, 'dashboard/admin_form.html', context)


@dashboard_login_required
@user_passes_test(can_access_admins)
def admin_edit(request, admin_id):
    """Edit admin"""
    admin_user = get_object_or_404(User, id=admin_id, is_staff=True)

    # Get or create admin profile
    admin_profile, created = AdminProfile.objects.get_or_create(
        user=admin_user,
        defaults={
            'can_access_settings': True,  # Default for legacy admins
            'can_access_users': True,
            'can_access_admins': True
        }
    )

    if request.method == 'POST':
        form = AdminEditForm(request.POST)
        if form.is_valid():
            try:
                # Update user fields
                admin_user.email = form.cleaned_data.get('email', '')
                admin_user.is_active = form.cleaned_data.get('is_active', True)
                admin_user.save()

                # Update admin profile
                admin_profile.full_name = form.cleaned_data.get('full_name', '')
                admin_profile.phone_number = form.cleaned_data.get('phone_number', '')
                admin_profile.can_access_settings = form.cleaned_data.get('can_access_settings', False)
                admin_profile.can_access_users = form.cleaned_data.get('can_access_users', False)
                admin_profile.can_access_admins = form.cleaned_data.get('can_access_admins', False)
                admin_profile.save()

                messages.success(request, f'Admin "{admin_user.username}" updated successfully!')
                return redirect('dashboard:admins')

            except Exception as e:
                messages.error(request, f'Error updating admin: {str(e)}')
    else:
        # Pre-populate form with existing data
        form = AdminEditForm(initial={
            'full_name': admin_profile.full_name,
            'email': admin_user.email,
            'phone_number': admin_profile.phone_number,
            'can_access_settings': admin_profile.can_access_settings,
            'can_access_users': admin_profile.can_access_users,
            'can_access_admins': admin_profile.can_access_admins,
            'is_active': admin_user.is_active
        })

    context = {
        'form': form,
        'admin_user': admin_user,
        'admin_profile': admin_profile,
        'title': f'Edit Admin: {admin_user.username}'
    }

    return render(request, 'dashboard/admin_form.html', context)


@dashboard_login_required
@user_passes_test(can_access_admins)
def admin_delete(request, admin_id):
    """Delete admin"""
    if request.method == 'POST':
        admin_user = get_object_or_404(User, id=admin_id, is_staff=True)

        # Prevent deletion of superuser or self
        if admin_user.is_superuser:
            messages.error(request, 'Cannot delete superuser!')
            return redirect('dashboard:admins')

        if admin_user == request.user:
            messages.error(request, 'Cannot delete yourself!')
            return redirect('dashboard:admins')

        username = admin_user.username
        admin_user.delete()
        messages.success(request, f'Admin "{username}" deleted successfully!')

    return redirect('dashboard:admins')


@dashboard_login_required
@user_passes_test(can_access_settings)
def settings_management(request):
    """Settings management page"""
    exchange_rate = ExchangeRate.objects.filter(is_active=True).first()
    payment_settings = PaymentSettings.objects.filter(is_active=True).first()

    if request.method == 'POST':
        # Handle Exchange Rate
        if 'exchange_rate' in request.POST:
            rate_value = request.POST.get('rate')
            if rate_value:
                try:
                    rate_value = float(rate_value)
                    if exchange_rate:
                        exchange_rate.usd_to_uzs = rate_value  # rate → usd_to_uzs
                        exchange_rate.save()
                        print(f"Updated: {exchange_rate.usd_to_uzs}, Time: {exchange_rate.updated_at}")  # Debug
                    else:
                        ExchangeRate.objects.create(
                            usd_to_uzs=rate_value,  # rate → usd_to_uzs
                            is_active=True,
                            created_by=request.user
                        )
                    messages.success(request, 'Exchange rate updated successfully!')
                except ValueError:
                    messages.error(request, 'Invalid exchange rate value!')

        # Handle Payment Settings
        elif 'payment_settings' in request.POST:
            form = PaymentSettingsForm(request.POST)
            if form.is_valid():
                if payment_settings:
                    payment_settings.card_number = form.cleaned_data['card_number']
                    payment_settings.card_holder_name = form.cleaned_data['card_holder_name']
                    payment_settings.bank_name = form.cleaned_data['bank_name']
                    payment_settings.admin_chat_id = form.cleaned_data.get('admin_chat_id', '')
                    payment_settings.save()
                else:
                    PaymentSettings.objects.create(
                        card_number=form.cleaned_data['card_number'],
                        card_holder_name=form.cleaned_data['card_holder_name'],
                        bank_name=form.cleaned_data['bank_name'],
                        admin_chat_id=form.cleaned_data.get('admin_chat_id', ''),
                        is_active=True
                    )
                messages.success(request, 'Payment settings updated successfully!')
            else:
                messages.error(request, 'Please correct the errors in payment settings form.')

        return redirect('dashboard:settings')

    # Prepare forms for GET request
    payment_form = PaymentSettingsForm(initial={
        'card_number': payment_settings.card_number if payment_settings else '',
        'card_holder_name': payment_settings.card_holder_name if payment_settings else '',
        'bank_name': payment_settings.bank_name if payment_settings else '',
        'admin_chat_id': payment_settings.admin_chat_id if payment_settings else '',
    })

    context = {
        'exchange_rate': exchange_rate,
        'payment_settings': payment_settings,
        'payment_form': payment_form,
    }

    return render(request, 'dashboard/settings.html', context)