# bot/main.py
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
from decouple import config
import api
from utils.database import User
from utils.otp_session import create_or_get_session

TOKEN = config("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True
)

# ===================== OTP yuborish =====================
async def send_otp(message: Message, otp_code: str):
    html_text = (
        f"✅ Salom, <b>{message.from_user.first_name}</b>!\n\n"
        f"🔑 Sizning OTP kodingiz: <code>{otp_code}</code>\n\n"
        "⏳ Kod 1 daqiqa ichida amal qiladi.\n"
        "❗ Iltimos, bu kodni hech kimga ko‘rsatmang."
    )
    await message.answer(html_text, parse_mode=ParseMode.HTML)
    await message.answer(
        "⚡️",
    )

# ===================== /start handler =====================
@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer(
        "🏆",
    )
    await message.answer(
        "✨",
    )
    
    await message.answer(
        "💯",
    )
    await message.answer(
        "Salom! Ro‘yxatdan o‘tish uchun telefon raqamingizni yuboring 👇",
        reply_markup=keyboard,
    )

@dp.message(lambda message: message.contact is not None)
async def contact_handler(message: Message):
    user_id = message.from_user.id
    phone = message.contact.phone_number
    username = message.from_user.username or f"user{user_id}"
    full_name = f"{message.contact.first_name or ''} {message.contact.last_name or ''}".strip()

    # Foydalanuvchi auth-serverda
    user, created = await User.get_or_create(
        telegram_id=user_id,
        defaults={"phone": phone, "full_name": full_name, "username": username}
    )

    # User mavjud bo‘lsa, yangilash
    if not created:
        user.phone = phone
        user.full_name = full_name
        user.username = username
        await user.save()
        await message.answer(
            f"Salom <b>{full_name}</b>! Siz allaqachon ro'yxatdan o'tgansiz.\n /login buyrug'ini bosing.",
            parse_mode=ParseMode.HTML
        )
        return

    # OTP + JWT
    user, otp_code, jwt_token, is_cached = await create_or_get_session(user_id, phone)

    if is_cached:
        await message.answer(
            "⚠️ Sizning OTP kodingiz o'zgarmagan.\n⏳ Iltimos, mavjud kodni ishlating.",
            parse_mode=ParseMode.HTML
        )
    else:
        await message.answer(
        "🎉",
        )
        await send_otp(message, otp_code)

@dp.message(Command("login"))
async def login_handler(message: Message):
    user_id = message.from_user.id
    user = await User.get_or_none(telegram_id=user_id)
    
    if not user:
        await message.answer(
            "⚠️ Siz ro‘yxatdan o‘tmagansiz.\n❗ /start orqali ro‘yxatdan o‘ting.",
            parse_mode=ParseMode.HTML
        )
        return

    # OTP + JWT
    user, otp_code, jwt_token, is_cached = await create_or_get_session(user_id, user.phone)


    await user.save()

    if is_cached:
        await message.answer("⚠️ Sizning OTP kodingiz o'zgarmagan.\n⏳ Iltimos, mavjud kodni ishlating.", parse_mode=ParseMode.HTML)
    else:
        await message.answer(
        "💯",
        )
        await send_otp(message, otp_code)


async def main():
    # DB va API server
    await api.init_db()
    runner = web.AppRunner(api.app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("🚀 API server: http://localhost:8080")

    # Bot polling
    polling_task = asyncio.create_task(dp.start_polling(bot))
    try:
        await polling_task
    finally:
        await runner.cleanup()
        try:
            await bot.session.close()
        except Exception:
            pass
        from tortoise import Tortoise
        await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(main())