import logging
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
from config import BOT_TOKEN, ADMIN_ID, TELEBIRR_PHONE, TELEBIRR_ACCOUNT_NAME
import database as db
from utils import security

# የሎግ ማስተካከያ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# =====================================================================
# 🔄 የውይይት መቆጣጠሪያ ደረጃዎች
# =====================================================================
AWAITING_BIO, AWAITING_PHONE = range(2)
AWAITING_TITLE, AWAITING_CATEGORY, AWAITING_DESC, AWAITING_PRICE, AWAITING_FILE = range(10, 15)
AWAITING_SEARCH_QUERY = range(20, 21)
AWAITING_TELEBIRR_REF = range(30, 31)

# =====================================================================
# ⌨️ የሁሉም ቋንቋዎች ኪቦርዶች
# =====================================================================
lang_keyboard = [["🇪🇹 አማርኛ", "🌳 Afaan Oromoo", "🇬🇧 English"]]

am_main_keyboard = [
    ["📚 መጻሕፍት", "📄 ማጠቃለያዎች/Handouts"],
    ["📝 የሞዴል ጥያቄዎች", "📁 ማስታወሻዎች"],
    ["🔍 ፈልግ (Search)", "📁 የእኔ ላይብረሪ"],
    ["✍️ ደራሲ መሆን እፈልጋለሁ", "➕ አዲስ ይዘት አክል", "☎️ እርዳታ"],
    ["📊 የሽያጭ ሪፖርት"]
]

am_cat_keyboard = [
    ["📖 ስነ-ጽሁፍ (Literature)", "🎓 ትምህርት (Education)"],
    ["📖 ሃይማኖት (Religion)", "📜 ታሪክ (History)"],
    ["💼 ንግድ (Business)", "💻 ቴክኖሎጂ (Technology)"],
    ["📄 ማጠቃለያዎች (Handouts)", "📁 ማስታወሻዎች (Notes)"],
    ["📝 የሞዴል ጥያቄዎች (Question Bank)", "⬅️ ወደ ዋናው ማውጫ"]
]

or_main_keyboard = [
    ["📚 Kitaabota", "📄 Qorannooslee/Handouts"],
    ["📝 Gaaffii Moodelii", "📁 Hubannoo/Notes"],
    ["🔍 Barbaadi (Search)", "📁 Kuusaa Koo"],
    ["✍️ Barreessaa Ta'uu", "➕ Kitaaba Haaraa Gali", "☎️ Gargaarsa"],
    ["📊 Gabaasa Gurgurtaa"]
]

or_cat_keyboard = [
    ["📖 Og-barruu (Literature)", "🎓 Barnoota (Education)"],
    ["📖 Amantiikaa (Religion)", "📜 Seenaa (History)"],
    ["💼 Daldala (Business)", "💻 Teeknoolojii (Technology)"],
    ["📄 Qorannooslee (Handouts)", "📁 Hubannoo (Notes)"],
    ["📝 Gaaffii Moodelii (Question Bank)", "⬅️ Gara Menuu Gurguddaatti"]
]

en_main_keyboard = [
    ["📚 Books", "📄 Handouts"],
    ["📝 Model Questions", "📁 Notes"],
    ["🔍 Search", "📁 My Library"],
    ["✍️ Become an Author", "➕ Add New Book", "☎️ Help"],
    ["📊 Sales Report"]
]

en_cat_keyboard = [
    ["📖 Literature", "🎓 Education"],
    ["📖 Religion", "📜 History"],
    ["💼 Business", "💻 Technology"],
    ["📄 Handouts", "📁 Notes"],
    ["📝 Model Questions (Question Bank)", "⬅️ Back to Main Menu"]
]


# =====================================================================
# 🚀 የጥሪ መጀመሪያ (START COMMAND)
# =====================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.save_user_info(user.id, user.username, user.first_name)
    
    msg = (
        "📚 Welcome to Kitab\n\nPlease select your language:\n\n"
        "እንኳን ወደ ኪታብ በደህና መጡ! እባክዎ ቋንቋ ይምረጡ፦\n\n"
        "Baga Gara Kitab Dhuftan! Maaloo afaan keessan filadha:-"
    )
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(lang_keyboard, resize_keyboard=True))


# =====================================================================
# 👑 የአድሚን መቆጣጠሪያ ክፍል (ተሻሽሏል)
# =====================================================================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ ይህንን ትዕዛዝ ለመጠቀም ፈቃድ የለዎትም!")
        return

    # 🆕 የተሻሻለ ጥሪ - መዝገብ ይመለሳል
    counts = db.get_pending_counts()

    msg = (
        "👑 **የኪታብ ማርኬትፕሌስ አድሚን ፓነል**\n\n"
        f"📝 ለመመስጠር የሚጠበቁ ይዘቶች፡ **{counts['pending_encryption']}**\n"
        f"📝 ለማጽደቅ የሚጠበቁ ይዘቶች፡ **{counts['pending_author_approval']}**\n"
        f"✍️ በግምገማ ላይ ያሉ ደራሲያን፡ **{counts['pending_authors']}**\n"
        f"💳 ማረጋገጫ የሚጠብቁ የደራሲ ክፍያዎች፡ **{counts['pending_author_payments']}**\n"
        f"💳 ማረጋገጫ የሚጠብቁ የአድሚን ክፍያዎች፡ **{counts['pending_admin_payments']}**\n"
        f"🚫 በአገልግሎት ክፍያ የታገዱ ይዘቶች፡ **{counts['blocked_contents']}**\n\n"
        "ከታች ያሉትን አዝራሮች በመጫን ተጨማሪ ስራዎችን ያከናውኑ፦"
    )
    keyboard = [
        [InlineKeyboardButton("📚 ሁሉንም ይዘቶች ይመልከቱ", callback_data="admin_view_all")],
        [InlineKeyboardButton("📊 አጠቃላይ ሽያጭ ሪፖርት", callback_data="admin_sales_report")]
    ]
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


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
        "🔔 **አዲስ ይዘት ለDRM መመስጠር ቀርቧል!**\n\n"
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
            await bot.send_document(
                chat_id=ADMIN_ID,
                document=open(file_path, 'rb'),
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
# ✍️ የደራሲያን ምዝገባ ፍሰት
# =====================================================================
async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    
    status = db.get_author_application_status(user_id)

    if status:
        if status == 'approved':
            if lang == "am": await update.message.reply_text("💡 እርስዎ አስቀድመው ደራሲ ሆነው ተመዝግበዋል!")
            elif lang == "or": await update.message.reply_text("💡 Isin duraan barreessaa ta'anii galmaaytaniittu!")
            else: await update.message.reply_text("💡 You are already registered as an author!")
            return ConversationHandler.END
        elif status == 'pending':
            if lang == "am": await update.message.reply_text("⏳ ማመልከቻዎ በአድሚን በመገምገም ላይ ነው፤ እባክዎ በትዕግስት ይጠብቁ።")
            elif lang == "or": await update.message.reply_text("⏳ Gafannoon keessan adminiin ilaalamaa jira, maaloo eegaa.")
            else: await update.message.reply_text("⏳ Your application is under review by admin, please wait.")
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
    lang = db.get_user_lang(user_id)
    
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
    lang = db.get_user_lang(user_id)
    phone = update.message.contact.phone_number if update.message.contact else update.message.text
    bio = context.user_data.get('bio', '')
    
    db.set_user_phone(user_id, phone)
    db.register_author_pending(user_id, bio)
    
    await notify_admin_new_author(context.bot, user_id, user.username, user.first_name, bio, phone)
    
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    if lang == "am":
        await update.message.reply_text("🎉 የማመልከቻ ፎርምዎ ለአድሚን ተልኳል! ሲጸድቅ በቦቱ በኩል መልዕክት ይደርስዎታል።", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    elif lang == "or":
        await update.message.reply_text("🎉 Gafannoon keessan adminiif ergameera! Yeroo mirkanaa'u ergaan isiniif deebi'a.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    else:
        await update.message.reply_text("🎉 Your application has been sent to admin! You will receive a message once approved.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return ConversationHandler.END


async def cancel_reg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    msg = "ምዝገባው ተቋርጧል።" if lang == "am" else ("Galmeen addaan citeera." if lang == "or" else "Registration canceled.")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return ConversationHandler.END


# =====================================================================
# ➕ አዲስ ይዘት ማስገቢያ ፍሰት
# =====================================================================
async def start_book_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    
    if not db.is_user_author(user_id):
        if lang == "am": await update.message.reply_text("❌ ይዘት ለመጫን መጀመሪያ ደራሲ ሆነው መመዝገብ እና መፅደቅ አለብዎት!")
        elif lang == "or": await update.message.reply_text("❌ Kitaaba galchuuf jalqaba barreessaa mirkanaa'e ta'uu qabdu!")
        else: await update.message.reply_text("❌ You must be an approved author first before uploading books!")
        return ConversationHandler.END

    if lang == "am": await update.message.reply_text("📝 እባክዎ የይዘቱን ርዕስ (Title) ያስገቡ፦", reply_markup=ReplyKeyboardRemove())
    elif lang == "or": await update.message.reply_text("📝 Maaloo mata duree kitaabaa galchaa:", reply_markup=ReplyKeyboardRemove())
    else: await update.message.reply_text("📝 Please enter the title of the content:", reply_markup=ReplyKeyboardRemove())
    return AWAITING_TITLE


async def save_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['upload_title'] = update.message.text
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    
    kb = am_cat_keyboard if lang == "am" else (or_cat_keyboard if lang == "or" else en_cat_keyboard)
    msg = "እባክዎ ተስማሚ የይዘት ዘርፍ (Category) ይምረጡ፦" if lang == "am" else ("Maaloo gosa kitaabaa filadha:" if lang == "or" else "Please select the category:")
    
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return AWAITING_CATEGORY


async def save_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    
    cat_map = {
        "📖 ስነ-ጽሁፍ (Literature)": "Literature", "📖 ስነ-ጽሑፍ (Literature)": "Literature", 
        "📖 Og-barruu (Literature)": "Literature", "📖 Literature": "Literature",
        "🎓 ትምህርት (Education)": "Education", "🎓 Barnoota (Education)": "Education", 
        "🎓 Education": "Education",
        "📖 ሃይማኖት (Religion)": "Religion", "📖 Amantiikaa (Religion)": "Religion", 
        "📖 Religion": "Religion",
        "📜 ታሪክ (History)": "History", "📜 Seenaa (History)": "History", 
        "📜 History": "History",
        "💼 ንግድ (Business)": "Business", "💼 Daldala (Business)": "Business", 
        "💼 Business": "Business",
        "💻 ቴክኖሎጂ (Technology)": "Technology", "💻 Teeknoolojii (Technology)": "Technology", 
        "💻 Technology": "Technology",
        "📄 ማጠቃለያዎች (Handouts)": "Handouts", "📄 Qorannooslee (Handouts)": "Handouts", 
        "📄 Handouts": "Handouts",
        "📁 ማስታወሻዎች (Notes)": "Notes", "📁 Hubannoo (Notes)": "Notes", 
        "📁 Notes": "Notes",
        "📝 የሞዴል ጥያቄዎች (Question Bank)": "QuestionBank", 
        "📝 Gaaffii Moodelii (Question Bank)": "QuestionBank", 
        "📝 Model Questions (Question Bank)": "QuestionBank"
    }
    
    context.user_data['upload_cat'] = cat_map.get(text, "Literature")
    
    msg = "📝 ስለ ይዘቱ አጭር መግለጫ (Description) ይጻፉ፦" if lang == "am" else ("Maaloo ibsa kitaabaa gabaabaan barreessaa:" if lang == "or" else "Please write a short description:")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return AWAITING_DESC


async def save_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['upload_desc'] = update.message.text
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    
    msg = "💰 የመሸጫ ዋጋ በብር (ETB) ያስገቡ (በነፃ ለማቅረብ 0 ያስገቡ)፦" if lang == "am" else ("💰 Gatii kitaabaa birriidhaan galchaa (fkn: 150):" if lang == "or" else "💰 Enter the price in ETB (Enter 0 for Free):")
    await update.message.reply_text(msg)
    return AWAITING_PRICE


async def save_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    
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
    lang = db.get_user_lang(user_id)
    
    if not update.message.document:
        msg = "❌ እባክዎ ፋይሉን እንደ Document (PDF) አድርገው ይጫኑት፦" if lang == "am" else ("❌ Maaloo faayilii PDF qofa ergaa:" if lang == "or" else "❌ Please upload the file as a Document (PDF):")
        await update.message.reply_text(msg)
        return AWAITING_FILE

    doc = update.message.document
    os.makedirs("files", exist_ok=True)
    
    # 🆕 የፋይል ስም ማጽዳት
    safe_filename = security.sanitize_filename(doc.file_name)
    file_path = f"files/{safe_filename}"
    
    telegram_file = await context.bot.get_file(doc.file_id)
    await telegram_file.download_to_drive(file_path)
    
    title = context.user_data.get('upload_title')
    category = context.user_data.get('upload_cat')
    desc = context.user_data.get('upload_desc')
    price = context.user_data.get('upload_price')
    
    # 🆕 አዲስ ጥሪ - status 'pending_encryption' ይሆናል
    inserted_id = db.add_content(user_id, title, category, desc, price, file_path)
    
    await notify_admin_new_book(context.bot, inserted_id, title, price, file_path)
    
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    if lang == "am": 
        await update.message.reply_text(
            "🎉 ይዘትዎ በተሳካ ሁኔታ ተጭኗል!\n\n"
            "⏳ አሁን ፋይሉ ለደህንነት ጥበቃ (DRM Encryption) ይዘጋጃል።\n"
            "📌 ሂደቱ ከተጠናቀቀ በኋላ ለማጽደቅ ይላክልዎታል።",
            reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
        )
    elif lang == "or":
        await update.message.reply_text(
            "🎉 Kitaabni keessan milkiyn galeera!\n\n"
            "⏳ Amma faayilii kun eegumsa (DRM Encryption) jedhamuuf qophaa'aa jira.\n"
            "📌 Hojii xumuramee booda mirkaneessuuf isinii ergama.",
            reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
        )
    else:
        await update.message.reply_text(
            "🎉 Content uploaded successfully!\n\n"
            "⏳ The file is now being prepared for DRM encryption.\n"
            "📌 You will receive it for approval once the process is complete.",
            reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
        )
    
    return ConversationHandler.END


async def cancel_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    msg = "የይዘት ጭነቱ ተቋርጧል።" if lang == "am" else ("Galmeen kitaabaa addaan citeera." if lang == "or" else "Upload canceled.")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return ConversationHandler.END


# =====================================================================
# 🔍 የፍለጋ ሥርዓት
# =====================================================================
async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    msg = "🔍 ለመፈለግ የፈለጉትን መጽሐፍ ወይም ይዘት ርዕስ (Title) በከፊል ወይም ሙሉ በሙሉ ይጻፉልኝ፦" if lang == "am" else ("🔍 Maaloo jecha qabiyyee barbaaddan barreessaa:" if lang == "or" else "🔍 Please enter the title or keyword you want to search for:")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return AWAITING_SEARCH_QUERY


async def execute_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_text = update.message.text.strip()
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    
    results = db.execute_search_query(query_text)
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    
    if not results:
        msg = "❌ ይቅርታ፣ ያቀረቡትን ቃል የሚመስል ምንም አይነት ይዘት አልተገኘም።" if lang == "am" else ("❌ Dardon, waan argamu hin jiru." if lang == "or" else "❌ No matching content found.")
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return ConversationHandler.END

    for item in results:
        caption = f"📌 **ርዕስ:** {item['title']}\n💰 **ዋጋ:** {item['price']} ETB\n📝 **መግለጫ:** {item['description']}"
        btn_text = "📥 በነፃ አውርድ" if item['price'] <= 0 else "💳 በ Chapa / Telebirr ክፈል"
        if lang == "or": btn_text = "📥 Buufadhu" if item['price'] <= 0 else "💳 Kaffaltii Raawwadhu"
        elif lang == "en": btn_text = "📥 Download" if item['price'] <= 0 else "💳 Pay Now"
        
        inline_kb = [[InlineKeyboardButton(btn_text, callback_data=f"buy_{item['id']}")]]
        await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(inline_kb), parse_mode="Markdown")
        
    await update.message.reply_text("🔍 የፍለጋ ውጤቶች እነዚህ ናቸው።", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return ConversationHandler.END


# =====================================================================
# 📁 የእኔ ላይብረሪ
# =====================================================================
async def view_library(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    
    my_contents = db.get_user_library(user_id)

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
# 💳 የተሻሻለ የክፍያ ማስተናገጃ (ከአዲሱ ሰንጠረዥ ጋር)
# =====================================================================

async def process_telebirr_ref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ተጠቃሚ የቴሌብር ደረሰኝ ቁጥር ሲያስገባ ይሰራል
    """
    tx_ref = update.message.text.strip()
    user = update.effective_user
    lang = db.get_user_lang(user.id)
    content_id = context.user_data.get('buying_book_id')
    
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    
    if not content_id:
        await update.message.reply_text("❌ ስህተት ተፈጥሯል። እባክዎ እንደገና ይሞክሩ", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return ConversationHandler.END
        
    book = db.get_content_by_id(content_id)
    if not book:
        await update.message.reply_text("❌ ይዘቱ አልተገኘም", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return ConversationHandler.END

    # 🆕 ትዕዛዝ መፍጠር - የገንዘብ አይነት መወሰን
    # ይዘቱ መጽሐፍ ከሆነ 'author', ሌላ ከሆነ 'admin'
    payment_type = 'author' if db.is_book_content(content_id) else 'admin'
    
    order_id = db.add_order(user.id, content_id, book['price'], tx_ref, payment_type=payment_type, status="pending")
    
    if not order_id:
        dup_msg = "❌ ይህ የግብይት ቁጥር (Ref) ቀድሞ ጥቅም ላይ ውሏል። እባክዎ ትክክለኛውን ቁጥር በድጋሚ ያስገቡ ወይም ድጋፍ ያግኙ።"
        if lang == "or": dup_msg = "❌ Lakkoofsi herrega kun (Ref) duraan itti fayyadameera. Maaloo lakkoofsa sirrii deebi'aa galchaa."
        elif lang == "en": dup_msg = "❌ This transaction reference has already been used. Please enter the correct reference or contact support."
        await update.message.reply_text(dup_msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return ConversationHandler.END

    # 🆕 የክፍያ መዝገብ መፍጠር
    if payment_type == 'author':
        payment_id = db.create_author_payment(order_id, book['author_id'], user.id, content_id, book['price'])
    else:
        payment_id = db.create_admin_payment(order_id, user.id, content_id, book['price'])
    
    context.user_data['payment_id'] = payment_id
    context.user_data['payment_type'] = payment_type

    msg = "🙏 የግብይት ቁጥርዎ ተመዝግቧል። በአድሚን ተረጋግጦ ይዘቱ ወዲያውኑ ይላክልዎታል።"
    if lang == "or": msg = "🙏 Lakkoofsi herrega keessanii galmeeffameera. Erga mirkanaa'ee booda isiniif ergama."
    elif lang == "en": msg = "🙏 Your transaction reference has been recorded. Content will be sent after verification."
    
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    
    # 🆕 ለአድሚን ማሳወቂያ - አዲስ ቅርጸት
    admin_msg = (
        f"💳 **አዲስ ክፍያ ለማረጋገጥ ቀርቧል**\n\n"
        f"👤 ተጠቃሚ: @{user.username} ({user.id})\n"
        f"📚 ይዘት: {book['title']}\n"
        f"💰 ዋጋ: {book['price']} ETB\n"
        f"📝 የቴሌብር Ref: `{tx_ref}`\n"
        f"📌 ክፍያ ዓይነት: {'📚 ደራሲ' if payment_type == 'author' else '👑 አድሚን'}\n"
        f"🆔 የክፍያ ID: `{payment_id}`"
    )
    admin_buttons = [[
        InlineKeyboardButton("✅ ክፍያውን አጽድቅ", callback_data=f"admin_app_pay_{payment_id}"),
        InlineKeyboardButton("❌ ውድቅ አድርግ", callback_data=f"admin_rej_pay_{payment_id}")
    ]]
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, reply_markup=InlineKeyboardMarkup(admin_buttons), parse_mode="Markdown")
    return ConversationHandler.END


# =====================================================================
# 📊 የደራሲ ሽያጭ ሪፖርት
# =====================================================================
async def author_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    
    if not db.is_user_author(user_id):
        msg = "❌ ይህን ለመጠቀም ደራሲ መሆን አለብዎት!"
        if lang == "or": msg = "❌ Kana fayyadamuf barreessaa ta'uu qabdu!"
        elif lang == "en": msg = "❌ You must be an author to use this!"
        await update.message.reply_text(msg)
        return
    
    sales_data = db.get_author_sales(user_id)
    if not sales_data['contents']:
        msg = "📭 እስካሁን ምንም ይዘት አላስገቡም።"
        if lang == "or": msg = "📭 Hanga ammaatti qabiyyee hin galchitan."
        elif lang == "en": msg = "📭 You haven't uploaded any content yet."
        await update.message.reply_text(msg)
        return
    
    lines = ["📊 **የሽያጭ ሪፖርት**", ""]
    for item in sales_data['contents']:
        lines.append(f"📌 **{item['title']}**")
        lines.append(f"   💰 ዋጋ: {item['price']} ETB")
        lines.append(f"   🛒 የተሸጠ ብዛት: {item['sales_count']}")
        lines.append(f"   💵 ገቢ: {item['income']} ETB")
        lines.append("")
    lines.append(f"💰 **ጠቅላላ ገቢ:** {sales_data['total_income']} ETB")
    
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# =====================================================================
# 🔄 አጠቃላይ የመልዕክት ማስተናገጃ
# =====================================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    
    if text in lang_keyboard[0]:
        lang = "am" if "አማርኛ" in text else ("or" if "Oromoo" in text else "en")
        db.set_user_lang(user_id, lang)
        kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
        msg = "ዋና ማውጫ" if lang == "am" else ("Menuu Gurguddaa" if lang == "or" else "Main Menu")
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return

    lang = db.get_user_lang(user_id)

    # 📊 የሽያጭ ሪፖርት አዝራር
    if text in ["📊 የሽያጭ ሪፖርት", "📊 Gabaasa Gurgurtaa", "📊 Sales Report"]:
        await author_stats(update, context)
        return

    # 📁 የእኔ ላይብረሪ አዝራር
    if text in ["📁 የእኔ ላይብረሪ", "📁 Kuusaa Koo", "📁 My Library"]:
        await view_library(update, context)
        return

    # 📚 ዋና የመጽሐፍ ማውጫ
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

    # 📌 ለዋና ዋና ምድቦች የቀጥታ አዝራሮች
    db_category = None
    if text in ["📄 ማጠቃለያዎች/Handouts", "📄 Qorannooslee/Handouts", "📄 Handouts", 
                "📄 ማጠቃለያዎች (Handouts)", "📄 Qorannooslee (Handouts)"]:
        db_category = "Handouts"
    elif text in ["📁 ማስታወሻዎች", "📁 Hubannoo/Notes", "📁 Notes", 
                  "📁 ማስታወሻዎች (Notes)", "📁 Hubannoo (Notes)"]:
        db_category = "Notes"
    elif text in ["📝 የሞዴል ጥያቄዎች", "📝 Gaaffii Moodelii", "📝 Model Questions", 
                  "📝 የሞዴል ጥያቄዎች (Question Bank)", "📝 Gaaffii Moodelii (Question Bank)", 
                  "📝 Model Questions (Question Bank)"]:
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
        books = db.get_contents_by_category(db_category)
        
        if not books:
            if lang == "am": msg = f"😔 ይቅርታ፣ በዚህ ሰዓት በ'{text}' ዘርፍ የተጫነ ይዘት የለም።"
            elif lang == "or": msg = f"😔 Dardon, gosa kanaan '{text}' qabiyyee argamu hin jiru."
            else: msg = f"😔 Sorry, there are no items available in the '{text}' category right now."
            await update.message.reply_text(msg)
            return

        for book in books:
            caption = f"📌 **ርዕስ:** {book['title']}\n💰 **ዋጋ:** {book['price']} ETB\n📝 **መግለጫ:** {book['description']}"
            btn_text = "📥 በነፃ አውርድ" if book['price'] <= 0 else "💳 በ Chapa / Telebirr ክፈል"
            if lang == "or": btn_text = "📥 Buufadhu" if book['price'] <= 0 else "💳 Kaffaltii Raawwadhu"
            elif lang == "en": btn_text = "📥 Download" if book['price'] <= 0 else "💳 Pay Now"
            
            inline_kb = [[InlineKeyboardButton(btn_text, callback_data=f"buy_{book['id']}")]]
            await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(inline_kb), parse_mode="Markdown")
        return

    # 📌 በስም በቀጥታ ሲፈልጉ
    book = db.get_content_by_title(text)

    if book:
        if lang == "am":
            checkout_msg = f"🛒 **የመግዣ ማጠቃለያ**\n\n📚 **ርዕስ:** {book['title']}\n💰 **ዋጋ:** {book['price']} ETB\n📝 **መግለጫ:** {book['description']}\n\nይህንን ይዘት ገዝተው በቅጽበት ለማውረድ ከታች ያለውን የክፍያ ቁልፍ ይጫኑ፦"
            btn_text = "💳 በ Chapa / Telebirr ክፈል"
        elif lang == "or":
            checkout_msg = f"🛒 **Maamilummaa Bitataa**\n\n📚 **Mata duree:** {book['title']}\n💰 **Gatii:** {book['price']} ETB\n📝 **Ibsa:** {book['description']}\n\nBitachuuf qabdoo gadii cuqaasaa:"
            btn_text = "💳 Kaffaltii Raawwadhu"
        else:
            checkout_msg = f"🛒 **Purchase Order**\n\n📚 **Title:** {book['title']}\n💰 **Price:** {book['price']} ETB\n📝 **Description:** {book['description']}\n\nClick the button below to complete your purchase:"
            btn_text = "💳 Pay Now"

        keyboard = [[InlineKeyboardButton(btn_text, callback_data=f"buy_{book['id']}")]]
        await update.message.reply_text(checkout_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return


# =====================================================================
# 💳 የክፍያ እና የአድሚን ውሳኔዎች ማስተናገጃ
# =====================================================================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)

    # የአድሚን-ብቻ ድርጊቶች ማረጋገጫ
    ADMIN_ONLY_PREFIXES = (
        "admin_app_pay_", "admin_rej_pay_",
        "approve_book_", "reject_book_",
        "approve_auth_", "reject_auth_",
        "admin_download_", "admin_view_all", "admin_sales_report"
    )
    if data.startswith(ADMIN_ONLY_PREFIXES) and user_id != ADMIN_ID:
        await query.answer("⛔ ይህንን ድርጊት ለመፈጸም ፈቃድ የለዎትም።", show_alert=True)
        return

    await query.answer()
    
    # ================================================================
    # 👑 አድሚን ክፍያ ማጽደቅ (የተሻሻለ)
    # ================================================================
    if data.startswith("admin_app_pay_"):
        payment_id = int(data.split("_")[3])
        # የክፍያ ዓይነት መለየት
        payment = db.get_author_payment_by_id(payment_id)
        if payment:
            success = db.admin_verify_author_payment(payment_id, "በአድሚን ጸድቋል")
            payment_type = 'author'
        else:
            payment = db.get_admin_payment_by_id(payment_id)
            if payment:
                success = db.admin_verify_admin_payment(payment_id, "በአድሚን ጸድቋል")
                payment_type = 'admin'
            else:
                await query.edit_message_text("❌ ክፍያው አልተገኘም")
                return
        
        if success:
            await query.edit_message_text(f"✅ ክፍያ #{payment_id} ተረጋግጧል!")
            
            # መጽሐፉን ለተጠቃሚ መላክ
            book = db.get_content_by_id(payment['content_id'])
            if book and os.path.exists(book['file_path']):
                await context.bot.send_message(
                    chat_id=payment['user_id'],
                    text="✅ ክፍያዎ በአድሚን ተረጋግጧል! ያዘዙት ይዘት ከታች ተልኮልዎታል።"
                )
                async with aiofiles.open(book['file_path'], 'rb') as f:
                    file_data = await f.read()
                await context.bot.send_document(
                    chat_id=payment['user_id'],
                    document=file_data,
                    filename=os.path.basename(book['file_path']),
                    protect_content=True
                )
        else:
            await query.edit_message_text(f"❌ ክፍያ #{payment_id} ማጽደቅ አልተቻለም")
        return

    # ================================================================
    # 👑 አድሚን ክፍያ ውድቅ ማድረግ (የተሻሻለ)
    # ================================================================
    elif data.startswith("admin_rej_pay_"):
        payment_id = int(data.split("_")[3])
        # የክፍያ ዓይነት መለየት
        payment = db.get_author_payment_by_id(payment_id)
        if payment:
            success = db.admin_reject_payment(payment_id, 'author', "በአድሚን ውድቅ ተደርጓል")
        else:
            payment = db.get_admin_payment_by_id(payment_id)
            if payment:
                success = db.admin_reject_payment(payment_id, 'admin', "በአድሚን ውድቅ ተደርጓል")
            else:
                await query.edit_message_text("❌ ክፍያው አልተገኘም")
                return
        
        if success:
            await query.edit_message_text(f"❌ ክፍያ #{payment_id} ውድቅ ተደርጓል።")
            if payment:
                await context.bot.send_message(
                    chat_id=payment['user_id'],
                    text="❌ ያስገቡት የክፍያ ማረጋገጫ ቁጥር ትክክል ባለመሆኑ በአድሚን ውድቅ ተደርጓል።"
                )
        else:
            await query.edit_message_text(f"❌ ክፍያ #{payment_id} ውድቅ ማድረግ አልተቻለም")
        return

    # ================================================================
    # 👑 አድሚን ሁሉንም ይዘቶች ማየት (የተሻሻለ - ገጽ መለያየት)
    # ================================================================
    if data == "admin_view_all":
        page = context.user_data.get('admin_page', 0)
        limit = 5
        result = db.get_all_contents(limit=limit, offset=page * limit)
        contents = result['items']
        total = result['total']
        
        if not contents:
            await context.bot.send_message(chat_id=user_id, text="📭 ምንም ይዘት የለም።")
            return
        
        for content in contents:
            sales_count = db.get_content_sales_count(content['id'])
            status_emoji = "✅" if content['status'] == 'approved' else ("⏳" if content['status'] in ['pending_encryption', 'pending_author_approval'] else "❌")
            caption = (
                f"📌 **{content['title']}**\n"
                f"👤 ደራሲ ID: {content['author_id']}\n"
                f"💰 {content['price']} ETB\n"
                f"📊 ሽያጭ: {sales_count}\n"
                f"📝 ሁኔታ: {status_emoji} {content['status']}"
            )
            kb = [[InlineKeyboardButton("📥 አውርድ", callback_data=f"admin_download_{content['id']}")]]
            await context.bot.send_message(chat_id=user_id, text=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        
        # ገጽ መለያየት አዝራሮች
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ ቀዳሚ", callback_data="admin_page_prev"))
        if (page + 1) * limit < total:
            nav_buttons.append(InlineKeyboardButton("➡️ ቀጣይ", callback_data="admin_page_next"))
        if nav_buttons:
            nav_buttons.append(InlineKeyboardButton("🔄 አዘምን", callback_data="admin_view_all"))
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📄 ገጽ {page + 1}/{((total - 1) // limit) + 1} (📚 {total} ይዘቶች)",
                reply_markup=InlineKeyboardMarkup([nav_buttons])
            )
        return

    # ================================================================
    # 📄 ገጽ መለያየት
    # ================================================================
    if data == "admin_page_next":
        context.user_data['admin_page'] = context.user_data.get('admin_page', 0) + 1
        # እንደገና መላክ
        await handle_callback(update, context)
        return
        
    if data == "admin_page_prev":
        context.user_data['admin_page'] = max(0, context.user_data.get('admin_page', 0) - 1)
        await handle_callback(update, context)
        return

    # ================================================================
    # 📊 አድሚን አጠቃላይ ሽያጭ ሪፖርት
    # ================================================================
    if data == "admin_sales_report":
        result = db.get_all_contents(limit=100, offset=0)
        contents = result['items']
        total_income = 0.0
        lines = ["📊 **አጠቃላይ የሽያጭ ሪፖርት**", ""]
        for content in contents:
            sales = db.get_content_sales_count(content['id'])
            income = sales * content['price']
            total_income += income
            if sales > 0:
                lines.append(f"📌 {content['title']} — {sales} ጊዜ ተሽጧል — {income} ETB")
        lines.append("")
        lines.append(f"💰 **ጠቅላላ ገቢ:** {total_income} ETB")
        await context.bot.send_message(chat_id=user_id, text="\n".join(lines), parse_mode="Markdown")
        return

    # ================================================================
    # 📥 አድሚን ፋይል ማውረድ
    # ================================================================
    if data.startswith("admin_download_"):
        content_id = data.split("_")[2]
        try:
            security.validate_content_id(int(content_id))
        except:
            await query.answer("❌ የተሳሳተ መታወቂያ", show_alert=True)
            return
        book = db.get_content_by_id(int(content_id))
        if book and os.path.exists(book['file_path']):
            async with aiofiles.open(book['file_path'], 'rb') as f:
                file_data = await f.read()
            await context.bot.send_document(
                chat_id=user_id,
                document=file_data,
                filename=os.path.basename(book['file_path']),
                caption=f"📥 {book['title']} (አድሚን አውርዷል)"
            )
            await query.answer("✅ ፋይሉ ተልኳል")
        else:
            await query.answer("❌ ፋይሉ አልተገኘም", show_alert=True)
        return

    # ================================================================
    # 🛒 የክፍያ ፍሰት - ግዢ
    # ================================================================
    if data.startswith("buy_"):
        row_id = data.split("_")[1]
        book = db.get_content_by_id(row_id)
        
        if book:
            if book['price'] <= 0:
                # ነጻ መጽሐፍ
                order_id = db.add_order(user_id, book['id'], 0, payment_ref="FREE_DOWNLOAD", status="paid")
                if order_id:
                    try:
                        file_path = book['file_path']
                        if os.path.exists(file_path):
                            if lang == "am": await context.bot.send_message(chat_id=user_id, text=f"✅ ይዘቱ ወደ '📁 የእኔ ላይብረሪ' ተጨምሯል። ፋይሉ እነሆ፦")
                            elif lang == "or": await context.bot.send_message(chat_id=user_id, text=f"✅ Kuusaa keessanitti dabalamuun, ፋይሉ ተልኳል፦")
                            else: await context.bot.send_message(chat_id=user_id, text=f"✅ Saved to your library. Here is your file:")
                            
                            async with aiofiles.open(file_path, 'rb') as f:
                                file_data = await f.read()
                            await context.bot.send_document(chat_id=user_id, document=file_data, filename=os.path.basename(file_path), protect_content=True)
                        else:
                            if lang == "am": await context.bot.send_message(chat_id=user_id, text="❌ ይቅርታ፣ የይዘቱ ፋይል በሲስተሙ ላይ አልተገኘም።")
                            else: await context.bot.send_message(chat_id=user_id, text="❌ Sorry, the file was not found on the server.")
                    except Exception as e:
                        logging.error(f"Error sending free file: {e}")
                return

            # የሚከፈልበት መጽሐፍ
            pay_msg = (
                f"💳 **የክፍያ መመሪያ ({book['title']})**\n\n"
                f"እባክዎ **{book['price']} ETB** ወደሚከተለው የቴሌብር (telebirr) ሂሳብ ያስገቡ፦\n\n"
                f"📱 **የስልክ ቁጥር:** `{TELEBIRR_PHONE}`\n"
                f"👤 **የአካውንት ስም:** `{TELEBIRR_ACCOUNT_NAME}`\n\n"
                f"ክፍያውን ከፈጸሙ በኋላ የደረሰኝ ቁጥሩን (Transaction ID/Ref) ለመላክ ከታች ያለውን አዝራር ይጫኑ፦"
            )
            inline_kb = [[InlineKeyboardButton("📩 የደረሰኝ ቁጥር (Ref) አስገባ", callback_data=f"submit_ref_{book['id']}")]]
            await context.bot.send_message(chat_id=user_id, text=pay_msg, reply_markup=InlineKeyboardMarkup(inline_kb), parse_mode="Markdown")

    # ================================================================
    # 📩 የደረሰኝ ቁጥር ማስገቢያ
    # ================================================================
    elif data.startswith("submit_ref_"):
        book_id = data.split("_")[2]
        context.user_data['buying_book_id'] = book_id
        msg = "✍️ እባክዎ የቴሌብር የግብይት መለያ ቁጥሩን (Transaction Ref Number) እዚህ ይጻፉልን፦"
        if lang == "or": msg = "✍️ Maaloo lakkoofsa heeregaa (Ref) barreessi፦"
        elif lang == "en": msg = "✍️ Please type the Transaction Ref number here:"
        await context.bot.send_message(chat_id=user_id, text=msg)
        return AWAITING_TELEBIRR_REF

    # ================================================================
    # 📥 ዳውንሎድ (ከቤተ-መጻሕፍት)
    # ================================================================
    elif data.startswith("download_"):
        content_id = data.split("_")[1]
        book = db.get_content_by_id(content_id)

        if book and not db.user_owns_content(user_id, content_id):
            no_access_msg = "❌ ይህንን ይዘት አልገዙትም፣ ስለዚህ ማውረድ አይችሉም።"
            if lang == "or": no_access_msg = "❌ Isin qabiyyee kana hin bitanne, kanaaf buufachuu hin dandeessan."
            elif lang == "en": no_access_msg = "❌ You haven't purchased this item, so you can't download it."
            await context.bot.send_message(chat_id=user_id, text=no_access_msg)
            return

        if book and os.path.exists(book['file_path']):
            async with aiofiles.open(book['file_path'], 'rb') as f:
                file_data = await f.read()
            await context.bot.send_document(chat_id=user_id, document=file_data, filename=os.path.basename(book['file_path']), caption=f"📥 {book['title']}", protect_content=True)

    # ================================================================
    # 👑 አድሚን ይዘት ማጽደቅ
    # ================================================================
    elif data.startswith("approve_book_"):
        book_id = data.split("_")[2]
        res = db.approve_content(book_id)
        
        await query.edit_message_caption(caption="✅ ይዘቱ በተሳካ ሁኔታ ጽድቋል!", reply_markup=None)
        if res:
            author_id, book_title = res[0], res[1]
            author_lang = db.get_user_lang(author_id)
            if author_lang == "am": auth_msg = f"🎉 እንኳን ደስ አለዎት! '{book_title}' የተሰኘው ይዘትዎ በአድሚን ተገምግሞ ጽድቋል።"
            elif author_lang == "or": auth_msg = f"🎉 Baga gammaddan! Qabiyyee keessan '{book_title}' adminiin mirkanaayeera."
            else: auth_msg = f"🎉 Congratulations! Your content '{book_title}' has been approved by the admin."
            try: await context.bot.send_message(chat_id=author_id, text=auth_msg)
            except: pass

    # ================================================================
    # 👑 አድሚን ይዘት መከልከል
    # ================================================================
    elif data.startswith("reject_book_"):
        book_id = data.split("_")[2]
        res = db.reject_content(book_id)
        
        await query.edit_message_caption(caption="❌ ይዘቱ ውድቅ (Rejected) ተደርጓል።", reply_markup=None)
        if res:
            author_id, book_title = res[0], res[1]
            author_lang = db.get_user_lang(author_id)
            if author_lang == "am": auth_msg = f"😔 ይቅርታ፣ '{book_title}' የተሰኘው ይዘትዎ ተከልክሏል።"
            elif author_lang == "or": auth_msg = f"😔 Gammachuun, qabiyyee keessan '{book_title}' adminiin fudhatama hin arganne."
            else: auth_msg = f"😔 Sorry, your content '{book_title}' has been rejected by the admin."
            try: await context.bot.send_message(chat_id=author_id, text=auth_msg)
            except: pass

    # ================================================================
    # 👑 አድሚን ደራሲ ማጽደቅ
    # ================================================================
    elif data.startswith("approve_auth_"):
        target_user_id = data.split("_")[2]
        db.approve_author(target_user_id)
        
        await query.edit_message_text(text="✅ ደራሲው በተሳካ ሁኔታ ጽድቋል!", reply_markup=None)
        
        author_lang = db.get_user_lang(target_user_id)
        kb = am_main_keyboard if author_lang == "am" else (or_main_keyboard if author_lang == "or" else en_main_keyboard)
        if author_lang == "am": auth_msg = "🎉 እንኳን ደስ አለዎት! የደራሲነት ማመልከቻዎ በአድሚን ጽድቋል። አሁን ይዘቶችን ማከል ይችላሉ!"
        elif author_lang == "or": auth_msg = "🎉 Baga gammaddan! Gafannoon barreessummaa keessan adminiin mirkanaayeera. Amma qabiyyee galchuu dandeessu!"
        else: auth_msg = "🎉 Congratulations! Your author application has been approved. You can now upload content!"
        try: await context.bot.send_message(chat_id=target_user_id, text=auth_msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        except: pass

    # ================================================================
    # 👑 አድሚን ደራሲ መከልከል
    # ================================================================
    elif data.startswith("reject_auth_"):
        target_user_id = data.split("_")[2]
        db.reject_author(target_user_id)
        await query.edit_message_text(text="❌ የደራሲነት ጥያቄው ውድቅ ተደርጓል።", reply_markup=None)
        return


# =====================================================================
# 🏁 ዋናው የማስነሻ ክፍል
# =====================================================================
def main():
    if not os.path.exists('files'):
        os.makedirs('files')
        logging.info("📁 'files' ፎልደር ተፈጥሯል።")

    db.init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    
    search_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^(🔍 ፈልግ \(Search\)|🔍 Barbaadi \(Search\)|🔍 Search)$"), start_search)],
        states={AWAITING_SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, execute_search)]},
        fallbacks=[]
    )

    reg_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^(✍️ ደራሲ መሆን እፈልጋለሁ|✍️ Barreessaa Ta'uu|✍️ Become an Author)$"), start_registration)],
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
    
    print("✅ Kitab Bot በተሳካ ሁኔታ ተነስቷል...")
    app.run_polling()

if __name__ == "__main__":
    main()
