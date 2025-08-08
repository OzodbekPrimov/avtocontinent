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
    Muddati tugagan va ishlatilgan TelegramAuth yozuvlarini o'chirish
    """
    now = timezone.now()

    # Muddati tugagan yozuvlarni o'chirish
    expired_count = TelegramAuth.objects.filter(expires_at__lt=now).count()
    TelegramAuth.objects.filter(expires_at__lt=now).delete()

    # Ishlatilgan va 1 soatdan eski yozuvlarni o'chirish
    # Agar created_at fieldi mavjud bo'lsa
    try:
        used_count = TelegramAuth.objects.filter(
            is_used=True,
            created_at__lt=now - timezone.timedelta(hours=1)
        ).count()
        TelegramAuth.objects.filter(
            is_used=True,
            created_at__lt=now - timezone.timedelta(hours=1)
        ).delete()
    except:
        # Agar created_at fieldi mavjud bo'lmasa, faqat is_used=True bo'lganlarni o'chirish
        used_count = TelegramAuth.objects.filter(is_used=True).count()
        TelegramAuth.objects.filter(is_used=True).delete()

    total_deleted = expired_count + used_count
    if total_deleted > 0:
        print(f"🧹 Tozalash: {expired_count} muddati tugagan, {used_count} ishlatilgan yozuv o'chirildi")

    return total_deleted


def merge_session_data_to_user(request, user):
    session_key = request.session.session_key
    print("🔄 merge_session_data_to_user ishlayapti")
    print("Session key:", session_key)

    if not session_key:
        print("❌ Sessiya mavjud emas")
        return

    try:
        session_cart = Cart.objects.get(session_key=session_key)
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

        # Clear session favorites
        request.session['favorites'] = []
        request.session.modified = True
        print(f"✅ Sessiya tozalandi. {favorites_merged} ta sevimli ko'chirildi")

    except Cart.DoesNotExist:
        print("❌ Session savati topilmadi")
        # Debug: show all session carts
        print("Barcha session_keylar:")
        for c in Cart.objects.filter(user=None):
            print(f"ID: {c.id}, session_key: {c.session_key}")
    except Exception as e:
        print(f"❌ Umumiy xatolik merge_session_data_to_user da: {e}")


from django.db import transaction
import time
import logging
logger = logging.getLogger(__name__)


@csrf_exempt
def telegram_callback(request):
    if request.method == "GET":
        session_token = request.GET.get("token")
        code = request.GET.get("code")

        if not session_token or not code:
            return JsonResponse({"success": False, "message": "Token yoki kod topilmadi."}, status=400)

        # RETRY MEXANIZMI - ba'zan ma'lumot hali yetib kelmagan bo'lishi mumkin
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                with transaction.atomic():
                    # SELECT FOR UPDATE - boshqa jarayonlar tomonidan o'zgartirilmasligi uchun
                    auth = TelegramAuth.objects.select_for_update().get(
                        session_token=session_token,
                        is_used=False
                    )

                    logger.info(
                        f"Found auth record: token={auth.session_token}, code_in_db={auth.code}, code_from_request={code}, is_used={auth.is_used}")

                    # Kodni tekshirish
                    if auth.code != code:
                        logger.warning(f"Code mismatch: expected {auth.code}, got {code}")
                        return JsonResponse({"success": False, "message": "Noto'g'ri kod."}, status=400)

                    if auth.is_expired:
                        logger.warning(f"Code expired for token: {session_token}")
                        return JsonResponse({"success": False, "message": "Kod muddati o'tgan."}, status=400)

                    phone_number = auth.phone_number
                    if not phone_number:
                        logger.error(f"Phone number not found for token: {session_token}")
                        return JsonResponse({"success": False, "message": "Telefon raqam topilmadi."}, status=400)

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

                    logger.info(f"Auth marked as used: token={auth.session_token}")

                    # Django sessionga login qilish
                    if not request.session.session_key:
                        request.session.create()
                    request.session.save()
                    auth_login(request, user)

                    # Session ma'lumotlarini foydalanuvchiga ko'chirish
                    merge_session_data_to_user(request, user)

                    return redirect('home')

            except TelegramAuth.DoesNotExist:
                retry_count += 1
                if retry_count < max_retries:
                    logger.warning(f"Auth not found, retrying... ({retry_count}/{max_retries})")
                    time.sleep(0.5)  # 500ms kutish
                    continue
                else:
                    logger.error(f"Auth not found after {max_retries} retries: token={session_token}, code={code}")

                    # DEBUG: Mavjud yozuvlarni ko'rish
                    existing_auths = TelegramAuth.objects.filter(session_token=session_token)
                    for auth in existing_auths:
                        logger.error(
                            f"Existing auth: token={auth.session_token}, code={auth.code}, is_used={auth.is_used}, phone={auth.phone_number}")

                    return JsonResponse({"success": False, "message": "Noto'g'ri kod yoki sessiya."}, status=400)

            except Exception as e:
                logger.error(f"Unexpected error in telegram_callback: {e}")
                return JsonResponse({"success": False, "message": "Server xatosi."}, status=500)

        return JsonResponse({"success": False, "message": "Noto'g'ri so'rov turi."}, status=400)


# TUZATILGAN verify_code FUNKSIYASI

import json
import time
import logging
from django.db import connection, transaction
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

logger = logging.getLogger('telegram_auth')


@csrf_exempt
def verify_code(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Noto'g'ri so'rov"})

    try:
        data = json.loads(request.body)
        code = data.get("code")
        session_token = request.session.get('login_token')

        logger.info(f"[VERIFY] Code verification request: token={session_token}, code={code}")

        if not session_token:
            return JsonResponse({"success": False, "message": "Sessiya yo'q. Qaytadan boshlang."})

        if not code:
            return JsonResponse({"success": False, "message": "Kod kiritilmagan."})

        # MUHIM: Database connection ni yopish
        connection.close()

        # Cache dan tekshirish
        cache_key = f"backup_auth_{session_token}"
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.info(f"[VERIFY] Found cached data for token: {session_token}")

        auth = None
        found_via = None

        # RETRY LOGIC - Server muhiti uchun
        max_retries = 8
        base_delay = 0.05  # 50ms

        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    # Database dan tekshirish
                    auth_qs = TelegramAuth.objects.select_for_update(
                        skip_locked=True  # Lock qilingan recordlarni o'tkazib yuborish
                    ).filter(
                        session_token=session_token,
                        is_used=False
                    )

                    auth = auth_qs.first()

                    if auth:
                        logger.info(f"[VERIFY] Found auth in DB on attempt {attempt + 1}")
                        found_via = "database"
                        break

                    # Agar DB da yo'q bo'lsa, cache dan tekshirish
                    elif cached_data and cached_data.get('code') == code:
                        logger.info(f"[VERIFY] Using cached data on attempt {attempt + 1}")

                        # Cache dan fake auth object yaratish
                        class CachedAuth:
                            def __init__(self, data):
                                self.session_token = session_token
                                self.code = data.get('code')
                                self.phone_number = data.get('phone')
                                self.chat_id = data.get('chat_id')
                                self.is_used = False
                                self._cached = True

                            @property
                            def is_expired(self):
                                # Cache da saqlangan ma'lumot uchun muddatni tekshirish
                                expires_at = cached_data.get('expires_at', 0)
                                if expires_at:
                                    return time.time() > expires_at
                                return False  # Agar expires_at yo'q bo'lsa, expired deb hisoblamaymiz

                            def save(self):
                                # Cache dan o'chirish
                                cache.delete(cache_key)
                                logger.info(f"[VERIFY] Cached auth marked as used")

                        auth = CachedAuth(cached_data)
                        found_via = "cache"
                        break

                    else:
                        logger.warning(f"[VERIFY] Auth not found, attempt {attempt + 1}/{max_retries}")

                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)  # Exponential backoff
                            time.sleep(min(delay, 2.0))  # Maximum 2 sekund kutish

                            # Har 3-chi urinishda connection ni yangilash
                            if attempt % 3 == 2:
                                connection.close()

            except Exception as db_error:
                logger.error(f"[VERIFY] Database error on attempt {attempt + 1}: {db_error}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(min(delay, 2.0))
                    connection.close()  # Connection ni qayta ochish
                else:
                    return JsonResponse({
                        "success": False,
                        "message": "Server bilan bog'lanishda xatolik."
                    }, status=500)

        # Auth topilmadi
        if not auth:
            logger.error(f"[VERIFY] Auth not found after {max_retries} attempts: token={session_token}")

            # Debug: Mavjud auth recordlarni ko'rish
            try:
                existing_auths = TelegramAuth.objects.filter(session_token=session_token)
                for existing_auth in existing_auths:
                    logger.error(f"[VERIFY-DEBUG] Existing auth: token={existing_auth.session_token}, "
                                 f"code={existing_auth.code}, is_used={existing_auth.is_used}, "
                                 f"phone={existing_auth.phone_number}")
            except Exception as debug_error:
                logger.error(f"[VERIFY-DEBUG] Error checking existing auths: {debug_error}")

            return JsonResponse({"success": False, "message": "Sessiya topilmadi yoki kod noto'g'ri."})

        # Validatsiya
        logger.info(f"[VERIFY] Auth found via {found_via}: code_db={auth.code}, code_input={code}")

        if auth.code != code:
            logger.warning(f"[VERIFY] Code mismatch: expected {auth.code}, got {code}")
            return JsonResponse({"success": False, "message": "Noto'g'ri kod."})

        if auth.is_expired:
            logger.warning(f"[VERIFY] Code expired for token: {session_token}")
            return JsonResponse({"success": False, "message": "Kod muddati o'tgan."})

        if not auth.phone_number:
            logger.error(f"[VERIFY] Phone number not found for token: {session_token}")
            return JsonResponse({"success": False, "message": "Telefon raqam topilmadi."})

        # User yaratish va login qilish
        try:
            with transaction.atomic():
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

                # Profile ni yangilash (agar kerak bo'lsa)
                if not profile_created and profile.telegram_chat_id != auth.chat_id:
                    profile.telegram_chat_id = auth.chat_id
                    profile.save()

                # Auth ni used qilish
                auth.is_used = True
                auth.save()

                logger.info(f"[VERIFY] User authenticated successfully: {username}")

                # Django session
                if not request.session.session_key:
                    request.session.create()
                request.session.save()
                auth_login(request, user)

                # Session ma'lumotlarini ko'chirish
                merge_session_data_to_user(request, user)

                # Cart va favorites count
                try:
                    user_cart = Cart.objects.get(user=user)
                    cart_total = user_cart.total_items
                except Cart.DoesNotExist:
                    cart_total = 0

                favorites_count = Favorite.objects.filter(user=user).count()

                # Cache tozalash
                if cache_key:
                    cache.delete(cache_key)

                return JsonResponse({
                    "success": True,
                    "message": "Kirish amalga oshirildi!",
                    "cart_total": cart_total,
                    "favorites_count": favorites_count
                })

        except Exception as user_error:
            logger.error(f"[VERIFY] User creation/login error: {user_error}")
            return JsonResponse({
                "success": False,
                "message": "Foydalanuvchi yaratishda xatolik."
            }, status=500)

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "Noto'g'ri ma'lumot formati."})
    except Exception as general_error:
        logger.error(f"[VERIFY] General error: {general_error}")
        return JsonResponse({
            "success": False,
            "message": "Server xatosi yuz berdi."
        }, status=500)


def login_request(request):
    # Avval eski va keraksiz yozuvlarni tozalash
    cleanup_expired_telegram_auth()

    # 6 belgi: login_a1b2c3 (jami 12 belgi)
    session_token = "login_" + secrets.token_hex(3)  # login_ + 6 hex → 12 belgi
    categories = Category.objects.filter(is_active=True)[:6]

    TelegramAuth.objects.create(
        session_token=session_token,
        expires_at=timezone.now() + timezone.timedelta(minutes=5)
    )

    request.session['login_token'] = session_token

    bot_username = settings.TELEGRAM_BOT_USERNAME
    start_link = f"https://t.me/{bot_username}?start={session_token}"

    return render(request, 'store/login.html', {
        'telegram_link': start_link,
        'categories': categories
    })


def store_logout(request):
    """Store logout view"""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('home')