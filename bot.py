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
DB_FILE = "global_system_v3.json"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- 2. BAZA BILAN ISHLASH ---
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
            'balance': Decimal('0.0'), 'loan': Decimal('0.0'), 
            'loan_time': None, 'game_count': 0, 'pay_step': None,
            'temp_deposit': '0'
        }
    return users[uid]

# --- 3. MATEMATIK MIYA ---
def get_finance(uid):
    u = get_u(uid)
    if not u['loan'] or u['loan'] <= 0 or u['loan_time'] is None: 
        return Decimal('0.0'), Decimal('0.0'), Decimal('0.0'), "Qarzingiz yo'q"

    l_time = datetime.strptime(u['loan_time'], "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    diff = now - l_time
    
    years = diff.days // 365
    days = diff.days % 365
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    time_str = f"{years} yil, {days} kun, {hours} soat, {minutes} minut, {seconds} sekund"

    total_hours_passed = Decimal(str(diff.total_seconds() / 3600))
    penya = Decimal('0.0')
    if total_hours_passed > 12:
        late_hours = total_hours_passed - Decimal('12.0')
        penya = (u['loan'] * Decimal('0.10') * late_hours).quantize(Decimal('0.01'))
    
    total_debt = (u['loan'] + penya).quantize(Decimal('0.01'))
    return u['loan'], penya, total_debt, time_str

# --- 4. KLAVIATURALAR ---
def main_kb(user_id):
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🎰 O'YINNI BOSHLASH"), types.KeyboardButton(text="👤 MA'LUMOTLARIM"))
    builder.row(types.KeyboardButton(text="💰 DEPOZIT"), types.KeyboardButton(text="💵 TEZKOR QARZ OLISH"))
    builder.row(types.KeyboardButton(text="🏦 QARZNI YOPISH"))
    if user_id == ADMIN_ID:
        builder.row(types.KeyboardButton(text="📊 BARCHA FOYDALANUVCHILAR"))
    return builder.as_markup(resize_keyboard=True)

# --- 5. RO'YXATDAN O'TISH ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    u = get_u(message.from_user.id)
    if not u['reg']:
        await message.answer("🚀 Xush kelibsiz!\nIsm va Familiyangizni yozing:")
    else:
        await message.answer("Tizim faol!", reply_markup=main_kb(message.from_user.id))

@dp.message(lambda m: not get_u(m.from_user.id)['reg'] and not m.contact)
async def reg_name(message: types.Message):
    uid = str(message.from_user.id)
    users[uid]['name'] = message.text
    save_db(users)
    kb = ReplyKeyboardBuilder().row(types.KeyboardButton(text="📱 RAQAMNI TASDIQLASH", request_contact=True))
    await message.answer(f"Rahmat! Endi raqamingizni yuboring:", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(F.contact)
async def reg_contact(message: types.Message):
    uid = str(message.from_user.id)
    if message.contact.user_id == message.from_user.id:
        users[uid]['phone'] = message.contact.phone_number
        users[uid]['reg'] = True
        save_db(users)
        await bot.send_message(ADMIN_ID, f"🆕 YANGI:\n👤 {users[uid]['name']}\n📞 {users[uid]['phone']}")
        await message.answer("✅ Ro'yxatdan o'tdingiz!", reply_markup=main_kb(message.from_user.id))

# --- 6. DEPOZIT TIZIMI ---
@dp.message(F.text == "💰 DEPOZIT")
async def dep_init(message: types.Message):
    uid = str(message.from_user.id)
    users[uid]['pay_step'] = 'dep_amt'
    await message.answer(f"💳 Admin kartasi: `{ADMIN_KARTA}`\n\nQancha depozit qilmoqchisiz? Summani yozing:", parse_mode="Markdown")

@dp.message(lambda m: get_u(m.from_user.id).get('pay_step') == 'dep_amt')
async def dep_amt(message: types.Message):
    uid = str(message.from_user.id)
    amt = re.sub(r'\D', '', message.text)
    if not amt or int(amt) < 1000:
        return await message.answer("❌ Minimal depozit 1,000 UZS. Qayta yozing:")
    
    users[uid]['temp_deposit'] = amt
    users[uid]['pay_step'] = 'dep_conf'
    kb = ReplyKeyboardBuilder().row(types.KeyboardButton(text="To'lovni qildim ✅"), types.KeyboardButton(text="Bekor qilish ❌"))
    await message.answer(f"Summa: {int(amt):,} UZS. To'lov qilgan bo'lsangiz tugmani bosing:", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(F.text == "To'lovni qildim ✅")
async def dep_done(message: types.Message):
    uid = str(message.from_user.id)
    u = users[uid]
    if u.get('pay_step') == 'dep_conf':
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="Tastiqlash ✅", callback_data=f"dep_ok_{uid}"),
               types.InlineKeyboardButton(text="Xato ❌", callback_data=f"dep_no_{uid}"))
        await bot.send_message(ADMIN_ID, f"💰 YANGI DEPOZIT:\n👤 {u['name']}\n💵 Summa: {int(u['temp_deposit']):,} UZS", reply_markup=kb.as_markup())
        await message.answer("⌛️ Depozit admin tomonidan tekshirilmoqda...", reply_markup=main_kb(message.from_user.id))
        u['pay_step'] = None
        save_db(users)

@dp.callback_query(F.data.startswith("dep_"))
async def admin_dep_res(call: types.CallbackQuery):
    action, uid = call.data.split("_")[1], call.data.split("_")[2]
    if action == "ok":
        amount = Decimal(users[uid]['temp_deposit'])
        users[uid]['balance'] += amount
        save_db(users)
        await bot.send_message(uid, f"✅ Depozit tastiqlandi! Balansga +{amount:,} UZS qo'shildi.")
        await call.message.edit_text("Depozit tastiqlandi ✅")
    else:
        await bot.send_message(uid, "❌ Depozit rad etildi. To'lovda xatolik!")
        await call.message.edit_text("Depozit rad etildi ❌")

# --- 7. O'YIN ---
@dp.message(F.text == "🎰 O'YINNI BOSHLASH")
async def start_game(message: types.Message):
    uid = str(message.from_user.id)
    u = get_u(uid)
    price, win = Decimal('250000.0'), Decimal('255000.0')
    if u['balance'] < price:
        return await message.answer("⚠️ Balans yetarli emas! Depozit qiling yoki qarz oling.")
    u['balance'] -= price
    u['game_count'] += 1
    await message.answer_dice(emoji="🎰")
    await asyncio.sleep(4)
    if u['game_count'] % 3 == 0:
        u['balance'] += win
        await message.answer(f"🎉 G'ALABA! +{win:,} UZS")
    else:
        await message.answer(f"😟 OMAD KELMADI.")
    save_db(users)

# --- 8. MA'LUMOTLAR ---
@dp.message(F.text == "👤 MA'LUMOTLARIM")
async def user_info(message: types.Message):
    uid = str(message.from_user.id)
    u = users[uid]
    loan_base, penya, total, time_spent = get_finance(uid)
    text = (
        f"👤 **ISM:** {u['name']}\n"
        f"💰 **BALANS:** {u['balance']:,} UZS\n\n"
        f"🕒 **QARZ MUDDATI:**\n{time_spent}\n\n"
        f"💵 **QARZ:** {loan_base:,} UZS\n"
        f"⚠️ **PENYA:** {penya:,} UZS\n"
        f"🛑 **UMUMIY:** {total:,} UZS"
    )
    await message.answer(text, parse_mode="Markdown")

# --- 9. QARZ VA QARZNI YOPISH (Oldingi mantiq saqlangan) ---
@dp.message(F.text == "💵 TEZKOR QARZ OLISH")
async def loan_offer(message: types.Message):
    u = get_u(message.from_user.id)
    if u['loan'] > 0: return await message.answer("⚠️ Avvalgi qarzni yoping!")
    kb = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="500 000", callback_data="get_500000"),
                                     types.InlineKeyboardButton(text="1 000 000", callback_data="get_1000000"))
    await message.answer("Miqdorni tanlang:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("get_"))
async def process_loan(call: types.CallbackQuery):
    uid = str(call.from_user.id); amt = Decimal(call.data.split("_")[1])
    users[uid]['loan'] = amt; users[uid]['balance'] += amt
    users[uid]['loan_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_db(users); await call.message.edit_text(f"✅ {amt:,} UZS berildi.")

@dp.message(F.text == "🏦 QARZNI YOPISH")
async def pay_init(message: types.Message):
    _, _, total, _ = get_finance(message.from_user.id)
    if total <= 0: return await message.answer("Qarzingiz yo'q.")
    users[str(message.from_user.id)]['pay_step'] = 'pay_amt'
    await message.answer(f"💳 Karta: {ADMIN_KARTA}\nSumma: {total:,} UZS\n\nTo'langan summani yozing:")

@dp.message(lambda m: get_u(m.from_user.id).get('pay_step') == 'pay_amt')
async def pay_amt(message: types.Message):
    uid = str(message.from_user.id); amt = re.sub(r'\D', '', message.text)
    users[uid]['temp_pay'] = amt; users[uid]['pay_step'] = 'pay_conf'
    kb = ReplyKeyboardBuilder().row(types.KeyboardButton(text="Tasdiqlayman ✅"), types.KeyboardButton(text="Bekor qilish ❌"))
    await message.answer(f"Summa: {int(amt):,} UZS. Tasdiqlaysizmi?", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(F.text == "Tasdiqlayman ✅")
async def pay_done(message: types.Message):
    uid = str(message.from_user.id); u = users[uid]
    if u.get('pay_step') == 'pay_conf':
        kb = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="OK ✅", callback_data=f"adm_ok_{uid}"),
                                         types.InlineKeyboardButton(text="NO ❌", callback_data=f"adm_no_{uid}"))
        await bot.send_message(ADMIN_ID, f"🛑 QARZ TO'LOVI:\n👤 {u['name']}\n💵 {int(u['temp_pay']):,}", reply_markup=kb.as_markup())
        await message.answer("⌛️ Tekshirilmoqda..."); u['pay_step'] = None; save_db(users)

@dp.callback_query(F.data.startswith("adm_"))
async def admin_pay_res(call: types.CallbackQuery):
    action, uid = call.data.split("_")[1], call.data.split("_")[2]
    if action == "ok":
        users[uid]['loan'] = Decimal('0.0'); users[uid]['loan_time'] = None; save_db(users)
        await bot.send_message(uid, "✅ Qarzingiz yopildi!"); await call.message.edit_text("Bajarildi ✅")
    else:
        await bot.send_message(uid, "❌ To'lov rad etildi."); await call.message.edit_text("Rad etildi ❌")

@dp.message(F.text == "Bekor qilish ❌")
async def cancel_action(message: types.Message):
    users[str(message.from_user.id)]['pay_step'] = None
    await message.answer("Bekor qilindi.", reply_markup=main_kb(message.from_user.id))

# --- 10. ISHGA TUSHIRISH ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


