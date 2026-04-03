import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Bot sozlamalari
TOKEN = "8612087037:AAF__p76LVMdAiE4Czb6J7DI5rY6Tq_4nP8"
ADMIN_ID = 526852806

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Narxlar
PRICES = {
    "7x": 700,
    "8x": 1100,
    "Bolachoq": 600
}

# Ma'lumotlar bazasini sozlash
def init_db():
    conn = sqlite3.connect("factory.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS workers 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, balance REAL DEFAULT 0, total_work INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS logs 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, worker_id INTEGER, type TEXT, amount INTEGER, sum REAL)''')
    conn.commit()
    conn.close()

# Holatlar (States)
class WorkState(StatesGroup):
    waiting_for_name = State()
    selecting_worker_for_job = State()
    selecting_type = State()
    entering_count = State()
    selecting_worker_for_payment = State()
    entering_payment = State()

# Klaviaturalar
def main_menu():
    kb = [
        [KeyboardButton(text="📊 Barcha hisobotlar")],
        [KeyboardButton(text="👤 Yangi ishchi qo'shish")],
        [KeyboardButton(text="🧹 Ishchilar qilgan ish soni")],
        [KeyboardButton(text="💸 Ishchilar pul oldi")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# Admin tekshiruvi uchun dekorator o'rniga oddiy filtr
@dp.message(F.from_user.id != ADMIN_ID)
async def not_admin(message: types.Message):
    await message.answer("Siz admin emassiz! Bu bot faqat admin uchun.")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Xush kelibsiz! Kerakli bo'limni tanlang:", reply_markup=main_menu())

# 1. Barcha hisobotlar
@dp.message(F.text == "📊 Barcha hisobotlar")
async def all_reports(message: types.Message):
    conn = sqlite3.connect("factory.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, total_work, balance FROM workers")
    workers = cursor.fetchall()
    conn.close()

    if not workers:
        return await message.answer("Hozircha ishchilar yo'q.")

    text = "📋 **Ishchilar hisoboti:**\n\n"
    for w in workers:
        text += f"👤 {w[0]}\n   - Jami ish: {w[1]} ta\n   - Qolgan pul (qarz): {w[2]:,.0f} so'm\n\n"
    await message.answer(text, parse_mode="Markdown")

# 2. Yangi ishchi qo'shish
@dp.message(F.text == "👤 Yangi ishchi qo'shish")
async def add_worker(message: types.Message, state: FSMContext):
    await message.answer("Yangi ishchining ismini kiriting:")
    await state.set_state(WorkState.waiting_for_name)

@dp.message(WorkState.waiting_for_name)
async def save_worker(message: types.Message, state: FSMContext):
    name = message.text
    conn = sqlite3.connect("factory.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO workers (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()
    await message.answer(f"{name} muvaffaqiyatli ro'yxatdan o'tdi.", reply_markup=main_menu())
    await state.clear()

# 3. Ish sonini kiritish
@dp.message(F.text == "🧹 Ishchilar qilgan ish soni")
async def select_worker_job(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("factory.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM workers")
    workers = cursor.fetchall()
    conn.close()

    if not workers:
        return await message.answer("Ishchilar mavjud emas.")

    buttons = [[InlineKeyboardButton(text=w[1], callback_data=f"job_{w[0]}")] for w in workers]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Ishchini tanlang:", reply_markup=kb)

@dp.callback_query(F.data.startswith("job_"))
async def select_type(callback: types.CallbackQuery, state: FSMContext):
    worker_id = callback.data.split("_")[1]
    await state.update_data(w_id=worker_id)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="7x (700)", callback_data="type_7x")],
        [InlineKeyboardButton(text="8x (1100)", callback_data="type_8x")],
        [InlineKeyboardButton(text="Bolachoq (600)", callback_data="type_Bolachoq")]
    ])
    await callback.message.edit_text("Turini tanlang:", reply_markup=kb)

@dp.callback_query(F.data.startswith("type_"))
async def enter_count(callback: types.CallbackQuery, state: FSMContext):
    job_type = callback.data.split("_")[1]
    await state.update_data(j_type=job_type)
    await callback.message.edit_text(f"{job_type} tanlandi. Miqdorini kiriting (nechta):")
    await state.set_state(WorkState.entering_count)

@dp.message(WorkState.entering_count)
async def save_job(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Faqat raqam kiriting!")
    
    count = int(message.text)
    data = await state.get_data()
    w_id, j_type = data['w_id'], data['j_type']
    summa = count * PRICES[j_type]

    conn = sqlite3.connect("factory.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE workers SET balance = balance + ?, total_work = total_work + ? WHERE id = ?", (summa, count, w_id))
    conn.commit()
    conn.close()

    await message.answer(f"Saqlandi! {summa:,.0f} so'm hisobga qo'shildi.", reply_markup=main_menu())
    await state.clear()

# 4. Pul berish
@dp.message(F.text == "💸 Ishchilar pul oldi")
async def select_worker_pay(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("factory.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM workers")
    workers = cursor.fetchall()
    conn.close()

    buttons = [[InlineKeyboardButton(text=w[1], callback_data=f"pay_{w[0]}")] for w in workers]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Pul olgan ishchini tanlang:", reply_markup=kb)

@dp.callback_query(F.data.startswith("pay_"))
async def enter_payment(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(w_id=callback.data.split("_")[1])
    await callback.message.edit_text("Berilgan pul miqdorini kiriting:")
    await state.set_state(WorkState.entering_payment)

@dp.message(WorkState.entering_payment)
async def save_payment(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Faqat raqam kiriting!")
    
    amount = int(message.text)
    data = await state.get_data()
    
    conn = sqlite3.connect("factory.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE workers SET balance = balance - ? WHERE id = ?", (amount, data['w_id']))
    conn.commit()
    conn.close()

    await message.answer(f"To'lov qayd etildi: {amount:,.0f} so'm.", reply_markup=main_menu())
    await state.clear()

async def main():
    init_db()
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


