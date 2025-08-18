from django.shortcuts import  get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from .home_views import dashboard_login_required, is_staff_user
from store.models import Product, Brand, Banner, CarModel, Category, Order, ProductImage

from django.http import JsonResponse

from django.utils import timezone

from django.views.decorators.http import require_POST


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
        category.save()  #
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


# Product images AJAX
@dashboard_login_required
@user_passes_test(is_staff_user)
@require_POST
def ajax_delete_product_image(request):
    image_id = request.POST.get('image_id')
    if not image_id:
        return JsonResponse({'success': False, 'message': 'image_id required'})
    try:
        img = ProductImage.objects.get(id=image_id)
        product_id = img.product_id
        img.delete()
        new_count = ProductImage.objects.filter(product_id=product_id).count()
        return JsonResponse({'success': True, 'new_count': new_count})
    except ProductImage.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Image not found'})


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