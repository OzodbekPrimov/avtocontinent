# bot/main.py
import logging
import os
import sys
import signal
import asyncio
from contextlib import asynccontextmanager
import django
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, \
    ReplyKeyboardRemove
from aiogram import F
from asgiref.sync import sync_to_async

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.utils import timezone
from store.models import TelegramAuth, Order
from django.core.cache import cache
from django.conf import settings

# Logging konfiguratsiyasi
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/var/log/bot.log') if os.path.exists('/var/log/') else logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Konfiguratsiya
API_TOKEN = settings.TELEGRAM_BOT_TOKEN
TELEGRAM_ADMIN_CHAT_ID = settings.TELEGRAM_ADMIN_CHAT_ID
ADMIN_PHONE_NUMBER = settings.ADMIN_PHONE_NUMBER

if not API_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not found in settings")
    sys.exit(1)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Graceful shutdown uchun
shutdown_event = asyncio.Event()


def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, shutting down...")
    shutdown_event.set()


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def get_retry_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Kodni yangilash", callback_data="retry_code")]
    ])
    return kb


@dp.message(Command("start"))
async def start(message: types.Message):
    try:
        args = message.text.split(" ")[1] if len(message.text.split(" ")) > 1 else None
        chat_id = message.chat.id

        logger.info(f"Start command received from chat_id: {chat_id}, args: {args}")

        if not args or not args.startswith("login_"):
            await message.answer("Iltimos, faqat sayt orqali berilgan havola orqali kirishni so'rang.")
            return

        session_token = args

        # Database operatsiyasi
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

            logger.info(f"Session found and updated for chat_id: {chat_id}")

        except TelegramAuth.DoesNotExist:
            logger.warning(f"Session not found for token: {session_token}")
            await message.answer("Sessiya topilmadi. Iltimos, saytdan boshlang.")
            return
        except Exception as e:
            logger.error(f"Database error in start command: {e}")
            await message.answer("Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
            return

        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)]
            ],
            resize_keyboard=True
        )
        await message.answer("Iltimos, telefon raqamingizni yuboring.", reply_markup=kb)

    except Exception as e:
        logger.error(f"Unexpected error in start command: {e}")
        await message.answer("Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")


@dp.message(F.contact)
async def handle_contact(message: types.Message):
    try:
        phone = message.contact.phone_number
        chat_id = message.chat.id

        logger.info(f"[DEBUG] Contact received from chat_id: {chat_id}, phone: {phone}")

        try:
            pending = await sync_to_async(
                lambda: TelegramAuth.objects.filter(
                    chat_id=chat_id,
                    phone_number__isnull=True,
                    is_used=False,
                    created_at__gte=timezone.now() - timezone.timedelta(minutes=10)
                ).order_by('-created_at').first()
            )()

            if not pending:
                await message.answer("Faol sessiya topilmadi. Iltimos, saytdan qayta boshlang.")
                return

            # DEBUG: Boshlang'ich holat
            logger.info(f"[DEBUG-1] BEFORE any changes: is_used={pending.is_used}")

        except Exception as e:
            logger.error(f"Database error in handle_contact: {e}")
            return

        import random
        code = str(random.randint(1000, 9999))
        login_url = f"{settings.SITE_URL}/auth/telegram/callback/?token={pending.session_token}&code={code}"

        # DEBUG: Field o'zgartirishdan oldin
        logger.info(f"[DEBUG-2] BEFORE field updates: is_used={pending.is_used}")

        # Field larni o'zgartirish
        pending.phone_number = phone
        pending.code = code
        pending.expires_at = timezone.now() + timezone.timedelta(minutes=2)

        # DEBUG: Field o'zgartirishdan keyin, save qilishdan oldin
        logger.info(f"[DEBUG-3] AFTER field updates, BEFORE save: is_used={pending.is_used}")

        # Aniq False qilib qo'yish
        pending.is_used = False
        logger.info(f"[DEBUG-4] EXPLICITLY set False, BEFORE save: is_used={pending.is_used}")

        # SAVE
        await sync_to_async(pending.save)()

        # DEBUG: Save qilishdan keyin
        logger.info(f"[DEBUG-5] IMMEDIATELY after save: is_used={pending.is_used}")

        # Fresh object yuklash
        fresh_pending = await sync_to_async(TelegramAuth.objects.get)(id=pending.id)
        logger.info(f"[DEBUG-6] FRESH from database: is_used={fresh_pending.is_used}")

        logger.info(f"Code generated for session: {pending.session_token}")

        await message.answer(
            f"🔐 Tasdiqlash kodingiz: `{code}`\n\n"
            f"⏳ Kod 2 daqiqa amal qiladi.\n\n"
            f"👉 Kirish uchun: [Bu yerga bosing]({login_url})",
            parse_mode="Markdown",
            reply_markup=get_retry_kb()
        )

        await message.answer("✅ Kod yuborildi!", reply_markup=ReplyKeyboardRemove())

    except Exception as e:
        logger.error(f"Unexpected error in handle_contact: {e}")
        await message.answer("Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")


@dp.callback_query(F.data == "retry_code")
async def retry_code(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id

        logger.info(f"Retry code requested by chat_id: {chat_id}")

        try:
            pending = await sync_to_async(
                lambda: TelegramAuth.objects.filter(
                    chat_id=chat_id,
                    phone_number__isnull=False,
                    is_used=False,
                    created_at__gte=timezone.now() - timezone.timedelta(minutes=10)
                ).order_by('-created_at').first()
            )()

            if not pending:
                await callback.message.edit_text("Faol sessiya topilmadi. Iltimos, saytdan qayta boshlang.")
                await callback.answer()
                return

        except Exception as e:
            logger.error(f"Database error in retry_code: {e}")
            await callback.answer("Xatolik yuz berdi.")
            return

        # Rate limiting
        cache_key = f"retry_limit_{pending.session_token}"
        attempts = cache.get(cache_key, 0)
        if attempts >= 3:
            await callback.message.edit_text("Siz juda ko'p urinish qildingiz. 5 daqiqa kutishingiz kerak.")
            await callback.answer()
            return

        import random
        new_code = str(random.randint(1000, 9999))
        pending.code = new_code
        pending.expires_at = timezone.now() + timezone.timedelta(minutes=2)
        await sync_to_async(pending.save)()

        cache.set(cache_key, attempts + 1, 300)  # 5 daqiqa

        login_url = f"{settings.SITE_URL}/auth/telegram/callback/?token={pending.session_token}&code={new_code}"

        await callback.message.edit_text(
            f"🔄 Yangi kod: `{new_code}`\n\n⏳ 2 daqiqa amal qiladi.\n\n"
            f"👉 Kirish uchun: [Bu yerga bosing]({login_url})",
            parse_mode="Markdown",
            reply_markup=get_retry_kb()
        )
        await callback.answer("Yangi kod yuborildi.")

        logger.info(f"New code generated for session: {pending.session_token}")

    except Exception as e:
        logger.error(f"Unexpected error in retry_code: {e}")
        await callback.answer("Xatolik yuz berdi.")


@dp.callback_query(F.data.startswith(("confirm_", "cancel_")))
async def handle_order_callback(callback: types.CallbackQuery):
    try:
        callback_data = callback.data
        user_id = callback.from_user.id  # User ID
        chat_id = callback.message.chat.id  # Chat ID (guruh uchun manfiy bo'ladi)
        order_id = callback_data.split('_')[1]

        logger.info(f"Order callback received: {callback_data} from user_id: {user_id}, chat_id: {chat_id}")


        is_admin = False

        if str(chat_id) == str(TELEGRAM_ADMIN_CHAT_ID):
            is_admin = True
        elif str(user_id) == str(TELEGRAM_ADMIN_CHAT_ID):
            is_admin = True

        if not is_admin:
            logger.warning(
                f"Unauthorized callback attempt: user_id={user_id}, chat_id={chat_id}, admin_id={TELEGRAM_ADMIN_CHAT_ID}")
            await callback.answer("❌ Sizda bu amalni bajarish uchun ruxsat yo'q.")
            return

        try:
            order = await sync_to_async(Order.objects.get)(order_id=order_id)
        except Order.DoesNotExist:
            await callback.answer("❌ Buyurtma topilmadi.")
            return
        except Exception as e:
            logger.error(f"Database error getting order: {e}")
            await callback.answer("❌ Ma'lumotlar bazasida xatolik yuz berdi.")
            return

        try:
            user_profile = await sync_to_async(lambda: order.user.userprofile)()
            user_chat_id = user_profile.telegram_chat_id
        except Exception:
            user_chat_id = None
            await bot.send_message(
                TELEGRAM_ADMIN_CHAT_ID,
                f"⚠️ Buyurtma {order_id} uchun foydalanuvchi profili topilmadi."
            )

        if callback_data.startswith('confirm_'):
            try:
                # Avval callback answer berish
                await callback.answer("✅ To'lov tasdiqlandi!")

                # Ma'lumotlar bazasini yangilash
                order.payment_confirmed = True
                order.payment_confirmed_at = timezone.now()
                await sync_to_async(order.save)()

                logger.info(f"Order {order_id} payment confirmed by user {user_id}")

                # Foydalanuvchiga xabar yuborish
                if user_chat_id:
                    try:
                        await bot.send_message(
                            user_chat_id,
                            f"✅ buyurtma #{order_id} To'lovi tasdiqlandi! Buyurtmangiz qayta ishlana boshlandi."
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify user {user_chat_id}: {e}")

                # Xabarni yangilash (oxirida qilish)
                try:
                    await callback.message.edit_text(
                        f"✅ Buyurtma {order_id} to'lovi tasdiqlandi.\n"
                        f"Vaqt: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                except Exception as e:
                    logger.error(f"Failed to edit message: {e}")
                    # Agar xabarni o'zgartira olmasak, yangi xabar yuboramiz
                    try:
                        await bot.send_message(
                            chat_id,
                            f"✅ Buyurtma {order_id} to'lovi tasdiqlandi!"
                        )
                    except Exception as e2:
                        logger.error(f"Failed to send new message: {e2}")

            except Exception as e:
                logger.error(f"Error confirming order {order_id}: {e}")
                try:
                    await callback.answer("❌ To'lovni tasdiqlashda xatolik yuz berdi.")
                except:
                    pass

        elif callback_data.startswith('cancel_'):
            try:
                # Avval callback answer berish
                await callback.answer("❌ To'lov bekor qilindi!")

                logger.info(f"Order {order_id} payment cancelled by user {user_id}")

                # Foydalanuvchiga xabar yuborish
                if user_chat_id:
                    try:
                        await bot.send_message(
                            user_chat_id,
                            f"❌ To'lov tasdiqlanmadi. Iltimos, admin bilan bog'laning.\nTelefon: {ADMIN_PHONE_NUMBER}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify user {user_chat_id}: {e}")

                # Xabarni yangilash
                try:
                    await callback.message.edit_text(
                        f"❌ Buyurtma {order_id} to'lovi bekor qilindi.\n"
                        f"Vaqt: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                except Exception as e:
                    logger.error(f"Failed to edit message: {e}")
                    # Agar xabarni o'zgartira olmasak, yangi xabar yuboramiz
                    try:
                        await bot.send_message(
                            chat_id,
                            f"❌ Buyurtma {order_id} to'lovi bekor qilindi!"
                        )
                    except Exception as e2:
                        logger.error(f"Failed to send new message: {e2}")

            except Exception as e:
                logger.error(f"Error cancelling order {order_id}: {e}")
                try:
                    await callback.answer("❌ To'lovni bekor qilishda xatolik yuz berdi.")
                except:
                    pass

    except Exception as e:
        logger.error(f"Unexpected error in handle_order_callback: {e}")
        await callback.answer("❌ Kutilmagan xatolik yuz berdi.")

        # Admin uchun batafsil xabar
        try:
            await bot.send_message(
                TELEGRAM_ADMIN_CHAT_ID,
                f"🚨 Callback xatoligi:\n"
                f"User: {callback.from_user.id}\n"
                f"Data: {callback.data}\n"
                f"Error: {str(e)}"
            )
        except:
            pass


# Health check endpoint uchun
@dp.message(Command("health"))
async def health_check(message: types.Message):
    if message.from_user.id == int(TELEGRAM_ADMIN_CHAT_ID):
        await message.answer("🟢 Bot ishlayapti!")


async def main():
    logger.info("Starting Telegram bot...")

    try:
        # Bot ma'lumotlarini olish
        bot_info = await bot.get_me()
        logger.info(f"Bot started: @{bot_info.username}")

        # Polling boshqarish
        await dp.start_polling(bot, handle_signals=False)

    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise
    finally:
        logger.info("Bot stopped")


async def run_with_graceful_shutdown():
    """Graceful shutdown bilan botni ishga tushirish"""
    try:
        # Bot taskini yaratish
        bot_task = asyncio.create_task(main())

        # Shutdown signalini kutish
        shutdown_task = asyncio.create_task(shutdown_event.wait())

        # Birinchi tugagan taskni kutish
        done, pending = await asyncio.wait(
            [bot_task, shutdown_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        # Qolgan tasklarni bekor qilish
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Agar bot task tugagan bo'lsa, xatolik bo'lgan deb hisoblaymiz
        if bot_task in done:
            exception = bot_task.exception()
            if exception:
                raise exception

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        raise
    finally:
        try:
            await bot.session.close()
            logger.info("Bot session closed")
        except Exception as e:
            logger.error(f"Error closing bot session: {e}")


if __name__ == '__main__':
    try:
        asyncio.run(run_with_graceful_shutdown())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)