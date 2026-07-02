"""
🤖 bot.py — ዋናው የኪታብ ቦት
"""

import logging
import os
import sys
import aiofiles
import re
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

# =====================================================================
# 📝 LOGGING CONFIGURATION (UTF-8 Compatible)
# =====================================================================

# Force UTF-8 encoding for stdout (fixes garbled text in Codespaces)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    # Python < 3.7 fallback
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

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
# 👑 የአድሚን መቆጣጠሪያ ክፍል
# =====================================================================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ ይህንን ትዕዛዝ ለመጠቀም ፈቃድ የለዎትም!")
        return

    counts = db.get_pending_counts()

    msg = (
        "👑 **የኪታብ ማርኬትፕሌስ አድሚን ፓነል**\n\n"
        f"🔐 ለመመስጠር የሚጠበቁ: **{counts['pending_encryption']}**\n"
        f"📝 ለማጽደቅ የሚጠበቁ: **{counts['pending_author_approval']}**\n"
        f"✍️ በግምገማ ላይ ያሉ ደራሲያን: **{counts['pending_authors']}**\n"
        f"💳 ማረጋገጫ የሚጠብቁ ክፍያዎች: **{counts['pending_author_payments'] + counts['pending_admin_payments']}**\n"
        f"🚫 የታገዱ ይዘቶች: **{counts['blocked_contents']}**\n\n"
        "📌 ሙሉ የአስተዳደር ፓነል ለማግኘት አድሚን ቦቱን ይጠቀሙ።"
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
        "🔔 **አዲስ ይዘት ለመመስጠር ቀርቧል!**\n\n"
        f"📚 **ርዕስ:** {title}\n"
        f"💰 **ዋጋ:** {price} ETB\n"
        f"🆔 **ID:** `{book_id}`\n\n"
        "📌 እባክዎ ፋይሉን በDRM በመመስጠር ለደራሲ ማጽደቅ ያዘጋጁ።"
    )
    keyboard = [[
        InlineKeyboardButton("🔐 ፋይሉን አመስጥር", callback_data=f"admin_encrypt_{book_id}")
    ]]
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
        logger.error(f"Failed to send file review to admin: {e}")


async def notify_admin_encryption_complete(bot, book_id, title, author_id):
    """ፋይሉ ተመስጥሯል እና ለደራሲ ማጽደቅ ዝግጁ መሆኑን ለአድሚን ያሳውቃል"""
    msg = (
        f"✅ **ይዘት ተመስጥሯል!**\n\n"
        f"📚 **ርዕስ:** {title}\n"
        f"🆔 **ID:** `{book_id}`\n"
        f"👤 **ደራሲ ID:** `{author_id}`\n\n"
        "📌 አሁን ለደራሲ ማጽደቅ ይጠበቃል።"
    )
    await bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode="Markdown")


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
    
    # ፋይሉ ፒዲኤፍ መሆኑን ማረጋገጥ
    if not doc.file_name.endswith('.pdf'):
        msg = "❌ እባክዎ የፒዲኤፍ (PDF) ፋይል ብቻ ይጫኑ!" if lang == "am" else ("❌ Maaloo faayilii PDF qofa ergaa!" if lang == "or" else "❌ Please upload only PDF files!")
        await update.message.reply_text(msg)
        return AWAITING_FILE
    
    os.makedirs("files", exist_ok=True)
    
    # ደህንነቱ የተጠበቀ የፋይል መንገድ
    safe_filename = security.sanitize_filename(doc.file_name)
    file_path = f"files/{safe_filename}"
    
    telegram_file = await context.bot.get_file(doc.file_id)
    await telegram_file.download_to_drive(file_path)
    
    title = context.user_data.get('upload_title')
    category = context.user_data.get('upload_cat')
    desc = context.user_data.get('upload_desc')
    price = context.user_data.get('upload_price')
    
    # 🆕 አዲስ ይዘት በ'pending_encryption' ሁኔታ
    inserted_id = db.add_content(user_id, title, category, desc, price, file_path)
    
    # ለአድሚን ማሳወቂያ (ፋይሉ ለመመስጠር ዝግጁ መሆኑን)
    await notify_admin_new_book(context.bot, inserted_id, title, price, file_path)
    
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    if lang == "am": 
        await update.message.reply_text(
            "✅ ይዘትዎ በተሳካ ሁኔታ ተጭኗል!\n\n"
            "⏳ አሁን ፋይሉ ለደህንነት ጥበቃ (DRM Encryption) በአድሚን ይዘጋጃል።\n"
            "📌 ሂደቱ ከተጠናቀቀ በኋላ ለማጽደቅ ይላክልዎታል።",
            reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
        )
    elif lang == "or":
        await update.message.reply_text(
            "✅ Kitaabni keessan milkiyn galeera!\n\n"
            "⏳ Amma faayilii kun eegumsa (DRM Encryption) jedhamuuf adminiin qophaa'aa jira.\n"
            "📌 Hojii xumuramee booda mirkaneessuuf isinii ergama.",
            reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
        )
    else:
        await update.message.reply_text(
            "✅ Content uploaded successfully!\n\n"
            "⏳ The file is now being prepared for DRM encryption by admin.\n"
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
    
    # የፍለጋ ጽሑፍ ማጽዳት
    safe_query = re.sub(r'[^a-zA-Z0-9አ-፥\s]', '', query_text)
    if not safe_query:
        msg = "❌ እባክዎ ትክክለኛ ቃል ያስገቡ" if lang == "am" else ("❌ Maaloo jecha sirrii galchaa" if lang == "or" else "❌ Please enter a valid search term")
        await update.message.reply_text(msg)
        return ConversationHandler.END
    
    results = db.execute_search_query(safe_query, limit=20)
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
# 💳 የክፍያ ስርዓት - ቀጥታ ወደ ደራሲ ክፍያ
# =====================================================================

async def show_payment_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE, book):
    """
    ደረጃ 1: ገዢው ወደ ደራሲው እንዲከፍል መመሪያ
    """
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    
    # ደራሲውን ማግኘት
    author = db.get_author_by_user_id(book['author_id'])
    if not author:
        await update.message.reply_text("❌ የደራሲ መረጃ አልተገኘም")
        return
    
    # የደራሲ ስልክ ቁጥር ማግኘት
    user = db.get_user_by_id(book['author_id'])
    author_phone = user.get('phone', TELEBIRR_PHONE) if user else TELEBIRR_PHONE
    
    # ምድቡን ማረጋገጥ - መጽሐፍ ከሆነ ወደ ደራሲ፣ ሌላ ከሆነ ወደ አድሚን
    is_book = db.is_book_content(book['id'])
    payment_type = 'author' if is_book else 'admin'
    
    if payment_type == 'author':
        payee = f"👤 ደራሲ: {user.get('first_name', '') if user else ''}"
        phone_display = author_phone
    else:
        payee = "👑 አድሚን"
        phone_display = TELEBIRR_PHONE
    
    msg = (
        f"💳 **የክፍያ መመሪያ**\n\n"
        f"📚 መጽሐፍ: **{book['title']}**\n"
        f"💰 ዋጋ: **{book['price']} ETB**\n"
        f"{payee}\n\n"
        f"1️⃣ ክፍያዎን ወደሚከተለው የቴሌብር ቁጥር ያስገቡ\n"
        f"📱 **{phone_display}**\n"
        f"👤 **{TELEBIRR_ACCOUNT_NAME}**\n\n"
        f"2️⃣ ከተከፈለ በኋላ ከቴሌብር የደረሰውን የሪሲት ሊንክ ያስገቡ\n"
        f"3️⃣ አድሚኑ ካረጋገጠ በኋላ መጽሐፉ ይለቀቃል\n\n"
        f"✍️ **የሪሲት ሊንኩን እዚህ ይላኩ**"
    )
    
    # ይዘቱን ለማስታወስ
    context.user_data['payment_book_id'] = book['id']
    context.user_data['payment_author_id'] = book['author_id']
    context.user_data['payment_type'] = payment_type
    context.user_data['payment_amount'] = book['price']
    
    await update.message.reply_text(msg, parse_mode="Markdown")


async def process_receipt_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ደረጃ 2: ገዢው የቴሌብር ሪሲት ሊንክ ያስገባል
    """
    receipt_link = update.message.text.strip()
    user = update.effective_user
    lang = db.get_user_lang(user.id)
    
    book_id = context.user_data.get('payment_book_id')
    author_id = context.user_data.get('payment_author_id')
    payment_type = context.user_data.get('payment_type', 'author')
    amount = context.user_data.get('payment_amount', 0)
    
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    
    if not book_id:
        await update.message.reply_text("❌ ስህተት ተፈጥሯል። እባክዎ እንደገና ይሞክሩ")
        return
    
    # ሊንክ መሆኑን ማረጋገጥ
    if not receipt_link.startswith(('http://', 'https://')):
        await update.message.reply_text("❌ እባክዎ ትክክለኛ ሊንክ ያስገቡ (https://...)")
        return
    
    # የሪሲት መለያ ቁጥር ከሊንክ ማውጣት (ለማስታወሻ)
    import re
    ref_match = re.search(r'[A-Z0-9\-]{8,}', receipt_link)
    receipt_ref = ref_match.group(0) if ref_match else f"REF-{book_id}-{user.id}"
    
    # ትዕዛዝ መፍጠር
    order_id = db.add_order(
        user_id=user.id,
        content_id=book_id,
        amount=amount,
        payment_ref=receipt_ref,
        payment_type=payment_type,
        status="pending"
    )
    
    if not order_id:
        await update.message.reply_text("❌ ትዕዛዝ መፍጠር አልተቻለም። እባክዎ እንደገና ይሞክሩ")
        return
    
    # ክፍያ መፍጠር
    if payment_type == 'author':
        payment_id = db.create_author_payment(
            order_id=order_id,
            author_id=author_id,
            user_id=user.id,
            content_id=book_id,
            amount=amount
        )
    else:
        payment_id = db.create_admin_payment(
            order_id=order_id,
            user_id=user.id,
            content_id=book_id,
            amount=amount
        )
    
    if not payment_id:
        await update.message.reply_text("❌ ክፍያ መፍጠር አልተቻለም። እባክዎ እንደገና ይሞክሩ")
        return
    
    # የሪሲት ሊንክ ማስቀመጥ
    success = db.submit_receipt_link(payment_id, receipt_link, receipt_ref, payment_type)
    
    if not success:
        await update.message.reply_text("❌ የሪሲት ሊንክ ማስቀመጥ አልተቻለም። እባክዎ እንደገና ይሞክሩ")
        return
    
    # ለገዢው ማሳወቂያ
    await update.message.reply_text(
        "✅ የሪሲት ሊንክዎ ተመዝግቧል!\n"
        "⏳ አድሚኑ ካረጋገጠ በኋላ መጽሐፉ ይለቀቃል።",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    
    # ለአድሚን ማሳወቂያ
    book = db.get_content_by_id(book_id)
    await notify_admin_pending_payment(context.bot, payment_id, payment_type, user, book, receipt_link, receipt_ref)


async def notify_admin_pending_payment(bot, payment_id, payment_type, user, book, receipt_link, receipt_ref):
    """
    አዲስ ክፍያ ለግምገማ መቅረቡን ለአድሚን ያሳውቃል
    """
    payment_type_label = "📚 ደራሲ" if payment_type == 'author' else "👑 አድሚን"
    msg = (
        f"💳 **አዲስ የክፍያ ማረጋገጫ ቀርቧል!**\n\n"
        f"📌 **ዓይነት:** {payment_type_label}\n"
        f"👤 **ተጠቃሚ:** {user.first_name} (@{user.username}) (ID: {user.id})\n"
        f"📚 **ይዘት:** {book['title']}\n"
        f"💰 **ዋጋ:** {book['price']} ETB\n"
        f"🆔 **ክፍያ ID:** `{payment_id}`\n"
        f"🔗 **ሪሲት ሊንክ:** [ክፈት]({receipt_link})\n"
        f"📝 **Ref:** `{receipt_ref}`\n\n"
        "📌 እባክዎ ሊንኩን ከፍተው ክፍያውን ያረጋግጡ።"
    )
    keyboard = [[
        InlineKeyboardButton("✅ አጽድቅ", callback_data=f"admin_app_pay_{payment_id}"),
        InlineKeyboardButton("❌ ውድቅ", callback_data=f"admin_rej_pay_{payment_id}")
    ]]
    await bot.send_message(chat_id=ADMIN_ID, text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# =====================================================================
# 📊 የደራሲ ሽያጭ ሪፖርት (የተሻሻለ)
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
    
    # የደራሲ ዳሽቦርድ አዝራሮች እንልካለን
    keyboard = [
        [InlineKeyboardButton("📊 አጠቃላይ ሪፖርት", callback_data=f"author_report_all_{user_id}")],
        [InlineKeyboardButton("📊 የዛሬ ሪፖርት", callback_data=f"author_report_day_{user_id}")],
        [InlineKeyboardButton("📊 የሳምንት ሪፖርት", callback_data=f"author_report_week_{user_id}")],
        [InlineKeyboardButton("📊 የወር ሪፖርት", callback_data=f"author_report_month_{user_id}")],
        [InlineKeyboardButton("👤 ሁሉንም ገዢዎች ይመልከቱ", callback_data=f"author_buyers_{user_id}")],
    ]
    
    await update.message.reply_text(
        "📊 **የደራሲ ሪፖርት ፓነል**\n\n"
        "ከታች ካሉት አማራጮች ይምረጡ፦",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def author_report_by_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """በጊዜ የሽያጭ ሪፖርት"""
    query = update.callback_query
    data = query.data
    parts = data.split("_")
    period = parts[2]
    user_id = int(parts[3])
    
    await query.answer()
    
    # የደራሲውን መለያ ማግኘት
    author = db.get_author_by_user_id(user_id)
    if not author:
        await query.edit_message_text("❌ ደራሲ አልተገኘም")
        return
    
    # ሪፖርት ማግኘት
    report = db.get_author_sales_report(author['user_id'], period)
    stats = report['stats']
    buyers = report['buyers']
    
    period_labels = {
        'all': 'አጠቃላይ',
        'day': 'ዛሬ',
        'week': 'በሳምንቱ',
        'month': 'በወሩ'
    }
    
    msg = (
        f"📊 **የሽያጭ ሪፖርት - {period_labels.get(period, '')}**\n"
        f"═══════════════════════\n\n"
        f"💰 ጠቅላላ ገቢ: **{stats['total_revenue']:.2f} ETB**\n"
        f"🛒 ጠቅላላ ግብይቶች: **{stats['total_transactions']}**\n"
        f"👤 ልዩ ገዢዎች: **{stats['unique_buyers']}**\n"
    )
    
    if buyers:
        msg += "\n🆕 **የቅርብ ጊዜ ገዢዎች (5)**\n"
        for buyer in buyers[:5]:
            msg += (
                f"• {buyer['first_name']} (@{buyer['username']})\n"
                f"  📚 {buyer['book_title']}\n"
                f"  💰 {buyer['amount']} ETB\n"
                f"  📅 {buyer['purchase_date'][:10]}\n\n"
            )
    
    keyboard = [[InlineKeyboardButton("🔙 ወደ ሪፖርት ፓነል", callback_data=f"author_menu_{user_id}")]]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def author_buyers_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """የደራሲውን ሁሉንም ገዢዎች ዝርዝር"""
    query = update.callback_query
    data = query.data
    user_id = int(data.split("_")[2])
    
    await query.answer()
    
    author = db.get_author_by_user_id(user_id)
    if not author:
        await query.edit_message_text("❌ ደራሲ አልተገኘም")
        return
    
    report = db.get_author_sales_report(author['user_id'], 'all')
    buyers = report['buyers']
    
    if not buyers:
        await query.edit_message_text("📭 እስካሁን ምንም ገዢ የለም።")
        return
    
    msg = "👤 **ሁሉም ገዢዎች**\n═══════════════════════\n\n"
    
    for buyer in buyers[:20]:
        msg += (
            f"• **{buyer['first_name']}** (@{buyer['username']})\n"
            f"  📚 {buyer['book_title']}\n"
            f"  💰 {buyer['amount']} ETB\n"
            f"  📅 {buyer['purchase_date'][:10]}\n"
            f"  📝 ID: `{buyer['telegram_id']}`\n\n"
        )
    
    if len(buyers) > 20:
        msg += f"\n... እና {len(buyers) - 20} ተጨማሪ ገዢዎች"
    
    keyboard = [[InlineKeyboardButton("🔙 ወደ ሪፖርት ፓነል", callback_data=f"author_menu_{user_id}")]]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def author_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ወደ ደራሲ ሪፖርት ፓነል መመለስ"""
    query = update.callback_query
    data = query.data
    user_id = int(data.split("_")[2])
    
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📊 አጠቃላይ ሪፖርት", callback_data=f"author_report_all_{user_id}")],
        [InlineKeyboardButton("📊 የዛሬ ሪፖርት", callback_data=f"author_report_day_{user_id}")],
        [InlineKeyboardButton("📊 የሳምንት ሪፖርት", callback_data=f"author_report_week_{user_id}")],
        [InlineKeyboardButton("📊 የወር ሪፖርት", callback_data=f"author_report_month_{user_id}")],
        [InlineKeyboardButton("👤 ሁሉንም ገዢዎች ይመልከቱ", callback_data=f"author_buyers_{user_id}")],
    ]
    
    await query.edit_message_text(
        "📊 **የደራሲ ሪፖርት ፓነል**\n\n"
        "ከታች ካሉት አማራጮች ይምረጡ፦",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


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
        result = db.get_contents_by_category(db_category, limit=50, offset=0)
        books = result if isinstance(result, list) else []
        
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
        await show_payment_instructions(update, context, book)
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
        "pay_app_", "pay_rej_",
        "approve_book_", "reject_book_",
        "approve_auth_", "reject_auth_",
        "admin_download_", "admin_view_all", "admin_sales_report",
        "admin_encrypt_"
    )
    if data.startswith(ADMIN_ONLY_PREFIXES) and user_id != ADMIN_ID:
        await query.answer("⛔ ይህንን ድርጊት ለመፈጸም ፈቃድ የለዎትም።", show_alert=True)
        return

    await query.answer()
    
    # --- የደራሲ ሪፖርት ካልባኮች ---
    if data.startswith("author_report_"):
        await author_report_by_period(update, context)
        return
    elif data.startswith("author_buyers_"):
        await author_buyers_list(update, context)
        return
    elif data.startswith("author_menu_"):
        await author_menu(update, context)
        return
    
    # --- የአድሚን ሁሉንም ይዘቶች ማየት ---
    if data == "admin_view_all":
        result = db.get_all_contents(limit=20, offset=0)
        contents = result['items'] if isinstance(result, dict) else []
        
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
        return

    # --- የአድሚን አጠቃላይ ሽያጭ ሪፖርት ---
    if data == "admin_sales_report":
        result = db.get_all_contents(limit=100, offset=0)
        contents = result['items'] if isinstance(result, dict) else []
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

    # --- አድሚን ፋይል ማውረድ ---
    if data.startswith("admin_download_"):
        content_id = data.split("_")[2]
        try:
            security._validate_content_id(int(content_id))
        except:
            await query.answer("❌ የተሳሳተ መታወቂያ", show_alert=True)
            return
        
        book = db.get_content_by_id(content_id)
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

    # --- የክፍያ ፍሰት ---
    if data.startswith("buy_"):
        row_id = data.split("_")[1]
        book = db.get_content_by_id(row_id)
        
        if book:
            await show_payment_instructions(update, context, book)
        return

    # --- የሪሲት ሊንክ አዝራር (ከተጠቃሚ ግቤት ይልቅ) ---
    elif data.startswith("submit_ref_"):
        book_id = data.split("_")[2]
        context.user_data['payment_book_id'] = book_id
        msg = "✍️ እባክዎ የቴሌብር የግብይት መለያ ቁጥሩን (Transaction Ref Number) እዚህ ይጻፉልን፦"
        if lang == "or": msg = "✍️ Maaloo lakkoofsa heeregaa (Ref) barreessi፦"
        elif lang == "en": msg = "✍️ Please type the Transaction Ref number here:"
        await context.bot.send_message(chat_id=user_id, text=msg)
        return AWAITING_TELEBIRR_REF

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

    # --- አድሚን ክፍያ ማጽደቅ (አዲስ ስርዓት) ---
    elif data.startswith("admin_app_pay_"):
        payment_id = int(data.split("_")[3])
        
        # ክፍያውን ማግኘት (በዓይነት)
        payment = db.get_author_payment_by_id(payment_id)
        payment_type = 'author'
        if not payment:
            payment = db.get_admin_payment_by_id(payment_id)
            payment_type = 'admin'
        
        if not payment:
            await query.edit_message_text("❌ ክፍያ አልተገኘም")
            return
        
        # ማረጋገጥ
        if payment_type == 'author':
            success = db.admin_verify_author_payment(payment_id, "በአድሚን ጸድቋል")
        else:
            success = db.admin_verify_admin_payment(payment_id, "በአድሚን ጸድቋል")
        
        if success:
            await query.edit_message_text("✅ ክፍያው ተረጋግጧል፣ ፋይሉ ለተጠቃሚው ተልኳል።")
            
            # ፋይሉን መላክ
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
            await query.edit_message_text("❌ ክፍያውን ማጽደቅ አልተቻለም።")
        return

    # --- አድሚን ክፍያ ውድቅ ማድረግ ---
    elif data.startswith("admin_rej_pay_"):
        payment_id = int(data.split("_")[3])
        success = db.admin_reject_payment(payment_id, 'author', "በአድሚን ውድቅ ተደርጓል")
        
        if success:
            await query.edit_message_text("❌ ክፍያው ውድቅ ተደርጓል።")
            payment = db.get_author_payment_by_id(payment_id)
            if payment:
                await context.bot.send_message(
                    chat_id=payment['user_id'],
                    text="❌ ያስገቡት የክፍያ ማረጋገጫ ቁጥር ትክክል ባለመሆኑ በአድሚን ውድቅ ተደርጓል።"
                )
        else:
            await query.edit_message_text("❌ ክፍያውን ውድቅ ማድረግ አልተቻለም።")
        return

    # --- አድሚን ይዘት ማጽደቅ ---
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
        return

    # --- አድሚን ይዘት መከልከል ---
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
        return

    # --- አድሚን ደራሲ ማጽደቅ ---
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
        return

    # --- አድሚን ደራሲ መከልከል ---
    elif data.startswith("reject_auth_"):
        target_user_id = data.split("_")[2]
        db.reject_author(target_user_id)
        await query.edit_message_text(text="❌ የደራሲነት ጥያቄው ውድቅ ተደርጓል።", reply_markup=None)
        return


# =====================================================================
# ⏳ የቴሌብር Ref መቀበያ (አሮጌ ስርዓት - ለኋላ ተኳሃኝነት)
# =====================================================================
async def process_telebirr_ref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """የቴሌብር Ref ማስተናገጃ (አሮጌ ስርዓት)"""
    # አሁን አዲሱን ስርዓት እየተጠቀምን ነው
    # ይህ ለኋላ ተኳሃኝነት ተቀምጧል
    await process_receipt_link(update, context)


# =====================================================================
# 🏁 ዋናው የማስነሻ ክፍል
# =====================================================================
def main():
    if not os.path.exists('files'):
        os.makedirs('files')
        logger.info("📁 'files' folder created.")

    db.init_db()
    logger.info("✅ Database initialized.")
    
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
    
    print("✅ Kitab Bot started successfully...")
    app.run_polling()


if __name__ == "__main__":
    main()
