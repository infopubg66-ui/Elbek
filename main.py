import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# --- SOZLAMALAR ---
# Siz bergan token:
TOKEN = "8729423224:AAGKzoZIxqlog3an5aWGTzMauczdZOUmvSs"

# Xatolarni konsolda ko'rish uchun loglar
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
    # Menyuda katta tugma yaratish
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="Barabanni aylantirish 🎰"))
    
    await message.answer(
        f"Salom, {message.from_user.first_name}! 👋\n"
        "Xursandchilik barabaniga xush kelibsiz. Sovg'angizni aniqlash uchun pastdagi tugmani bosing!",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

# --- BARABAN VA NATIJA ---
@dp.message(F.text == "Barabanni aylantirish 🎰")
async def spin_wheel(message: types.Message):
    # Telegram slot machine (🎰) effektini yuborish
    dice_msg = await message.answer_dice(emoji="🎰")
    
    # Baraban 4 soniya aylanadi, shuning uchun kutamiz
    await asyncio.sleep(4)
    
    # Tasodifiy sovg'ani tanlash
    yutug = random.choice(sovglar)
    
    # Natijani e'lon qilish
    await message.answer(
        f"🎉 Baraban to'xtadi!\n\n"
        f"Sizning sovg'angiz: **{yutug}**\n\n"
        "Yana o'ynash uchun tugmani bosing!"
    )

# --- BOTNI ISHGA TUSHIRISH ---
async def main():
    print("Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        async :run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi")
