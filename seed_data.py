import sqlite3

def init_and_seed_db():
    conn = sqlite3.connect("mindfulness_bot.db")
    cursor = conn.cursor()

    # Table အဟောင်းများကို ရှင်းထုတ်ပြီး ပြန်လည်တည်ဆောက်ခြင်း
    cursor.execute("DROP TABLE IF EXISTS dhamma_resources")
    cursor.execute("DROP TABLE IF EXISTS daily_quotes")
    cursor.execute("DROP TABLE IF EXISTS bot_users")

    # ၁။ တရားစာအုပ်နှင့် ဗီဒီယိုများ Table
    cursor.execute("""
        CREATE TABLE dhamma_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            type TEXT NOT NULL,       -- 'video' သို့မဟုတ် 'book'
            category TEXT NOT NULL,   -- 'stress', 'sadness', 'anger', 'mindfulness'
            source TEXT NOT NULL
        )
    """)

    # ၂။ စာရင်းသွင်းထားသော User များ Table
    cursor.execute("""
        CREATE TABLE bot_users (
            chat_id INTEGER PRIMARY KEY,
            first_name TEXT,
            subscribed INTEGER DEFAULT 1 -- 1 = active, 0 = unsubscribed
        )
    """)

    # ၃။ နေ့စဉ် သတိပဋ္ဌာန် စိတ်ခွန်အားဖြည့် စာတိုများ Table
    cursor.execute("""
        CREATE TABLE daily_quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote TEXT NOT NULL
        )
    """)

    # Resources Data
    resources = [
        ("စိတ်ဖိစီးမှု လျှော့ချနည်းနှင့် သတိထားခြင်း တရားတော်", "video", "stress", "https://www.youtube.com/watch?v=sample1"),
        ("ဒေါသကို သတိဖြင့် အနိုင်ယူခြင်း", "video", "anger", "https://www.youtube.com/watch?v=sample2"),
        ("ဝမ်းနည်းကြေကွဲမှုကို ကုစားခြင်း", "video", "sadness", "https://www.youtube.com/watch?v=sample3"),
        ("လက်ရှိပစ္စုပ္ပန်တည့်တည့်မှာ နေထိုင်နည်း", "video", "mindfulness", "https://www.youtube.com/watch?v=sample4"),
        ("သောကကင်းဝေး စိတ်အေးချမ်းရေး စာအုပ်", "book", "stress", "books/stress_relief.pdf"),
        ("ဒေါသစိတ်ကို ငြိမ်းအေးစေမည့် လမ်းစဉ်", "book", "anger", "books/anger_management.pdf"),
        ("စိတ်ငြိမ်းချမ်းရေးနှင့် သတိပဋ္ဌာန် လက်စွဲ", "book", "mindfulness", "books/mindfulness_guide.pdf"),
    ]
    cursor.executemany("INSERT INTO dhamma_resources (title, type, category, source) VALUES (?, ?, ?, ?)", resources)

    # Daily Dhamma Quotes Data (ဆရာကြီးဒေါက်တာစိုးလွင်၏ သတိပေးစာတိုများ)
    daily_quotes = [
        ("🌸 'စိတ်ဆိုတာ မွေးမြူထားတဲ့ မျောက်တစ်ကောင်လိုပဲ။ ဟိုပြေးဒီလွှား မငြိမ်မသက် ဖြစ်တတ်တယ်။ အတင်းမထိန်းချုပ်ပါနဲ့၊ ဖြစ်နေတာလေးကို သတိနဲ့ အသိအမှတ်ပြုပေးရုံပါပဲ။' - ဆရာကြီးဒေါက်တာစိုးလွင်",),
        ("🌿 'လောကမှာ ဖြစ်ပျက်သမျှဟာ ကိုယ့်စိတ်ကြိုက်ချည်း ဖြစ်မလာနိုင်ပါဘူး။ လောကဓံကို လက်ခံတတ်ဖို့ ပစ္စုပ္ပန်တည့်တည့်မှာ နေတတ်ရမယ်။' - ဆရာကြီးဒေါက်တာစိုးလွင်",),
        ("☕ 'ဒီနေ့ အလုပ်တွေ မစတင်ခင် အသက်ကို ဖြည်းဖြည်းလေး ရှူသွင်း ရှူထုတ်ပြီး ခန္ဓာကိုယ်နဲ့ စိတ်ရဲ့ ငြိမ်သက်မှုကို ၁ မိနစ်လောက် ခံစားကြည့်ပါ။' - သတိပဋ္ဌာန် အလေ့အကျင့်",),
        ("✨ 'ဒေါသဖြစ်တဲ့အခါ ဒေါသကို ရန်မလုပ်ပါနဲ့၊ ဒေါသထွက်နေတဲ့ ကိုယ့်စိတ်ကို သတိနဲ့ ပြန်စောင့်ကြည့်လိုက်ပါ၊ အလိုလို အားလျော့သွားပါလိမ့်မယ်။' - ဆရာကြီးဒေါက်တာစိုးလွင်",),
        ("🍃 'အတိတ်က အမှားတွေအတွက် နောင်တမရပါနဲ့၊ အနာဂတ်အတွက် မစိုးရိမ်ပါနဲ့။ အခု ရောက်နေတဲ့ ဒီစက္ကန့်လေးမှာပဲ အပြည့်အဝ နေထိုင်ပါ။' - ဆရာကြီးဒေါက်တာစိုးလွင်",)
    ]
    cursor.executemany("INSERT INTO daily_quotes (quote) VALUES (?)", daily_quotes)

    conn.commit()
    conn.close()
    print("✅ Database အသစ်နှင့် အချက်အလက်များ အောင်မြင်စွာ ပြင်ဆင်ပြီးပါပြီ။")

if __name__ == "__main__":
    init_and_seed_db()