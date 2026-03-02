import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- SOZLAMALAR ---
TOKEN = "8705296063:AAEKfTBfe4_f3gRmdYLcMKQymMeqyIlEk24"
ADMIN_USER = "@TEZGO_001"
ADMIN_ID = 5271810793  # O'z ID raqamingiz

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- HOLATLAR ---
class ShopState(StatesGroup):
    village = State()
    menu = State()
    qty = State()

# --- MAHSULOTLAR (Uzum narxi + 5000 so'm) ---
ITEMS = {
    "🍫 Shokolad (25,000 UZS)": {"price": 25000, "img": "https://images.uzum.uz/cl9v39ln7at6uobba6lg/original.jpg"},
    "🥤 Flash (20,000 UZS)": {"price": 20000, "img": "https://images.uzum.uz/cl1m1ln6sfhsc0ulv6rg/original.jpg"},
    "🥤 Coca-Cola (15,000 UZS)": {"price": 15000, "img": "https://images.uzum.uz/ckp520cvutv4veof9tkg/original.jpg"}
}

# --- KLAVIATURALAR ---
v_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Cholyunus")], [KeyboardButton(text="Chol-Miraxamdam")]], resize_keyboard=True)
m_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🛍 Maxsulotlar")], 
    [KeyboardButton(text="👨‍💻 Admin bilan bog'lanish")]
], resize_keyboard=True)

# --- BOT LOGIKASI ---
@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    await message.answer("Xush kelibsiz! Qishlog'ingizni tanlang:", reply_markup=v_kb)
    await state.set_state(ShopState.village)

@dp.message(ShopState.village)
async def set_v(message: types.Message, state: FSMContext):
    await state.update_data(v=message.text)
    await message.answer(f"Tanlandi: {message.text}\nMinimal buyurtma: 50,000 UZS\nYetkazib berish: 2-3 kun.", reply_markup=m_kb)
    await state.set_state(ShopState.menu)

@dp.message(F.text == "👨‍💻 Admin bilan bog'lanish")
async def to_admin(message: types.Message):
    await message.answer(f"Savollar bo'yicha adminga yozing: {ADMIN_USER}")

@dp.message(F.text == "🛍 Maxsulotlar")
async def show_items(message: types.Message):
    for name, data in ITEMS.items():
        ikb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Sotib olish", callback_data=f"buy_{name}")]])
        await message.answer_photo(photo=data['img'], caption=name, reply_markup=ikb)

@dp.callback_query(F.data.startswith("buy_"))
async def ask_qty(call: types.CallbackQuery, state: FSMContext):
    name = call.data.split("_")[1]
    await state.update_data(item=name, price=ITEMS[name]['price'])
    await call.message.answer(f"{name} dan nechta kerak? (Faqat raqam)")
    await state.set_state(ShopState.qty)

@dp.message(ShopState.qty)
async def finish(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Raqam yozing!")
    
    data = await state.get_data()
    total = int(message.text) * data['price']
    
    if total < 50000:
        return await message.answer(f"Kam! Minimal 50,000 UZS bo'lishi kerak. Sizda: {total:,} UZS")

    order_text = (f"🔔 Yangi buyurtma!\n📍 Qishloq: {data['v']}\n🛍 {data['item']}: {message.text} ta\n"
                  f"💰 Jami: {total:,} UZS\n👤 Mijoz: @{message.from_user.username}")
    
    await bot.send_message(ADMIN_ID, order_text)
    await message.answer(f"Rahmat! Buyurtma qabul qilindi ({total:,} UZS). Admin bog'lanadi.", reply_markup=m_kb)
    await state.set_state(ShopState.menu)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
