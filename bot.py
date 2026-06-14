import logging
import sqlite3
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler
)
from config import BOT_TOKEN, DB_NAME
import database

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

AWAITING_BIO, AWAITING_PHONE = range(2)

# =====================================================================
# ⌨️ የሁሉም ቋንቋዎች ኪቦርዶች (KEYBOARDS)
# =====================================================================
lang_keyboard = [["🇪🇹 አማርኛ", "🌳 Afaan Oromoo", "🇬🇧 English"]]

# --- የአማርኛ ኪቦርዶች ---
am_main_keyboard = [
    ["📚 መጻሕፍት", "📄 ማጠቃለያዎች/Handouts"],
    ["📝 የጥያቄ ባንክ", "📁 ማስታወሻዎች"],
    ["🔍 ፈልግ (Search)", "📁 የእኔ ላይብረሪ"],
    ["✍️ ደራሲ መሆን እፈልጋለሁ", "☎️ እርዳታ"]
]
am_cat_keyboard = [
    ["📖 ስነ-ጽሁፍ (Literature)", "🎓 ትምህርት (Education)"],
    ["📖 ሃይማኖት (Religion)", "📜 ታሪክ (History)"],
    ["💼 ንግድ (Business)", "💻 ቴክኖሎጂ (Technology)"],
    ["⬅️ ወደ ዋናው ማውጫ"]
]

# --- የኦሮሚኛ ኪቦርዶች ---
or_main_keyboard = [
    ["📚 Kitaabota", "📄 Qorannooslee/Handouts"],
    ["📝 Baankii Gaaffii", "📁 Hubannoo/Notes"],
    ["🔍 Barbaadi (Search)", "📁 Kuusaa Koo"],
    ["✍️ Barreessaa Ta'uu", "☎️ Gargaarsa"]
]
or_cat_keyboard = [
    ["📖 Og-barruu (Literature)", "🎓 Barnoota (Education)"],
    ["📖 Amantiikaa (Religion)", "📜 Seenaa (History)"],
    ["💼 Daldala (Business)", "💻 Teeknoolojii (Technology)"],
    ["⬅️ Gara Menuu Gurguddaatti"]
]

# --- የእንግሊዘኛ ኪቦርዶች ---
en_main_keyboard = [
    ["📚 Books", "📄 Handouts"],
    ["📝 Question Bank", "📁 Notes"],
    ["🔍 Search", "📁 My Library"],
    ["✍️ Become an Author", "☎️ Help"]
]
en_cat_keyboard = [
    ["📖 Literature", "🎓 Education"],
    ["📖 Religion", "📜 History"],
    ["💼 Business", "💻 Technology"],
    ["⬅️ Back to Main Menu"]
]


# --- የቦቱ መጀመሪያ /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    database.save_user(user.id, user.username, user.first_name)
    
    msg = (
        "📚 Welcome to Kitab\n\n"
        "Please select your language:\n\n"
        "እንኳን ወደ ኪታብ በደህና መጡ! እባክዎ ቋንቋ ይምረጡ፦\n\n"
        "Baga Gara Kitab Dhuftan! Maaloo afaan keessan filadha:-"
    )
    await update.message.reply_text(
        msg, 
        reply_markup=ReplyKeyboardMarkup(lang_keyboard, resize_keyboard=True)
    )


def get_user_lang(telegram_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT language FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "am"


# =====================================================================
# ✍️ የደራሲያን ምዝገባ ፍሰት (AUTHOR REGISTRATION FLOW)
# =====================================================================

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM authors WHERE user_id = ?", (user_id,))
    author = cursor.fetchone()
    conn.close()
    
    if author:
        if lang == "am":
            await update.message.reply_text(f"💡 እርስዎ አስቀድመው ደራሲ ሆነው ተመዝግበዋል! የፊርማዎ ሁኔታ፦ {author[0]}")
        elif lang == "or":
            await update.message.reply_text(f"💡 Isin duraan barreessaa ta'anii galmaaytaniittu! Haalli keessan: {author[0]}")
        else:
            await update.message.reply_text(f"💡 You are already registered as an author! Status: {author[0]}")
        return ConversationHandler.END

    if lang == "am":
        await update.message.reply_text(
            "👋 ወደ ደራሲያን ምዝገባ እንኳን በደህና መጡ!\n\n"
            "እባክዎን አጭር የህይወት ታሪክዎን ወይም ስለራስዎ ማብራሪያ (Biography) ይጻፉልን፦",
            reply_markup=ReplyKeyboardRemove()
        )
    elif lang == "or":
        await update.message.reply_text(
            "👋 Gara galmee barreessitootaa baga nagaan dhuftan!\n\n"
            "Maaloo seenaa keessan gabaabaan (Biography) nuu barreessaa:",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text(
            "👋 Welcome to Author Registration!\n\n"
            "Please write a short biography or description about yourself:",
            reply_markup=ReplyKeyboardRemove()
        )
    return AWAITING_BIO


async def save_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['bio'] = update.message.text
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    if lang == "am":
        phone_btn = [[KeyboardButton("📲 ስልክ ቁጥር አጋራ", request_contact=True)]]
        msg = "በጣም ጥሩ! አሁን ደግሞ ለክፍያ እና ለግንኙነት የሚሆን ስልክ ቁጥርዎን ያስገቡ (ወይም ከታች ያለውን ቁልፍ ተጭነው ያጋሩን)፦"
    elif lang == "or":
        phone_btn = [[KeyboardButton("📲 Lakkoofsa Bilbilaa Agarsiisi", request_contact=True)]]
        msg = "Gaarii dha! Amma ammoo kaffaltii fi qunnamtiidhaaf lakkoofsa bilbila keessan nuu barreessaa (ykn gadi tuquun nuu ergaa):"
    else:
        phone_btn = [[KeyboardButton("📲 Share Phone Number", request_contact=True)]]
        msg = "Great! Now please enter your phone number for payments and communication (or press the button below to share):"
        
    await update.message.reply_text(
        msg, 
        reply_markup=ReplyKeyboardMarkup(phone_btn, resize_keyboard=True, one_time_keyboard=True)
    )
    return AWAITING_PHONE


async def save_phone_and_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text
        
    bio = context.user_data.get('bio', '')
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET phone = ? WHERE telegram_id = ?", (phone, user_id))
    cursor.execute("INSERT OR IGNORE INTO authors (user_id, status, biography) VALUES (?, 'approved', ?)", (user_id, bio))
    conn.commit()
    conn.close()
    
    if lang == "am":
        await update.message.reply_text(
            "🎉 እንኳን ደስ አለዎት! የደራሲነት ምዝገባዎ በተሳካ ሁኔታ ተጠናቆ ወዲያውኑ ጸድቋል።\nአሁን መጻሕፍትዎን ማቅረብ ይችላሉ።",
            reply_markup=ReplyKeyboardMarkup(am_main_keyboard, resize_keyboard=True)
        )
    elif lang == "or":
        await update.message.reply_text(
            "🎉 Baga gammaddan! Galmeen barreessummaa keessan milkiyn xumuramee mirkanaayeera.\nAmma kitaabota keessan galchuu dandeessu.",
            reply_markup=ReplyKeyboardMarkup(or_main_keyboard, resize_keyboard=True)
        )
    else:
        await update.message.reply_text(
            "🎉 Congratulations! Your author registration was completed and approved successfully.\nNow you can submit your books.",
            reply_markup=ReplyKeyboardMarkup(en_main_keyboard, resize_keyboard=True)
        )
    return ConversationHandler.END


async def cancel_reg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    if lang == "am":
        await update.message.reply_text("ምዝገባው ተቋርጧል።", reply_markup=ReplyKeyboardMarkup(am_main_keyboard, resize_keyboard=True))
    elif lang == "or":
        await update.message.reply_text("Galmeen addaan citeera.", reply_markup=ReplyKeyboardMarkup(or_main_keyboard, resize_keyboard=True))
    else:
        await update.message.reply_text("Registration canceled.", reply_markup=ReplyKeyboardMarkup(en_main_keyboard, resize_keyboard=True))
    return ConversationHandler.END


# =====================================================================
# 🔄 አጠቃላይ የመልዕክት ማስተናገጃ (GENERAL MESSAGE HANDLER)
# =====================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    # 1. የቋንቋ ምርጫዎች
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

    # 2. የመጻሕፍት ማውጫ መክፈቻ ቁልፎች
    if text in ["📚 መጻሕፍት", "📚 Kitaabota", "📚 Books"]:
        if lang == "am":
            await update.message.reply_text("እባክዎ ማየት የሚፈልጉትን የይዘት ዘርፍ (Category) ይምረጡ፦", reply_markup=ReplyKeyboardMarkup(am_cat_keyboard, resize_keyboard=True))
        elif lang == "or":
            await update.message.reply_text("Maaloo gosa kitaboota arguu barbaaddan filadha:-", reply_markup=ReplyKeyboardMarkup(or_cat_keyboard, resize_keyboard=True))
        else:
            await update.message.reply_text("Please select the content category you want to view:", reply_markup=ReplyKeyboardMarkup(en_cat_keyboard, resize_keyboard=True))
        return
        
    # 3. ወደ ዋናው ማውጫ መመለሻ ቁልፎች
    elif text in ["⬅️ ወደ ዋናው ማውጫ", "⬅️ Gara Menuu Gurguddaatti", "⬅️ Back to Main Menu"]:
        if lang == "am":
            await update.message.reply_text("ወደ ዋናው ማውጫ ተመልሰዋል፦", reply_markup=ReplyKeyboardMarkup(am_main_keyboard, resize_keyboard=True))
        elif lang == "or":
            await update.message.reply_text("Gara menuu gurguddaatti debi'aniittu:-", reply_markup=ReplyKeyboardMarkup(or_main_keyboard, resize_keyboard=True))
        else:
            await update.message.reply_text("Returned to Main Menu:", reply_markup=ReplyKeyboardMarkup(en_main_keyboard, resize_keyboard=True))
        return

    # 4. የካቴጎሪ መፃሕፍት ማውጫ ማካተቻ (Category Mapper)
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
            if lang == "am":
                await update.message.reply_text("በዚህ ዘርፍ በአሁኑ ሰዓት የተመዘገበ መጽሐፍ የለም።")
            elif lang == "or":
                await update.message.reply_text("Gosa kanaan kitabni galmaa'e hin jiru.")
            else:
                await update.message.reply_text("There are no books registered in this category at the moment.")
            return

        for book in books:
            if lang == "am":
                caption = f"📚 ርዕስ: {book['title']}\n✍️ ደራሲ: Sample Author\n💰 ዋጋ: {book['price']} ETB\n📝 መግለጫ: {book['description']}\n\n🛒 ለመግዛት በቅርቡ የሚዘረጋውን የክፍያ ሥርዓት ይጠቀሙ።"
            elif lang == "or":
                caption = f"📚 Mata duree: {book['title']}\n✍️ Barreessaa: Sample Author\n💰 Gatii: {book['price']} ETB\n📝 ibsa: {book['description']}\n\n🛒 Bitachuuf kaffaltii dhiyeenyatti gadi lakkifamu fayyadamaa."
            else:
                caption = f"📚 Title: {book['title']}\n✍️ Author: Sample Author\n💰 Price: {book['price']} ETB\n📝 Description: {book['description']}\n\n🛒 Use the upcoming payment system to purchase."
                
            await update.message.reply_text(caption)
        return


# =====================================================================
# 🏁 ዋናው የማስነሻ ክፍል (MAIN FUNCTION)
# =====================================================================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    reg_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^(✍️ ደራሲ መሆን እፈልጋለሁ|✍️ Barreessaa Ta'uu|✍️ Become an Author)$"), start_registration)
        ],
        states={
            AWAITING_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_bio)],
            AWAITING_PHONE: [MessageHandler(filters.TEXT | filters.CONTACT, save_phone_and_finish)]
        },
        fallbacks=[CommandHandler("cancel", cancel_reg)]
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(reg_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Kitab Bot በ 3ቱም ቋንቋዎች (አማርኛ፣ ኦሮሚኛ፣ እንግሊዘኛ) በተሳካ ሁኔታ ተነስቷል...")
    app.run_polling()

if __name__ == "__main__":
    main()
