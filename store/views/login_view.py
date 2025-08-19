import secrets

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from store.models import TelegramAuth, UserProfile, Cart, CartItem, Product, Favorite, Category
from django.contrib.auth.models import User
import json
from django.contrib.auth import login as auth_login
import re
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib import messages


def cleanup_expired_telegram_auth():
    """
    Faqat muddati tugagan TelegramAuth yozuvlarini o'chirish
    """
    now = timezone.now()

    # Faqat muddati tugagan yozuvlarni o'chirish
    expired_count = TelegramAuth.objects.filter(expires_at__lt=now).count()
    TelegramAuth.objects.filter(expires_at__lt=now).delete()

    if expired_count > 0:
        print(f"🧹 Tozalash: {expired_count} muddati tugagan yozuv o'chirildi")

    return expired_count


def merge_session_data_to_user(request, user):
    session_key = request.session.session_key
    print("🔄 merge_session_data_to_user ishlayapti")
    print("Session key:", session_key)

    if not session_key:
        print("❌ Sessiya mavjud emas")
        return

    try:
        # Only get session cart that belongs to guest users (user=None)
        session_cart = Cart.objects.get(session_key=session_key, user=None)
        print("✅ Session savati topildi:", session_cart.id)

        user_cart, created = Cart.objects.get_or_create(user=user)
        print("Foydalanuvchi savati:", user_cart.id, "Yaratilganmi:", created)

        # Merge cart items with better error handling
        items_merged = 0
        for item in session_cart.items.all():
            try:
                cart_item, item_created = CartItem.objects.get_or_create(
                    cart=user_cart,
                    product=item.product,
                    defaults={'quantity': item.quantity}
                )
                if not item_created:
                    # If item already exists, add quantities but respect stock limits
                    new_quantity = cart_item.quantity + item.quantity
                    if new_quantity > item.product.stock_quantity:
                        new_quantity = item.product.stock_quantity
                    cart_item.quantity = new_quantity
                    cart_item.save()
                    print(f"🔄 {item.product.name} miqdori yangilandi: {cart_item.quantity}")
                else:
                    print(f"✅ {item.product.name} foydalanuvchi savatiga qo'shildi")
                items_merged += 1
            except Exception as e:
                print(f"❌ Xatolik: {item.product.name} ni qo'shishda xatolik: {e}")
                continue

        # Delete session cart only after successful merge
        session_cart.delete()
        print(f"🗑️ Session savati o'chirildi. {items_merged} ta mahsulot ko'chirildi")

        # Merge favorites with better error handling
        favorites_merged = 0
        session_favorites = request.session.get('favorites', [])
        for product_id in session_favorites:
            try:
                product = Product.objects.get(pk=product_id)
                favorite, created = Favorite.objects.get_or_create(user=user, product=product)
                if created:
                    favorites_merged += 1
                    print(f"❤️ {product.name} sevimlilarga qo'shildi")
            except Product.DoesNotExist:
                print(f"❌ Mahsulot topilmadi: ID {product_id}")
                continue
            except Exception as e:
                print(f"❌ Xatolik: sevimlilarga qo'shishda xatolik: {e}")
                continue

        # Clear session data completely after successful merge
        request.session['favorites'] = []
        request.session['cart_initialized'] = False  # Reset cart initialization flag
        request.session.modified = True
        print(f"✅ Sessiya tozalandi. {favorites_merged} ta sevimli ko'chirildi")

    except Cart.DoesNotExist:
        print("❌ Session savati topilmadi")
        # Clean up session flags anyway
        request.session['cart_initialized'] = False
        request.session['favorites'] = []
        request.session.modified = True
    except Exception as e:
        print(f"❌ Umumiy xatolik merge_session_data_to_user da: {e}")
        # Clean up session flags on error
        request.session['cart_initialized'] = False
        request.session.modified = True


@csrf_exempt
def telegram_callback(request):
    if request.method == "GET":
        session_token = request.GET.get("token")
        code = request.GET.get("code")

        if not session_token or not code:
            return JsonResponse({"success": False, "message": "Token yoki kod topilmadi."}, status=400)

        try:
            # is_used holatini e'tiborsiz qoldiramiz, faqat token va kodni tekshiramiz
            auth = TelegramAuth.objects.get(
                session_token=session_token,
                code=code,
                # is_used=False  # Bu qatorni olib tashlaymiz
            )

            if auth.is_expired:
                return JsonResponse({"success": False, "message": "Kod muddati o'tgan."}, status=400)

            # Agar allaqachon ishlatilgan bo'lsa ham, muddati tugamagan bo'lsa ruxsat beramiz
            if auth.is_used:
                print(f"[WARNING] Auth {session_token} allaqachon ishlatilgan, lekin muddati hali tugamagan")

            phone_number = auth.phone_number
            username = re.sub(r'\D', '', phone_number)
            if len(username) > 30:
                username = username[-30:]

            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'first_name': 'Foydalanuvchi'
                }
            )

            profile, profile_created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'phone_number': phone_number,
                    'is_phone_verified': True,
                    'telegram_chat_id': auth.chat_id
                }
            )

            # Muvaffaqiyatli autentifikatsiya
            auth.is_used = True
            auth.save()

            # Django sessionga login qilish
            if not request.session.session_key:
                request.session.create()
            request.session.save()
            auth_login(request, user)

            # Session ma'lumotlarini foydalanuvchiga ko'chirish
            merge_session_data_to_user(request, user)

            return redirect('home')

        except TelegramAuth.DoesNotExist:
            return JsonResponse({"success": False, "message": "Noto'g'ri kod yoki sessiya."}, status=400)

    return JsonResponse({"success": False, "message": "Noto'g'ri so'rov turi."}, status=400)


@csrf_exempt
def verify_code(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Noto'g'ri so'rov"})

    data = json.loads(request.body)
    code = data.get("code")
    session_token = request.session.get('login_token')

    if not session_token:
        return JsonResponse({"success": False, "message": "Sessiya yo'q. Qaytadan boshlang."})

    try:
        auth = TelegramAuth.objects.get(
            session_token=session_token,
            code=code,
            # is_used=False  # Bu qatorni olib tashlaymiz
        )

        if auth.is_expired:
            return JsonResponse({"success": False, "message": "Kod muddati o'tgan."})

        # Agar allaqachon ishlatilgan bo'lsa ham, muddati tugamagan bo'lsa ruxsat beramiz
        if auth.is_used:
            print(f"[WARNING] Auth {session_token} allaqachon ishlatilgan, lekin muddati hali tugamagan")

        # ... qolgan kod bir xil
        phone_number = auth.phone_number
        username = re.sub(r'\D', '', phone_number)
        if len(username) > 30:
            username = username[-30:]

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@example.com',
                'first_name': 'Foydalanuvchi'
            }
        )

        profile, profile_created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'phone_number': phone_number,
                'is_phone_verified': True,
                'telegram_chat_id': auth.chat_id
            }
        )

        # Muvaffaqiyatli autentifikatsiya
        auth.is_used = True
        auth.save()

        if not request.session.session_key:
            request.session.create()
        request.session.save()
        auth_login(request, user)

        merge_session_data_to_user(request, user)

        # Get updated cart and favorites count after merging
        try:
            user_cart = Cart.objects.get(user=user)
            cart_total = user_cart.total_items
        except Cart.DoesNotExist:
            cart_total = 0

        favorites_count = Favorite.objects.filter(user=user).count()

        return JsonResponse({
            "success": True,
            "message": "Kirish amalga oshirildi!",
            "cart_total": cart_total,
            "favorites_count": favorites_count
        })

    except TelegramAuth.DoesNotExist:
        return JsonResponse({"success": False, "message": "Noto'g'ri kod."})


def login_request(request):
    # Avval eski va keraksiz yozuvlarni tozalash
    cleanup_expired_telegram_auth()

    # 6 belgi: login_a1b2c3 (jami 12 belgi)
    session_token = "login_" + secrets.token_hex(3)  # login_ + 6 hex → 12 belgi
    categories = Category.objects.filter(is_active=True)[:6]

    TelegramAuth.objects.create(
        session_token=session_token,
        expires_at=timezone.now() + timezone.timedelta(minutes=5),
        is_used=False,
    )

    request.session['login_token'] = session_token

    bot_username = settings.TELEGRAM_BOT_USERNAME
    start_link = f"https://t.me/{bot_username}?start={session_token}"

    return render(request, 'store/login.html', {
        'telegram_link': start_link,
        'categories': categories
    })


def store_logout(request):
    """Store logout view with session cleanup"""
    # Clear session cart data before logout
    if request.session.session_key:
        request.session['cart_initialized'] = False
        request.session['favorites'] = []
        request.session.modified = True
    
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('home')