import logging
import sqlite3
import os
import datetime
import pytz
import requests
from dotenv import load_dotenv
from google import genai
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    KeyboardButton, 
    ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

load_dotenv()

# ----------------- CONFIGURATION -----------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Token သို့မဟုတ် API Key မရှိသေးပါ။")

client = genai.Client(api_key=GEMINI_API_KEY)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# ----------------- DATABASE HELPERS -----------------
def get_db_connection():
    return sqlite3.connect("mindfulness_bot.db")

def register_user(chat_id: int, first_name: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO bot_users (chat_id, first_name, subscribed)
        VALUES (?, ?, 1)
    """, (chat_id, first_name))
    conn.commit()
    conn.close()

def get_subscribed_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM bot_users WHERE subscribed = 1")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

def get_random_daily_quote():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT quote FROM daily_quotes ORDER BY RANDOM() LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "လက်ရှိ ပစ္စုပ္ပန်တည့်တည့်မှာ သတိဖြင့် အေးချမ်းပါစေ။"

def get_resources(category: str, r_type: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT title, source FROM dhamma_resources WHERE category = ? AND type = ?", 
        (category, r_type)
    )
    results = cursor.fetchall()
    conn.close()
    return results

# ----------------- WEATHER API (FREE, NO KEY NEEDED) -----------------
def get_weather(lat: float, lon: float) -> str:
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
        )
        headers = {
            "User-Agent": "MindfulnessTelegramBot/1.0"
        }
        res = requests.get(url, headers=headers, timeout=10)
        
        print(f"Weather API Status Code: {res.status_code}") # စစ်ဆေးရန်
        
        if res.status_code != 200:
            return f"ရာသီဥတုဆာဗာ တုံ့ပြန်မှု မရရှိပါ (Status: {res.status_code})"

        data = res.json()
        current = data.get("current", {})
        
        temp = current.get("temperature_2m", "N/A")
        humidity = current.get("relative_humidity_2m", "N/A")
        wind = current.get("wind_speed_10m", "N/A")
        code = current.get("weather_code", 0)

        condition = "သာယာကြည်လင်နေပါသည် ☀️"
        if code in [1, 2, 3]:
            condition = "တိမ်အနည်းငယ် ရှိနေပါသည် ⛅"
        elif code in [45, 48]:
            condition = "မြူခိုးများ ရှိနေပါသည် 🌫️"
        elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
            condition = "မိုးရွာသွန်းနေပါသည် 🌧️"
        elif code in [95, 96, 99]:
            condition = "မိုးကြိုးမုန်တိုင်း ဖြစ်ပေါ်နိုင်ပါသည် ⛈️"

        return (
            f"🌤️ အခြေအနေ: {condition}\n"
            f"🌡️ အပူချိန်: {temp}°C\n"
            f"💧 စိုထိုင်းဆ: {humidity}%\n"
            f"💨 လေတိုက်နှုန်း: {wind} km/h"
        )
    except Exception as e:
        print(f"DEBUG - Weather Fetch Error: {repr(e)}") # အမှားအစစ်ကို terminal တွင် ပြပေးမည်
        return f"မိုးလေဝသ အချက်အလက် ယူ၍မရပါ ({type(e).__name__})"

def get_all_resources(r_type: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT title, source FROM dhamma_resources WHERE type = ?", (r_type,))
    results = cursor.fetchall()
    conn.close()
    return results


# ----------------- SCHEDULED BROADCAST JOBS -----------------
async def broadcast_quote(context: ContextTypes.DEFAULT_TYPE, title: str):
    users = get_subscribed_users()
    quote = get_random_daily_quote()
    msg = f"{title}\n\n{quote}"
    for chat_id in users:
        try:
            await context.bot.send_message(chat_id=chat_id, text=msg)
        except Exception:
            pass

async def morning_job(context: ContextTypes.DEFAULT_TYPE):
    await broadcast_quote(context, "🌅 မင်္ဂလာနံနက်ခင်းပါ... ဒီနေ့အတွက် ဆရာကြီးဒေါက်တာစိုးလွင်၏ ဓမ္မလက်ဆောင်:")

async def noon_job(context: ContextTypes.DEFAULT_TYPE):
    await broadcast_quote(context, "☀️ မွန်းတည့်ခေတ္တ အမောပြေ... စိတ်ကို သတိလေး ပြန်ကပ်ကြည့်ပါ:")

async def evening_job(context: ContextTypes.DEFAULT_TYPE):
    await broadcast_quote(context, "🌙 တစ်နေ့တာအပြီး ညချမ်းချိန် စိတ်အေးချမ်းရေး တရားစကား:")

# ----------------- BOT HANDLERS -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user.id, user.first_name)
    context.user_data["chat_history"] = []

    # အောက်ခြေ Main Menu Bar
    custom_keyboard = [
        [KeyboardButton("🌤️ လက်ရှိ မိုးလေဝသ ကြည့်မယ်", request_location=True)],
        [KeyboardButton("🌸 တရားဓမ္မ")]
    ]
    reply_markup_bottom = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"မင်္ဂလာပါ {user.first_name}။ စိတ်၏ ငြိမ်းချမ်းမှု ရရှိစေရန် ကြိုဆိုပါတယ်။\n\n"
        "နေ့စဉ် မနက်၊ နေ့လယ်၊ ည သတိပဋ္ဌာန် စိတ်ခွန်အားဖြည့် စာတိုလေးများ ပို့ပေးသွားပါမည်။\n\n"
        "တရားတော်များ ကြည့်ရှုဖတ်ရှုလိုပါက အောက်ခြေရှိ '🌸 တရားဓမ္မ' ခလုတ်ကို နှိပ်နိုင်ပါသည်ခင်ဗျာ။",
        reply_markup=reply_markup_bottom
    )

# "🌸 တရားဓမ္မ" ကို နှိပ်သည့်အခါ ပြသမည့် Menu
async def dhamma_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🧘 စိတ်ခံစားချက်အလိုက် ရွေးချယ်မယ်", callback_data="dhamma_by_mood")],
        [InlineKeyboardButton("📚 စာအုပ်နှင့် ဗီဒီယို အားလုံး ကြည့်မယ်", callback_data="dhamma_all_list")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "တရားဓမ္မ ဒေသနာများကို မည်သို့ ရွေးချယ်လေ့လာလိုပါသလဲခင်ဗျာ-",
        reply_markup=reply_markup
    ) 

async def dhamma_options_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # ၁။ စိတ်ခံစားချက်အလိုက် ရွေးချယ်လိုလျှင်
    if query.data == "dhamma_by_mood":
        inline_keyboard = [
            [
                InlineKeyboardButton("စိတ်ဖိစီးနေတယ် 😣", callback_data="mood_stress"),
                InlineKeyboardButton("ဝမ်းနည်းနေတယ် 😔", callback_data="mood_sadness")
            ],
            [
                InlineKeyboardButton("ဒေါသထွက်နေတယ် 😡", callback_data="mood_anger"),
                InlineKeyboardButton("စိတ်ငြိမ်သက်ချင်တယ် 🧘", callback_data="mood_mindfulness")
            ]
        ]
        await query.edit_message_text(
            "သင့်ရဲ့ လက်ရှိ စိတ်ခံစားချက်လေးကို ရွေးချယ်ပေးပါ-",
            reply_markup=InlineKeyboardMarkup(inline_keyboard)
        )

    # ၂။ စိတ်ခံစားချက် မရွေးဘဲ List အားလုံး ကြည့်လိုလျှင်
    elif query.data == "dhamma_all_list":
        choice_keyboard = [
            [
                InlineKeyboardButton("📖 တရားစာအုပ် အားလုံး", callback_data="list_all_book"),
                InlineKeyboardButton("🎬 Video အားလုံး", callback_data="list_all_video")
            ]
        ]
        await query.edit_message_text(
            "စာအုပ်များအားလုံး ဖတ်ရှုလိုပါသလား၊ ဗီဒီယိုအားလုံး ကြည့်ရှုလိုပါသလား ရွေးချယ်ပေးပါ-",
            reply_markup=InlineKeyboardMarkup(choice_keyboard)
        )

# List အားလုံးကို ထုတ်ပြပေးသည့် Callback
async def list_all_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    r_type = query.data.replace("list_all_", "") # 'book' or 'video'
    resources = get_all_resources(r_type)

    if not resources:
        await query.message.reply_text("လက်ရှိတွင် မည်သည့် အချက်အလက်မျှ မရှိသေးပါ။")
        return

    if r_type == "video":
        await query.message.reply_text("🎬 **ဆရာကြီးဒေါက်တာစိုးလွင်၏ တရားတော် ဗီဒီယိုများ အားလုံး-**")
        for title, source in resources:
            await query.message.reply_text(f"🔹 {title}\n🔗 {source}")
            
    elif r_type == "book":
        await query.message.reply_text("📖 **ဆရာကြီး၏ စာအုပ်များ ပေးပို့နေပါသည်...**")
        for title, source in resources:
            if os.path.exists(source):
                with open(source, "rb") as doc:
                    await context.bot.send_document(
                        chat_id=query.message.chat_id,
                        document=doc,
                        caption=f"📘 {title}"
                    )


# Mood ရွေးပြီးပါက စာအုပ်ဖတ်မလား၊ Video ကြည့်မလား ရွေးခိုင်းသည့် Handler
async def mood_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category = query.data.replace("mood_", "")
    context.user_data["selected_category"] = category

    choice_keyboard = [
        [
            InlineKeyboardButton("📖 တရားစာအုပ် ဖတ်မယ်", callback_data=f"res_book_{category}"),
            InlineKeyboardButton("🎬 Video တရားတော် ကြည့်မယ်", callback_data=f"res_video_{category}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(choice_keyboard)

    await query.edit_message_text(
        "သင့်ခံစားချက်အတွက် စာအုပ်ဖတ်ရှုလိုပါသလား၊ တရားတော် ဗီဒီယို ကြည့်ရှုလိုပါသလား ရွေးချယ်ပေးပါ-",
        reply_markup=reply_markup
    )

# စာအုပ် သို့မဟုတ် Video ပို့ပေးသည့် Handler
async def resource_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Callback data ပုံစံ: res_book_stress သို့မဟုတ် res_video_stress
    parts = query.data.split("_")
    r_type = parts[1]      # 'book' or 'video'
    category = parts[2]    # 'stress', 'sadness', etc.

    resources = get_resources(category, r_type)

    if not resources:
        await query.message.reply_text("ဤကဏ္ဍအတွက် အချက်အလက်များ မရှိသေးပါ။")
        return

    if r_type == "video":
        await query.message.reply_text("🎬 **သင့်အတွက် ဆရာကြီး၏ တရားတော် ဗီဒီယိုများ-**")
        for title, source in resources:
            await query.message.reply_text(f"🔹 {title}\n🔗 {source}")
    elif r_type == "book":
        await query.message.reply_text("📖 **ဆရာကြီး၏ စာအုပ်များ ပေးပို့နေပါသည်...**")
        for title, source in resources:
            if os.path.exists(source):
                with open(source, "rb") as doc:
                    await context.bot.send_document(
                        chat_id=query.message.chat_id,
                        document=doc,
                        caption=f"📘 {title}"
                    )

# စိတ်ခံစားချက် ပြန်ရွေးမည့်ခလုတ်ကို စာရိုက်လိုက်သည့် Handler

async def text_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🌸 တရားဓမ္မ":
        await dhamma_main_menu(update, context)
        return

    # ကျန်စာသားများဖြစ်ပါက Gemini AI နှင့် ဆွေးနွေးခြင်း
    user_msg = text
    sys_prompt = "သင်သည် ဆရာကြီးဒေါက်တာစိုးလွင်၏ သတိပဋ္ဌာန်အမြင်အတိုင်း နွေးထွေးစွာ ပြန်လည်နှစ်သိမ့်ဆွေးနွေးပေးသော အကူဖြစ်ပါသည်။"
    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=user_msg,
            config={"system_instruction": sys_prompt}
        )
        await update.message.reply_text(response.text)
    except Exception:
        await update.message.reply_text("စိတ်ကို သတိလေးကပ်ပြီး အသက်ကို ဖြည်းဖြည်း ရှူသွင်း ရှူထုတ် လုပ်ပေးပါခင်ဗျာ။")


async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        loc = update.message.location
        weather_info = get_weather(loc.latitude, loc.longitude)
        
        reply_text = (
            "📍 သင့်တည်နေရာ မိုးလေဝသ အခြေအနေ\n\n"
            f"{weather_info}\n\n"
            "🌧️ ရာသီဥတု အပြောင်းအလဲမှာ ခန္ဓာကိုယ်ရော စိတ်နှလုံးပါ ကျန်းမာအေးချမ်းပါစေခင်ဗျာ။"
        )
        # parse_mode မပါဘဲ ပို့ခြင်းဖြင့် Markdown error လုံးဝ ကင်းဝေးစေပါသည်
        await update.message.reply_text(reply_text)
    except Exception as e:
        logging.error(f"Location handler error: {e}")
        await update.message.reply_text("မိုးလေဝသ အချက်အလက် ရယူရာတွင် အခက်အခဲရှိနေပါသည်။ ခေတ္တစောင့်ပြီး ပြန်လည်စမ်းသပ်ပေးပါခင်ဗျာ။")


# ----------------- MAIN -----------------
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    job_queue = app.job_queue

    # ၁ နေ့ ၃ ကြိမ် သတိပဋ္ဌာန်စာတို ပို့မည့် အချိန်များ သတ်မှတ်ခြင်း (မြန်မာစံတော်ချိန်)
    if job_queue:
        mm_tz = pytz.timezone("Asia/Yangon")
        job_queue.run_daily(morning_job, time=datetime.time(hour=7, minute=30, tzinfo=mm_tz))
        job_queue.run_daily(noon_job, time=datetime.time(hour=12, minute=30, tzinfo=mm_tz))
        job_queue.run_daily(evening_job, time=datetime.time(hour=20, minute=0, tzinfo=mm_tz))

    app.add_handler(CommandHandler("start", start))
# Callback Handlers (အစီအစဉ်အတိုင်း ထားပါ)
    app.add_handler(CallbackQueryHandler(dhamma_options_callback, pattern="^dhamma_"))
    app.add_handler(CallbackQueryHandler(list_all_callback, pattern="^list_all_"))


    app.add_handler(CallbackQueryHandler(mood_callback, pattern="^mood_"))
    app.add_handler(CallbackQueryHandler(resource_callback, pattern="^res_"))

# Message Handlers
    app.add_handler(MessageHandler(filters.LOCATION, location_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_menu_handler))

    print("Bot is running with Weather and 3x Daily Schedule...")
    app.run_polling()

if __name__ == "__main__":
    main()