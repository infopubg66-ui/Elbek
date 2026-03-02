import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# --- SOZLAMALAR ---
TOKEN = "8729423224:AAGKzoZIxqlog3an5aWGTzMauczdZOUmvSs"
ADMIN_ID = 7013452402  # Siz bergan Admin ID

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- SOVG'ALAR ---
sovglar = [
    "🍫 Alpen Gold! Kuningiz shirin o'tsin!",
    "🍹 Muzdek Moxitto! Tetiklashib oling!",
    "🌯 Mazali Lavash! Yoqimli ishtaha!"
]

# --- START BUYRUG'I ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="Barabanni aylantirish 🎰"))
    
    await message.answer(
        f"Salom, {message.from_user.first_name}! 👋\n"
        "Barabanni aylantirish uchun pastdagi tugmani bosing!",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

# --- BARABAN VA NATIJA ---
@dp.message(F.text == "Barabanni aylantirish 🎰")
async def spin_wheel(message: types.Message):
    # Telegram slot machine yuborish
    dice_msg = await message.answer_dice(emoji="🎰")
    
    # Baraban aylanishi uchun 4 soniya kutish
    await asyncio.sleep(4)
    
    yutug = random.choice(sovglar)
    user_name = message.from_user.full_name
    user_handle = f"@{message.from_user.username}" if message.from_user.username else "Username yo'q"

    # Foydalanuvchiga natijani yuborish
    await message.answer(
        f"🎉 Baraban to'xtadi!\n\n"
        f"Sizning sovg'angiz: **{yutug}**\n\n"
        f"Iltimos, ushbu natijani skrinshot qilib Admin @TEZGO_001 ga yuboring!"
    )

    # ADMINGA XABAR YUBORISH (Avtomatik)
    admin_text = (
        f"🔔 **Yangi yutuq!**\n\n"
        f"👤 Foydalanuvchi: {user_name} ({user_handle})\n"
        f"🆔 ID: {message.from_user.id}\n"
        f"🎁 Sovg'a: {yutug}"
    )
    try:
        await bot.send_message(chat_id=ADMIN_ID, text=admin_text)
    except Exception as e:
        logging.error(f"Adminga xabar yuborishda xato: {e}")

# --- BOTNI ISHGA TUSHIRISH ---
async def main():
    print("Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi")

