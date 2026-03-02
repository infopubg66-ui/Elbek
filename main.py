import asyncio
import sqlite3
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- SOZLAMALAR ---
TOKEN = "8729423224:AAGKzoZIxqlog3an5aWGTzMauczdZOUmvSs
OPENAI_API_KEY = "Sk-proj-o0E7cTS9GTCTW1T2VzvKcUMQDraH8JOlOp9yATTZi2cfxJyBn33OnZcUmxqszB5eN7AB3KpWZ7T3BlbkFJhbjZettT0b6LgTnGkaa01GX-XihLIekL7YXSq9sediLiObPjE0Tf3tmEZDeQ-turlPTdxmjRMA"
ADMIN_USER = "@TEZGO_001"
FOUNDER = "HAYDAROV ELBEK"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect('maktab_platforma.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY, name TEXT, grade TEXT, phone TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- HOLATLAR ---
class AppState(StatesGroup):
    name = State()
    grade = State()
    phone = State()
    subject = State()
    learning = State()

# --- TUGMALAR ---
def main_menu():
    kb = [
        [KeyboardButton(text="📚 Fan tanlash va O'rganish")],
        [KeyboardButton(text="👤 Profilim"), KeyboardButton(text="ℹ️ Bot haqida")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def subjects_kb():
    subjects = [
        [KeyboardButton(text="🇬🇧 Ingliz tili"), KeyboardButton(text="🔢 Matematika")],
        [KeyboardButton(text="⚛️ Fizika"), KeyboardButton(text="📜 Tarix")],
        [KeyboardButton(text="☣️ Biologiya"), KeyboardButton(text="🌍 Geografiya")],
        [KeyboardButton(text="⬅️ Orqaga")]
    ]
    return ReplyKeyboardMarkup(keyboard=subjects, resize_keyboard=True)

# --- CHATGPT (AI) BILAN ALOQA ---
async def ai_tutor(subject, user_message):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": f"Siz 31-maktab o'quvchilari uchun {subject} fanidan aqlli va mehribon o'qituvchisiz. Bot asoschisi: {FOUNDER}. Maqsadingiz - fanni 0 dan boshlab, juda sodda va tushunarli tilda o'rgatish. Yoshlarni ilmga qiziqtiring va har doim motivatsiya bering."},
            {"role": "user", "content": user_message}
        ]
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data['choices'][0]['message']['content']
                return "Hozircha AI o'qituvchi band. Birozdan so'ng urinib ko'ring (API balansini tekshiring)."
        except:
            return "Ulanishda xatolik yuz berdi."

# --- BOT BUYRUQLARI ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer(f"Assalomu alaykum! {FOUNDER} tomonidan yaratilgan 31-maktab ta'lim botiga xush kelibsiz! ✨\n\nBu yerda barcha fanlarni 0 dan o'rganishingiz mumkin.\n\nRo'yxatdan o'tish uchun Ism-Familiyangizni yozing:")
    await state.set_state(AppState.name)

@dp.message(AppState.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    grades = [[KeyboardButton(text=f"{i}-sinf")] for i in range(5, 12)]
    await message.answer("Sinfingizni tanlang:", reply_markup=ReplyKeyboardMarkup(keyboard=grades, resize_keyboard=True))
    await state.set_state(AppState.grade)

@dp.message(AppState.grade)
async def get_grade(message: types.Message, state: FSMContext):
    await state.update_data(grade=message.text)
    await message.answer("Telefon raqamingizni yuboring:", 
                         reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Raqamni ulash", request_contact=True)]], resize_keyboard=True))
    await state.set_state(AppState.phone)

@dp.message(AppState.phone, F.contact)
async def save_user(message: types.Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect('maktab_platforma.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", 
                   (message.from_user.id, data['name'], data['grade'], message.contact.phone_number))
    conn.commit()
    conn.close()
    await message.answer(f"Tabriklaymiz {data['name']}! Ro'yxatdan o'tdingiz. Bilim olishni boshlaymizmi? 🚀", reply_markup=main_menu())
    await state.clear()

@dp.message(F.text == "ℹ️ Bot haqida")
async def about(message: types.Message):
    await message.answer(f"🏗 **Bot asoschisi:** {FOUNDER}\n👨‍💻 **Admin:** {ADMIN_USER}\n\nUshbu bot yoshlarni o'qishga jalb qilish va maktab fanlarini 0 dan mukammal o'rganishlari uchun yaratilgan.")

@dp.message(F.text == "👤 Profilim")
async def profile(message: types.Message):
    conn = sqlite3.connect('maktab_platforma.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (message.from_user.id,))
    u = cursor.fetchone()
    conn.close()
    if u:
        await message.answer(f"👤 **Profilingiz:**\n\nIsm: {u[1]}\nSinf: {u[2]}\nTel: {u[3]}")

@dp.message(F.text == "📚 Fan tanlash va O'rganish")
async def choose_sub(message: types.Message, state: FSMContext):
    await message.answer("Qaysi fanni o'rganishni istaysiz?", reply_markup=subjects_kb())
    await state.set_state(AppState.subject)

@dp.message(AppState.subject)
async def start_learning(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga":
        await message.answer("Asosiy menyu", reply_markup=main_menu())
        await state.clear()
        return
    await state.update_data(chosen_sub=message.text)
    await message.answer(f"Siz {message.text} fanini tanladingiz. Savolingizni bering yoki 'Menga ushbu fanni 0 dan tushuntir' deb yozing!", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Orqaga")]], resize_keyboard=True))
    await state.set_state(AppState.learning)

@dp.message(AppState.learning)
async def learning_process(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga":
        await message.answer("Fanlar ro'yxati", reply_markup=subjects_kb())
        await state.set_state(AppState.subject)
        return
    
    data = await state.get_data()
    msg = await message.answer("O'qituvchi tayyorlanyapti... ⏳")
    response = await ai_tutor(data['chosen_sub'], message.text)
    await msg.edit_text(response)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
