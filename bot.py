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
            'name': '', 'phone': '', 'reg': False, 'step': 'start',
            'balance': Decimal('0.0'), 'loan': Decimal('0.0'), 
            'loan_time': None, 'game_count': 0, 'pay_step': None,
            'temp_deposit': '0', 'temp_withdraw': {}
        }
    return users[uid]

# --- 3. MATEMATIK MIYA (PENYA VA QARZ) ---
def get_finance(uid):
    u = get_u(uid)
    if not u['loan'] or u['loan'] <= 0 or u['loan_time'] is None: 
        return Decimal('0.0'), Decimal('0.0'), Decimal('0.0'), "Qarzingiz yo'q"

    l_time = datetime.strptime(u['loan_time'], "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    diff = now - l_time
    
    time_str = f"{diff.days} kun, {diff.seconds // 3600} soat, {(diff.seconds // 60) % 60} min, {diff.seconds % 60} sek"

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
    builder.row(types.KeyboardButton(text="💰 DEPOZIT"), types.KeyboardButton(text="💸 PUL YECHISH"))
    builder.row(types.KeyboardButton(text="💵 TEZKOR QARZ OLISH"), types.KeyboardButton(text="🏦 QARZNI YOPISH"))
    if user_id == ADMIN_ID:
        builder.row(types.KeyboardButton(text="📊 BARCHA FOYDALANUVCHILAR"))
    return builder.as_markup(resize_keyboard=True)

# --- 5. RO'YXATDAN O'TISH ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    u = get_u(message.from_user.id)
    if not u['reg']:
        u['step'] = 'get_name'
        save_db(users)
        await message.answer("🚀 Xush kelibsiz!\nIsm va Familiyangizni yozing:")
    else:
        await message.answer("Tizim faol!", reply_markup=main_kb(message.from_user.id))

@dp.message(lambda m: get_u(m.from_user.id)['step'] == 'get_name')
async def process_name(message: types.Message):
    uid = str(message.from_user.id)
    users[uid]['name'] = message.text
    users[uid]['step'] = 'get_phone'
    save_db(users)
    kb = ReplyKeyboardBuilder().row(types.KeyboardButton(text="📱 RAQAMNI YUBORISH", request_contact=True))
    await message.answer(f"Rahmat, {message.text}!\nEndi telefon raqamingizni yuboring:", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(F.contact)
async def process_contact(message: types.Message):
    uid = str(message.from_user.id)
    u = get_u(uid)
    if u['step'] == 'get_phone':
        u['phone'] = message.contact.phone_number
        u['reg'] = True
        u['step'] = 'completed'
        save_db(users)
        await bot.send_message(ADMIN_ID, f"🆕 YANGI AZO:\n👤 {u['name']}\n📞 {u['phone']}")
        await message.answer("✅ Ro'yxatdan o'tdingiz!", reply_markup=main_kb(uid))

# --- 6. PUL YECHISH TIZIMI ---
@dp.message(F.text == "💸 PUL YECHISH")
async def withdraw_start(message: types.Message):
    uid = str(message.from_user.id)
    _, _, total_debt, _ = get_finance(uid)
    if total_debt > 0:
        return await message.answer(f"❌ Qarzingiz bor ({total_debt:,} UZS). Avval qarzni to'lang!")
    users[uid]['pay_step'] = 'w_card'
    await message.answer("💳 Karta raqamingizni kiriting:")

@dp.message(lambda m: get_u(m.from_user.id).get('pay_step') == 'w_card')
async def withdraw_card(message: types.Message):
    uid = str(message.from_user.id)
    card = re.sub(r'\D', '', message.text)
    if len(card) < 16: return await message.answer("❌ Karta xato. Qayta yozing:")
    users[uid]['temp_withdraw'] = {'card': card}
    users[uid]['pay_step'] = 'w_name'
    await message.answer("👤 Karta egasining ism-familiyasi:")

@dp.message(lambda m: get_u(m.from_user.id).get('pay_step') == 'w_name')
async def withdraw_name(message: types.Message):
    uid = str(message.from_user.id)
    users[uid]['temp_withdraw']['name'] = message.text
    users[uid]['pay_step'] = 'w_conf_step'
    kb = ReplyKeyboardBuilder().row(types.KeyboardButton(text="Tasdiqlayman ✅"), types.KeyboardButton(text="Orqaga ❌"))
    await message.answer(f"Karta: {users[uid]['temp_withdraw']['card']}\nEga: {message.text}\n\nTo'g'rimi?", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(F.text == "Tasdiqlayman ✅")
async def withdraw_confirm_info(message: types.Message):
    uid = str(message.from_user.id)
    if users[uid].get('pay_step') == 'w_conf_step':
        users[uid]['pay_step'] = 'w_amt'
        await message.answer("💰 Summani yozing (Min: 300,000 | Max: 150,000,000):")

@dp.message(lambda m: get_u(m.from_user.id).get('pay_step') == 'w_amt')
async def withdraw_amount(message: types.Message):
    uid = str(message.from_user.id)
    amt_text = re.sub(r'\D', '', message.text)
    if not amt_text: return
    amt = int(amt_text)
    if amt < 300000 or amt > 150000000: return await message.answer("❌ Limit xato!")
    if Decimal(str(amt)) > users[uid]['balance']: return await message.answer("❌ Balans yetarli emas!")

    u = users[uid]
    kb = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="Pul tushdi ✅", callback_data=f"w_ok_{uid}_{amt}"),
                                     types.InlineKeyboardButton(text="TASTIQLANMADI ❌", callback_data=f"w_no_{uid}"))
    await bot.send_message(ADMIN_ID, f"🔔 YECHISH:\n👤 {u['temp_withdraw']['name']}\n💳 {u['temp_withdraw']['card']}\n💵 {amt:,} UZS", reply_markup=kb.as_markup())
    await message.answer("⌛️ So'rov yuborildi.", reply_markup=main_kb(uid))
    users[uid]['pay_step'] = None; save_db(users)

@dp.callback_query(F.data.startswith("w_"))
async def admin_withdraw_res(call: types.CallbackQuery):
    data = call.data.split("_")
    action, uid = data[1], data[2]
    if action == "ok":
        amt = Decimal(data[3])
        users[uid]['balance'] -= amt; save_db(users)
        await bot.send_message(uid, f"✅ To'lov bajarildi: {amt:,} UZS"); await call.message.edit_text("OK ✅")
    else:
        await bot.send_message(uid, "❌ Rad etildi."); await call.message.edit_text("RAD ❌")

# --- 7. DEPOZIT ---
@dp.message(F.text == "💰 DEPOZIT")
async def dep_init(message: types.Message):
    users[str(message.from_user.id)]['pay_step'] = 'dep_amt'
    await message.answer(f"💳 Karta: {ADMIN_KARTA}\nSummani yozing:")

@dp.message(lambda m: get_u(m.from_user.id).get('pay_step') == 'dep_amt')
async def dep_amt(message: types.Message):
    uid = str(message.from_user.id); amt = re.sub(r'\D', '', message.text)
    users[uid]['temp_deposit'] = amt; users[uid]['pay_step'] = 'dep_conf'
    kb = ReplyKeyboardBuilder().row(types.KeyboardButton(text="To'lov qildim ✅"), types.KeyboardButton(text="Orqaga ❌"))
    await message.answer(f"Summa: {int(amt):,} UZS. Tasdiqlaysizmi?", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(F.text == "To'lov qildim ✅")
async def dep_done(message: types.Message):
    uid = str(message.from_user.id); u = users[uid]
    kb = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="Tastiqlash ✅", callback_data=f"d_ok_{uid}"),
                                     types.InlineKeyboardButton(text="Xato ❌", callback_data=f"d_no_{uid}"))
    await bot.send_message(ADMIN_ID, f"💰 DEPOZIT: {u['name']}\n💵 {int(u['temp_deposit']):,}", reply_markup=kb.as_markup())
    await message.answer("⌛️ Tekshirilmoqda..."); users[uid]['pay_step'] = None; save_db(users)

@dp.callback_query(F.data.startswith("d_"))
async def admin_dep_res(call: types.CallbackQuery):
    action, uid = call.data.split("_")[1], call.data.split("_")[2]
    if action == "ok":
        users[uid]['balance'] += Decimal(users[uid]['temp_deposit'])
        save_db(users); await bot.send_message(uid, "✅ Depozit tasdiqlandi!"); await call.message.edit_text("OK")
    else:
        await bot.send_message(uid, "❌ Depozit rad etildi."); await call.message.edit_text("XATO")

# --- 8. O'YIN VA MA'LUMOTLAR ---
@dp.message(F.text == "🎰 O'YINNI BOSHLASH")
async def start_game(message: types.Message):
    uid = str(message.from_user.id); u = get_u(uid)
    price, win = Decimal('250000.0'), Decimal('255000.0')
    if u['balance'] < price: return await message.answer("⚠️ Mablag' yetarli emas!")
    u['balance'] -= price; u['game_count'] += 1
    await message.answer_dice(emoji="🎰"); await asyncio.sleep(4)
    if u['game_count'] % 3 == 0:
        u['balance'] += win; await message.answer(f"🎉 G'ALABA! +{win:,}")
    else:
        await message.answer("😟 OMAD KELMADI.")
    save_db(users)

@dp.message(F.text == "👤 MA'LUMOTLARIM")
async def user_info(message: types.Message):
    uid = str(message.from_user.id); u = users[uid]
    loan_base, penya, total, time_spent = get_finance(uid)
    text = (f"👤 **ISM:** {u['name']}\n💰 **BALANS:** {u['balance']:,} UZS\n\n"
            f"🕒 **MUDDAT:** {time_spent}\n💵 **QARZ:** {loan_base:,} UZS\n"
            f"⚠️ **PENYA:** {penya:,} UZS\n🛑 **JAMI:** {total:,} UZS")
    await message.answer(text, parse_mode="Markdown")

# --- 9. QARZ TIZIMI ---
@dp.message(F.text == "💵 TEZKOR QARZ OLISH")
async def loan_offer(message: types.Message):
    u = get_u(message.from_user.id)
    if u['loan'] > 0: return await message.answer("⚠️ Avvalgi qarzni yoping!")
    kb = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="500,000", callback_data="g_500000"),
                                     types.InlineKeyboardButton(text="1,000,000", callback_data="g_1000000"))
    await message.answer("Limit:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("g_"))
async def process_loan(call: types.CallbackQuery):
    uid = str(call.from_user.id); amt = Decimal(call.data.split("_")[1])
    users[uid]['loan'] = amt; users[uid]['balance'] += amt
    users[uid]['loan_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_db(users); await call.message.edit_text(f"✅ {amt:,} UZS berildi.")

@dp.message(F.text == "🏦 QARZNI YOPISH")
async def pay_init(message: types.Message):
    _, _, total, _ = get_finance(message.from_user.id)
    if total <= 0: return await message.answer("Qarzingiz yo'q.")
    users[str(message.from_user.id)]['pay_step'] = 'p_amt'
    await message.answer(f"💳 Karta: {ADMIN_KARTA}\nSumma: {total:,} UZS\nTo'lovni yozing:")

@dp.message(lambda m: get_u(m.from_user.id).get('pay_step') == 'p_amt')
async def pay_amt(message: types.Message):
    uid = str(message.from_user.id); amt = re.sub(r'\D', '', message.text)
    users[uid]['temp_pay'] = amt; users[uid]['pay_step'] = 'p_conf'
    kb = ReplyKeyboardBuilder().row(types.KeyboardButton(text="To'lovni tasdiqlayman ✅"), types.KeyboardButton(text="Orqaga ❌"))
    await message.answer(f"Summa: {int(amt):,} UZS. Tasdiqlaysizmi?", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(F.text == "To'lovni tasdiqlayman ✅")
async def pay_done(message: types.Message):
    uid = str(message.from_user.id); u = users[uid]
    kb = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="OK ✅", callback_data=f"a_ok_{uid}"),
                                     types.InlineKeyboardButton(text="NO ❌", callback_data=f"a_no_{uid}"))
    await bot.send_message(ADMIN_ID, f"🛑 QARZ YOPISH: {u['name']}\n💵 {int(u['temp_pay']):,}", reply_markup=kb.as_markup())
    await message.answer("⌛️ Tekshirilmoqda..."); u['pay_step'] = None; save_db(users)

@dp.callback_query(F.data.startswith("a_"))
async def admin_pay_res(call: types.CallbackQuery):
    action, uid = call.data.split("_")[1], call.data.split("_")[2]
    if action == "ok":
        users[uid]['loan'] = Decimal('0.0'); users[uid]['loan_time'] = None; save_db(users)
        await bot.send_message(uid, "✅ Qarz yopildi!"); await call.message.edit_text("OK ✅")
    else:
        await bot.send_message(uid, "❌ Rad etildi."); await call.message.edit_text("RAD ❌")

@dp.message(F.text == "Orqaga ❌")
async def cancel(message: types.Message):
    users[str(message.from_user.id)]['pay_step'] = None
    await message.answer("Bekor qilindi.", reply_markup=main_kb(message.from_user.id))

# --- 10. ISHGA TUSHIRISH ---
async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())



