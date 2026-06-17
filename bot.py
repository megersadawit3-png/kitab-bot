import logging
import sqlite3
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
    CallbackQueryHandler
)
from config import BOT_TOKEN, DB_NAME, ADMIN_ID
import database

# የሎግ ማስተካከያ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# =====================================================================
# 🔄 የውይይት መቆጣጠሪያ ደረጃዎች (CONVERSATION STATES)
# =====================================================================
AWAITING_BIO, AWAITING_PHONE = range(2)
AWAITING_TITLE, AWAITING_CATEGORY, AWAITING_DESC, AWAITING_PRICE, AWAITING_FILE = range(10, 15)
AWAITING_SEARCH_QUERY = range(20, 21)

# --- ⚙️ የቴሌብር ማኑዋል አካውንት ማዋቀሪያ (የተቀየረ) ---
TELEBIRR_ACCOUNT_NUM = "0947843445"
TELEBIRR_ACCOUNT_NAME = "Dawit Megersa"

# =====================================================================
# ⌨️ የሁሉም ቋንቋዎች ኪቦርዶች (KEYBOARDS)
# =====================================================================
lang_keyboard = [["🇪🇹 አማርኛ", "🌳 Afaan Oromoo", "🇬🇧 English"]]

am_main_keyboard = [
    ["📚 መጻሕፍት", "📄 ማጠቃለያዎች/Handouts"],
    ["📝 የጥያቄ ባንክ", "📁 ማስታወሻዎች"],
    ["🔍 ፈልግ (Search)", "📁 የእኔ ላይብረሪ"],
    ["✍️ ደራሲ መሆን እፈልጋለሁ", "➕ አዲስ መጽሐፍ አክል", "☎️ እርዳታ"]
]
am_cat_keyboard = [
    ["📖 ስነ-ጽሁፍ (Literature)", "🎓 ትምህርት (Education)"],
    ["📖 ሃይማኖት (Religion)", "📜 ታሪክ (History)"],
    ["💼 ንግድ (Business)", "💻 ቴክኖሎጂ (Technology)"],
    ["📄 ማጠቃለያዎች (Handouts)", "📁 ማስታወሻዎች (Notes)"],
    ["📝 የጥያቄ ባንክ (Question Bank)", "⬅️ ወደ ዋናው ማውጫ"]
]

or_main_keyboard = [
    ["📚 Kitaabota", "📄 Qorannooslee/Handouts"],
    ["📝 Baankii Gaaffii", "📁 Hubannoo/Notes"],
    ["🔍 Barbaadi (Search)", "📁 Kuusaa Koo"],
    ["✍️ Barreessaa Ta'uu", "➕ Kitaaba Haaraa Gali", "☎️ Gargaarsa"]
]
or_cat_keyboard = [
    ["📖 Og-barruu (Literature)", "🎓 Barnoota (Education)"],
    ["📖 Amantiikaa (Religion)", "📜 Seenaa (History)"],
    ["💼 Daldala (Business)", "💻 Teeknoolojii (Technology)"],
    ["📄 Qorannooslee (Handouts)", "📁 Hubannoo (Notes)"],
    ["📝 Baankii Gaaffii (Question Bank)", "⬅️ Gara Menuu Gurguddaatti"]
]

en_main_keyboard = [
    ["📚 Books", "📄 Handouts"],
    ["📝 Question Bank", "📁 Notes"],
    ["🔍 Search", "📁 My Library"],
    ["✍️ Become an Author", "➕ Add New Book", "☎️ Help"]
]
en_cat_keyboard = [
    ["📖 Literature", "🎓 Education"],
    ["📖 Religion", "📜 History"],
    ["💼 Business", "💻 Technology"],
    ["📄 Handouts", "📁 Notes"],
    ["📝 Question Bank", "⬅️ Back to Main Menu"]
]

# =====================================================================
# 🗄️ የውስጥ ዳታቤዝ ረዳት ፋንክሽኖች (DATABASE WRAPPERS)
# =====================================================================
def get_user_lang(telegram_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT language FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if (row and row[0]) else "am"

def set_user_lang(telegram_id, lang):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET language = ? WHERE telegram_id = ?", (lang, telegram_id))
    conn.commit()
    conn.close()

def save_user_info(telegram_id, username, first_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (telegram_id, username, first_name) 
        VALUES (?, ?, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET username=EXCLUDED.username, first_name=EXCLUDED.first_name
    """, (telegram_id, username, first_name))
    conn.commit()
    conn.close()

def is_user_author(telegram_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM authors WHERE user_id = ? AND status = 'approved'", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def get_contents_by_category(category):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contents WHERE category = ? AND status = 'approved'", (category,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_content_by_id(content_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contents WHERE id = ?", (content_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def execute_search_query(query_text):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM contents WHERE (title LIKE ? OR description LIKE ?) AND status = 'approved'", 
        (f"%{query_text}%", f"%{query_text}%")
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_user_library(telegram_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.* FROM contents c
        JOIN orders o ON c.id = o.content_id
        WHERE o.user_id = ? AND o.status = 'approved'
    """, (telegram_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_order(user_id, content_id, amount, payment_ref, status="pending"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orders (user_id, content_id, amount, payment_reference, status)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, content_id, amount, payment_ref, status))
    conn.commit()
    conn.close()


# =====================================================================
# 🚀 የጥሪ መጀመሪያ (START COMMAND)
# =====================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user_info(user.id, user.username, user.first_name)
    
    msg = (
        "📚 Welcome to Kitab\n\nPlease select your language:\n\n"
        "እንኳን ወደ ኪታብ በደህና መጡ! እባክዎ ቋንቋ ይምረጡ፦\n\n"
        "Baga Gara Kitab Dhuftan! Maaloo afaan keessan filadha:-"
    )
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(lang_keyboard, resize_keyboard=True))


# =====================================================================
# 👑 የአድሚን መቆጣጠሪያ ክፍል (ADMIN PANEL FUNCTIONS)
# =====================================================================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ ይህንን ትዕዛዝ ለመጠቀም ፈቃድ የለዎትም!")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM contents WHERE status = 'pending'")
    pending_books = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM authors WHERE status = 'pending'")
    pending_authors = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
    pending_orders = cursor.fetchone()[0]
    conn.close()

    msg = (
        "👑 **የኪታብ ማርኬትፕሌስ አድሚን ፓነል**\n\n"
        f"📝 በግምገማ ላይ ያሉ ይዘቶች/መጻሕፍት፡ **{pending_books}**\n"
        f"✍️ በግምገማ ላይ ያሉ ደራሲያን፡ **{pending_authors}**\n"
        f"💳 ማረጋገጫ የሚጠብቁ የቴሌብር ክፍያዎች፡ **{pending_orders}**\n\n"
        "አዲስ ይዘት፣ የደራሲነት ጥያቄ ወይም የቴሌብር ክፍያ ሲመጣ ቦቱ እዚህ ያቀርብልዎታል።"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def notify_admin_new_author(bot, user_id, username, first_name, bio, phone):
    msg = (
        "🔔 **አዲስ የደራሲነት ማመልከቻ ቀርቧል!**\n\n"
        f"👤 **ስም:** {first_name} (@{username if username else 'የለውም'})\n"
        f"🆔 **ID:** `{user_id}`\n"
        f"📞 **ስልክ:** {phone}\n"
        f"📝 **የህይወት ታሪክ:** {bio}\n"
    )
    keyboard = [
        [
            InlineKeyboardButton("✅ ፍቀድ (Approve)", callback_data=f"approve_auth_{user_id}"),
            InlineKeyboardButton("❌ ከልክል (Reject)", callback_data=f"reject_auth_{user_id}")
        ]
    ]
    await bot.send_message(chat_id=ADMIN_ID, text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def notify_admin_new_book(bot, book_id, title, price, file_path):
    msg = (
        "🔔 **አዲስ ይዘት ለግምገማ ቀርቧል!**\n\n"
        f"📚 **ርዕስ:** {title}\n"
        f"💰 **ዋጋ:** {price} ETB\n\n"
        "ℹ️ *እባክዎ መጀመሪያ ከላይ ያለውን ፋይል አውርደው ከተመለከቱ በኋላ ከታች ካሉት አማራጮች አንዱን ይምረጡ፦*"
    )
    keyboard = [
        [
            InlineKeyboardButton("✅ ፍቀድ (Approve)", callback_data=f"approve_book_{book_id}"),
            InlineKeyboardButton("❌ ከልክል (Reject)", callback_data=f"reject_book_{book_id}")
        ]
    ]
    try:
        if os.path.exists(file_path):
            await bot.send_document(chat_id=ADMIN_ID, document=open(file_path, 'rb'), caption=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await bot.send_message(chat_id=ADMIN_ID, text=f"⚠️ ፋይሉ አልተገኘም ግን ተመዝግቧል፦\nርዕስ፦ {title}", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logging.error(f"Failed to send file review to admin: {e}")


async def notify_admin_pending_payment(bot, user, book, tx_ref):
    msg = (
        "💳 **አዲስ የቴሌብር ማኑዋል ክፍያ ማረጋገጫ ጥያቄ!**\n\n"
        f"👤 **ገዢ:** {user.first_name} (@{user.username if user.username else 'የለውም'})\n"
        f"🆔 **የገዢ Telegram ID:** `{user.id}`\n"
        f"📚 **የይዘት ርዕስ:** {book['title']} (ID: {book['id']})\n"
        f"💰 **መክፈል ያለበት ዋጋ:** {book['price']} ETB\n"
        f"🧾 **የተላከው የግብይት ቁጥር (Tx Ref):** `{tx_ref}`\n\n"
        "⚠️ *እባክዎ በቴሌብር SMS መግቢያዎ ላይ ከላይ ያለው የግብይት መለያ ቁጥር እና ብር በትክክል መግባቱን ያረጋግጡ።*"
    )
    keyboard = [
        [
            InlineKeyboardButton("✅ ክፍያውን አረጋግጥና ፋይሉን ልክለት", callback_data=f"pay_approve_{user.id}_{book['id']}_{tx_ref}"),
            InlineKeyboardButton("❌ ውድቅ አድርግ (ያልገባ ክፍያ)", callback_data=f"pay_reject_{user.id}_{book['id']}")
        ]
    ]
    await bot.send_message(chat_id=ADMIN_ID, text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# =====================================================================
# ✍️ የደራሲያን ምዝገባ ፍሰት (AUTHOR REGISTRATION FLOW)
# =====================================================================
async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM authors WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        status = row[0]
        if status == 'approved':
            msg = "💡 እርስዎ አስቀድመው ደራሲ ሆነው ተመዝግበዋል!" if lang == "am" else ("💡 Isin duraan barreessaa ta'anii galmaaytaniittu!" if lang == "or" else "💡 You are already registered as an author!")
            await update.message.reply_text(msg)
            return ConversationHandler.END
        elif status == 'pending':
            msg = "⏳ ማመልከቻዎ በአድሚን በመገምገም ላይ ነው፤ እባክዎ በትዕግስት ይጠብቁ。" if lang == "am" else ("⏳ Gafannoon keessan adminiin ilaalamaa jira, maaloo eegaa." if lang == "or" else "⏳ Your application is under review by admin, please wait.")
            await update.message.reply_text(msg)
            return ConversationHandler.END

    msg = "👋 ወደ ደራሲያን ምዝገባ እንኳን በደህና መጡ!\n\nእባክዎን አጭር የህይወት ታሪክዎን (Biography) ይጻፉልን፦" if lang == "am" else ("👋 Gara galmee barreessitootaa baga nagaan dhuftan!\n\nMaaloo seenaa keessan gabaabaan (Biography) nuu barreessaa:" if lang == "or" else "👋 Welcome to Author Registration!\n\nPlease write a short biography about yourself:")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return AWAITING_BIO


async def save_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['bio'] = update.message.text
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    if lang == "am":
        phone_btn = [[KeyboardButton("📲 ስልክ ቁጥር አጋራ", request_contact=True)]]
        msg = "በጣም ጥሩ! አሁን ደግሞ ለክፍያ የሚሆን ስልክ ቁጥርዎን ያስገቡ ወይም ያጋሩን፦"
    elif lang == "or":
        phone_btn = [[KeyboardButton("📲 Lakkoofsa Bilbilaa Agarsiisi", request_contact=True)]]
        msg = "Gaarii dhamma! Amma ammoo kaffaltii fi qunnamtiidhaaf lakkoofsa bilbila keessan nuu ergaa:"
    else:
        phone_btn = [[KeyboardButton("📲 Share Phone Number", request_contact=True)]]
        msg = "Great! Now please enter or share your phone number for payments:"
        
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(phone_btn, resize_keyboard=True, one_time_keyboard=True))
    return AWAITING_PHONE


async def save_phone_and_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    lang = get_user_lang(user_id)
    phone = update.message.contact.phone_number if update.message.contact else update.message.text
    bio = context.user_data.get('bio', '')
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET phone = ? WHERE telegram_id = ?", (phone, user_id))
    cursor.execute("INSERT OR IGNORE INTO authors (user_id, status, biography) VALUES (?, 'pending', ?)", (user_id, bio))
    conn.commit()
    conn.close()
    
    await notify_admin_new_author(context.bot, user_id, user.username, user.first_name, bio, phone)
    
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    msg = "🎉 የማመልከቻ ፎርምዎ ለአድሚን ተልኳል! ሲጸድቅ በቦቱ በኩል መልዕክት ይደርስዎታል።" if lang == "am" else ("🎉 Gafannoon keessan adminiif ergameera! Yeroo mirkanaa'u ergaan isiniif deebi'a." if lang == "or" else "🎉 Your application has been sent to admin! You will receive a message once approved.")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return ConversationHandler.END


async def cancel_reg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    msg = "❌ የምዝገባ ሂደት ተሰርዟል።" if lang == "am" else ("❌ Galmeen haqameera." if lang == "or" else "❌ Registration cancelled.")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return ConversationHandler.END


# =====================================================================
# ➕ አዲስ ይዘት ማስገቢያ ፍሰት (CONTENT UPLOAD FLOW)
# =====================================================================
async def start_book_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    if not is_user_author(user_id):
        msg = "❌ ይዘት ለመጫን መጀመሪያ ደራሲ ሆነው መመዝገብ እና መፅደቅ አለብዎት!" if lang == "am" else ("❌ Kitaaba galchuuf jalqaba barreessaa mirkanaa'e ta'uu qabdu!" if lang == "or" else "❌ You must be an approved author first before uploading books!")
        await update.message.reply_text(msg)
        return ConversationHandler.END

    msg = "📝 እባክዎ የይዘቱን ርዕስ (Title) ያስገቡ፦\n(ለማሰረዝ /cancel ይጻፉ)" if lang == "am" else ("📝 Maaloo mata duree kitaabaa galchaa:\n(Haqaaf /cancel barreessi)" if lang == "or" else "📝 Please enter the title of the content:\n(Type /cancel to abort)")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return AWAITING_TITLE


async def save_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['upload_title'] = update.message.text
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    kb = am_cat_keyboard if lang == "am" else (or_cat_keyboard if lang == "or" else en_cat_keyboard)
    msg = "እባክዎ ተስማሚ የይዘት ዘርፍ (Category) ይምረጡ፦" if lang == "am" else ("Maaloo gosa kitaabaa filadha:" if lang == "or" else "Please select the category:")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return AWAITING_CATEGORY


async def save_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    cat_map = {
        "📖 ስነ-ጽሁፍ (Literature)": "Literature", "📖 ስነ-ጽሑፍ (Literature)": "Literature", "📖 Og-barruu (Literature)": "Literature", "📖 Literature": "Literature",
        "🎓 ትምህርት (Education)": "Education", "🎓 Barnoota (Education)": "Education", "🎓 Education": "Education",
        "📖 ሃይማኖት (Religion)": "Religion", "📖 Amantiikaa (Religion)": "Religion", "📖 Religion": "Religion",
        "📜 ታሪክ (History)": "History", "📜 Seenaa (History)": "History", "📜 History": "History",
        "💼 ንግድ (Business)": "Business", "💼 Daldala (Business)": "Business", "💼 Business": "Business",
        "💻 ቴክኖሎጂ (Technology)": "Technology", "💻 Teeknoolojii (Technology)": "Technology", "💻 Technology": "Technology",
        "📄 ማጠቃለያዎች (Handouts)": "Handouts", "📄 Qorannooslee (Handouts)": "Handouts", "📄 Handouts": "Handouts",
        "📁 ማስታወሻዎች (Notes)": "Notes", "📁 Hubannoo (Notes)": "Notes", "📁 Notes": "Notes",
        "📝 የጥያቄ ባንክ (Question Bank)": "QuestionBank", "📝 Baankii Gaaffii (Question Bank)": "QuestionBank", "📝 Question Bank": "QuestionBank"
    }
    context.user_data['upload_cat'] = cat_map.get(text, "Literature")
    
    msg = "📝 ስለ ይዘቱ አጭር መግለጫ (Description) ይጻፉ፦" if lang == "am" else ("Maaloo ibsa kitaabaa gabaabaan barreessaa:" if lang == "or" else "Please write a short description:")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return AWAITING_DESC


async def save_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['upload_desc'] = update.message.text
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    msg = "💰 የመሸጫ ዋጋ በብር (ETB) ያስገቡ (በነፃ ለማቅረብ 0 ያስገቡ)፦" if lang == "am" else ("💰 Gatii kitaabaa birriidhaan galchaa (fkn: 150, Bilisaaf 0):" if lang == "or" else "💰 Enter the price in ETB (Enter 0 for Free):")
    await update.message.reply_text(msg)
    return AWAITING_PRICE


async def save_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    try:
        price = float(text)
        context.user_data['upload_price'] = price
    except ValueError:
        msg = "❌ እባክዎ በትክክል ቁጥር ብቻ ያስገቡ፦" if lang == "am" else ("❌ Maaloo lakkoofsa qofa galchaa:" if lang == "or" else "❌ Please enter a valid number only:")
        await update.message.reply_text(msg)
        return AWAITING_PRICE

    msg = "📄 አሁን የይዘቱን PDF ፋይል ይጫኑ (Upload Document)፦" if lang == "am" else ("📄 Amma faayilii PDF kitaabichaa ergaa:" if lang == "or" else "📄 Now please upload the PDF file:")
    await update.message.reply_text(msg)
    return AWAITING_FILE


async def save_file_and_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    if not update.message.document:
        msg = "❌ እባክዎ ፋይሉን እንደ Document (PDF) አድርገው ይጫኑት፦" if lang == "am" else ("❌ Maaloo faayilii PDF qofa ergaa:" if lang == "or" else "❌ Please upload the file as a Document (PDF):")
        await update.message.reply_text(msg)
        return AWAITING_FILE

    doc = update.message.document
    os.makedirs("files", exist_ok=True)
    file_path = f"files/{doc.file_name}"
    
    telegram_file = await context.bot.get_file(doc.file_id)
    await telegram_file.download_to_drive(file_path)
    
    title = context.user_data.get('upload_title')
    category = context.user_data.get('upload_cat')
    desc = context.user_data.get('upload_desc')
    price = context.user_data.get('upload_price')
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO contents (author_id, title, category, description, price, file_path, status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending')
    """, (user_id, title, category, desc, price, file_path))
    cursor.execute("SELECT last_insert_rowid()")
    inserted_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    
    await notify_admin_new_book(context.bot, inserted_id, title, price, file_path)
    
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    msg = "🎉 ይዘትዎ በተሳካ ሁኔታ ተጭኗል! በአድሚን ተገምግሞ ሲጸድቅ ለተጠቃሚዎች ይበቃል፡፡" if lang == "am" else ("🎉 Kitaabni keessan milkiyn galeera! Erga admin mirkaneesseen booda gabaaf dhiyaata.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return ConversationHandler.END


async def cancel_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    msg = "❌ ይዘት የመጫን ሂደት ተሰርዟል።" if lang == "am" else ("❌ Hojjiin kitaaba galchuu haqameera." if lang == "or" else "❌ Upload process cancelled.")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return ConversationHandler.END


# =====================================================================
# 🔍 የፍለጋ ሥርዓት (SEARCH CONVERSATION)
# =====================================================================
async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    msg = "🔍 ለመፈለግ የፈለጉትን መጽሐፍ ወይም ይዘት ርዕስ (Title) በከፊል ወይም ሙሉ በሙሉ ይጻፉልኝ፦" if lang == "am" else ("🔍 Maaloo jecha qabiyyee barbaaddan barreessaa:" if lang == "or" else "🔍 Please enter the title or keyword you want to search for:")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return AWAITING_SEARCH_QUERY


async def execute_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_text = update.message.text.strip()
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    results = execute_search_query(query_text)
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    
    if not results:
        msg = "❌ ይቅርታ፣ ያቀረቡትን ቃል የሚመስል ምንም አይነት ይዘት አልተገኘም።" if lang == "am" else ("❌ Dardon, waan argamu hin jiru." if lang == "or" else "❌ No matching content found.")
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return ConversationHandler.END

    for item in results:
        await send_content_preview(update, context, item, lang)
        
    msg = "🔍 የፍለጋ ውጤቶች እነዚህ ናቸው።" if lang == "am" else ("🔍 Bu'aan barbaaddanii kanadha." if lang == "or" else "🔍 Search results displayed.")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return ConversationHandler.END


# =====================================================================
# 📁 የእኔ ላይብረሪ (MY LIBRARY SYSTEM)
# =====================================================================
async def view_library(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    my_contents = get_user_library(user_id)

    if not my_contents:
        msg = "📁 የእርስዎ ላይብረሪ ባዶ ነው! እስካሁን የገዙት ይዘት የለም።" if lang == "am" else ("📁 Kuusaan keessan duwwaa dha! Hanga ammaatti waan bitattan hin jiru." if lang == "or" else "📁 Your library is empty! You haven't purchased any items yet.")
        await update.message.reply_text(msg)
        return

    msg = "📁 የገዟቸው መጻሕፍት እና ማጠቃለያዎች ዝርዝር እነሆ፦\nለማውረድ የሚፈልጉትን ፋይል ይጫኑ፦" if lang == "am" else ("📁 Kuusaa qabiyyee keessanii, buufachuuf cuqaasaa፦" if lang == "or" else "📁 Here is your purchased content library. Click to download:")
    keyboard = []
    for item in my_contents:
        keyboard.append([InlineKeyboardButton(f"📥 {item['title']}", callback_data=f"download_{item['id']}")])
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))


# =====================================================================
# 🛠️ የይዘት ማሳያ ቁልፍ አመክንዮ (0 ብር ከሆነ Download ፣ ክፍያ ካለው telebirr)
# =====================================================================
async def send_content_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, book, lang):
    user_id = update.effective_user.id
    
    # 🎁 ዋጋው 0 ከሆነ (ነፃ ከሆነ) በቀጥታ ዳውንሎድ ቁልፍ ያሳያል
    if float(book['price']) == 0:
        if lang == "am":
            caption = f"📌 **ርዕስ:** {book['title']}\n💰 **ዋጋ:** 🎁 ነፃ (Free!)\n📝 **&nbsp;መግለጫ:** {book['description']}\n\nይህ ይዘት በነፃ የሚቀርብ ነው። ያለ ምንም ክፍያ ወዲያውኑ ማውረድ ይችላሉ!"
            btn_text = "📥 አውርድ (Download)"
        elif lang == "or":
            caption = f"📌 **Mata duree:** {book['title']}\n💰 **Gatii:** 🎁 Bilisa (Free!)\n📝 **Ibsa:** {book['description']}\n\nQabiyyee bilisaadha, ammuma buufachuu dandeessu!"
            btn_text = "📥 Buufadhu (Download)"
        else:
            caption = f"📌 **Title:** {book['title']}\n💰 **Price:** 🎁 Free!\n📝 **Description:** {book['description']}\n\nThis content is free. You can download it directly!"
            btn_text = "📥 Download Now"
            
        inline_kb = [[InlineKeyboardButton(btn_text, callback_data=f"free_dl_{book['id']}")]]
    
    # 💳 ክፍያ ካለው በቴሌብር ማኑዋል ክፍያ ቁልፍ ያሳያል
    else:
        if lang == "am":
            caption = f"📌 **ርዕስ:** {book['title']}\n💰 **ዋጋ:** {book['price']} ETB\n📝 **መግለጫ:** {book['description']}"
            btn_text = "💳 በቴሌብር (telebirr) ክፈል"
        elif lang == "or":
            caption = f"📌 **Mata duree:** {book['title']}\n💰 **Gatii:** {book['price']} ETB\n📝 **Ibsa:** {book['description']}"
            btn_text = "💳 telebirr Kaffali"
        else:
            caption = f"📌 **Title:** {book['title']}\n💰 **Price:** {book['price']} ETB\n📝 **Description:** {book['description']}"
            btn_text = "💳 Pay with telebirr"
            
        inline_kb = [[InlineKeyboardButton(btn_text, callback_data=f"buy_{book['id']}")]]
        
    await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(inline_kb), parse_mode="Markdown")


# =====================================================================
# 🔄 አጠቃላይ የመልዕክት ማስተናገጃ (GENERAL MESSAGE HANDLER)
# =====================================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    
    if text == "🇪🇹 አማርኛ":
        set_user_lang(user_id, "am")
        await update.message.reply_text("ወደ ዋናው ማውጫ እንኳን በደህና መጡ!", reply_markup=ReplyKeyboardMarkup(am_main_keyboard, resize_keyboard=True))
        return
    elif text == "🌳 Afaan Oromoo":
        set_user_lang(user_id, "or")
        await update.message.reply_text("Gara menuu gurguddaatti baga nagaan dhuftan!", reply_markup=ReplyKeyboardMarkup(or_main_keyboard, resize_keyboard=True))
        return
    elif text == "🇬🇧 English":
        set_user_lang(user_id, "en")
        await update.message.reply_text("Welcome to the Main Menu!", reply_markup=ReplyKeyboardMarkup(en_main_keyboard, resize_keyboard=True))
        return

    lang = get_user_lang(user_id)

    if text in ["📁 የእኔ ላይብረሪ", "📁 Kuusaa Koo", "📁 My Library"]:
        await view_library(update, context)
        return

    if text in ["📚 መጻሕፍት", "📚 Kitaabota", "📚 Books"]:
        kb = am_cat_keyboard if lang == "am" else (or_cat_keyboard if lang == "or" else en_cat_keyboard)
        msg = "እባክዎ የይዘት ዘርፍ ይምረጡ፦" if lang == "am" else ("Maaloo gosa kitaboota arguu barbaaddan filadha:-" if lang == "or" else "Please select the content category:")
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return
        
    elif text in ["⬅️ ወደ ዋናው ማውጫ", "⬅️ Gara Menuu Gurguddaatti", "⬅️ Back to Main Menu"]:
        kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
        msg = "ወደ ዋናው ማውጫ ተመልሰዋል፦" if lang == "am" else ("Gara menuu gurguddaatti debi'aniittu:-" if lang == "or" else "Returned to Main Menu:")
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return

    # 📌 የምድቦች ማጣሪያ
    db_category = None
    if text in ["📄 ማጠቃለያዎች/Handouts", "📄 Qorannooslee/Handouts", "📄 Handouts", "📄 ማጠቃለያዎች (Handouts)", "📄 Qorannooslee (Handouts)"]:
        db_category = "Handouts"
    elif text in ["📁 ማስታወሻዎች", "📁 Hubannoo/Notes", "📁 Notes", "📁 ማስታወሻዎች (Notes)", "📁 Hubannoo (Notes)"]:
        db_category = "Notes"
    elif text in ["📝 የጥያቄ ባንክ", "📝 Baankii Gaaffii", "📝 Question Bank", "📝 የጥያቄ ባንክ (Question Bank)", "📝 Baankii Gaaffii (Question Bank)"]:
        db_category = "QuestionBank"
    elif "Literature" in text or "ስነ-ጽሁፍ" in text or "ስነ-ጽሑፍ" in text or "Og-barruu" in text:
        db_category = "Literature"
    elif "Education" in text or "ትምህርት" in text or "Barnoota" in text:
        db_category = "Education"
    elif "Religion" in text or "ሃይማኖት" in text or "Amantiikaa" in text:
        db_category = "Religion"
    elif "History" in text or "ታሪክ" in text or "Seenaa" in text:
        db_category = "History"
    elif "Business" in text or "ንግድ" in text or "Daldala" in text:
        db_category = "Business"
    elif "Technology" in text or "ቴክኖሎጂ" in text or "Teeknoolojii" in text:
        db_category = "Technology"

    if db_category:
        books = get_contents_by_category(db_category)
        if not books:
            msg = f"😔 ይቅርታ፣ በዚህ ሰዓት በ'{text}' ዘርፍ የተጫነ ይዘት የለም。" if lang == "am" else (f"😔 Dardon, gosa kanaan '{text}' qabiyyee argamu hin jiru." if lang == "or" else f"😔 Sorry, there are no items available in the '{text}' category right now.")
            await update.message.reply_text(msg)
            return

        for book in books:
            await send_content_preview(update, context, book, lang)
        return

    # 📌 በስም በቀጥታ ሲፈልጉ (Exact matching)
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contents WHERE LOWER(title) = LOWER(?) AND status = 'approved'", (text,))
    book = cursor.fetchone()
    conn.close()

    if book:
        await send_content_preview(update, context, dict(book), lang)
        return


# =====================================================================
# 💳 የክፍያ እና የአድሚን ውሳኔዎች ማስተናገጃ (CALLBACK QUERY HANDLER)
# =====================================================================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = update.effective_user
    user_id = user.id
    lang = get_user_lang(user_id)
    
    # 📌 ነጻ ይዘት ማውረጃ (0 ብር ሲሆን)
    if data.startswith("free_dl_"):
        content_id = data.split("_")[2]
        book = get_content_by_id(content_id)
        if book:
            # በቀጥታ ወደ ተጠቃሚው ላይብረሪ ይጨምራል
            add_order(user_id, book['id'], 0, payment_ref=f"FREE_{user_id}_{book['id']}", status="approved")
            if os.path.exists(book['file_path']):
                msg = "🎁 ይሄው ነጻ ይዘት ስለሆነ በቀጥታ ተልኮልዎታል። ወደ ላይብረሪዎም ተከማችቷል፦" if lang == "am" else "🎁 Qabiyyee bilisaa waan ta'eef isiniif ergameera:-"
                await context.bot.send_message(chat_id=user_id, text=msg)
                await context.bot.send_document(chat_id=user_id, document=open(book['file_path'], 'rb'))
            else:
                await context.bot.send_message(chat_id=user_id, text="❌ ፋይሉ በሰርቨር ላይ አልተገኘም።")

    # 📌 ክፍያ ላላቸው ይዘቶች - የDawit Megersa የቴሌብር ማኑዋል ክፍያ መመሪያ
    elif data.startswith("buy_"):
        book_id = data.split("_")[1]
        book = get_content_by_id(book_id)
        
        if book:
            context.user_data['paying_for_book_id'] = book_id
            
            if lang == "am":
                pay_instruction = (
                    f"🛒 **የክፍያ መመሪያ (telebirr)**\n\n"
                    f"የመረጡት ይዘት፦ **{book['title']}**\n"
                    f"መክፈል ያለብዎት መጠን፦ **{book['price']} ETB**\n\n"
                    f"🔸 **እባክዎ በቴሌብር 'ገንዘብ ላክ' (Send Money) በመጠቀም፦**\n"
                    f"📞 ወደ ስልክ ቁጥር፦ `{TELEBIRR_ACCOUNT_NUM}`\n"
                    f"👤 ስም፦ **{TELEBIRR_ACCOUNT_NAME}**\n"
                    f"ልክ ያድርጉ።\n\n"
                    f"⚠️ **ከከፈሉ በኋላ፦** የቴሌብር SMS መልዕክት ላይ የሚመጣውን **የግብይት መለያ ቁጥር (Transaction ID / Ref)** (ለምሳሌ፡ `A1B2C3D4...`) እባክዎ ቀጥታ እዚህ ቦት ላይ ይጻፉልን። አድሚን ክፍያውን ሲያረጋግጥ ፋይሉ ይላክለታል።"
                )
            else:
                pay_instruction = (
                    f"🛒 **Instruction telebirr**\n\n"
                    f"Content: **{book['title']}**\n"
                    f"Price: **{book['price']} ETB**\n\n"
                    f"🔸 **Send via telebirr Send Money to:**\n"
                    f"📞 Phone: `{TELEBIRR_ACCOUNT_NUM}`\n"
                    f"👤 Name: **{TELEBIRR_ACCOUNT_NAME}**\n\n"
                    f"⚠️ **After payment:** Please reply to this bot with the **Transaction ID / Reference Number** from your telebirr SMS."
                )
            
            await context.bot.send_message(chat_id=user_id, text=pay_instruction, parse_mode="Markdown")
            context.user_data['state'] = 'awaiting_tx'

    # --- ከላይብረሪ ላይ ዳውንሎድ ሲያደርጉ ---
    elif data.startswith("download_"):
        content_id = data.split("_")[1]
        book = get_content_by_id(content_id)
        if book and os.path.exists(book['file_path']):
            await context.bot.send_document(chat_id=user_id, document=open(book['file_path'], 'rb'), caption=f"📥 {book['title']}")

    # --- 👑 አድሚን የቴሌብር ክፍያ ሲያጸድቅ ---
    elif data.startswith("pay_approve_"):
        parts = data.split("_")
        target_user_id = int(parts[2])
        book_id = int(parts[3])
        tx_ref = parts[4]
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET status = 'approved' WHERE user_id = ? AND content_id = ?", (target_user_id, book_id))
        conn.commit()
        conn.close()
        
        await query.edit_message_text(text="✅ የቴሌብር ክፍያው ተረጋግጧል፣ ፋይሉ ለተጠቃሚው ተልኳል!", reply_markup=None)
        
        book = get_content_by_id(book_id)
        target_lang = get_user_lang(target_user_id)
        if book:
            if target_lang == "am": msg = f"✅ የቴሌብር ክፍያዎ ተረጋግጧል! '{book['title']}' ወደ ላይብረሪዎ ተጨምሯል። መጽሐፉ እነሆ፦"
            else: msg = f"✅ telebirr payment verified! '{book['title']}' added to your library. File:"
            
            try:
                await context.bot.send_message(chat_id=target_user_id, text=msg)
                await context.bot.send_document(chat_id=target_user_id, document=open(book['file_path'], 'rb'))
            except Exception as e:
                logging.error(f"Manual payment delivery failed: {e}")

    # --- 👑 አድሚን የቴሌብር ክፍያ ውድቅ ሲያደርግ ---
    elif data.startswith("pay_reject_"):
        parts = data.split("_")
        target_user_id = int(parts[2])
        book_id = int(parts[3])
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET status = 'rejected' WHERE user_id = ? AND content_id = ?", (target_user_id, book_id))
        conn.commit()
        conn.close()
        
        await query.edit_message_text(text="❌ ክፍያው የለም በሚል ውድቅ ተደርጓል።", reply_markup=None)
        target_lang = get_user_lang(target_user_id)
        msg = "❌ ይቅርታ፣ ያቀረቡት የቴሌብር ክፍያ ማረጋገጫ በአድሚን አልተገኘም (ውድቅ ተደርጓል)። እባክዎ በትክክል መላክዎን ያረጋግጡ።" if target_lang == "am" else "❌ telebirr payment verification failed. Rejected by admin."
        try: await context.bot.send_message(chat_id=target_user_id, text=msg)
        except: pass

    # --- 👑 አድሚን መጽሐፍ ሲያጸድቅ ---
    elif data.startswith("approve_book_"):
        book_id = data.split("_")[2]
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE contents SET status = 'approved' WHERE id = ?", (book_id,))
        cursor.execute("SELECT author_id, title FROM contents WHERE id = ?", (book_id,))
        res = cursor.fetchone()
        conn.commit()
        conn.close()
        await query.edit_message_caption(caption="✅ ይዘቱ በተሳካ ሁኔታ ጽድቋል! አሁን ለሁሉም ተጠቃሚዎች ይታያል።", reply_markup=None)
        if res:
            author_id, book_title = res[0], res[1]
            author_lang = get_user_lang(author_id)
            auth_msg = f"🎉 እንኳን ደስ አለዎት! '{book_title}' የተሰኘው ይዘትዎ በአድሚን ተገምግሞ ጽድቋል።" if author_lang == "am" else f"🎉 Congratulations! Your content '{book_title}' has been approved."
            try: await context.bot.send_message(chat_id=author_id, text=auth_msg)
            except: pass

    # --- 👑 አድሚን መጽሐፍ ሲከለክል ---
    elif data.startswith("reject_book_"):
        book_id = data.split("_")[2]
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE contents SET status = 'rejected' WHERE id = ?", (book_id,))
        conn.commit()
        conn.close()
        await query.edit_message_caption(caption="❌ ይዘቱ ውድቅ (Rejected) ተደርጓል።", reply_markup=None)

    # --- 👑 አድሚን ደራሲ ሲያጸድቅ ---
    elif data.startswith("approve_auth_"):
        target_user_id = data.split("_")[2]
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE authors SET status = 'approved' WHERE user_id = ?", (target_user_id,))
        conn.commit()
        conn.close()
        await query.edit_message_text(text="✅ ደራሲው በተሳካ ሁኔታ ጽድቋል!", reply_markup=None)
        author_lang = get_user_lang(target_user_id)
        kb = am_main_keyboard if author_lang == "am" else (or_main_keyboard if author_lang == "or" else en_main_keyboard)
        auth_msg = "🎉 እንኳን ደስ አለዎት! የደራሲነት ማመልከቻዎ በአድሚን ጽድቋል። አሁን ይዘቶችን ማከል ይችላሉ!" if author_lang == "am" else "🎉 Congratulations! Your author application has been approved."
        try: await context.bot.send_message(chat_id=target_user_id, text=auth_msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        except: pass

    # --- 👑 አድሚን ደራሲ ሲከለክል ---
    elif data.startswith("reject_auth_"):
        target_user_id = data.split("_")[2]
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE authors SET status = 'rejected' WHERE user_id = ?", (target_user_id,))
        conn.commit()
        conn.close()
        await query.edit_message_text(text="❌ የደራሲነት ጥያቄው ውድቅ ተደርጓል።", reply_markup=None)


# =====================================================================
# ⚡ የቴሌብር ማኑዋል ክፍያ ቴክስት መልዕክት መቀበያ (TEXT INTERCEPTOR)
# =====================================================================
async def handle_text_payment_ref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    if context.user_data.get('state') == 'awaiting_tx':
        tx_ref = update.message.text.strip()
        
        # ተጠቃሚው በስህተት ሌላ ትዕዛዝ ከጻፈ ፍሰቱን እንዳያበላሽ መከላከያ
        if tx_ref.startswith('/'):
            return False
            
        book_id = context.user_data.get('paying_for_book_id')
        book = get_content_by_id(book_id)
        
        if book:
            add_order(user_id, book['id'], book['price'], payment_ref=tx_ref, status="pending")
            await notify_admin_pending_payment(context.bot, update.effective_user, book, tx_ref)
            
            context.user_data['state'] = None
            context.user_data['paying_for_book_id'] = None
            
            kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
            msg = "⏳ እናመሰግናለን! የግብይት ቁጥርዎ ለአድሚን ተልኳል። ክፍያው ሲረጋገጥ (ባጭር ደቂቃ ውስጥ) ፋይሉ ይላክለታል።" if lang == "am" else "⏳ Thank you! Your Transaction ID has been sent to admin for verification."
            await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
            return True
    return False


# =====================================================================
# 🏁 ዋናው የማስነሻ ክፍል (MAIN FUNCTION)
# =====================================================================
def main():
    database.init_db()  # የዳታቤዝ ቴብሎችን መጀመሪያ ማረጋገጫ
    app = Application.builder().token(BOT_TOKEN).build()
    
    search_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^(🔍 ፈልግ \(Search\)|🔍 Barbaadi \(Search\)|🔍 Search)$"), start_search)],
        states={AWAITING_SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, execute_search)]},
        fallbacks=[]
    )

    reg_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^(✍️ ደራሲ መሆን እፈልጋለሁ|✍️ Barreessaa Ta'uu|✍️ Become an Author)$"), start_registration)],
        states={
            AWAITING_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_bio)],
            AWAITING_PHONE: [MessageHandler(filters.TEXT | filters.CONTACT, save_phone_and_finish)]
        },
        fallbacks=[CommandHandler("cancel", cancel_reg)]
    )
    
    upload_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^(➕ አዲስ መጽሐፍ አክል|➕ Kitaaba Haaraa Gali|➕ Add New Book)$"), start_book_upload)],
        states={
            AWAITING_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_title)],
            AWAITING_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_category)],
            AWAITING_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_desc)],
            AWAITING_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_price)],
            AWAITING_FILE: [MessageHandler(filters.Document.ALL, save_file_and_finish)]
        },
        fallbacks=[CommandHandler("cancel", cancel_upload)]
    )
    
    # 📌 ጽሑፎችን ለመያዝ ቀድመን የክፍያ መለያ መሆኑን የምናይበት ራውተር
    async def global_message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_payment = await handle_text_payment_ref(update, context)
        if not is_payment:
            await handle_message(update, context)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(search_handler)
    app.add_handler(reg_handler)
    app.add_handler(upload_handler)
    app.add_handler(CallbackQueryHandler(handle_callback)) 
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, global_message_router))
    
    print("Kitab Bot (Free Logic + telebirr Manual) በተሳካ ሁኔታ ተነስቷል...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
