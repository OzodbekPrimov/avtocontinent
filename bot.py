# bot/main.py
import logging
import os
import django
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram import F
from asgiref.sync import sync_to_async


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.utils import timezone
from store.models import TelegramAuth, Order
from django.core.cache import cache
from django.conf import settings

API_TOKEN = settings.TELEGRAM_BOT_TOKEN
TELEGRAM_ADMIN_CHAT_ID = settings.TELEGRAM_ADMIN_CHAT_ID
ADMIN_PHONE_NUMBER = settings.ADMIN_PHONE_NUMBER


bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def get_retry_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Kodni yangilash", callback_data="retry_code")]
    ])
    return kb

@dp.message(Command("start"))
async def start(message: types.Message):
    args = message.text.split(" ")[1] if len(message.text.split(" ")) > 1 else None
    chat_id = message.chat.id

    if not args or not args.startswith("login_"):
        await message.answer("Iltimos, faqat sayt orqali berilgan havola orqali kirishni so'rang.")
        return

    session_token = args

    # ✅ sync_to_async bilan
    try:
        auth = await sync_to_async(TelegramAuth.objects.get)(
            session_token=session_token,
            is_used=False
        )

        auth.chat_id = chat_id
        await sync_to_async(auth.save)()

        if await sync_to_async(lambda: auth.is_expired)():
            await message.answer("Sessiya muddati o'tgan. Iltimos, saytdan qayta urinib ko'ring.")
            return
    except TelegramAuth.DoesNotExist:
        await message.answer("Sessiya topilmadi. Iltimos, saytdan boshlang.")
        return

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)]
        ],
        resize_keyboard=True
    )
    await message.answer("Iltimos, telefon raqamingizni yuboring.", reply_markup=kb)

@dp.message(F.contact)
async def handle_contact(message: types.Message):
    phone = message.contact.phone_number
    chat_id = message.chat.id

    # Session tokenni olish
    text = message.text
    if text and text.startswith("/start "):
        args = text.split(" ")[1]
        if args.startswith("login_"):
            session_token = args
        else:
            session_token = None
    else:
        session_token = None

    if session_token:
        try:
            pending = await sync_to_async(TelegramAuth.objects.get)(
                session_token=session_token,
                is_used=False
            )
        except TelegramAuth.DoesNotExist:
            await message.answer("Sessiya topilmadi.")
            return
    else:
        try:
            pending = await sync_to_async(
                lambda: TelegramAuth.objects.filter(
                    phone_number__isnull=True,
                    is_used=False,
                    created_at__gte=timezone.now() - timezone.timedelta(minutes=5)
                ).order_by('-created_at').first()
            )()
            if not pending:
                await message.answer("Sessiya topilmadi yoki muddati o'tgan.")
                return
            session_token = pending.session_token
        except Exception as e:
            await message.answer("Xatolik yuz berdi.")
            return

    # Tasdiqlash kodi yaratish
    import random
    code = str(random.randint(1000, 9999))

    # Login URL yaratish
    login_url = f"{settings.SITE_URL}/auth/telegram/callback/?token={session_token}&code={code}"

    # TelegramAuth modelini yangilash
    pending.phone_number = phone
    pending.chat_id = chat_id
    pending.code = code
    pending.expires_at = timezone.now() + timezone.timedelta(minutes=1)
    await sync_to_async(pending.save)()

    # Xabar va URL yuborish
    await message.answer(
        f"🔐 Tasdiqlash kodingiz: `{code}`\n\n"
        f"⏳ Kod 1 daqiqa amal qiladi.\n\n"
        f"👉 Kirish uchun: [Bu yerga bosing]({login_url})",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.callback_query(F.data == "retry_code")
async def retry_code(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    try:
        pending = await sync_to_async(
            lambda: TelegramAuth.objects.filter(
                phone_number__isnull=False,
                is_used=False,
                created_at__gte=timezone.now() - timezone.timedelta(minutes=5)
            ).order_by('-created_at').first()
        )()

        if not pending:
            await bot.send_message(user_id, "Faol sessiya topilmadi.")
            await callback.answer()
            return

        # Rate limiting
        cache_key = f"retry_limit_{pending.session_token}"
        attempts = cache.get(cache_key, 0)
        if attempts >= 3:
            await bot.send_message(user_id, "Siz juda ko'p urinish qildingiz. 5 daqiqa kutishingiz kerak.")
            await callback.answer()
            return

        import random
        new_code = str(random.randint(1000, 9999))
        pending.code = new_code
        pending.expires_at = timezone.now() + timezone.timedelta(minutes=1)
        await sync_to_async(pending.save)()

        cache.set(cache_key, attempts + 1, 300)

        await bot.send_message(
            user_id,
            f"🔄 Yangi kod: `{new_code}`\n\n⏳ 1 daqiqa amal qiladi.",
            parse_mode="Markdown",
            reply_markup=get_retry_kb()
        )
        await callback.answer("Yangi kod yuborildi.")
    except Exception as e:
        await callback.answer("Xatolik yuz berdi.")

@dp.callback_query(F.data.startswith(("confirm_", "cancel_")))
async def handle_order_callback(callback: types.CallbackQuery):
    callback_data = callback.data
    chat_id = callback.from_user.id
    order_id = callback_data.split('_')[1]

    # Faqat admin callback'ni bossa ishlov berish
    if chat_id != TELEGRAM_ADMIN_CHAT_ID:
        await callback.answer("Sizda bu amalni bajarish uchun ruxsat yo'q.")
        return

    try:
        order = await sync_to_async(Order.objects.get)(order_id=order_id)
    except Order.DoesNotExist:
        await callback.answer("Buyurtma topilmadi.")
        return

    try:
        user_profile = await sync_to_async(lambda: order.user.userprofile)()
        user_chat_id = user_profile.telegram_chat_id
    except order.user.userprofile.DoesNotExist:
        user_chat_id = None
        await bot.send_message(
            TELEGRAM_ADMIN_CHAT_ID,
            f"⚠️ Buyurtma {order_id} uchun foydalanuvchi profili topilmadi."
        )

    if callback_data.startswith('confirm_'):
        if user_chat_id:
            order.payment_confirmed = True
            order.payment_confirmed_at = timezone.now()
            await sync_to_async(order.save)()
            await bot.send_message(
                user_chat_id,
                "✅ To'lov tasdiqlandi! Buyurtmangiz qayta ishlana boshlandi.",
                parse_mode="Markdown"
            )
        await bot.send_message(
            TELEGRAM_ADMIN_CHAT_ID,
            f"✅ Buyurtma {order_id} to'lovi tasdiqlandi.",
            parse_mode="Markdown"
        )
        await callback.answer("To'lov tasdiqlandi.")
    elif callback_data.startswith('cancel_'):
        if user_chat_id:
            await bot.send_message(
                user_chat_id,
                f"❌ To'lov tasdiqlanmadi. Iltimos, admin bilan bog'laning.\nTelefon: {ADMIN_PHONE_NUMBER}",
                parse_mode="Markdown"
            )
        await bot.send_message(
            TELEGRAM_ADMIN_CHAT_ID,
            f"❌ Buyurtma {order_id} to'lovi bekor qilindi.",
            parse_mode="Markdown"
        )
        await callback.answer("To'lov bekor qilindi.")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    dp.run_polling(bot)