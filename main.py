import asyncio
import sqlite3
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# --- KONFIGURATSIYA ---
TOKEN = "8180332379:AAFGvvwNyFEssmVyosmaoVUzN1n0Ko2LIY4"
ADMIN_ID = 7013452402
CHANNEL_URL = "https://t.me/fargonauzb_201"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect("users.db")
    conn.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, name TEXT, gender TEXT, phone TEXT, timestamp REAL)''')
    conn.commit()
    conn.close()

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

# --- ASOSIY FUNKSIYALAR ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(f"Assalomu alaykum, {message.from_user.full_name}!\n"
                         "**H.E INVEST** tizimiga xush kelibsiz. Kerakli bo'limni tanlang:",
                         reply_markup=main_menu(), parse_mode="Markdown")

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
    kb = [[KeyboardButton(text="Erkak 🧔"), KeyboardButton(text="Ayol 👩")]]
    await message.answer("Jinsingizni tanlang:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(Register.gender)

@dp.message(Register.gender)
async def get_gender(message: types.Message, state: FSMContext):
    await state.update_data(gender=message.text)
    kb = [[KeyboardButton(text="📱 Raqamni yuborish", request_contact=True)]]
    await message.answer("Telefon raqamingizni yuboring (tugmani bosing):", 
                         reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(Register.phone)

@dp.message(Register.phone, F.contact)
async def get_phone(message: types.Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect("users.db")
    conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?)", 
                 (message.from_user.id, data['name'], data['gender'], message.contact.phone_number, time.time()))
    conn.commit()
    conn.close()
    
    await message.answer("✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!\n\n"
                         f"Hozirda barcha ish o'rinlari shu yerda: {CHANNEL_URL}\n"
                         "Sizni yana kutib qolamiz! ✨", reply_markup=main_menu())
    await state.clear()

# --- ADMIN PANEL ---
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        conn = sqlite3.connect("users.db")
        # 3 oydan eski (90 kun) ma'lumotlarni o'chirish
        conn.execute("DELETE FROM users WHERE timestamp < ?", (time.time() - 7776000,))
        conn.commit()
        users = conn.execute("SELECT * FROM users").fetchall()
        conn.close()
        
        res = "👮‍♂️ **Admin Panel**\n\n"
        for u in users:
            res += f"🔹 {u[1]} | {u[3]} | {u[2]}\n"
        await message.answer(res if users else "Foydalanuvchilar yo'q.")
    else:
        await message.answer("Taqqiqlangan bo'lim!")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

                         


