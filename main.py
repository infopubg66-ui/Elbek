import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# 1. BOT SOZLAMALARI
TOKEN = "8729423224:AAGKzoZIxqlog3an5aWGTzMauczdZOUmvSs"
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# 2. SOVG'ALAR RO'YXATI
sovglar = [
    "🍫 Alpen Gold! Kuningiz shirin o'tsin!",
    "🍹 Muzdek Moxitto! Tetiklashib oling!",
    "🌯 Mazali Lavash! Yoqimli ishtaha!"
]

# 3. START BUYRUG'I
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="Barabanni aylantirish 🎰"))
    
    await message.answer(
        f"Salom, {message.from_user.first_name}! 👋\n"
        "Xursandchilik barabaniga xush kelibsiz. Sovg'angizni aniqlash uchun tugmani bosing!",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

# 4. BARABAN VA NATIJA MANTIQI
@dp.message(F.text == "Barabanni aylantirish 🎰")
async def spin_wheel(message: types.Message):
    # Telegram slot machine (🎰) yuborish
    dice_msg = await message.answer_dice(emoji="🎰")
    
    # Baraban aylanishi uchun 4 soniya kutish
    await asyncio.sleep(4)
    
    # Tasodifiy sovg'ani tanlash
    yutug_matni = random.choice(sovglar)
    
    # Natijani e'lon qilish
    await message.answer(
        f"🎉 Baraban to'xtadi!\n\n"
        f"Sizning sovg'angiz: **{yutug_matni}**\n\n"
        "Yana o'ynash uchun tugmani bosing!"
    )

# 5. BOTNI ISHGA TUSHIRISH
async def main():
    print("Bot GitHub-dan muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi")

# ---------------------------------------------------------
# GITHUB UCHUN QO'SHIMCHA MA'LUMOT (requirements.txt):
# GitHub-ga yuklaganda 'requirements.txt' degan fayl ochib, 
# ichiga pastdagi so'zni yozib qo'ying:
# aiogram
# ---------------------------------------------------------

