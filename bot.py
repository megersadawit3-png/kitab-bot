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
from config import BOT_TOKEN, ADMIN_ID
import database as db

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
# 👑 የአድሚን መቆጣጠሪያ ክፍል (ADMIN PANEL FUNCTIONS)
# =====================================================================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ ይህንን ትዕዛዝ ለመጠቀም ፈቃድ የለዎትም!")
        return

    pending_books, pending_authors, pending_payments = db.get_pending_counts()

    msg = (
        "👑 **የኪታብ ማርኬትፕሌስ አድሚን ፓነል**\n\n"
        f"📝 በግምገማ ላይ ያሉ ይዘቶች/መጻሕፍት፡ **{pending_books}**\n"
        f"✍️ በግምገማ ላይ ያሉ ደራሲያን፡ **{pending_authors}**\n"
        f"💳 ማረጋገጫ የሚጠብቁ ክፍያዎች፡ **{pending_payments}**\n\n"
        "አዲስ ይዘት ወይም የደራሲነት ጥያቄ ሲመጣ ቦቱ በቀጥታ እዚህ ያቅርብልዎታል።"
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
# ✍️ የደራሲያን ምዝገባ ፍሰት (AUTHOR REGISTRATION FLOW)
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
# ➕ አዲስ ይዘት ማስገቢያ ፍሰት (CONTENT UPLOAD FLOW)
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
    file_path = f"files/{doc.file_name}"
    
    telegram_file = await context.bot.get_file(doc.file_id)
    await telegram_file.download_to_drive(file_path)
    
    title = context.user_data.get('upload_title')
    category = context.user_data.get('upload_cat')
    desc = context.user_data.get('upload_desc')
    price = context.user_data.get('upload_price')
    
    inserted_id = db.add_content(user_id, title, category, desc, price, file_path)
    
    await notify_admin_new_book(context.bot, inserted_id, title, price, file_path)
    
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    if lang == "am": await update.message.reply_text("🎉 ይዘትዎ በተሳካ ሁኔታ ተጭኗል! በአድሚን ተገምግሞ ሲጸድቅ ለተጠቃሚዎች ይበቃል፡፡", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    elif lang == "or": await update.message.reply_text("🎉 Kitaabni keessan milkiyn galeera! Erga admin mirkaneesseen booda gabaaf dhiyaata.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    else: await update.message.reply_text("🎉 Content uploaded successfully! It will be available after admin approval.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    
    return ConversationHandler.END


async def cancel_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    msg = "የይዘት ጭነቱ ተቋርጧል።" if lang == "am" else ("Galmeen kitaabaa addaan citeera." if lang == "or" else "Upload canceled.")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return ConversationHandler.END


# =====================================================================
# 🔍 የፍለጋ ሥርዓት (SEARCH CONVERSATION)
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
# 📁 የእኔ ላይብረሪ (MY LIBRARY SYSTEM)
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
# 📞 የቴሌብር ማኑዋል የደረሰኝ ቁጥር መቀበያ (PROCESS TELEBIRR REF)
# =====================================================================
async def process_telebirr_ref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tx_ref = update.message.text.strip()
    user = update.effective_user
    lang = db.get_user_lang(user.id)
    # 📌 [ዋና ማስተካከያ] submit_ref_ ላይ የተቀመጠውን በትክክል buying_book_id ብሎ ያነባል
    content_id = context.user_data.get('buying_book_id')
    
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    
    if not content_id:
        await update.message.reply_text("❌ Error", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return ConversationHandler.END
        
    book = db.get_content_by_id(content_id)
    if not book:
        await update.message.reply_text("❌ Error", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return ConversationHandler.END

    order_created = db.add_order(user.id, content_id, book['price'], tx_ref, status="pending")

    # 📌 [Security Fix #1] payment_ref ቀድሞ ጥቅም ላይ ከዋለ (UNIQUE constraint ቢጣስ)
    # ይህ ማለት ይህ የቴሌብር ግብይት ቁጥር ቀድሞ በሌላ (ወይም በራሱ) ትዕዛዝ ላይ ጥቅም ላይ ውሏል
    # ማለት ነው — ምናልባት የግልባጭ ቁጥር ድግግሞሽ/ሙከራ ሊሆን ይችላል
    if not order_created:
        dup_msg = "❌ ይህ የግብይት ቁጥር (Ref) ቀድሞ ጥቅም ላይ ውሏል። እባክዎ ትክክለኛውን ቁጥር በድጋሚ ያስገቡ ወይም ድጋፍ ያግኙ።"
        if lang == "or": dup_msg = "❌ Lakkoofsi herrega kun (Ref) duraan itti fayyadameera. Maaloo lakkoofsa sirrii deebi'aa galchaa."
        elif lang == "en": dup_msg = "❌ This transaction reference has already been used. Please enter the correct reference or contact support."
        await update.message.reply_text(dup_msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return ConversationHandler.END

    msg = "🙏 የግብይት ቁጥርዎ ተመዝግቧል። በአድሚን ተረጋግጦ ይዘቱ ወዲያውኑ ይላክልዎታል።"
    if lang == "or": msg = "🙏 Lakkoofsi herrega keessanii galmeeffameera. Erga mirkanaa'ee booda isiniif ergama."
    elif lang == "en": msg = "🙏 Your transaction reference has been recorded. Content will be sent after verification."
    
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    
    # ለአድሚን ማሳወቂያ መላክ
    admin_msg = f"💳 **አዲስ የክፍያ ማረጋገጫ ቀርቧል**\n\nተጠቃሚ: @{user.username} ({user.id})\nይዘት: {book['title']}\nዋጋ: {book['price']} ETB\nየቴሌብር Ref: `{tx_ref}`"
    admin_buttons = [[
        # 📌 [ዋና ማስተካከያ] ለአድሚን አፕሩቫል ፈንክሽኖች ትክክለኛውን parameters እንዲልክ ተደርጓል
        InlineKeyboardButton("✅ ክፍያውን አጽድቅ", callback_data=f"pay_app_{user.id}_{book['id']}_{tx_ref}"),
        InlineKeyboardButton("❌ ውድቅ አድርግ", callback_data=f"pay_rej_{user.id}_{book['id']}")
    ]]
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, reply_markup=InlineKeyboardMarkup(admin_buttons), parse_mode="Markdown")
    return ConversationHandler.END


# =====================================================================
# 🔄 አጠቃላይ የመልዕክት ማስተናገጃ (GENERAL MESSAGE HANDLER)
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

    # 📌 የእኔ ላይብረሪ አዝራሮች መቆጣጠሪያ
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

    # 📌 ለዋና ዋና ምድቦች የቀጥታ አዝራሮች (Handouts, Notes, Question Bank)
    db_category = None
    if text in ["📄 ማጠቃለያዎች/Handouts", "📄 Qorannooslee/Handouts", "📄 Handouts", "📄 ማጠቃለያዎች (Handouts)", "📄 Qorannooslee (Handouts)"]:
        db_category = "Handouts"
    elif text in ["📁 ማስታወሻዎች", "📁 Hubannoo/Notes", "📁 Notes", "📁 ማስታወሻዎች (Notes)", "📁 Hubannoo (Notes)"]:
        db_category = "Notes"
    elif text in ["📝 የጥያቄ ባንክ", "📝 Baankii Gaaffii", "📝 Question Bank", "📝 የጥያቄ ባንክ (Question Bank)", "📝 Baankii Gaaffii (Question Bank)"]:
        db_category = "QuestionBank"
    # 📌 ንዑስ የመጽሐፍ ምድቦች ማጣሪያ
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

    # 📌 በስም በቀጥታ ሲፈልጉ (Exact matching)
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
# 💳 የክፍያ እና የአድሚን ውሳኔዎች ማስተናገጃ (CALLBACK QUERY HANDLER)
# =====================================================================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)

    # 📌 [Security Fix #2] የአድሚን-ብቻ ድርጊቶችን ADMIN_ID ካልሆነ ሰው መከልከል
    # (ከዚህ በፊት callback_data ራሱ ላይ ምንም ማረጋገጫ አልነበረውም — ማንኛውም ሰው
    # callback_data ቢገምት/ቢፈብርክ ራሱን አድሚን አስመስሎ ክፍያ/ይዘት/ደራሲ ማጽደቅ ይችል ነበር)
    ADMIN_ONLY_PREFIXES = (
        "pay_app_", "pay_rej_",
        "approve_book_", "reject_book_",
        "approve_auth_", "reject_auth_",
    )
    if data.startswith(ADMIN_ONLY_PREFIXES) and user_id != ADMIN_ID:
        await query.answer("⛔ ይህንን ድርጊት ለመፈጸም ፈቃድ የለዎትም።", show_alert=True)
        return

    await query.answer()
    
    # --- የክፍያ ፍሰት ማስተናገጃ ---
    if data.startswith("buy_"):
        row_id = data.split("_")[1]
        book = db.get_content_by_id(row_id)
        
        if book:
            # 📌 የ0 ብር (ነፃ) ከሆነ ፋይሉን በቀጥታ ይላክ
            if book['price'] <= 0:
                db.add_order(user_id, book['id'], 0, payment_ref="FREE_DOWNLOAD", status="approved")
                try:
                    file_path = book['file_path']
                    if os.path.exists(file_path):
                        if lang == "am": await context.bot.send_message(chat_id=user_id, text=f"✅ ይዘቱ ወደ '📁 የእኔ ላይብረሪ' ተጨምሯል። ፋይሉ እነሆ፦")
                        elif lang == "or": await context.bot.send_message(chat_id=user_id, text=f"✅ Kuusaa keessanitti dabalamuun, ፋይሉ ተልኳል፦")
                        else: await context.bot.send_message(chat_id=user_id, text=f"✅ Saved to your library. Here is your file:")
                        
                        async with aiofiles.open(file_path, 'rb') as f:
                            file_data = await f.read()
                        await context.bot.send_document(chat_id=user_id, document=file_data, filename=os.path.basename(file_path))
                    else:
                        if lang == "am": await context.bot.send_message(chat_id=user_id, text="❌ ይቅርታ፣ የይዘቱ ፋይል በሲስተሙ ላይ አልተገኘም።")
                        else: await context.bot.send_message(chat_id=user_id, text="❌ Sorry, the file was not found on the server.")
                except Exception as e:
                    logging.error(f"Error sending free file: {e}")
                return

            # 📌 የሚከፈልበት ከሆነ የቴሌብር መረጃ መስጠት
            pay_msg = (
                f"💳 **የክፍያ መመሪያ ({book['title']})**\n\n"
                f"እባክዎ **{book['price']} ETB** ወደሚከተለው የቴሌብር (telebirr) ሂሳብ ያስገቡ፦\n\n"
                f"📱 **የስልክ ቁጥር:** `0947843445`\n"
                f"👤 **የአካውንት ስም:** `Dawit Megersa`\n\n"
                f"ክፍያውን ከፈጸሙ በኋላ የደረሰኝ ቁጥሩን (Transaction ID/Ref) ለመላክ ከታች ያለውን አዝራር ይጫኑ፦"
            )
            # 📌 [ዋና ማስተካከያ] submit_ref_ በትክክል የመጽሐፉን ID እንዲይዝ ኢንዴክስ 2 ላይ እናስቀምጠዋለን
            inline_kb = [[InlineKeyboardButton("📩 የደረሰኝ ቁጥር (Ref) አስገባ", callback_data=f"submit_ref_{book['id']}")]]
            await context.bot.send_message(chat_id=user_id, text=pay_msg, reply_markup=InlineKeyboardMarkup(inline_kb), parse_mode="Markdown")

    elif data.startswith("submit_ref_"):
        book_id = data.split("_")[2]
        context.user_data['buying_book_id'] = book_id
        msg = "✍️ እባክዎ የቴሌብር የግብይት መለያ ቁጥሩን (Transaction Ref Number) እዚህ ይጻፉልን፦"
        if lang == "or": msg = "✍️ Maaloo lakkoofsa heeregaa (Ref) barreessi፦"
        elif lang == "en": msg = "✍️ Please type the Transaction Ref number here:"
        await context.bot.send_message(chat_id=user_id, text=msg)
        return AWAITING_TELEBIRR_REF

    elif data.startswith("download_"):
        content_id = data.split("_")[1]
        book = db.get_content_by_id(content_id)

        # 📌 [Security Fix #3] ይህን ይዘት በትክክል መግዛቱን (ወይም ነፃ መሆኑን) ካላረጋገጥን
        # በስተቀር አንልክም — ከዚህ በፊት content_id ብቻ የሚያውቅ ማንኛውም ሰው ሳይከፍል
        # ማውረድ ይችል ነበር
        if book and not db.user_owns_content(user_id, content_id):
            no_access_msg = "❌ ይህንን ይዘት አልገዙትም፣ ስለዚህ ማውረድ አይችሉም።"
            if lang == "or": no_access_msg = "❌ Isin qabiyyee kana hin bitanne, kanaaf buufachuu hin dandeessan."
            elif lang == "en": no_access_msg = "❌ You haven't purchased this item, so you can't download it."
            await context.bot.send_message(chat_id=user_id, text=no_access_msg)
            return

        if book and os.path.exists(book['file_path']):
            async with aiofiles.open(book['file_path'], 'rb') as f:
                file_data = await f.read()
            await context.bot.send_document(chat_id=user_id, document=file_data, filename=os.path.basename(book['file_path']), caption=f"📥 {book['title']}")

    # --- 👑 አድሚን ክፍያ ሲያጸድቅ (Approve Payment) ---
    elif data.startswith("pay_app_"):
        parts = data.split("_")
        target_uid = int(parts[2])
        book_id = int(parts[3])
        tx_ref = parts[4]
        
        db.approve_payment(target_uid, book_id, tx_ref)
        
        await query.edit_message_text(text="✅ ክፍያው ተረጋግጧል፣ ፋይሉ ለተጠቃሚው ተልኳል።")
        
        book = db.get_content_by_id(book_id)
        if book and os.path.exists(book['file_path']):
            await context.bot.send_message(chat_id=target_uid, text="✅ ክፍያዎ በአድሚን ተረጋግጧል! ያዘዙት ይዘት ከታች ተልኮልዎታል።")
            async with aiofiles.open(book['file_path'], 'rb') as f:
                file_data = await f.read()
            await context.bot.send_document(chat_id=target_uid, document=file_data, filename=os.path.basename(book['file_path']))

    # --- 👑 አድሚን ክፍያ ውድቅ ሲያደርግ (Reject Payment) ---
    elif data.startswith("pay_rej_"):
        target_uid = int(data.split("_")[2])
        book_id = int(data.split("_")[3])
        
        db.reject_payment(target_uid, book_id)
        
        await query.edit_message_text(text="❌ ክፍያው ውድቅ ተደርጓል።")
        await context.bot.send_message(chat_id=target_uid, text="❌ ያስገቡት የክፍያ ማረጋገጫ ቁጥር ትክክል ባለመሆኑ በአድሚን ውድቅ ተደርጓል። እባክዎ እንደገና በትክክል ያስገቡ።")

    # --- 👑 አድሚን መጽሐፍ ሲያጸድቅ (Approve Content) ---
    elif data.startswith("approve_book_"):
        book_id = data.split("_")[2]
        res = db.approve_content(book_id)
        
        await query.edit_message_caption(caption="✅ ይዘቱ በተሳካ ሁኔታ ጽድቋል! አሁን ለሁሉም ተጠቃሚዎች ይታያል።", reply_markup=None)
        if res:
            author_id, book_title = res[0], res[1]
            author_lang = db.get_user_lang(author_id)
            if author_lang == "am": auth_msg = f"🎉 እንኳን ደስ አለዎት! '{book_title}' የተሰኘው ይዘትዎ በአድሚን ተገምግሞ ጽድቋል።"
            elif author_lang == "or": auth_msg = f"🎉 Baga gammaddan! Qabiyyee keessan '{book_title}' adminiin mirkanaayeera."
            else: auth_msg = f"🎉 Congratulations! Your content '{book_title}' has been approved by the admin."
            try: await context.bot.send_message(chat_id=author_id, text=auth_msg)
            except: pass

    # --- 👑 አድሚን መጽሐፍ ሲያቀረቅር/ሲከለክል (Reject Content) ---
    elif data.startswith("reject_book_"):
        book_id = data.split("_")[2]
        res = db.reject_content(book_id)
        
        await query.edit_message_caption(caption="❌ ይዘቱ ውድቅ (Rejected) ተደርጓል።", reply_markup=None)
        if res:
            author_id, book_title = res[0], res[1]
            author_lang = db.get_user_lang(author_id)
            if author_lang == "am": auth_msg = f"😔 ይቅርታ፣ '{book_title}' የተሰኘው ይዘትዎ በሕግና ደንብ ምክንያት በአድሚን ውድቅ ተደርጓል።"
            elif author_lang == "or": auth_msg = f"😔 Gammachuun, qabiyyee keessan '{book_title}' adminiin fudhatama hin arganne."
            else: auth_msg = f"😔 Sorry, your content '{book_title}' has been rejected by the admin."
            try: await context.bot.send_message(chat_id=author_id, text=auth_msg)
            except: pass

    # --- 👑 አድሚን ደራሲ ሲያጸድቅ ---
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

    # --- 👑 አድሚን ደራሲ ሲከለክል ---
    elif data.startswith("reject_auth_"):
        target_user_id = data.split("_")[2]
        db.reject_author(target_user_id)
        await query.edit_message_text(text="❌ የደራሲነት ጥያቄው ውድቅ ተደርጓል።", reply_markup=None)
        return ConversationHandler.END


# =====================================================================
# 🏁 ዋናው የማስነሻ ክፍል (MAIN FUNCTION)
# =====================================================================
def main():
    # 'files' ፎልደር በፕሮጀክቱ ማውጫ ውስጥ መኖሩን ማረጋገጥ፣ ከሌለ መፍጠር።
    if not os.path.exists('files'):
        os.makedirs('files')
        logging.info("📁 'files' የተባለው ፎልደር በራስ-ሰር በተሳካ ሁኔታ ተፈጥሯል።")

    db.init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    
    # 🔍 የፍለጋ መቆጣጠሪያ ፍሰት (Search Conversation) - r"" የሪጅክስ ቅንፎችን ስህተት ይከላከላል
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
    
    print("Kitab Bot (ያልተቀነሰ እና ሙሉ በሙሉ ራሱን የቻለ) በተሳካ ሁኔታ ተነስቷል...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
