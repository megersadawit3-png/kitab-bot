import logging
import sqlite3
import os
import aiofiles
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

# የሎግ ማስተካከያ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# =====================================================================
# 🔄 የውይይት መቆጣጠሪያ ደረጃዎች (CONVERSATION STATES)
# =====================================================================
AWAITING_BIO, AWAITING_PHONE = range(2)
AWAITING_TITLE, AWAITING_CATEGORY, AWAITING_DESC, AWAITING_PRICE, AWAITING_FILE = range(10, 15)
AWAITING_SEARCH_QUERY = range(20, 21)
AWAITING_TELEBIRR_REF = range(30, 31)

# =====================================================================
# ⌨️ የሁሉም ቋንቋዎች ኪቦርዶች (KEYBOARDS)
# =====================================================================
lang_keyboard = [["🇪🇹 አማርኛ", "🌳 Afaan Oromoo", "🇬🇧 English"]]

am_main_keyboard = [
    ["📚 መጻሕፍት", "📄 ማጠቃለያዎች/Handouts"],
    ["📝 የጥያቄ ባንክ", "📁 ማስታወሻዎች"],
    ["🔍 ፈልግ (Search)", "📁 የእኔ ላይብረሪ"],
    ["✍️ ደራሲ መሆን እፈልጋለሁ", "➕ አዲስ ይዘት አክል", "☎️ እርዳታ"]
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
# 🗄️ የውስጥ ዳታቤዝ ረዳት ፋንክሽኖች (INLINE DATABASE FUNCTIONS)
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
        INSERT INTO orders (user_id, content_id, amount, payment_ref, status)
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
    pending_payments = cursor.fetchone()[0]
    conn.close()

    msg = (
        "👑 **የኪታብ ማርኬትፕሌስ አድሚን ፓነል**\n\n"
        f"📝 በግምገማ ላይ ያሉ ይዘቶች፦ **{pending_books}**\n"
        f"✍️ በግምገማ ላይ ያሉ ደራሲያን፦ **{pending_authors}**\n"
        f"💳 ማረጋገጫ የሚጠብቁ ክፍያዎች፦ **{pending_payments}**\n\n"
        "አዳዲስ ማመልከቻዎች ወይም ክፍያዎች ሲመጡ ቦቱ በቀጥታ እዚህ ያቀርብልዎታል።"
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
            async with aiofiles.open(file_path, 'rb') as f:
                file_data = await f.read()
            await bot.send_document(
                chat_id=ADMIN_ID,
                document=file_data,
                filename=os.path.basename(file_path),
                caption=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        else:
            await bot.send_message(
                chat_id=ADMIN_ID, 
                text=f"⚠️ ፋይሉ በሲስተም ላይ አልተገኘም ግን ይዘቱ ተመዝግቧል፦\nርዕስ፦ {title}", 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception as e:
        logging.error(f"Failed to send file review to admin: {e}")

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
    msg = "ምዝገባው ተቋርጧል።" if lang == "am" else ("Galmeen addaan citeera." if lang == "or" else "Registration canceled.")
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

    msg = "📝 እባክዎ የይዘቱን ርዕስ (Title) ያስገቡ፦" if lang == "am" else ("📝 Maaloo mata duree kitaabaa galchaa:" if lang == "or" else "📝 Please enter the title of the content:")
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
        "📖 ስነ-ጽሁф (Literature)": "Literature", "📖 ስነ-ጽሑፍ (Literature)": "Literature", "📖 Og-barruu (Literature)": "Literature", "📖 Literature": "Literature",
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
    msg = "💰 የመሸጫ ዋጋ በብር (ETB) ያስገቡ (በነፃ ለማቅረብ 0 ያስገቡ)፦" if lang == "am" else ("💰 Gatii kitaabaa birriidhaan galchaa (fkn: 150):" if lang == "or" else "💰 Enter the price in ETB (Enter 0 for Free):")
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
    msg = "🎉 ይዘትዎ በተሳካ ሁኔታ ተጭኗል! በአድሚን ተገምግሞ ሲጸድቅ ለተጠቃሚዎች ይበቃል፡፡" if lang == "am" else ("🎉 Kitaabni keessan milkiyn galeera! Erga admin mirkaneesseen booda gabaaf dhiyaata." if lang == "or" else "🎉 Content uploaded successfully! It will be available after admin approval.")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return ConversationHandler.END

async def cancel_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    msg = "የይዘት ጭነቱ ተቋርጧል።" if lang == "am" else ("Galmeen kitaabaa addaan citeera." if lang == "or" else "Upload canceled.")
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
        caption = f"📌 **ርዕስ:** {item['title']}\n💰 **ዋጋ:** {item['price']} ETB\n📝 **መግለጫ:** {item['description']}"
        btn_text = "📥 በነፃ አውርድ" if item['price'] <= 0 else "💳 በ Chapa / Telebirr ክፈል"
        inline_kb = [[InlineKeyboardButton(btn_text, callback_data=f"buy_{item['id']}")]]
        await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(inline_kb), parse_mode="Markdown")
        
    await update.message.reply_text("🔍 የፍለጋ ውጤቶች እነዚህ ናቸው።", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return ConversationHandler.END

# =====================================================================
# 💳 የቴሌብር ማኑዋል ክፍያ ፍሰት (TELEBIRR MANUAL FLOW)
# =====================================================================
async def process_telebirr_ref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ref_text = update.message.text.strip()
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    book_id = context.user_data.get('buying_book_id')
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    
    book = get_content_by_id(book_id)
    if not book:
        await update.message.reply_text("❌ ስህተት ተከስቷል። እባክዎ እንደገና ይሞክሩ።", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return ConversationHandler.END

    add_order(user_id, book['id'], book['price'], payment_ref=ref_text, status="pending")
    
    admin_msg = (
        "💳 **አዲስ የቴሌብር ማኑዋል ክፍያ ማረጋገጫ ጥያቄ!**\n\n"
        f"👤 **ተጠቃሚ ID:** `{user_id}`\n"
        f"📚 **የይዘት ርዕስ:** {book['title']}\n"
        f"💰 **የተከፈለው መጠን:** {book['price']} ETB\n"
        f"🆔 **የግብይት መለያ (Transaction ID/Ref):** `{ref_text}`\n"
    )
    admin_kb = [
        [
            InlineKeyboardButton("✅ ክፍያ አጽድቅ (Approve)", callback_data=f"pay_app_{user_id}_{book['id']}"),
            InlineKeyboardButton("❌ ውድቅ አድርግ (Reject)", callback_data=f"pay_rej_{user_id}_{book['id']}")
        ]
    ]
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, reply_markup=InlineKeyboardMarkup(admin_kb), parse_mode="Markdown")

    reply_msg = "🙏 ማረጋገጫዎ ለአድሚን ተልኳል! ክፍያዎ ተረጋግጦ ሲጸድቅ ፋይሉ በቅጽበት ይላክልዎታል።" if lang == "am" else "🎉 Kaffaltiin keessan adminiif ergameera! Erga mirkanaa'uun booda faayiliin isiniif ergama."
    await update.message.reply_text(reply_msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
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
            caption = f"📌 **ርዕስ:** {book['title']}\n💰 **ዋጋ:** {book['price']} ETB\n📝 **መግለጫ:** {book['description']}"
            btn_text = "📥 በነፃ አውርድ" if book['price'] <= 0 else "💳 በ Chapa / Telebirr ክፈል"
            inline_kb = [[InlineKeyboardButton(btn_text, callback_data=f"buy_{book['id']}")]]
            await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(inline_kb), parse_mode="Markdown")
        return

# =====================================================================
# 💳 የክፍያ እና የአድሚን ውሳኔዎች ማስተናገጃ (CALLBACK QUERY HANDLER)
# =====================================================================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    if data.startswith("buy_"):
        row_id = data.split("_")[1]
        book = get_content_by_id(row_id)
        
        if book:
            # 📌 የ0 ብር (ነፃ) ከሆነ ፋይሉን በቀጥታ ይላክ
            if book['price'] <= 0:
                add_order(user_id, book['id'], 0, payment_ref="FREE_DOWNLOAD", status="approved")
                if os.path.exists(book['file_path']):
                    async with aiofiles.open(book['file_path'], 'rb') as f:
                        file_data = await f.read()
                    await context.bot.send_document(chat_id=user_id, document=file_data, filename=os.path.basename(book['file_path']), caption=f"📥 {book['title']}")
                return

            # 📌 የሚከፈልበት ከሆነ የቴሌብር መረጃ መስጠት
            pay_msg = (
                f"💳 **የክፍያ መመሪያ ({book['title']})**\n\n"
                f"እባክዎ **{book['price']} ETB** ወደሚከተለው የቴሌብር (telebirr) ሂሳብ ያስገቡ፦\n\n"
                f"📱 **የስልክ ቁጥር:** `0947843445`\n"
                f"👤 **የአካውንት ስም:** `Dawit Megersa`\n\n"
                f"ክፍያውን ከፈጸሙ በኋላ የደረሰኝ ቁጥሩን (Transaction ID/Ref) ለመላክ ከታች ያለውን አዝራር ይጫኑ፦"
            )
            inline_kb = [[InlineKeyboardButton("📩 የደረሰኝ ቁጥር (Ref) አስገባ", callback_data=f"submit_ref_{book['id']}")]]
            await context.bot.send_message(chat_id=user_id, text=pay_msg, reply_markup=InlineKeyboardMarkup(inline_kb), parse_mode="Markdown")

    elif data.startswith("submit_ref_"):
        book_id = data.split("_")[2]
        context.user_data['buying_book_id'] = book_id
        await context.bot.send_message(chat_id=user_id, text="📝 እባክዎ የቴሌብር የግብይት መለያ (Transaction Reference ቁጥር) ብቻ ይጻፉልኝ፦")
        # ⚠️ ማስታወሻ፡ ውይይቱን ወደ ConversationHandler ለማስተላለፍ 'telebirr_manual_handler' መስመር ላይ ይገባል።

    elif data.startswith("download_"):
        content_id = data.split("_")[1]
        book = get_content_by_id(content_id)
        if book and os.path.exists(book['file_path']):
            async with aiofiles.open(book['file_path'], 'rb') as f:
                file_data = await f.read()
            await context.bot.send_document(chat_id=user_id, document=file_data, filename=os.path.basename(book['file_path']), caption=f"📥 {book['title']}")

    # --- 👑 አድሚን ክፍያ ሲያጸድቅ (Approve Payment) ---
    elif data.startswith("pay_app_"):
        target_uid = int(data.split("_")[2])
        book_id = int(data.split("_")[3])
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET status = 'approved' WHERE user_id = ? AND content_id = ?", (target_uid, book_id))
        conn.commit()
        conn.close()
        
        await query.edit_message_text(text="✅ ክፍያው ተረጋግጧል፣ ፋይሉ ለተጠቃሚው ተልኳል።")
        
        book = get_content_by_id(book_id)
        if book and os.path.exists(book['file_path']):
            await context.bot.send_message(chat_id=target_uid, text="✅ ክፍያዎ በአድሚን ተረጋግጧል! የገዙት ፋይል እነሆ፦")
            async with aiofiles.open(book['file_path'], 'rb') as f:
                file_data = await f.read()
            await context.bot.send_document(chat_id=target_uid, document=file_data, filename=os.path.basename(book['file_path']))

    # --- 👑 አድሚን ክፍያ ውድቅ ሲያደርግ (Reject Payment) ---
    elif data.startswith("pay_rej_"):
        target_uid = int(data.split("_")[2])
        await query.edit_message_text(text="❌ ክፍያው ውድቅ ተደርጓል።")
        await context.bot.send_message(chat_id=target_uid, text="❌ ይቅርታ፣ ያስገቡት የክፍያ ማረጋገጫ በአድሚን ዘንድ ተቀባይነት አላገኘም። እባክዎ በትክክል መክፈልዎን ያረጋግጡ።")

    # --- 👑 አድሚን መጽሐፍ ሲያጸድቅ (Approve Content) ---
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
            author_id = res[0]
            author_lang = get_user_lang(author_id)
            auth_msg = f"🎉 እንኳን ደስ አለዎት! '{res[1]}' የተሰኘው ይዘትዎ በአድሚን ተገምግሞ ጽድቋል።" if author_lang == "am" else f"🎉 Congratulations! Your content '{res[1]}' has been approved."
            try: await context.bot.send_message(chat_id=author_id, text=auth_msg)
            except: pass

    # --- 👑 አድሚን መጽሐፍ ሲከለክል (Reject Content) ---
    elif data.startswith("reject_book_"):
        book_id = data.split("_")[2]
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE contents SET status = 'rejected' WHERE id = ?", (book_id,))
        cursor.execute("SELECT author_id, title FROM contents WHERE id = ?", (book_id,))
        res = cursor.fetchone()
        conn.commit()
        conn.close()
        
        await query.edit_message_caption(caption="❌ ይዘቱ ውድቅ (Rejected) ተደርጓል።", reply_markup=None)
        if res:
            author_id = res[0]
            author_lang = get_user_lang(author_id)
            auth_msg = f"😔 ይቅርታ፣ '{res[1]}' የተሰኘው ይዘትዎ በሕግና ደንብ ምክንያት በአድሚን ውድቅ ተደርጓል።" if author_lang == "am" else f"😔 Sorry, your content '{res[1]}' has been rejected."
            try: await context.bot.send_message(chat_id=author_id, text=auth_msg)
            except: pass

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
# 🏁 ዋናው የማስነሻ ክፍል (MAIN FUNCTION)
# =====================================================================
def main():
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
        entry_points=[MessageHandler(filters.Regex("^(➕ አዲስ ይዘት አክል|➕ Kitaaba Haaraa Gali|➕ Add New Book)$"), start_book_upload)],
        states={
            AWAITING_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_title)],
            AWAITING_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_category)],
            AWAITING_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_desc)],
            AWAITING_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_price)],
            AWAITING_FILE: [MessageHandler(filters.Document.ALL, save_file_and_finish)]
        },
        fallbacks=[CommandHandler("cancel", cancel_upload)]
    )

    telebirr_manual_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_callback, pattern="^submit_ref_")],
        states={AWAITING_TELEBIRR_REF: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_telebirr_ref)]},
        fallbacks=[]
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(search_handler)
    app.add_handler(reg_handler)
    app.add_handler(upload_handler)
    app.add_handler(telebirr_manual_handler)
    app.add_handler(CallbackQueryHandler(handle_callback)) 
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Kitab Bot (የተስተካከለ እና የተሟላ) በተሳካ ሁኔታ ተነስቷል...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
