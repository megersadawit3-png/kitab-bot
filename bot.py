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

or_main_keyboard = [
    ["📚 Kitaabota", "📄 Guduunfaalee/Handouts"],
    ["📝 Baanki Gaaffilee", "📁 Yaadannoolee"],
    ["🔍 Barbaadi (Search)", "📁 Mana Kitaaba koo"],
    ["✍️ Barreessaa Ta'uun Barbaada", "➕ Kitaaba Haaraa Gali", "☎️ Gargaarsa"]
]

en_main_keyboard = [
    ["📚 Books", "📄 Summaries/Handouts"],
    ["📝 Question Bank", "📁 Notes"],
    ["🔍 Search", "📁 My Library"],
    ["✍️ Become an Author", "➕ Add New Book", "☎️ Help"]
]

am_cat_keyboard = [
    ["📖 ስነ-ጽሁፍ (Literature)", "🧠 ፍልስፍና (Philosophy)"],
    ["📐 አርክቴክቸር (Architecture)", "💻 ቴክኖሎጂ (Technology)"],
    ["⬅️ ወደ ዋናው ማውጫ"]
]

or_cat_keyboard = [
    ["📖 Og-barruu (Literature)", "🧠 Fiilosofii (Philosophy)"],
    ["📐 Arkiteक्चर (Architecture)", "💻 Teeknoolojii (Technology)"],
    ["⬅️ Gara Menuu Gurguddaatti"]
]

en_cat_keyboard = [
    ["📖 Literature", "🧠 Philosophy"],
    ["📐 Architecture", "💻 Technology"],
    ["⬅️ Back to Main Menu"]
]

# =====================================================================
# 🗄 የዳታቤዝ ረዳት ተግባራት (DATABASE FUNCTIONS)
# =====================================================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            lang TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS authors (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            bio TEXT,
            phone TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_id INTEGER,
            title TEXT,
            category TEXT,
            description TEXT,
            price REAL,
            file_path TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content_id INTEGER,
            tx_ref TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')
    conn.commit()
    conn.close()

def save_user_info(user_id, username):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()

def set_user_lang(user_id, lang):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
    conn.commit()
    conn.close()

def get_user_lang(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else None

def is_user_author(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM authors WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row and row[0] == 'approved'

def add_author_request(user_id, username, bio, phone):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO authors (user_id, username, bio, phone, status) VALUES (?, ?, ?, ?, 'pending')", 
                   (user_id, username, bio, phone))
    conn.commit()
    conn.close()

def add_content_request(author_id, title, category, description, price, file_path):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO contents (author_id, title, category, description, price, file_path, status) VALUES (?, ?, ?, ?, ?, ?, 'pending')", 
                   (author_id, title, category, description, price, file_path))
    content_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return content_id

def get_contents_by_category(category):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description, price FROM contents WHERE category = ? AND status = 'approved'", (category,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_content_by_id(content_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, author_id, title, description, price, file_path FROM contents WHERE id = ?", (content_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {'id': row[0], 'author_id': row[1], 'title': row[2], 'description': row[3], 'price': row[4], 'file_path': row[5]}
    return None

def search_contents(query_text):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, price FROM contents WHERE (title LIKE ? OR description LIKE ?) AND status = 'approved'", 
                   (f'%{query_text}%', f'%{query_text}%'))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_pending_books_count():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM contents WHERE status = 'pending'")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_pending_authors_count():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM authors WHERE status = 'pending'")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def add_order(user_id, content_id, tx_ref):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (user_id, content_id, tx_ref, status) VALUES (?, ?, ?, 'pending')", (user_id, content_id, tx_ref))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id

def approve_order_in_db(order_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = 'approved' WHERE id = ?", (order_id,))
    cursor.execute("SELECT user_id, content_id FROM orders WHERE id = ?", (order_id,))
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    return row

def get_user_library(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.id, c.title FROM contents c
        JOIN orders o ON c.id = o.content_id
        WHERE o.user_id = ? AND o.status = 'approved'
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows

def has_user_purchased(user_id, content_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM orders WHERE user_id = ? AND content_id = ? AND status = 'approved'", (user_id, content_id))
    row = cursor.fetchone()
    conn.close()
    return row is not None

# =====================================================================
# 🤖 የቦቱ ዋና ተግባራት (BOT LOGIC)
# =====================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    save_user_info(user.id, user.username)
    await update.message.reply_text(
        "እንኳን ወደ ኪታብ ዲጂታል መደብር በደህና መጡ! እባክዎ ቋንቋ ይምረጡ።\n\n"
        "Baga Gara Gabaa Diijitaalaa Kitaabitti Gaariin Dhuftan! Maaloo Qooqaan Filadhu.\n\n"
        "Welcome to Kitab Digital Marketplace! Please choose a language.",
        reply_markup=ReplyKeyboardMarkup(lang_keyboard, resize_keyboard=True)
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔️ ይህንን ትዕዛዝ ለመጠቀም ፈቃድ የለዎትም።")
        return
    
    p_books = get_pending_books_count()
    p_auths = get_pending_authors_count()
    
    await update.message.reply_text(
        f"⚙️ **የአድሚን መቆጣጠሪያ ፓነል**\n\n"
        f"⏳ በግምገማ ላይ ያሉ ይዘቶች፡ {p_books}\n"
        f"⏳ ፈቃድ የሚጠብቁ ደራሲያን፡ {p_auths}",
        parse_mode="Markdown"
    )

# --- የደራሲያን ምዝገባ ፍሰት ---
async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_user_lang(update.effective_user.id)
    msg = "እባክዎ አጭር የህይወት ታሪክዎን (Bio) ይጻፉልን፦"
    if lang == "or": msg = "Maaloo Seenaa keessan gabaabaa (Bio) barreessaichaa፦"
    elif lang == "en": msg = "Please write a short biography (Bio) of yourself:"
    
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return AWAITING_BIO

async def save_bio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['author_bio'] = update.message.text
    lang = get_user_lang(update.effective_user.id)
    
    msg = "እባክዎ ከታች ያለውን ቁልፍ ተጭነው ስልክ ቁጥርዎን ያጋሩን፦"
    btn_text = "📱 ስልክ ቁጥር ያጋሩ"
    if lang == "or":
        msg = "Maaloo hantuuta gadii cuqaasuun lakkoofsa bilbilaa keessan nuun jiru፦"
        btn_text = "📱 Bilbila Ergi"
    elif lang == "en":
        msg = "Please share your phone number using the button below:"
        btn_text = "📱 Share Phone Number"
        
    keyboard = [[KeyboardButton(text=btn_text, request_contact=True)]]
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return AWAITING_PHONE

async def save_phone_and_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    lang = get_user_lang(user.id)
    phone = update.message.contact.phone_number if update.message.contact else update.message.text
    bio = context.user_data.get('author_bio')
    
    add_author_request(user.id, user.username, bio, phone)
    
    msg = "✍️ የምዝገባ ማመልከቻዎ ለአድሚን ተልኳል። ሲጸድቅ ማሳወቂያ ይደርስዎታል።"
    main_kb = am_main_keyboard
    if lang == "or":
        msg = "✍️ Gaaffiin keessan Adminiif ergameera. Yeroo mirkanaa'u isiniif ni himama."
        main_kb = or_main_keyboard
    elif lang == "en":
        msg = "✍️ Your registration request has been sent to admin. You will be notified once approved."
        main_kb = en_main_keyboard
        
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(main_kb, resize_keyboard=True))
    
    # ለአድሚን ማሳወቂያ መላክ
    admin_msg = f"👤 **አዲስ የደራሲነት ማመልከቻ**\n\nስም: @{user.username}\nባዮ: {bio}\nስልክ: {phone}"
    admin_buttons = [[
        InlineKeyboardButton("✅ አጽድቅ (Approve)", callback_data=f"approve_auth_{user.id}"),
        InlineKeyboardButton("❌ ውድቅ አድርግ", callback_data=f"reject_auth_{user.id}")
    ]]
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, reply_markup=InlineKeyboardMarkup(admin_buttons), parse_mode="Markdown")
    return ConversationHandler.END

async def cancel_reg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_user_lang(update.effective_user.id)
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    await update.message.reply_text("❌", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return ConversationHandler.END

# --- የይዘት ጭነት ፍሰት ---
async def start_book_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    if not is_user_author(user_id):
        msg = "⛔️ ይዘት ለመጫን መጀመሪያ ደራሲ ሆነው መመዝገብ እና መጽደቅ አለብዎት።"
        if lang == "or": msg = "⛔️ Kitaaba galchuuf jalqaba barreessaa taatanii mirkanaa'uu qabdu."
        elif lang == "en": msg = "⛔️ You must be an approved author to upload content."
        await update.message.reply_text(msg)
        return ConversationHandler.END
        
    msg = "📝 እባክዎ የይዘቱን (የመጽሐፉን) ርዕስ ያስገቡ፦"
    if lang == "or": msg = "Maaloo mata duree kitaabaa galchi፦"
    elif lang == "en": msg = "Please enter the title of the content:"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return AWAITING_TITLE

async def save_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['upload_title'] = update.message.text
    lang = get_user_lang(update.effective_user.id)
    msg = "📂 እባክዎ ከታች ካሉት አማራጮች የይዘቱን ዘርፍ (Category) ይምረጡ፦"
    kb = am_cat_keyboard
    if lang == "or":
        msg = "Maaloo gosa kitaabaa filadhu፦"
        kb = or_cat_keyboard
    elif lang == "en":
        msg = "Please select the category from below:"
        kb = en_cat_keyboard
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return AWAITING_CATEGORY

async def save_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['upload_cat'] = update.message.text
    lang = get_user_lang(update.effective_user.id)
    msg = "✍️ ስለ ይዘቱ አጭር መግለጫ (Description) ይጻፉ፦"
    if lang == "or": msg = "Maaloo ibsa gabaabaa kitaabichaa barreessi፦"
    elif lang == "en": msg = "Please write a short description of the content:"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return AWAITING_DESC

async def save_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['upload_desc'] = update.message.text
    lang = get_user_lang(update.effective_user.id)
    msg = "💰 የይዘቱን ዋጋ በብር ያስገቡ (በነጻ ለማቅረብ 0 ያስገቡ)፦"
    if lang == "or": msg = "Gatiikkaa kitaabaa Qarshiin galchi (Bilaisaaf 0 galchi)፦"
    elif lang == "en": msg = "Enter the price in ETB (Enter 0 for Free):"
    await update.message.reply_text(msg)
    return AWAITING_PRICE

async def save_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        price = float(update.message.text)
        context.user_data['upload_price'] = price
    except ValueError:
        await update.message.reply_text("❌ እባክዎ በትክክል ቁጥር ብቻ ያስገቡ፦")
        return AWAITING_PRICE
        
    lang = get_user_lang(update.effective_user.id)
    msg = "📎 እባክዎ የይዘቱን ፋይል (PDF Document) ያያይዙ፦"
    if lang == "or": msg = "Maaloo faayilii kitaabaa (PDF Document) ergi፦"
    elif lang == "en": msg = "Please upload the content file (PDF Document):"
    await update.message.reply_text(msg)
    return AWAITING_FILE

async def save_file_and_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    doc = update.message.document
    lang = get_user_lang(update.effective_user.id)
    
    if not doc or not doc.file_name.lower().endswith('.pdf'):
        await update.message.reply_text("❌ እባክዎ የ PDF ፋይል ብቻ ያያይዙ፦")
        return AWAITING_FILE
        
    telegram_file = await doc.get_file()
    file_path = f"files/{doc.file_name}"
    await telegram_file.download_to_drive(file_path)
    
    title = context.user_data.get('upload_title')
    category = context.user_data.get('upload_cat')
    desc = context.user_data.get('upload_desc')
    price = context.user_data.get('upload_price')
    author_id = update.effective_user.id
    
    content_id = add_content_request(author_id, title, category, desc, price, file_path)
    
    msg = "✅ ይዘቱ በተሳካ ሁኔታ ተጭኗል። በአድሚን ተገምግሞ ሲፈቀድ በገበያ ላይ ይውላል。"
    kb = am_main_keyboard
    if lang == "or":
        msg = "✅ Kitaabni galmeeffameera. Erga Adminiin ilaalamee mirkanaa'ee gabaa irra oola."
        kb = or_main_keyboard
    elif lang == "en":
        msg = "✅ Content uploaded successfully. It will be live after admin approval."
        kb = en_main_keyboard
        
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    
    # ለአድሚን ለግምገማ መላክ
    admin_msg = f"📚 **አዲስ ይዘት ቀርቧል**\n\nርዕስ: {title}\nዘርፍ: {category}\nዋጋ: {price} ETB\nመግለጫ: {desc}"
    admin_buttons = [[
        InlineKeyboardButton("✅ ፍቀድ (Approve)", callback_data=f"approve_book_{content_id}"),
        InlineKeyboardButton("❌ ውድቅ አድርግ", callback_data=f"reject_book_{content_id}")
    ]]
    await context.bot.send_document(chat_id=ADMIN_ID, document=open(file_path, 'rb'), caption=admin_msg, reply_markup=InlineKeyboardMarkup(admin_buttons), parse_mode="Markdown")
    return ConversationHandler.END

async def cancel_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_user_lang(update.effective_user.id)
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    await update.message.reply_text("❌", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return ConversationHandler.END

# --- የፍለጋ (Search) ፍሰት ---
async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_user_lang(update.effective_user.id)
    msg = "🔍 ለመፈለግ የሚፈልጉትን ቃል (የርዕስ ወይም የደራሲ ስም) ያስገቡ፦"
    if lang == "or": msg = "🔍 Jecha barbaaduu barbaaddan galchi፦"
    elif lang == "en": msg = "🔍 Enter the word you want to search:"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return AWAITING_SEARCH_QUERY

async def execute_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query_text = update.message.text
    lang = get_user_lang(update.effective_user.id)
    results = search_contents(query_text)
    
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    
    if not results:
        msg = "😔 ምንም ዓይነት የተገኘ ይዘት የለም。"
        if lang == "or": msg = "😔 Bu'aan barbaachisaa hin argamne."
        elif lang == "en": msg = "😔 No content found matching your search."
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return ConversationHandler.END
        
    for item in results:
        c_id, title, price = item
        text = f"📚 {title}\n💰 Gatiin: {price} ETB" if lang == "or" else (f"📚 {title}\n💰 Price: {price} ETB" if lang == "en" else f"📚 {title}\n💰 ዋጋ: {price} ETB")
        btn_lbl = "📥 ያውርዱ" if price == 0 else "💳 ግዛ"
        if lang == "or": btn_lbl = "📥 Buusi" if price == 0 else "💳 Bitadhu"
        elif lang == "en": btn_lbl = "📥 Download" if price == 0 else "💳 Buy"
        
        inline_kb = [[InlineKeyboardButton(btn_lbl, callback_data=f"buy_{c_id}")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(inline_kb))
        
    await update.message.reply_text("✨", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return ConversationHandler.END

# --- የቴሌብር ክፍያ ማረጋገጫ (Telebirr Manual Ref) ፍሰት ---
async def process_telebirr_ref(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tx_ref = update.message.text.strip()
    user = update.effective_user
    lang = get_user_lang(user.id)
    content_id = context.user_data.get('pending_buy_id')
    
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    
    if not content_id:
        await update.message.reply_text("❌ Error", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return ConversationHandler.END
        
    book = get_content_by_id(content_id)
    order_id = add_order(user.id, content_id, tx_ref)
    
    msg = "🙏 የግብይት ቁጥርዎ ተመዝግቧል። በአድሚን ተረጋግጦ ይዘቱ ወዲያውኑ ይላክልዎታል።"
    if lang == "or": msg = "🙏 Lakkoofsi herrega keessanii galmeeffameera. Erga mirkanaa'ee booda isiniif ergama."
    elif lang == "en": msg = "🙏 Your transaction reference has been recorded. Content will be sent after verification."
    
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    
    # ለአድሚን ማሳወቂያ መላክ
    admin_msg = f"💳 **አዲስ የክፍያ ማረጋገጫ ቀርቧል**\n\nተጠቃሚ: @{user.username} ({user.id})\nይዘት: {book['title']}\nዋጋ: {book['price']} ETB\nየቴሌብር Ref: `{tx_ref}`"
    admin_buttons = [[
        InlineKeyboardButton("✅ ክፍያውን አጽдቅ", callback_data=f"pay_app_{order_id}"),
        InlineKeyboardButton("❌ ውድቅ አድርግ", callback_data=f"pay_rej_{order_id}")
    ]]
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, reply_markup=InlineKeyboardMarkup(admin_buttons), parse_mode="Markdown")
    return ConversationHandler.END

# --- የካቴጎሪ እና አጠቃላይ መልዕክቶች ማስተናገጃ ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    user_id = update.effective_user.id
    
    if text in lang_keyboard[0]:
        lang = "am" if "አማርኛ" in text else ("or" if "Oromoo" in text else "en")
        set_user_lang(user_id, lang)
        kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
        msg = "ዋና ማውጫ" if lang == "am" else ("Menuu Gurguddaa" if lang == "or" else "Main Menu")
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return

    lang = get_user_lang(user_id)
    
    if text in ["📚 መጻሕፍት", "📚 Kitaabota", "📚 Books"]:
        kb = am_cat_keyboard if lang == "am" else (or_cat_keyboard if lang == "or" else en_cat_keyboard)
        await update.message.reply_text("📂 ዘርፍ ይምረጡ / Filadhu / Select:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return
        
    if text in ["⬅️ ወደ ዋናው ማውጫ", "⬅️ Gara Menuu Gurguddaatti", "⬅️ Back to Main Menu"]:
        kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
        await update.message.reply_text("🏠", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return
        
    if text in ["📁 የእኔ ላይብረሪ", "📁 Mana Kitaaba koo", "📁 My Library"]:
        lib = get_user_library(user_id)
        if not lib:
            msg = "📥 እስካሁን የገዙት ወይም ያወረዱት ይዘት የለም。"
            if lang == "or": msg = "📥 Kitaabni ati bitatte hin jiru."
            elif lang == "en": msg = "📥 You haven't purchased or downloaded any content yet."
            await update.message.reply_text(msg)
            return
        for b_id, title in lib:
            kb_view = [[InlineKeyboardButton("📖 አንብብ/ክፈት", callback_data=f"buy_{b_id}")]]
            await update.message.reply_text(f"📘 {title}", reply_markup=InlineKeyboardMarkup(kb_view))
        return

    # ካቴጎሪ ከተመረጠ መጻሕፍትን ማሳየት
    all_cats = [c for row in am_cat_keyboard + or_cat_keyboard + en_cat_keyboard for c in row]
    if text in all_cats:
        books = get_contents_by_category(text)
        if not books:
            await update.message.reply_text("⚠️ በዚህ ዘርፍ የተገኙ ይዘቶች የሉም። / No content here.")
            return
        for b in books:
            b_id, title, desc, price = b
            cap = f"📚 **{title}**\n\n📝 {desc}\n\n💰 ዋጋ: {price} ETB"
            btn_lbl = "📥 ያውርዱ" if price == 0 else "💳 ግዛ (Buy)"
            inline_kb = [[InlineKeyboardButton(btn_lbl, callback_data=f"buy_{b_id}")]]
            await update.message.reply_text(cap, reply_markup=InlineKeyboardMarkup(inline_kb), parse_mode="Markdown")

# --- የውስጥ ቁልፎች (Inline Click) ማስተናገጃ ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    lang = get_user_lang(user_id)
    
    # የይዘት ግዢ ጥያቄ
    if data.startswith("buy_"):
        content_id = int(data.split("_")[1])
        book = get_content_by_id(content_id)
        
        if book['price'] == 0 or has_user_purchased(user_id, content_id):
            async with aiofiles.open(book['file_path'], 'rb') as f:
                content_bytes = await f.read()
            await context.bot.send_document(chat_id=user_id, document=content_bytes, filename=os.path.basename(book['file_path']))
            return ConversationHandler.END
            
        context.user_data['pending_buy_id'] = content_id
        pay_msg = (
            f"💳 **የክፍያ መመሪያ**\n\n"
            f"እባክዎ {book['price']} ብር በቴሌብር (Telebirr) ቁጥር `0912345678` ላይ ይላኩ።\n"
            f"ክፍያውን እንደፈጸሙ የተቀበሉትን የግብይት ቁጥር (Transaction ID / Ref) ከታች ያለውን ቁልፍ ተጭነው ያስገቡ。"
        )
        btn_txt = "📥 የደረሰኝ ቁጥር አስገባ"
        if lang == "or":
            pay_msg = f"እባክዎ Qarshii {book['price']} lakkoofsa Telebirr `0912345678` irratti ergaa. Erga kaffaltanii booda 'Ref' galchaa."
            btn_txt = "📥 Lakkoofsa Ref Galchi"
        elif lang == "en":
            pay_msg = f"Please send {book['price']} ETB via Telebirr to `0912345678`. After paying, submit your Transaction Ref number."
            btn_txt = "📥 Submit Transaction Ref"
            
        kb = [[InlineKeyboardButton(btn_txt, callback_data=f"submit_ref_{content_id}")]]
        await context.bot.send_message(chat_id=user_id, text=pay_msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return ConversationHandler.END

    # ተጠቃሚው የክፍያ Ref ለማስገባት ሲዘጋጅ (የመጀመሪያ Entry Point)
    if data.startswith("submit_ref_"):
        msg = "✍️ እባክዎ የቴሌብር የግብይት መለያ ቁጥሩን (Transaction Ref Number) እዚህ ይጻፉልን፦"
        if lang == "or": msg = "✍️ Maaloo lakkoofsa heeregaa (Ref) barreessi፦"
        elif lang == "en": msg = "✍️ Please type the Transaction Ref number here:"
        await context.bot.send_message(chat_id=user_id, text=msg)
        return AWAITING_TELEBIRR_REF

    # የአድሚን አፕሩቫል ሂደቶች
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    if data.startswith("approve_auth_"):
        auth_id = int(data.split("_")[2])
        cursor.execute("UPDATE authors SET status = 'approved' WHERE user_id = ?", (auth_id,))
        conn.commit()
        await query.edit_message_text("✅ ደራሲው በተሳካ ሁኔታ ጸድቋል።")
        await context.bot.send_message(chat_id=auth_id, text="🎉 እንኳን ደስ አለዎት! የደራሲነት ማመልከቻዎ ጽድቆ ወደ ስራ መግባት ይችላሉ።")
        
    elif data.startswith("approve_book_"):
        book_id = int(data.split("_")[2])
        cursor.execute("UPDATE contents SET status = 'approved' WHERE id = ?", (book_id,))
        conn.commit()
        cursor.execute("SELECT author_id, title FROM contents WHERE id = ?", (book_id,))
        row = cursor.fetchone()
        await query.edit_message_text("✅ ይዘቱ እንዲሸጥ ተፈቅዷል።")
        await context.bot.send_message(chat_id=row[0], text=f"🎉 ' {row[1]} ' የተባለው ይዘትዎ በአድሚን ጽድቆ ለገበያ ቀርቧል።")
        
    elif data.startswith("pay_app_"):
        order_id = int(data.split("_")[2])
        buyer_id, b_id = approve_order_in_db(order_id)
        book = get_content_by_id(b_id)
        await query.edit_message_text("✅ ክፍያው ጽድቋል፣ ፋይሉ ለተጠቃሚው ተልኳል።")
        await context.bot.send_message(chat_id=buyer_id, text=f"🎉 ክፍያዎ ተረጋግጧል! ያዘዙት ' {book['title']} ' ይዘት ከታች ተልኮልዎታል።")
        async with aiofiles.open(book['file_path'], 'rb') as f:
            content_bytes = await f.read()
        await context.bot.send_document(chat_id=buyer_id, document=content_bytes, filename=os.path.basename(book['file_path']))
        
    elif data.startswith("pay_rej_"):
        order_id = int(data.split("_")[2])
        cursor.execute("UPDATE orders SET status = 'rejected' WHERE id = ?", (order_id,))
        cursor.execute("SELECT user_id FROM orders WHERE id = ?", (order_id,))
        buyer_id = cursor.fetchone()[0]
        conn.commit()
        await query.edit_message_text("❌ ክፍያው ውድቅ ተደርጓል።")
        await context.bot.send_message(chat_id=buyer_id, text="❌ ያስገቡት የክፍያ ማረጋገጫ ቁጥር ትክክል ባለመሆኑ በአድሚን ውድቅ ተደርጓል። እባክዎ እንደገና በትክክል ያስገቡ።")

    conn.close()
    return ConversationHandler.END

# =====================================================================
# 🚀 ቦቱን የማስነሻ ዋና ክፍል (MAIN APPLICATION)
# =====================================================================
async def main() -> None:
    # 📁 'files' ፎልደር መኖሩን ማረጋገጥ፣ ከሌለ መፍጠር።
    if not os.path.exists('files'):
        os.makedirs('files')
        logging.info("📁 'files' የተባለው ፎልደር በተሳካ ሁኔታ ተፈጥሯል።")

    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    
    search_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^(🔍 ፈልግ \(Search\)|🔍 Barbaadi \(Search\)|🔍 Search)$"), start_search)],
        states={AWAITING_SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, execute_search)]},
        fallbacks=[]
    )
    
    reg_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^(✍️ ደራሲ መሆን እፈልጋለሁ|✍️ Barreessaa Ta'uun Barbaada|✍️ Become an Author)$"), start_registration)],
        states={
            AWAITING_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_bio)],
            AWAITING_PHONE: [MessageHandler(filters.TEXT | filters.CONTACT, save_phone_and_finish)]
        },
        fallbacks=[CommandHandler("cancel", cancel_reg)]
    )
    
    upload_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^(➕ አዲስ ይዘት አክል|➕ Kitaaba Haaraa Gali|➕ Add New Book)$"), start_book_upload)],
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
    
    print("🚀 ቦቱ በተሳካ ሁኔታ ተነስቷል...")
    await app.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
