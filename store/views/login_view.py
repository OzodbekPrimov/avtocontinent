import secrets

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from store.models import TelegramAuth, UserProfile, Cart, CartItem, Product, Favorite, Category
from django.contrib.auth.models import User
import json
from django.contrib.auth import login as auth_login
import re
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib import messages


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

        for item in session_cart.items.all():
            cart_item, item_created = CartItem.objects.get_or_create(
                cart=user_cart,
                product=item.product,
                defaults={'quantity': item.quantity}
            )
            if not item_created:
                cart_item.quantity += item.quantity
                if cart_item.quantity > item.product.stock_quantity:
                    cart_item.quantity = item.product.stock_quantity
                cart_item.save()
                print(f"🔄 {item.product.name} miqdori yangilandi: {cart_item.quantity}")
            else:
                print(f"✅ {item.product.name} foydalanuvchi savatiga qo'shildi")

        session_cart.delete()
        print("🗑️ Session savati o'chirildi")

        # Sevimlilarni ko'chirish
        session_favorites = request.session.get('favorites', [])
        for product_id in session_favorites:
            try:
                product = Product.objects.get(pk=product_id)
                Favorite.objects.get_or_create(user=user, product=product)
            except Product.DoesNotExist:
                continue

        request.session['favorites'] = []
        request.session.modified = True
        print("✅ Sessiya tozalandi")

    except Cart.DoesNotExist:
        print("❌ Session savati topilmadi")
        # Barcha session_keylarni ko'rish (debug uchun)
        print("Barcha session_keylar:")
        for c in Cart.objects.filter(user=None):
            print(f"ID: {c.id}, session_key: {c.session_key}")


@csrf_exempt
def verify_code(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Notog'ri so'rov"})

    data = json.loads(request.body)
    code = data.get("code")
    session_token = request.session.get('login_token')

    if not session_token:
        return JsonResponse({"success": False, "message": "Sessiya yo'q. Qaytadan boshlang."})

    try:
        auth = TelegramAuth.objects.get(
            session_token=session_token,
            code=code,
            is_used=False
        )

        tg_chat_id = auth.chat_id

        if auth.is_expired:
            return JsonResponse({"success": False, "message": "Kod muddati o'tgan."})

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
                'telegram_chat_id':tg_chat_id
            }
        )

        # Muvaffaqiyatli autentifikatsiya
        auth.is_used = True
        auth.save()

        # 🔥 MUHIM: session_key ni doimiy qilish
        if not request.session.session_key:
            request.session.create()  # session_key yaratish
        request.session.save()  # ✅ sessionni saqlash

        # Django sessionga login qilish
        auth_login(request, user)

        # 🔥 SESSIONDAGI MA'LUMOTLARNI Foydalanuvchiga KO'CHIRISH
        merge_session_data_to_user(request, user)

        return JsonResponse({"success": True, "message": "Kirish amalga oshirildi!"})

    except TelegramAuth.DoesNotExist:
        return JsonResponse({"success": False, "message": "Noto'g'ri kod."})

def login_request(request):
    # 6 belgi: login_a1b2c3 (jami 12 belgi)
    session_token = "login_" + secrets.token_hex(3)  # login_ + 6 hex → 12 belgi
    categories = Category.objects.filter(is_active=True)[:6]

    TelegramAuth.objects.create(
        session_token=session_token,
        expires_at=timezone.now() + timezone.timedelta(minutes=5)
    )

    request.session['login_token'] = session_token

    bot_username = "avtokon_bot"
    start_link = f"https://t.me/{bot_username}?start={session_token}"

    return render(request, 'store/login.html', {
        'telegram_link': start_link,
        'categories':categories
    })


def store_logout(request):
    """Store logout view"""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('home')
