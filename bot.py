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


LANGUAGE_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🇪🇹 አማርኛ"],
        ["🌳 Afaan Oromoo"],
        ["🇬🇧 English"]
    ],
    resize_keyboard=True
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    save_user(
        user.id,
        user.username,
        user.first_name
    )

    await update.message.reply_text(
        "📚 Welcome to Kitab\n\nPlease select your language:",
        reply_markup=LANGUAGE_KEYBOARD
    )


async def language_selected(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text

    if text == "🇪🇹 አማርኛ":

        set_language(update.effective_user.id, "am")

        await update.message.reply_text(
            "እንኳን ወደ ክታብ በደህና መጡ!"
        )

    elif text == "🌳 Afaan Oromoo":

        set_language(update.effective_user.id, "om")

        await update.message.reply_text(
            "Baga gara Kitab dhuftan!"
        )

    elif text == "🇬🇧 English":

        set_language(update.effective_user.id, "en")

        await update.message.reply_text(
            "Welcome to Kitab!"
        )


def main():

    init_db()

    app = Application.builder().token(
        BOT_TOKEN
    ).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT,
            language_selected
        )
    )

    app.run_polling()


if __name__ == "__main__":
    main()
