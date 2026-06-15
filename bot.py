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
from config import BOT_TOKEN, DB_NAME
import database

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# የውይይት መቆጣጠሪያ ደረጃዎች (Conversation States)
AWAITING_BIO, AWAITING_PHONE = range(2)
AWAITING_TITLE, AWAITING_CATEGORY, AWAITING_DESC, AWAITING_PRICE, AWAITING_FILE = range(10, 15)

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
    ["⬅️ ወደ ዋናው ማውጫ"]
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
    ["⬅️ Gara Menuu Gurguddaatti"]
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
    ["⬅️ Back to Main Menu"]
]


# --- ረዳት ፋንክሽኖች ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    database.save_user(user.id, user.username, user.first_name)
    
    msg = (
        "📚 Welcome to Kitab\n\nPlease select your language:\n\n"
        "እንኳን ወደ ኪታብ በደህና መጡ! እባክዎ ቋንቋ ይምረጡ፦\n\n"
        "Baga Gara Kitab Dhuftan! Maaloo afaan keessan filadha:-"
    )
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(lang_keyboard, resize_keyboard=True))


def get_user_lang(telegram_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT language FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if (row and row[0]) else "am"


def is_user_author(telegram_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM authors WHERE user_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None


# =====================================================================
# ✍️ የደራሲያን ምዝገባ ፍሰት (AUTHOR REGISTRATION FLOW)
# =====================================================================
async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    if is_user_author(user_id):
        if lang == "am": await update.message.reply_text("💡 እርስዎ አስቀድመው ደራሲ ሆነው ተመዝግበዋል!")
        elif lang == "or": await update.message.reply_text("💡 Isin duraan barreessaa ta'anii galmaaytaniittu!")
        else: await update.message.reply_text("💡 You are already registered as an author!")
        return ConversationHandler.END

    if lang == "am":
        await update.message.reply_text("👋 ወደ ደራሲያን ምዝገባ እንኳን በደህና መጡ!\n\nእባክዎን አጭር የህይወት ታሪክዎን (Biography) ይጻፉልን፦", reply_markup=ReplyKeyboardRemove())
    elif lang == "or":
        await update.message.reply_text("👋 Gara galmee barreessitootaa baga nagaan dhuftan!\n\nMaaloo seenaa keessan gabaabaan (Biography) nuu barreessaa:", reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text("👋 Welcome to Author Registration!\n\nPlease write a short biography about yourself:", reply_markup=ReplyKeyboardRemove())
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
        msg = "Gaarii dha! Amma ammoo kaffaltii fi qunnamtiidhaaf lakkoofsa bilbila keessan nuu ergaa:"
    else:
        phone_btn = [[KeyboardButton("📲 Share Phone Number", request_contact=True)]]
        msg = "Great! Now please enter or share your phone number for payments:"
        
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(phone_btn, resize_keyboard=True, one_time_keyboard=True))
    return AWAITING_PHONE


async def save_phone_and_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    phone = update.message.contact.phone_number if update.message.contact else update.message.text
    bio = context.user_data.get('bio', '')
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET phone = ? WHERE telegram_id = ?", (phone, user_id))
    cursor.execute("INSERT OR IGNORE INTO authors (user_id, status, biography) VALUES (?, 'approved', ?)", (user_id, bio))
    conn.commit()
    conn.close()
    
    if lang == "am":
        await update.message.reply_text("🎉 የደራሲነት ምዝገባዎ በተሳካ ሁኔታ ተጠናቆ ጸድቋል!", reply_markup=ReplyKeyboardMarkup(am_main_keyboard, resize_keyboard=True))
    elif lang == "or":
        await update.message.reply_text("🎉 Galmeen barreessummaa keessan milkiyn mirkanaayeera!", reply_markup=ReplyKeyboardMarkup(or_main_keyboard, resize_keyboard=True))
    else:
        await update.message.reply_text("🎉 Your author registration was approved successfully!", reply_markup=ReplyKeyboardMarkup(en_main_keyboard, resize_keyboard=True))
    return ConversationHandler.END


async def cancel_reg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    msg = "ምዝገባው ተቋርጧል።" if lang == "am" else ("Galmeen addaan citeera." if lang == "or" else "Registration canceled.")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return ConversationHandler.END


# =====================================================================
# ➕ አዲስ መጽሐፍ ማስገቢያ ፍሰት (BOOK UPLOAD FLOW)
# =====================================================================
async def start_book_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    if not is_user_author(user_id):
        if lang == "am": await update.message.reply_text("❌ መጽሐፍ ለመጫን መጀመሪያ ደራሲ ሆነው መመዝገብ አለብዎት!")
        elif lang == "or": await update.message.reply_text("❌ Kitaaba galchuuf jalqaba barreessaa ta'uu qabdu!")
        else: await update.message.reply_text("❌ You must register as an author first before uploading books!")
        return ConversationHandler.END

    if lang == "am": await update.message.reply_text("📝 እባክዎ የመጽሐፉን ርዕስ (Title) ያስገቡ፦", reply_markup=ReplyKeyboardRemove())
    elif lang == "or": await update.message.reply_text("📝 Maaloo mata duree kitaabaa galchaa:", reply_markup=ReplyKeyboardRemove())
    else: await update.message.reply_text("📝 Please enter the title of the book:", reply_markup=ReplyKeyboardRemove())
    return AWAITING_TITLE


async def save_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['upload_title'] = update.message.text
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    kb = am_cat_keyboard if lang == "am" else (or_cat_keyboard if lang == "or" else en_cat_keyboard)
    msg = "እባክዎ የመጽሐፉን ዘርፍ (Category) ይምረጡ፦" if lang == "am" else ("Maaloo gosa kitaabaa filadha:" if lang == "or" else "Please select the book category:")
    
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return AWAITING_CATEGORY


async def save_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    cat_map = {
        "📖 ስነ-ጽሁፍ (Literature)": "Literature", "📖 Og-barruu (Literature)": "Literature", "📖 Literature": "Literature",
        "🎓 ትምህርት (Education)": "Education", "🎓 Barnoota (Education)": "Education", "🎓 Education": "Education",
        "📖 ሃይማኖት (Religion)": "Religion", "📖 Amantiikaa (Religion)": "Religion", "📖 Religion": "Religion",
        "📜 ታሪክ (History)": "History", "📜 Seenaa (History)": "History", "📜 History": "History",
        "💼 ንግድ (Business)": "Business", "💼 Daldala (Business)": "Business", "💼 Business": "Business",
        "💻 ቴክኖሎጂ (Technology)": "Technology", "💻 Teeknoolojii (Technology)": "Technology", "💻 Technology": "Technology"
    }
    
    context.user_data['upload_cat'] = cat_map.get(text, "Literature")
    
    msg = "📝 ስለ መጽሐፉ አጭር መግለጫ (Description) ይጻፉ፦" if lang == "am" else ("Maaloo ibsa kitaabaa gabaabaan barreessaa:" if lang == "or" else "Please write a short description of the book:")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return AWAITING_DESC


async def save_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['upload_desc'] = update.message.text
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    msg = "💰 የመጽሐፉን ዋጋ በብር (ETB) ያስገቡ (ምሳሌ፦ 150)፦" if lang == "am" else ("💰 Gatii kitaabaa birriidhaan galchaa (fkn: 150):" if lang == "or" else "💰 Enter the price of the book in ETB (e.g., 150):")
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

    msg = "📄 አሁን የመጽሐፉን የPDF ፋይል ይጫኑ (Upload Document)፦" if lang == "am" else ("📄 Amma faayilii PDF kitaabichaa ergaa:" if lang == "or" else "📄 Now please upload the PDF file of the book:")
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
        VALUES (?, ?, ?, ?, ?, ?, 'approved')
    """, (user_id, title, category, desc, price, file_path))
    conn.commit()
    conn.close()
    
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    if lang == "am": await update.message.reply_text("🎉 መጽሐፍዎ በተሳካ ሁኔታ ተጭኗል! አሁን በካቴጎሪው ውስጥ ማግኘት ይቻላል።", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    elif lang == "or": await update.message.reply_text("🎉 Kitaabni keessan milkiyn galeera! Amma argachuun ni danda'ama.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    else: await update.message.reply_text("🎉 Your book has been uploaded successfully! It is now available in its category.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    
    return ConversationHandler.END


async def cancel_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    msg = "የመጽሐፍ ጭነቱ ተቋርጧል።" if lang == "am" else ("Galmeen kitaabaa addaan citeera." if lang == "or" else "Book upload canceled.")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return ConversationHandler.END


# =====================================================================
# 🔄 አጠቃላይ የመልዕክት ማስተናገጃ (GENERAL MESSAGE HANDLER)
# =====================================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "🇪🇹 አማርኛ":
        database.set_language(user_id, "am")
        await update.message.reply_text("ወደ ዋናው ማውጫ እንኳን በደህና መጡ!", reply_markup=ReplyKeyboardMarkup(am_main_keyboard, resize_keyboard=True))
        return
    elif text == "🌳 Afaan Oromoo":
        database.set_language(user_id, "or")
        await update.message.reply_text("Gara menuu gurguddaatti baga nagaan dhuftan!", reply_markup=ReplyKeyboardMarkup(or_main_keyboard, resize_keyboard=True))
        return
    elif text == "🇬🇧 English":
        database.set_language(user_id, "en")
        await update.message.reply_text("Welcome to the Main Menu!", reply_markup=ReplyKeyboardMarkup(en_main_keyboard, resize_keyboard=True))
        return

    lang = get_user_lang(user_id)

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

    cat_map = {
        "📖 ስነ-ጽሁፍ (Literature)": "Literature", "📖 Og-barruu (Literature)": "Literature", "📖 Literature": "Literature",
        "🎓 ትምህርት (Education)": "Education", "🎓 Barnoota (Education)": "Education", "🎓 Education": "Education",
        "📖 ሃይማኖት (Religion)": "Religion", "📖 Amantiikaa (Religion)": "Religion", "📖 Religion": "Religion",
        "📜 ታሪክ (History)": "History", "📜 Seenaa (History)": "History", "📜 History": "History",
        "💼 ንግድ (Business)": "Business", "💼 Daldala (Business)": "Business", "💼 Business": "Business",
        "💻 ቴክኖሎጂ (Technology)": "Technology", "💻 Teeknoolojii (Technology)": "Technology", "💻 Technology": "Technology"
    }

    if text in cat_map:
        db_category = cat_map[text]
        books = database.get_contents_by_category("Book", db_category)
        
        if not books:
            msg = "በዚህ ዘርፍ መጽሐፍ የለም።" if lang == "am" else ("Gosa kanaan kitabni hin jiru." if lang == "or" else "No books in this category.")
            await update.message.reply_text(msg)
            return

        for book in books:
            if lang == "am": caption = f"📚 ርዕስ: {book['title']}\n💰 ዋጋ: {book['price']} ETB\n📝 መግለጫ: {book['description']}"
            elif lang == "or": caption = f"📚 Mata duree: {book['title']}\n💰 Gatii: {book['price']} ETB\n📝 Ibsa: {book['description']}"
            else: caption = f"📚 Title: {book['title']}\n💰 Price: {book['price']} ETB\n📝 Description: {book['description']}"
            await update.message.reply_text(caption)
        return

    # 🔍 ተጠቃሚው የመጽሐፍ ርዕስ በቀጥታ ሲጽፍ ትዕዛዝ ማስተናገጃ (Title Handler)
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT rowid, * FROM contents WHERE title = ? AND status = 'approved'", (text,))
    book = cursor.fetchone()
    conn.close()

    if book:
        if lang == "am":
            checkout_msg = (
                f"🛒 **የመግዣ ማጠቃለያ**\n\n"
                f"📚 **ርዕስ:** {book['title']}\n"
                f"💰 **ዋጋ:** {book['price']} ETB\n"
                f"📝 **መግለጫ:** {book['description']}\n\n"
                f"ይህንን መጽሐፍ ገዝተው በቅጽበት ለማውረድ ከታች ያለውን የክፍያ ቁልፍ ይጫኑ፦"
            )
            btn_text = "💳 በ Chapa / Telebirr ክፈል"
        elif lang == "or":
            checkout_msg = (
                f"🛒 **Maamilummaa Bitataa**\n\n"
                f"📚 **Mata duree:** {book['title']}\n"
                f"💰 **Gatii:** {book['price']} ETB\n"
                f"📝 **Ibsa:** {book['description']}\n\n"
                f"Kitaaba kana bitachuuf qabdoo gadii cuqaasaa:"
            )
            btn_text = "💳 Kaffaltii Raawwadhu"
        else:
            checkout_msg = (
                f"🛒 **Purchase Order**\n\n"
                f"📚 **Title:** {book['title']}\n"
                f"💰 **Price:** {book['price']} ETB\n"
                f"📝 **Description:** {book['description']}\n\n"
                f"Click the button below to complete your purchase and download the book:"
            )
            btn_text = "💳 Pay Now"

        keyboard = [[InlineKeyboardButton(btn_text, callback_data=f"buy_{book['rowid']}")]]
        await update.message.reply_text(checkout_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return


# =====================================================================
# 💳 የክፍያ እና ፋይል ማድረሻ ማስተናገጃ (CALLBACK QUERY HANDLER)
# =====================================================================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    if data.startswith("buy_"):
        row_id = data.split("_")[1]
        
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM contents WHERE rowid = ?", (row_id,))
        book = cursor.fetchone()
        conn.close()
        
        if book:
            if lang == "am":
                await query.edit_message_text(f"⏳ የክፍያ ማረጋገጫ... እባክዎ ይጠብቁ...")
            elif lang == "or":
                await query.edit_message_text(f"⏳ Kaffaltii mirkaneessaa... maaloo eegaa...")
            else:
                await query.edit_message_text(f"⏳ Verifying payment... please wait...")
            
            # ፋይሉን የመላክ ሂደት
            try:
                file_path = book['file_path']
                if os.path.exists(file_path):
                    if lang == "am":
                        await context.bot.send_message(chat_id=user_id, text=f"✅ ክፍያዎ ተረጋግጧል! የገዙት መጽሐፍ እነሆ፦")
                    elif lang == "or":
                        await context.bot.send_message(chat_id=user_id, text=f"✅ Kaffaltiin keessan mirkanaayeera! Kitaabni keessan ergameera፦")
                    else:
                        await context.bot.send_message(chat_id=user_id, text=f"✅ Payment successful! Here is your book:")
                        
                    await context.bot.send_document(chat_id=user_id, document=open(file_path, 'rb'))
                else:
                    if lang == "am": await context.bot.send_message(chat_id=user_id, text="❌ ይቅርታ፣ የመጽሐፉ ፋይል በሴርቨሩ ላይ አልተገኘም።")
                    else: await context.bot.send_message(chat_id=user_id, text="❌ Sorry, the book file was not found on the server.")
            except Exception as e:
                logging.error(f"Error sending file: {e}")


# =====================================================================
# 🏁 ዋናው የማስነሻ ክፍል (MAIN FUNCTION)
# =====================================================================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # 1. የደራሲያን ምዝገባ ማስተናገጃ
    reg_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^(✍️ ደራሲ መሆን እፈልጋለሁ|✍️ Barreessaa Ta'uu|✍️ Become an Author)$"), start_registration)],
        states={
            AWAITING_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_bio)],
            AWAITING_PHONE: [MessageHandler(filters.TEXT | filters.CONTACT, save_phone_and_finish)]
        },
        fallbacks=[CommandHandler("cancel", cancel_reg)]
    )
    
    # 2. የመጽሐፍ ጭነት ማስተናገጃ
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
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(reg_handler)
    app.add_handler(upload_handler)
    app.add_handler(CallbackQueryHandler(handle_callback)) # የክፍያ በተኑን ለመስማት የተጨመረ
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Kitab Bot (የመጽሐፍ መግዣ Flow የተካተተበት) ተነስቷል...")
    app.run_polling()

if __name__ == "__main__":
    main()
