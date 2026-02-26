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
DB_FILE = "bank_database_final.json"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- 2. YORDAMCHI FUNKSIYALAR ---
def f_money(amount):
    return "{:,.2f}".format(float(amount)).replace(",", " ")

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
        penya = (u['loan'] * Decimal('0.05') * Decimal(str(passed_hours - 12))).quantize(Decimal('0.01'))
    total = (u['loan'] + penya).quantize(Decimal('0.01'))
    return u['loan'], penya, total

# --- 3. KLAVIATURALAR ---
def main_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🎰 OMADLI O'YIN"), types.KeyboardButton(text="💰 BALANS"))
    builder.row(types.KeyboardButton(text="✨ TEZKOR QARZ OLISH ✨"))
    builder.row(types.KeyboardButton(text="💳 DEPOZIT"), types.KeyboardButton(text="🏦 QARZNI YOPISH"))
    return builder.as_markup(resize_keyboard=True)

# --- 4. START VA REGISTRATSIYA ---
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
        save_db(users)
        kb = ReplyKeyboardBuilder().row(types.KeyboardButton(text="📱 RAQAMNI TASDIQLASH", request_contact=True))
        await message.answer("Endi raqamingizni tugma orqali tasdiqlang:", reply_markup=kb.as_markup(resize_keyboard=True))
    else:
        await message.answer("⚠️ Iltimos, pastdagi tugmani bosing!")

@dp.message(F.contact)
async def reg_contact(message: types.Message):
    uid = str(message.from_user.id)
    if message.contact.user_id == message.from_user.id:
        users[uid]['phone'] = message.contact.phone_number
        users[uid]['reg'] = True
        save_db(users)
        await message.answer("✅ Ro'yxatdan o'tdingiz!", reply_markup=main_kb())
    else:
        await message.answer("❌ Faqat o'z kontaktingizni yuboring!")

# --- 5. O'YIN (TUGATILGAN VA ISHLAYDIGAN) ---
@dp.message(F.text == "🎰 OMADLI O'YIN")
async def game_start(message: types.Message):
    uid = str(message.from_user.id)
    u = users[uid]
    bet = Decimal('100000.0')

    if u['balance'] < bet:
        return await message.answer(f"⚠️ Balans yetarli emas! O'yin narxi: {f_money(bet)} UZS")

    u['balance'] -= bet
    save_db(users)
    
    msg = await message.answer_dice("🎰")
    await asyncio.sleep(4)

    # Dice qiymati 1, 2, 3 bo'lsa yutqazadi, 4, 5, 6 bo'lsa yutadi (yoki random)
    if random.random() < 0.40: # 40% yutish imkoniyati
        win = Decimal(str(random.uniform(101000, 105000))).quantize(Decimal('0.01'))
        u['balance'] += win
        await message.answer(f"🎉 TABRIKLAYMIZ!\n✅ Siz yutdingiz: +{f_money(win)} UZS\n💰 Yangi balans: {f_money(u['balance'])} UZS")
    else:
        await message.answer(f"😟 Afsus, omad kelmadi.\n💸 Yo'qotildi: {f_money(bet)} UZS\n💰 Qolgan balans: {f_money(u['balance'])} UZS")
    save_db(users)

# --- 6. QARZ OLISH ---
@dp.message(F.text == "✨ TEZKOR QARZ OLISH ✨")
async def loan_menu(message: types.Message):
    u = get_u(message.from_user.id)
    if u['loan'] > 0: return await message.answer("🛑 Faol qarzingiz bor!")
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="💰 500 000 UZS", callback_data="loan_500000"))
    kb.row(types.InlineKeyboardButton(text="💰 1 000 000 UZS", callback_data="loan_1000000"))
    await message.answer("Kredit miqdorini tanlang:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("loan_"))
async def get_loan(call: types.CallbackQuery):
    uid = str(call.from_user.id)
    amt = Decimal(call.data.split("_")[1])
    users[uid]['loan'] = amt
    users[uid]['balance'] += amt
    users[uid]['loan_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_db(users)
    await call.message.edit_text(f"✅ {f_money(amt)} UZS hisobingizga tushdi!")

# --- 7. DEPOZIT VA QARZNI YOPISH (TASDIQLASH TIZIMI) ---
@dp.message(F.text.in_(["💳 DEPOZIT", "🏦 QARZNI YOPISH"]))
async def pay_start(message: types.Message):
    mode = "DEP" if "DEPOZIT" in message.text else "PAY"
    l, p, total = get_finance(message.from_user.id)
    if mode == "PAY" and total <= 0: return await message.answer("Qarzingiz yo'q.")
    
    users[str(message.from_user.id)]['wait_mode'] = mode
    txt = "To'lov summasini kiriting:" if mode == "DEP" else f"To'lov miqdori: {f_money(total)} UZS"
    await message.answer(f"💳 Karta: `{ADMIN_KARTA}`\n{txt}\n\n*To'lov qilgach, summani yozib yuboring:*", parse_mode="Markdown")

@dp.message(lambda m: get_u(m.from_user.id).get('wait_mode'))
async def pay_confirm(message: types.Message):
    uid = str(message.from_user.id)
    mode = users[uid].pop('wait_mode')
    try:
        amt = Decimal(re.sub(r'\D', '', message.text))
        kb = InlineKeyboardBuilder()
        # Callback data formatini aniq qilamiz
        kb.row(types.InlineKeyboardButton(text="✅ TASTIQLASH", callback_data=f"adm_ok_{mode}_{uid}_{amt}"),
               types.InlineKeyboardButton(text="❌ RAD ETISH", callback_data=f"adm_no_{uid}"))
        await bot.send_message(ADMIN_ID, f"📥 TO'LOV SO'ROVI:\nTur: {mode}\nSumma: {f_money(amt)}\nMijoz: {users[uid]['name']}", reply_markup=kb.as_markup())
        await message.answer("⌛️ So'rov yuborildi. Admin tasdiqlashini kuting...")
    except: await message.answer("Faqat raqam yozing!")

@dp.callback_query(F.data.startswith("adm_"))
async def admin_res(call: types.CallbackQuery):
    d = call.data.split("_")
    status = d[1] # ok yoki no
    if status == "ok":
        mode = d[2]
        uid = d[3]
        amt = Decimal(d[4])
        if mode == "DEP":
            users[uid]['balance'] += amt
        else:
            users[uid]['loan'] = Decimal('0.0')
            users[uid]['loan_time'] = None
        save_db(users)
        await bot.send_message(uid, f"✅ Admin to'lovni tasdiqladi! Balansingiz yangilandi.")
    else:
        uid = d[2]
        await bot.send_message(uid, "❌ Admin to'lovni rad etdi. Ma'lumotlarni tekshiring.")
    await call.message.edit_text(f"Bajarildi: {status}")

# --- 8. BALANS ---
@dp.message(F.text == "💰 BALANS")
async def show_bal(message: types.Message):
    l, p, total = get_finance(message.from_user.id)
    u = get_u(message.from_user.id)
    await message.answer(f"👤 Mijoz: {u['name']}\n💵 Balans: {f_money(u['balance'])} UZS\n🛑 Qarz: {f_money(total)} UZS (Asosiy: {f_money(l)}, Penya: {f_money(p)})")

# --- 9. AVTOMATIK OGOHLANTIRISH (FONDA ISHLAYDI) ---
async def auto_warning():
    while True:
        await asyncio.sleep(3600) # Har soatda tekshiradi
        for uid in list(users.keys()):
            l, p, total = get_finance(uid)
            if p > 0: # Agar penya bo'lsa
                try:
                    await bot.send_message(uid, f"🚨 **OGOHLANTIRISH**\n\nSizning qarzingiz bo'yicha muddat o'tib ketgan! Penya hisoblanmoqda.\nJami qarz: {f_money(total)} UZS\n\nIltimos, qarzni tezroq yoping!")
                except: pass

async def main():
    asyncio.create_task(auto_warning()) # Ogohlantirishni ishga tushirish
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

