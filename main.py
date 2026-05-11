import asyncio
import sqlite3
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# --- KONFIGURATSIYA ---
TOKEN = "SIZNING_BOT_TOKENINGIZ" # BotFather'dan olingan tokenni qo'ying
ADMIN_ID = 7013452402
CHANNEL_ID = "@fargonauzb_201"
CHANNEL_URL = "https://t.me/fargonauzb_201"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect("users.db")
    curr = conn.cursor()
    curr.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, name TEXT, gender TEXT, phone TEXT, timestamp REAL)''')
    conn.commit()
    conn.close()

# --- HOLATLAR (FSM) ---
class Register(StatesGroup):
    name = State()
    gender = State()
    phone = State()

# --- KLAVIATURALAR ---
def main_menu():
    kb = [
        [KeyboardButton(text="💼 Ish bo'yicha"), KeyboardButton(text="📩 Shaxsiy xabar")],
        [KeyboardButton(text="📊 Mening hisobim"), KeyboardButton(text="ℹ️ Bot haqida")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def gender_menu():
    kb = [[KeyboardButton(text="Erkak 🧔"), KeyboardButton(text="Ayol 👩")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def contact_menu():
    kb = [[KeyboardButton(text="📱 Raqamni yuborish", request_contact=True)]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- START ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(f"Assalomu alaykum, **{message.from_user.full_name}**!\n"
                         "**H.E INVEST** tizimiga xush kelibsiz. Kerakli bo'limni tanlang:",
                         reply_markup=main_menu(), parse_mode="Markdown")

# --- RO'YXATDAN O'TISH JARAYONI ---
@dp.message(F.text == "💼 Ish bo'yicha")
async def start_reg(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("users.db")
    user = conn.execute("SELECT * FROM users WHERE id=?", (message.from_user.id,)).fetchone()
    conn.close()

    if user:
        await message.answer(f"Xush kelibsiz! Ishlarni ko'rish uchun kanalimizga o'ting: {CHANNEL_URL}\n"
                             "Sizni yana kutib qolamiz! 😊", reply_markup=main_menu())
    else:
        await message.answer("Ishlarni ko'rish uchun ro'yxatdan o'ting.\nIsm va familiyangizni kiriting:")
        await state.set_state(Register.name)

@dp.message(Register.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Jinsingizni tanlang:", reply_markup=gender_menu())
    await state.set_state(Register.gender)

@dp.message(Register.gender)
async def get_gender(message: types.Message, state: FSMContext):
    if message.text in ["Erkak 🧔", "Ayol 👩"]:
        await state.update_data(gender=message.text)
        await message.answer("Telefon raqamingizni yuboring:", reply_markup=contact_menu())
        await state.set_state(Register.phone)
    else:
        await message.answer("Iltimos, tugmalardan birini tanlang!")

@dp.message(Register.phone, F.contact)
async def get_phone(message: types.Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect("users.db")
    conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", 
                 (message.from_user.id, data['name'], data['gender'], message.contact.phone_number, time.time()))
    conn.commit()
    conn.close()
    
    await message.answer("✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!\n\n"
                         f"Hozirda barcha ish o'rinlari shu yerda: {CHANNEL_URL}\n"
                         "Siz bilan ishlashdan mamnunmiz, sizni yana kutib qolamiz! ✨", 
                         reply_markup=main_menu())
    await state.clear()

# --- ADMIN PANEL ---
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        conn = sqlite3.connect("users.db")
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        await message.answer(f"👮‍♂️ Admin Panel\n\nJami foydalanuvchilar: {users} ta")
    else:
        await message.answer("Bu buyruq faqat admin uchun!")

# --- BOTNI ISHGA TUSHIRISH ---
async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
                         


