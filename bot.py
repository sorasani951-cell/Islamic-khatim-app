import os
import time
import threading
import requests
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

BOT_TOKEN = "9281042407:AAHGrxMCiTfO4MMpkqRFERAhvyR6x95FMHo"
CHANNEL_ID = "@nurtestb"
ADMIN_ID = 8356035160

FIREBASE_URL = "https://islamic-7074d-default-rtdb.firebaseio.com"
WEB_APP_URL = "https://sorasani951-cell.github.io/Islamic-khatim-app/?v=2"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
BOT_USERNAME = bot.get_me().username
BOT_MINI_APP_LINK = f"https://t.me/{BOT_USERNAME}/khatm"

tracked_khatm_msgs = {}
tracked_zikr_msgs = {}

# ================= 24/7 Keep-Alive Web Server =================
app = Flask(__name__)

@app.route("/")
def home():
    return "Nur Digital Hybrid Bot is Running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ================= የቦቱ ዋና ተግባራት =================
def is_admin(message):
    if message.from_user and message.from_user.id == ADMIN_ID:
        return True
    if message.chat.type in ["group", "supergroup"]:
        try:
            member = bot.get_chat_member(message.chat.id, message.from_user.id)
            return member.status in ["creator", "administrator"]
        except Exception:
            pass
    return False

def get_khatm_data():
    try:
        res = requests.get(f"{FIREBASE_URL}/khatm_board.json", timeout=10).json()
        return res if isinstance(res, dict) else {}
    except Exception:
        return {}

def get_zikr_count():
    try:
        res = requests.get(f"{FIREBASE_URL}/shared_zikr.json", timeout=10).json()
        return int(res) if res else 0
    except Exception:
        return 0

def build_khatm_view(state):
    done_count = sum(1 for i in range(1, 31) if state.get(str(i), {}).get("status") == "done")
    taken_count = sum(1 for i in range(1, 31) if state.get(str(i), {}).get("status") == "taken")
    
    text = (
        "📖 <b>የጋራ የቁርአን ኸትም መርሐ-ግብር</b>\n\n"
        f"✅ የተጠናቀቀ: <b>{done_count}/30</b> | 🟨 የተያዘ: <b>{taken_count}/30</b>\n"
        "👇 <i>ጁዝ ለመያዝ (1x)፣ ሲጨርሱ ለማጠናቀቅ (2x) ይንኩ፦</i>"
    )
    
    markup = InlineKeyboardMarkup(row_width=5)
    buttons = []
    for i in range(1, 31):
        item = state.get(str(i), {})
        status = item.get("status", "open")
        icon = "⬜" if status == "open" else ("🟨" if status == "taken" else "✅")
        buttons.append(InlineKeyboardButton(f"{i} {icon}", callback_data=f"juz_{i}"))
    markup.add(*buttons)
    markup.row(InlineKeyboardButton("📱 በ Web App (ዝርዝር) ክፈት", url=BOT_MINI_APP_LINK))
    return text, markup

def build_zikr_view(count):
    text = (
        "🤲 <b>የዕለቱ ዚክር</b>\n\n"
        "«أَسْتَغْفِرُ اللَّهَ الْعَظِيمَ وَأَتُوبُ إِلَيْهِ»\n"
        "<i>«ታላቁን አላህ ምሕረትን እጠይቃለሁ፤ ወደ እርሱም እመለሳለሁ።»</i>"
    )
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(f"📿 አስተግፊሩላህ ({count})", callback_data="zikr_tap"),
        InlineKeyboardButton("📱 በ Web App ክፈት", url=BOT_MINI_APP_LINK)
    )
    return text, markup

@bot.message_handler(commands=["start", "help", "panel"])
def admin_panel(message):
    if message.chat.type != "private":
        return
    if message.from_user.id != ADMIN_ID:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📖 ኸትም እና ዚክር ክፈት", web_app=WebAppInfo(url=WEB_APP_URL)))
        bot.reply_to(message, "🌙 አሰላሙ ዓለይኩም! ለመሳተፍ ከታች ይንኩ፦", reply_markup=markup)
        return

    text = "🌙 <b>የአድሚን መቆጣጠሪያ (Hybrid 24/7)</b>\n\nበቻናል/ግሩፕ 30ውን ቁልፎች ለመልቀቅ ከታች ይምረጡ፦"
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📖 30ውን ጁዝ ቻናል ላይ ፖስት አድርግ", callback_data="admin_post_khatm"),
        InlineKeyboardButton("📿 የጋራ ዚክር ቻናል ላይ ፖስት አድርግ", callback_data="admin_post_zikr"),
        InlineKeyboardButton("🔄 30ውን ጁዝ Reset አድርግ", callback_data="admin_reset_khatm"),
        InlineKeyboardButton("📱 Web App-ውን ክፈት", web_app=WebAppInfo(url=WEB_APP_URL))
    )
    bot.reply_to(message, text, reply_markup=markup)

def post_khatm(chat_id):
    text, markup = build_khatm_view(get_khatm_data())
    msg = bot.send_message(chat_id, text, reply_markup=markup)
    tracked_khatm_msgs[chat_id] = msg.message_id

def post_zikr(chat_id):
    text, markup = build_zikr_view(get_zikr_count())
    msg = bot.send_message(chat_id, text, reply_markup=markup)
    tracked_zikr_msgs[chat_id] = msg.message_id

@bot.message_handler(commands=["start_khatm"])
def cmd_start_khatm(message):
    if not is_admin(message):
        return
    target = CHANNEL_ID if message.chat.type == "private" else message.chat.id
    post_khatm(target)

@bot.message_handler(commands=["post_zikr"])
def cmd_post_zikr(message):
    if not is_admin(message):
        return
    target = CHANNEL_ID if message.chat.type == "private" else message.chat.id
    post_zikr(target)

@bot.channel_post_handler(commands=["start_khatm", "post_zikr"])
def channel_commands(message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass
    if "/start_khatm" in message.text:
        post_khatm(message.chat.id)
    elif "/post_zikr" in message.text:
        post_zikr(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("juz_"))
def handle_juz_tap(call):
    juz_num = call.data.split("_")[1]
    uid = call.from_user.id
    name = call.from_user.first_name or "አንባቢ"

    state = get_khatm_data()
    current = state.get(juz_num, {"status": "open", "name": ""})
    status = current.get("status", "open")

    if status == "open":
        new_item = {"status": "taken", "uid": uid, "name": name}
        requests.put(f"{FIREBASE_URL}/khatm_board/{juz_num}.json", json=new_item, timeout=10)
        state[juz_num] = new_item
        bot.answer_callback_query(call.id, f"🟨 ጁዝ {juz_num}ን ይዘዋል! ሲጨርሱ በድጋሚ ይንኩት።")
    elif status == "taken" and current.get("uid") == uid:
        new_item = {"status": "done", "uid": uid, "name": name}
        requests.put(f"{FIREBASE_URL}/khatm_board/{juz_num}.json", json=new_item, timeout=10)
        state[juz_num] = new_item
        bot.answer_callback_query(call.id, f"✅ ማሻ አላህ! ጁዝ {juz_num}ን አጠናቀዋል!")
    elif status == "done" and current.get("uid") == uid:
        new_item = {"status": "open", "name": ""}
        requests.put(f"{FIREBASE_URL}/khatm_board/{juz_num}.json", json=new_item, timeout=10)
        state[juz_num] = new_item
        bot.answer_callback_query(call.id, f"⬜ ጁዝ {juz_num} እንደገና ክፍት ሆኗል።")
    else:
        owner = current.get("name", "ሌላ ሰው")
        msg = "ተይዟል" if status == "taken" else "ተጠናቋል"
        bot.answer_callback_query(call.id, f"ጁዝ {juz_num} በ {owner} {msg}!", show_alert=True)
        return

    text, markup = build_khatm_view(state)
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data == "zikr_tap")
def handle_zikr_tap(call):
    count = get_zikr_count() + 1
    requests.put(f"{FIREBASE_URL}/shared_zikr.json", json=count, timeout=10)
    bot.answer_callback_query(call.id, f"🤲 አላህ ይቀበልዎ! ({count})")
    text, markup = build_zikr_view(count)
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def handle_admin_callbacks(call):
    if call.from_user.id != ADMIN_ID:
        return
    if call.data == "admin_post_khatm":
        post_khatm(CHANNEL_ID)
        bot.answer_callback_query(call.id, "✅ 30ውም ጁዝ ቻናሉ ላይ ተፖስቷል!", show_alert=True)
    elif call.data == "admin_post_zikr":
        post_zikr(CHANNEL_ID)
        bot.answer_callback_query(call.id, "✅ ዚክር ቻናሉ ላይ ተፖስቷል!", show_alert=True)
    elif call.data == "admin_reset_khatm":
        state = {str(i): {"status": "open", "name": ""} for i in range(1, 31)}
        requests.put(f"{FIREBASE_URL}/khatm_board.json", json=state, timeout=15)
        bot.answer_callback_query(call.id, "🔄 30ውም ጁዝ Reset ሆኗል!", show_alert=True)

def sync_webapp_to_chat():
    last_khatm = None
    last_zikr = None
    while True:
        time.sleep(5)
        if tracked_khatm_msgs:
            state = get_khatm_data()
            if state != last_khatm:
                last_khatm = state
                text, markup = build_khatm_view(state)
                for cid, mid in list(tracked_khatm_msgs.items()):
                    try:
                        bot.edit_message_text(text, cid, mid, reply_markup=markup)
                    except Exception:
                        pass
        if tracked_zikr_msgs:
            count = get_zikr_count()
            if count != last_zikr:
                last_zikr = count
                text, markup = build_zikr_view(count)
                for cid, mid in list(tracked_zikr_msgs.items()):
                    try:
                        bot.edit_message_text(text, cid, mid, reply_markup=markup)
                    except Exception:
                        pass

threading.Thread(target=run_web, daemon=True).start()
threading.Thread(target=sync_webapp_to_chat, daemon=True).start()

print(f"🤖 @{BOT_USERNAME} (24/7 Hybrid) ተነስቷል!")
bot.infinity_polling(timeout=30, long_polling_timeout=20)
