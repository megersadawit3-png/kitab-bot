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
    set_language
)
from config import BOT_TOKEN

# 1. የቋንቋ መምረጫ ኪቦርድ
LANGUAGE_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🇪🇹 አማርኛ"],
        ["🌳 Afaan Oromoo"],
        ["🇬🇧 English"]
    ],
    resize_keyboard=True
)

# 2. የዋና ሜኑ ቁልፎች በየቋንቋው (የስፔሲፊኬሽኑ 8 ቁልፎች)
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # ተጠቃሚውን በዳታቤዝ ውስጥ መመዝገብ
    save_user(
        user.id,
        user.username,
        user.first_name
    )

    await update.message.reply_text(
        "📚 Welcome to Kitab\n\nPlease select your language:\n\nእንኳን ወደ ክታብ በደህና መጡ! እባክዎ ቋንቋ ይምረጡ፦",
        reply_markup=LANGUAGE_KEYBOARD
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    # --- ሀ. የቋንቋ ምርጫ አያያዝ ---
    if text == "🇪🇹 አማርኛ":
        set_language(user_id, "am")
        await update.message.reply_text(
            "ቋንቋ መረጣዎ ተስተካክሏል። ወደ ዋናው ማውጫ እንኳን በደህና መጡ! ምን ማየት ይፈልጋሉ?",
            reply_markup=MAIN_MENU_AM
        )
        return

    elif text == "🌳 Afaan Oromoo":
        set_language(user_id, "om")
        await update.message.reply_text(
            "Filannoon afaan keessanii sirreeffameera. Gara gara fulduratti baga nagaan dhuftan! Maal arguu barbaaddu?",
            reply_markup=MAIN_MENU_OM
        )
        return

    elif text == "🇬🇧 English":
        set_language(user_id, "en")
        await update.message.reply_text(
            "Language selection saved. Welcome to the Main Menu! What would you like to explore?",
            reply_markup=MAIN_MENU_EN
        )
        return

    # --- ለ. የዋና ሜኑ ቁልፎች ምላሽ (ለሙከራ ያህል) ---
    # አማርኛ ሜኑ
    if text in ["📚 መጻሕፍት", "📄 ማጠቃለያዎች/Handouts", "📝 የጥያቄ ባንክ", "📒 ማስታወሻዎች", "🔍 ፈልግ (Search)", "📂 የእኔ ላይብረሪ", "✍️ ደራሲ መሆን እፈልጋለሁ", "☎️ እርዳታ"]:
        await update.message.reply_text(f"እሺ፣ '{text}' የሚለውን መርጠሃል። ይህ ክፍል በPhase 2 እና Phase 3 ላይ ሙሉ በሙሉ ይሰራል።")
        return

    # Afaan Oromoo Menu
    elif text in ["📚 Kitaabota", "📄 Qorannooslee/Handouts", "📝 Baankii Gaaffii", "📒 Hubannoo/Notes", "🔍 Barbaadi (Search)", "📂 Kuusaa Koo", "✍️ Barreessaa Ta'uu", "☎️ Gargaarsa"]:
        await update.message.reply_text(f"Tole, '{text}' filatteetta. Kutaan kun Phase 2 fi Phase 3 keessatti ni hojjedha.")
        return

    # English Menu
    elif text in ["📚 Books", "📄 Handouts", "📝 Question Banks", "📒 Notes", "🔍 Search", "📂 My Library", "✍️ Become an Author", "☎️ Help"]:
        await update.message.reply_text(f"You selected '{text}'. This section will be functional in Phase 2 & Phase 3.")
        return

    # ሌሎች ያልታወቁ ፅሁፎች ከመጡ
    await update.message.reply_text("እባክዎ ከታች ካሉት አማራጮች አንዱን ይምረጡ።\nPlease use the menu buttons below.")

def main():
    # ዳታቤዙን መጀመሪያ ማስነሳት
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    
    # ሁሉንም የፅሁፍ መልዕክቶች በአንድ ላይ የሚይዝ ሀንድለር
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Kitab Bot በተሳካ ሁኔታ ተነስቷል... በመስራት ላይ ነው!")
    app.run_polling()

if __name__ == "__main__":
    main()
