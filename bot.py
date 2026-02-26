          
import telebot
from telebot import types
import re
import time
import threading
import random
from datetime import datetime, timedelta
import os

# --- 1. ASOSIY KONFIGURATSIYA ---
TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE' #
ADMIN_ID = 8299021738  # Sizning Admin ID raqamingiz
ADMIN_KARTA = "9860 6067 5582 9722" # Sizning karta raqamingiz
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
            # 12 soatdan keyin har bir soat uchun 5% penya qo'shiladi
            penya = int(user['loan'] * 0.05 * (hours - 12))
    total_to_pay = user['loan'] + penya
    return user['loan'], penya, total_to_pay

# --- 3. AVTOMATIK OGOHLANTIRISH TIZIMI (THREADING) ---
def scare_system():
    while True:
        now = datetime.now()
        for uid, u in users.items():
            if u['loan'] > 0 and u['loan_time']:
                if (now - u['loan_time']) > timedelta(hours=12):
                    if not u['last_scare'] or (now - u['last_scare']) > timedelta(hours=2):
                        try:
                            bot.send_message(uid, "‼️ DIQQAT! QARZ MUDDATI O'TDI!\n\nSizga penya hisoblanmoqda. Iltimos, qarzni tezroq to'lang!")
                            u['last_scare'] = now
                        except:
                            pass
        time.sleep(60)

# Avtomatik ogohlantirishni alohida oqimda ishga tushirish
threading.Thread(target=scare_system, daemon=True).start()

# --- 4. KLAVIATURALAR (MENYU) ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 777 O'yini", "💰 Balans")
    markup.row("💳 Depozit qilish", "💸 Qarz olish")
    markup.row("🏦 Qarzni to'lash", "ℹ️ Ma'lumot")
    markup.row("📤 Pul yechish")
    return markup

# --- 5. RO'YXATDAN O'TISH (TELEFON TUGMASI BILAN) ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user = get_user(message.chat.id)
    if not user['reg']:
        msg = bot.send_message(message.chat.id, "👋 Xush kelibsiz! Botdan foydalanish uchun ro'yxatdan o'ting.\n\nTo'liq Ism va Familiyangizni kiriting:")
        bot.register_next_step_handler(msg, reg_name)
    else:
        bot.send_message(message.chat.id, "Asosiy menyuga xush kelibsiz!", reply_markup=main_menu())

def reg_name(message):
    get_user(message.chat.id)['name'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = types.KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True) #
    markup.add(button)
    msg = bot.send_message(message.chat.id, "📞 Pastdagi tugmani bosing va telefon raqamingizni yuboring:", reply_markup=markup)
    bot.register_next_step_handler(msg, reg_phone)

def reg_phone(message):
    user = get_user(message.chat.id)
    if message.contact:
        user['phone'] = message.contact.phone_number
        user['reg'] = True
        bot.send_message(message.chat.id, "✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!", reply_markup=main_menu())
        # Adminga yangi a'zo haqida xabar
        bot.send_message(ADMIN_ID, f"🆕 YANGI FOYDALANUVCHI:\n👤 Ism: {user['name']}\n📞 Tel: {user['phone']}\n🆔 ID: {message.chat.id}")
    else:
        msg = bot.send_message(message.chat.id, "⚠️ Iltimos, raqamingizni yuborish uchun faqat tugmani bosing!")
        bot.register_next_step_handler(msg, reg_phone)

# --- 6. O'YIN TIZIMI (YANGILANGAN YUTUQ LIMITLARI) ---
@bot.message_handler(func=lambda m: m.text == "🎰 777 O'yini")
def game_777(message):
    user = get_user(message.chat.id)
    bet = 50000  # Tikish miqdori
    
    if user['balance'] < bet:
        return bot.send_message(message.chat.id, f"⚠️ Balansingiz yetarli emas. Kamida {bet:,} UZS kerak.")
    
    user['balance'] -= bet
    bot.send_message(message.chat.id, "🎰 O'yin boshlandi! Omadingizni kutyapmiz...")
    bot.send_dice(message.chat.id, emoji='🎰')
    time.sleep(4)
    
    # REJIM: 3 ta yutqaziq : 1 ta yutuq (25% ehtimol)
    is_winner = random.choice([False, False, False, True])
    
    if is_winner:
        # Eng kam 10,000 va eng ko'p 130,000 UZS yutuq
        win_amt = random.randint(10000, 130000) 
        user['balance'] += win_amt
        bot.send_message(message.chat.id, f"🎉 TABRIKLAYMIZ! Siz yutdingiz!\n✅ Yutuq: +{win_amt:,} UZS\n💵 Yangi balans: {user['balance']:,} UZS")
    else:
        bot.send_message(message.chat.id, f"😟 Afsuski, omad kulib boqmadi.\n❌ Yutqazdingiz: -{bet:,} UZS\n💵 Qolgan balans: {user['balance']:,} UZS")

# --- 7. QARZ OLISH VA SHARTNOMA ---
@bot.message_handler(func=lambda m: m.text == "💸 Qarz olish")
def loan_init(message):
    user = get_user(message.chat.id)
    if user['loan'] > 0:
        return bot.send_message(message.chat.id, "❌ Sizda to'lanmagan qarz bor! Avval uni to'lang.")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Tasdiqlayman", callback_data="l_yes"),
               types.InlineKeyboardButton("❌ Bekor qilish", callback_data="l_no"))
    bot.send_message(message.chat.id, "⚠️ QARZ SHARTLARI:\n• Muddat: 12 soat (0% foiz)\n• Kechiksa: Har soat uchun +5% penya hisoblanadi\n\nUshbu shartlarga rozimisiz?", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('l_'))
def loan_callback(call):
    if call.data == "l_yes":
        msg = bot.send_message(call.message.chat.id, "💰 Qarz miqdorini yozing (100,000 - 2,000,000 UZS):")
        bot.register_next_step_handler(msg, loan_finish)
    else:
        bot.edit_message_text("Qarz olish bekor qilindi.", call.message.chat.id, call.message.message_id)

def loan_finish(message):
    try:
        amt = int(re.sub(r'\D', '', message.text))
        if 100000 <= amt <= 2000000:
            user = get_user(message.chat.id)
            user['loan'] = amt
            user['balance'] += amt
            user['loan_time'] = datetime.now()
            bot.send_message(message.chat.id, f"✅ Tabriklaymiz! Hisobingizga {amt:,} UZS qarz o'tkazildi.")
            bot.send_message(ADMIN_ID, f"💸 QARZ OLINDI:\n👤 {user['name']}\n💰 Miqdor: {amt:,} UZS")
        else:
            bot.send_message(message.chat.id, "❌ Limit: 100,000 dan 2,000,000 gacha.")
    except:
        bot.send_message(message.chat.id, "⚠️ Iltimos, faqat raqam yozing.")

# --- 8. DEPOZIT VA TO'LOV TIZIMI ---
@bot.message_handler(func=lambda m: m.text in ["💳 Depozit qilish", "🏦 Qarzni to'lash"])
def payment_start(message):
    mode = "DEP" if "Depozit" in message.text else "PAY"
    l, p, total = calculate_loan(message.chat.id)
    if mode == "PAY" and total == 0:
        return bot.send_message(message.chat.id, "✅ Sizning qarzingiz yo'q.")
    
    msg = bot.send_message(message.chat.id, f"💳 Karta raqam: {ADMIN_KARTA}\n\nTo'lov qilgach, yuborgan summani raqamda yozib yuboring:")
    bot.register_next_step_handler(msg, lambda m: payment_req(m, mode))

def payment_req(message, mode):
    try:
        amt = int(re.sub(r'\D', '', message.text))
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ TASDIQLASH", callback_data=f"adm_ok_{mode}_{message.chat.id}_{amt}"),
                   types.InlineKeyboardButton("❌ RAD ETISH", callback_data=f"adm_no_{mode}_{message.chat.id}"))
        bot.send_message(ADMIN_ID, f"🔔 TO'LOV SO'ROVI ({mode}):\nID: {message.chat.id}\nSumma: {amt:,} UZS", reply_markup=markup)
        bot.send_message(message.chat.id, "⌛️ So'rov yuborildi. Admin tasdiqlashini kuting...")
    except:
        bot.send_message(message.chat.id, "⚠️ Iltimos, summani raqamda kiriting.")

# --- 9. PUL YECHISH ---
@bot.message_handler(func=lambda m: m.text == "📤 Pul yechish")
def withdraw_init(message):
    user = get_user(message.chat.id)
    _, _, total_loan = calculate_loan(message.chat.id)
    if total_loan > 0:
        return bot.send_message(message.chat.id, "❌ Avval qarzingizni to'lang!")
    if user['balance'] < 300000:
        return bot.send_message(message.chat.id, "⚠️ Minimal yechish miqdori: 300,000 UZS.")
    
    msg = bot.send_message(message.chat.id, "💳 Karta raqamingizni va Ism-familiyangizni yozing:")
    bot.register_next_step_handler(msg, withdraw_final)

def withdraw_final(message):
    bot.send_message(ADMIN_ID, f"📤 PUL YECHISH SO'ROVI:\nMa'lumot: {message.text}\nID: {message.chat.id}")
    bot.send_message(message.chat.id, "✅ So'rovingiz adminga yuborildi.")

# --- 10. ADMIN CALLBACK (TASDIQLASH) ---
@bot.callback_query_handler(func=lambda c: c.data.startswith('adm_'))
def admin_callback(call):
    data = call.data.split('_')
    status, mode, uid, amt = data[1], data[2], int(data[3]), int(data[4] if len(data) > 4 else 0)
    user = get_user(uid)

    if status == 'ok':
        if mode == 'DEP':
            user['balance'] += amt
        elif mode == 'PAY':
            user['loan'] = 0
            user['loan_time'] = None
        bot.send_message(uid, f"✅ Tabriklaymiz! So'rovingiz tasdiqlandi!")
    else:
        bot.send_message(uid, "❌ Afsuski, so'rovingiz admin tomonidan rad etildi.")
    
    bot.edit_message_text(f"Bajarildi: {status}", call.message.chat.id, call.message.message_id)

# --- 11. BALANS VA MA'LUMOT ---
@bot.message_handler(func=lambda m: m.text == "💰 Balans")
def show_balance(message):
    l, p, total = calculate_loan(message.chat.id)
    user = get_user(message.chat.id)
    bot.send_message(message.chat.id, f"💵 BALANSINGIZ: {user['balance']:,} UZS\n💸 TO'LANMAGAN QARZ: {total:,} UZS\n(Asosiy: {l:,} + Penya: {p:,})")

@bot.message_handler(func=lambda m: m.text == "ℹ️ Ma'lumot")
def info_view(message):
    user = get_user(message.chat.id)
    bot.send_message(message.chat.id, f"👤 Ism: {user['name']}\n📞 Tel: {user['phone']}\n💰 Balans: {user['balance']:,} UZS\n🆔 ID: {message.chat.id}")

# BOTNI ISHGA TUSHIRISH
bot.polling(none_stop=True)
