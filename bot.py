from telegram import (
    Update,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from database import (
    init_db,
    save_user,
    set_language,
    get_contents_by_category,
    seed_sample_data
)
from config import BOT_TOKEN

# 1. የቋንቋ መምረጫ ኪቦርድ
LANGUAGE_KEYBOARD = ReplyKeyboardMarkup(
    [["🇪🇹 አማርኛ"], ["🌳 Afaan Oromoo"], ["🇬🇧 English"]],
    resize_keyboard=True
)

# 2. የዋና ሜኑ ቁልፎች በ3ቱም ቋንቋ
MAIN_MENU_AM = ReplyKeyboardMarkup(
    [
        ["📚 መጻሕፍት", "📄 ማጠቃለያዎች/Handouts"],
        ["📝 የጥያቄ ባንክ", "📒 ማስታወሻዎች"],
        ["🔍 ፈልግ (Search)", "📂 የእኔ ላይብረሪ"],
        ["✍️ ደራሲ መሆን እፈልጋለሁ", "☎️ እርዳታ"]
    ],
    resize_keyboard=True
)

MAIN_MENU_OM = ReplyKeyboardMarkup(
    [
        ["📚 Kitaabota", "📄 Qorannooslee/Handouts"],
        ["📝 Baankii Gaaffii", "📒 Hubannoo/Notes"],
        ["🔍 Barbaadi (Search)", "📂 Kuusaa Koo"],
        ["✍️ Barreessaa Ta'uu", "☎️ Gargaarsa"]
    ],
    resize_keyboard=True
)

MAIN_MENU_EN = ReplyKeyboardMarkup(
    [
        ["📚 Books", "📄 Handouts"],
        ["📝 Question Banks", "📒 Notes"],
        ["🔍 Search", "📂 My Library"],
        ["✍️ Become an Author", "☎️ Help"]
    ],
    resize_keyboard=True
)

# 3. የካቴጎሪ ምርጫ ቁልፎች በ3ቱም ቋንቋ (Phase 2)
CATEGORIES_AM = ReplyKeyboardMarkup(
    [
        ["📖 ስነ-ጽሁፍ (Literature)", "🎓 ትምህርት (Education)"],
        ["የሃይማኖት (Religion)", "📜 ታሪክ (History)"],
        ["💼 ንግድ (Business)", "💻 ቴክኖሎጂ (Technology)"],
        ["🔙 ወደ ዋናው ማውጫ"]
    ],
    resize_keyboard=True
)

CATEGORIES_OM = ReplyKeyboardMarkup(
    [
        ["📖 Og-barruu (Literature)", "🎓 Barnoota (Education)"],
        ["Amantiikaa (Religion)", "📜 Seenaa (History)"],
        ["💼 Daldala (Business)", "💻 Teeknoolojii (Technology)"],
        ["🔙 Gara Menuu Gurguddaatti"]
    ],
    resize_keyboard=True
)

CATEGORIES_EN = ReplyKeyboardMarkup(
    [
        ["📖 Literature", "🎓 Education"],
        ["Religion", "History"],
        ["💼 Business", "💻 Technology"],
        ["🔙 Back to Main Menu"]
    ],
    resize_keyboard=True
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id, user.username, user.first_name)

    await update.message.reply_text(
        "📚 Welcome to Kitab\n\nPlease select your language:\n\n"
        "እንኳን ወደ ክታብ በደህና መጡ! እባክዎ ቋንቋ ይምረጡ፦\n\n"
        "Baga Gara Kitab Dhuftan! Maaloo afaan keessan filadha፦",
        reply_markup=LANGUAGE_KEYBOARD
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    # --- ሀ. የቋንቋ ምርጫ አያያዝ ---
    if text == "🇪🇹 አማርኛ":
        set_language(user_id, "am")
        await update.message.reply_text("ወደ ዋናው ማውጫ እንኳን በደህና መጡ!", reply_markup=MAIN_MENU_AM)
        return
    elif text == "🌳 Afaan Oromoo":
        set_language(user_id, "om")
        await update.message.reply_text("Gara menuu gurguddaatti baga nagaan dhuftan!", reply_markup=MAIN_MENU_OM)
        return
    elif text == "🇬🇧 English":
        set_language(user_id, "en")
        await update.message.reply_text("Welcome to the Main Menu!", reply_markup=MAIN_MENU_EN)
        return

    # --- ለ. ወደ ዋና ሜኑ መመለሻ ቁልፎች ---
    if text in ["🔙 ወደ ዋናው ማውጫ", "🔙 Gara Menuu Gurguddaatti", "🔙 Back to Main Menu"]:
        if text == "🔙 ወደ ዋናው ማውጫ":
            await update.message.reply_text("ወደ ዋናው ማውጫ ተመልሰዋል፦", reply_markup=MAIN_MENU_AM)
        elif text == "🔙 Gara Menuu Gurguddaatti":
            await update.message.reply_text("Gara menuu gurguddaatti debi'aniሩ፦", reply_markup=MAIN_MENU_OM)
        else:
            await update.message.reply_text("Returned to Main Menu:", reply_markup=MAIN_MENU_EN)
        return

    # --- ሐ. ከዋናው ሜኑ 'መጻሕፍት' ሲመረጥ ---
    if text in ["📚 መጻሕፍት", "📚 Kitaabota", "📚 Books"]:
        if text == "📚 መጻሕፍት":
            reply_markup = CATEGORIES_AM
            msg = "እባክዎ ማየት የሚፈልጉትን የይዘት ዘርፍ (Category) ይምረጡ፦"
        elif text == "📚 Kitaabota":
            reply_markup = CATEGORIES_OM
            msg = "Maaloo gosa kitaboota arguu barbaaddan filadha፦"
        else:
            reply_markup = CATEGORIES_EN
            msg = "Please select a category:"
            
        await update.message.reply_text(msg, reply_markup=reply_markup)
        return

    # --- መ. ካቴጎሪ ሲመረጥ በውስጡ ያሉትን መጻሕፍት ማሳየት ---
    if text in ["📖 ስነ-ጽሁፍ (Literature)", "📖 Og-barruu (Literature)", "📖 Literature"]:
        books = get_contents_by_category("book", "Literature")
        
        if not books:
            msg_empty = "በዚህ ዘርፍ በአሁኑ ሰዓት የተመዘገበ መጽሐፍ የለም።"
            if text == "📖 Og-barruu (Literature)":
                msg_empty = "Gosa kanaan kitabni galmaa'e hin jiru."
            elif text == "📖 Literature":
                msg_empty = "No books found in this category."
            await update.message.reply_text(msg_empty)
            return
            
        for book in books:
            # የእያንዳንዱን መጽሐፍ ዝርዝር እንደየቋንቋው ማሳየት
            if text == "📖 ስነ-ጽሁፍ (Literature)":
                detail_text = (
                    f"📚 **ርዕስ:** {book['title']}\n"
                    f"✍️ **ደራሲ:** Sample Author\n"
                    f"💰 **ዋጋ:** {book['price']} ETB\n"
                    f"📝 **መግለጫ:** {book['description']}\n\n"
                    f"🛒 ለመግዛት በቅርቡ የሚዘረጋውን የክፍያ ስርአት ይጠቀሙ።"
                )
            elif text == "📖 Og-barruu (Literature)":
                detail_text = (
                    f"📚 **Mata-duree:** {book['title']}\n"
                    f"✍️ **Barreessaa:** Sample Author\n"
                    f"💰 **Gatii:** {book['price']} ETB\n"
                    f"📝 **Ibsa:** {book['description']}\n\n"
                    f"🛒 Bitachuuf sirna kaffaltii dhiheenyatti falamu fayyadamaa."
                )
            else:
                detail_text = (
                    f"📚 **Title:** {book['title']}\n"
                    f"✍️ **Author:** Sample Author\n"
                    f"💰 **Price:** {book['price']} ETB\n"
                    f"📝 **Description:** {book['description']}\n\n"
                    f"🛒 Use the upcoming payment system to buy."
                )
            await update.message.reply_text(detail_text, parse_mode="Markdown")
        return

    # ለቀሩት ክፍሎች ጊዜያዊ ምላሽ
    if text in ["📄 ማጠቃለያዎች/Handouts", "📄 Qorannooslee/Handouts", "📄 Handouts", 
                "📝 የጥያቄ ባንክ", "📝 Baankii Gaaffii", "📝 Question Banks", 
                "📒 ማስታወሻዎች", "📒 Hubannoo/Notes", "📒 Notes"]:
        await update.message.reply_text(f"'{text}' ⏳...")
        return

    await update.message.reply_text("እባክዎ የሜኑ ቁልፎችን ይጠቀሙ / Please use the menu buttons.")

def main():
    init_db()
    try:
        seed_sample_data()
    except Exception:
        pass 

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Kitab Bot በ 3ቱም ቋንቋዎች በተሳካ ሁኔታ ተነስቷል...")
    app.run_polling()

if __name__ == "__main__":
    main()
