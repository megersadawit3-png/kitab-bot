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

# á‹¨áˆŽáŒ áˆ›áˆµá‰°áŠ«áŠ¨á‹«
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# =====================================================================
# ðŸ”„ á‹¨á‹á‹­á‹­á‰µ áˆ˜á‰†áŒ£áŒ áˆªá‹« á‹°áˆ¨áŒƒá‹Žá‰½ (CONVERSATION STATES)
# =====================================================================
AWAITING_BIO, AWAITING_PHONE = range(2)
AWAITING_TITLE, AWAITING_CATEGORY, AWAITING_DESC, AWAITING_PRICE, AWAITING_FILE = range(10, 15)
AWAITING_SEARCH_QUERY = range(20, 21)
AWAITING_TELEBIRR_REF = range(30, 31)

# =====================================================================
# âŒ¨ï¸ á‹¨áˆáˆ‰áˆ á‰‹áŠ•á‰‹á‹Žá‰½ áŠªá‰¦áˆ­á‹¶á‰½ (KEYBOARDS)
# =====================================================================
lang_keyboard = [["ðŸ‡ªðŸ‡¹ áŠ áˆ›áˆ­áŠ›", "ðŸŒ³ Afaan Oromoo", "ðŸ‡¬ðŸ‡§ English"]]

am_main_keyboard = [
    ["ðŸ“š áˆ˜áŒ»áˆ•áá‰µ", "ðŸ“„ áˆ›áŒ á‰ƒáˆˆá‹«á‹Žá‰½/Handouts"],
    ["ðŸ“ á‹¨áŒ¥á‹«á‰„ á‰£áŠ•áŠ­", "ðŸ“ áˆ›áˆµá‰³á‹ˆáˆ»á‹Žá‰½"],
    ["ðŸ” áˆáˆáŒ (Search)", "ðŸ“ á‹¨áŠ¥áŠ” áˆ‹á‹­á‰¥áˆ¨áˆª"],
    ["âœï¸ á‹°áˆ«áˆ² áˆ˜áˆ†áŠ• áŠ¥áˆáˆáŒ‹áˆˆáˆ", "âž• áŠ á‹²áˆµ á‹­á‹˜á‰µ áŠ áŠ­áˆ", "â˜Žï¸ áŠ¥áˆ­á‹³á‰³"]
]
am_cat_keyboard = [
    ["ðŸ“– áˆµáŠ-áŒ½áˆá (Literature)", "ðŸŽ“ á‰µáˆáˆ…áˆ­á‰µ (Education)"],
    ["ðŸ“– áˆƒá‹­áˆ›áŠ–á‰µ (Religion)", "ðŸ“œ á‰³áˆªáŠ­ (History)"],
    ["ðŸ’¼ áŠ•áŒá‹µ (Business)", "ðŸ’» á‰´áŠ­áŠ–áˆŽáŒ‚ (Technology)"],
    ["ðŸ“„ áˆ›áŒ á‰ƒáˆˆá‹«á‹Žá‰½ (Handouts)", "ðŸ“ áˆ›áˆµá‰³á‹ˆáˆ»á‹Žá‰½ (Notes)"],
    ["ðŸ“ á‹¨áŒ¥á‹«á‰„ á‰£áŠ•áŠ­ (Question Bank)", "â¬…ï¸ á‹ˆá‹° á‹‹áŠ“á‹ áˆ›á‹áŒ«"]
]

or_main_keyboard = [
    ["ðŸ“š Kitaabota", "ðŸ“„ Qorannooslee/Handouts"],
    ["ðŸ“ Baankii Gaaffii", "ðŸ“ Hubannoo/Notes"],
    ["ðŸ” Barbaadi (Search)", "ðŸ“ Kuusaa Koo"],
    ["âœï¸ Barreessaa Ta'uu", "âž• Kitaaba Haaraa Gali", "â˜Žï¸ Gargaarsa"]
]
or_cat_keyboard = [
    ["ðŸ“– Og-barruu (Literature)", "ðŸŽ“ Barnoota (Education)"],
    ["ðŸ“– Amantiikaa (Religion)", "ðŸ“œ Seenaa (History)"],
    ["ðŸ’¼ Daldala (Business)", "ðŸ’» Teeknoolojii (Technology)"],
    ["ðŸ“„ Qorannooslee (Handouts)", "ðŸ“ Hubannoo (Notes)"],
    ["ðŸ“ Baankii Gaaffii (Question Bank)", "â¬…ï¸ Gara Menuu Gurguddaatti"]
]

en_main_keyboard = [
    ["ðŸ“š Books", "ðŸ“„ Handouts"],
    ["ðŸ“ Question Bank", "ðŸ“ Notes"],
    ["ðŸ” Search", "ðŸ“ My Library"],
    ["âœï¸ Become an Author", "âž• Add New Book", "â˜Žï¸ Help"]
]
en_cat_keyboard = [
    ["ðŸ“– Literature", "ðŸŽ“ Education"],
    ["ðŸ“– Religion", "ðŸ“œ History"],
    ["ðŸ’¼ Business", "ðŸ’» Technology"],
    ["ðŸ“„ Handouts", "ðŸ“ Notes"],
    ["ðŸ“ Question Bank", "â¬…ï¸ Back to Main Menu"]
]

# =====================================================================
# ðŸš€ á‹¨áŒ¥áˆª áˆ˜áŒ€áˆ˜áˆªá‹« (START COMMAND)
# =====================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.save_user_info(user.id, user.username, user.first_name)
    
    msg = (
        "ðŸ“š Welcome to Kitab\n\nPlease select your language:\n\n"
        "áŠ¥áŠ•áŠ³áŠ• á‹ˆá‹° áŠªá‰³á‰¥ á‰ á‹°áˆ…áŠ“ áˆ˜áŒ¡! áŠ¥á‰£áŠ­á‹Ž á‰‹áŠ•á‰‹ á‹­áˆáˆ¨áŒ¡á¦\n\n"
        "Baga Gara Kitab Dhuftan! Maaloo afaan keessan filadha:-"
    )
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(lang_keyboard, resize_keyboard=True))


# =====================================================================
# ðŸ‘‘ á‹¨áŠ á‹µáˆšáŠ• áˆ˜á‰†áŒ£áŒ áˆªá‹« áŠ­ááˆ (ADMIN PANEL FUNCTIONS)
# =====================================================================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("âŒ á‹­áˆ…áŠ•áŠ• á‰µá‹•á‹›á‹ áˆˆáˆ˜áŒ á‰€áˆ áˆá‰ƒá‹µ á‹¨áˆˆá‹Žá‰µáˆ!")
        return

    pending_books, pending_authors, pending_payments = db.get_pending_counts()

    msg = (
        "ðŸ‘‘ **á‹¨áŠªá‰³á‰¥ áˆ›áˆ­áŠ¬á‰µá•áˆŒáˆµ áŠ á‹µáˆšáŠ• á“áŠáˆ**\n\n"
        f"ðŸ“ á‰ áŒáˆáŒˆáˆ› áˆ‹á‹­ á‹«áˆ‰ á‹­á‹˜á‰¶á‰½/áˆ˜áŒ»áˆ•áá‰µá¡ **{pending_books}**\n"
        f"âœï¸ á‰ áŒáˆáŒˆáˆ› áˆ‹á‹­ á‹«áˆ‰ á‹°áˆ«áˆ²á‹«áŠ•á¡ **{pending_authors}**\n"
        f"ðŸ’³ áˆ›áˆ¨áŒ‹áŒˆáŒ« á‹¨áˆšáŒ á‰¥á‰ áŠ­áá‹«á‹Žá‰½á¡ **{pending_payments}**\n\n"
        "áŠ á‹²áˆµ á‹­á‹˜á‰µ á‹ˆá‹­áˆ á‹¨á‹°áˆ«áˆ²áŠá‰µ áŒ¥á‹«á‰„ áˆ²áˆ˜áŒ£ á‰¦á‰± á‰ á‰€áŒ¥á‰³ áŠ¥á‹šáˆ… á‹«á‰…áˆ­á‰¥áˆá‹Žá‰³áˆá¢"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def notify_admin_new_author(bot, user_id, username, first_name, bio, phone):
    msg = (
        "ðŸ”” **áŠ á‹²áˆµ á‹¨á‹°áˆ«áˆ²áŠá‰µ áˆ›áˆ˜áˆáŠ¨á‰» á‰€áˆ­á‰§áˆ!**\n\n"
        f"ðŸ‘¤ **áˆµáˆ:** {first_name} (@{username if username else 'á‹¨áˆˆá‹áˆ'})\n"
        f"ðŸ†” **ID:** `{user_id}`\n"
        f"ðŸ“ž **áˆµáˆáŠ­:** {phone}\n"
        f"ðŸ“ **á‹¨áˆ…á‹­á‹ˆá‰µ á‰³áˆªáŠ­:** {bio}\n"
    )
    keyboard = [
        [
            InlineKeyboardButton("âœ… áá‰€á‹µ (Approve)", callback_data=f"approve_auth_{user_id}"),
            InlineKeyboardButton("âŒ áŠ¨áˆáŠ­áˆ (Reject)", callback_data=f"reject_auth_{user_id}")
        ]
    ]
    await bot.send_message(chat_id=ADMIN_ID, text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def notify_admin_new_book(bot, book_id, title, price, file_path):
    msg = (
        "ðŸ”” **áŠ á‹²áˆµ á‹­á‹˜á‰µ áˆˆáŒáˆáŒˆáˆ› á‰€áˆ­á‰§áˆ!**\n\n"
        f"ðŸ“š **áˆ­á‹•áˆµ:** {title}\n"
        f"ðŸ’° **á‹‹áŒ‹:** {price} ETB\n\n"
        "â„¹ï¸ *áŠ¥á‰£áŠ­á‹Ž áˆ˜áŒ€áˆ˜áˆªá‹« áŠ¨áˆ‹á‹­ á‹«áˆˆá‹áŠ• á‹á‹­áˆ áŠ á‹áˆ­á‹°á‹ áŠ¨á‰°áˆ˜áˆˆáŠ¨á‰± á‰ áŠ‹áˆ‹ áŠ¨á‰³á‰½ áŠ«áˆ‰á‰µ áŠ áˆ›áˆ«áŒ®á‰½ áŠ áŠ•á‹±áŠ• á‹­áˆáˆ¨áŒ¡á¦*"
    )
    keyboard = [
        [
            InlineKeyboardButton("âœ… áá‰€á‹µ (Approve)", callback_data=f"approve_book_{book_id}"),
            InlineKeyboardButton("âŒ áŠ¨áˆáŠ­áˆ (Reject)", callback_data=f"reject_book_{book_id}")
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
                text=f"âš ï¸ á‹á‹­áˆ‰ á‰ áˆ²áˆµá‰°áˆ áˆ‹á‹­ áŠ áˆá‰°áŒˆáŠ˜áˆ áŒáŠ• á‹­á‹˜á‰± á‰°áˆ˜á‹áŒá‰§áˆá¦\náˆ­á‹•áˆµá¦ {title}", 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception as e:
        logging.error(f"Failed to send file review to admin: {e}")


# =====================================================================
# âœï¸ á‹¨á‹°áˆ«áˆ²á‹«áŠ• áˆá‹áŒˆá‰£ ááˆ°á‰µ (AUTHOR REGISTRATION FLOW)
# =====================================================================
async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    
    status = db.get_author_application_status(user_id)

    if status:
        if status == 'approved':
            if lang == "am": await update.message.reply_text("ðŸ’¡ áŠ¥áˆ­áˆµá‹Ž áŠ áˆµá‰€á‹µáˆ˜á‹ á‹°áˆ«áˆ² áˆ†áŠá‹ á‰°áˆ˜á‹áŒá‰ á‹‹áˆ!")
            elif lang == "or": await update.message.reply_text("ðŸ’¡ Isin duraan barreessaa ta'anii galmaaytaniittu!")
            else: await update.message.reply_text("ðŸ’¡ You are already registered as an author!")
            return ConversationHandler.END
        elif status == 'pending':
            if lang == "am": await update.message.reply_text("â³ áˆ›áˆ˜áˆáŠ¨á‰»á‹Ž á‰ áŠ á‹µáˆšáŠ• á‰ áˆ˜áŒˆáˆáŒˆáˆ áˆ‹á‹­ áŠá‹á¤ áŠ¥á‰£áŠ­á‹Ž á‰ á‰µá‹•áŒáˆµá‰µ á‹­áŒ á‰¥á‰á¢")
            elif lang == "or": await update.message.reply_text("â³ Gafannoon keessan adminiin ilaalamaa jira, maaloo eegaa.")
            else: await update.message.reply_text("â³ Your application is under review by admin, please wait.")
            return ConversationHandler.END

    if lang == "am":
        await update.message.reply_text("ðŸ‘‹ á‹ˆá‹° á‹°áˆ«áˆ²á‹«áŠ• áˆá‹áŒˆá‰£ áŠ¥áŠ•áŠ³áŠ• á‰ á‹°áˆ…áŠ“ áˆ˜áŒ¡!\n\náŠ¥á‰£áŠ­á‹ŽáŠ• áŠ áŒ­áˆ­ á‹¨áˆ…á‹­á‹ˆá‰µ á‰³áˆªáŠ­á‹ŽáŠ• (Biography) á‹­áŒ»á‰áˆáŠ•á¦", reply_markup=ReplyKeyboardRemove())
    elif lang == "or":
        await update.message.reply_text("ðŸ‘‹ Gara galmee barreessitootaa baga nagaan dhuftan!\n\nMaaloo seenaa keessan gabaabaan (Biography) nuu barreessaa:", reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text("ðŸ‘‹ Welcome to Author Registration!\n\nPlease write a short biography about yourself:", reply_markup=ReplyKeyboardRemove())
    return AWAITING_BIO


async def save_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['bio'] = update.message.text
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    
    if lang == "am":
        phone_btn = [[KeyboardButton("ðŸ“² áˆµáˆáŠ­ á‰áŒ¥áˆ­ áŠ áŒ‹áˆ«", request_contact=True)]]
        msg = "á‰ áŒ£áˆ áŒ¥áˆ©! áŠ áˆáŠ• á‹°áŒáˆž áˆˆáŠ­áá‹« á‹¨áˆšáˆ†áŠ• áˆµáˆáŠ­ á‰áŒ¥áˆ­á‹ŽáŠ• á‹«áˆµáŒˆá‰¡ á‹ˆá‹­áˆ á‹«áŒ‹áˆ©áŠ•á¦"
    elif lang == "or":
        phone_btn = [[KeyboardButton("ðŸ“² Lakkoofsa Bilbilaa Agarsiisi", request_contact=True)]]
        msg = "Gaarii dhamma! Amma ammoo kaffaltii fi qunnamtiidhaaf lakkoofsa bilbila keessan nuu ergaa:"
    else:
        phone_btn = [[KeyboardButton("ðŸ“² Share Phone Number", request_contact=True)]]
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
        await update.message.reply_text("ðŸŽ‰ á‹¨áˆ›áˆ˜áˆáŠ¨á‰» áŽáˆ­áˆá‹Ž áˆˆáŠ á‹µáˆšáŠ• á‰°áˆáŠ³áˆ! áˆ²áŒ¸á‹µá‰… á‰ á‰¦á‰± á‰ áŠ©áˆ áˆ˜áˆá‹•áŠ­á‰µ á‹­á‹°áˆ­áˆµá‹Žá‰³áˆá¢", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    elif lang == "or":
        await update.message.reply_text("ðŸŽ‰ Gafannoon keessan adminiif ergameera! Yeroo mirkanaa'u ergaan isiniif deebi'a.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    else:
        await update.message.reply_text("ðŸŽ‰ Your application has been sent to admin! You will receive a message once approved.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return ConversationHandler.END


async def cancel_reg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    msg = "áˆá‹áŒˆá‰£á‹ á‰°á‰‹áˆ­áŒ§áˆá¢" if lang == "am" else ("Galmeen addaan citeera." if lang == "or" else "Registration canceled.")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return ConversationHandler.END


# =====================================================================
# âž• áŠ á‹²áˆµ á‹­á‹˜á‰µ áˆ›áˆµáŒˆá‰¢á‹« ááˆ°á‰µ (CONTENT UPLOAD FLOW)
# =====================================================================
async def start_book_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    
    if not db.is_user_author(user_id):
        if lang == "am": await update.message.reply_text("âŒ á‹­á‹˜á‰µ áˆˆáˆ˜áŒ«áŠ• áˆ˜áŒ€áˆ˜áˆªá‹« á‹°áˆ«áˆ² áˆ†áŠá‹ áˆ˜áˆ˜á‹áŒˆá‰¥ áŠ¥áŠ“ áˆ˜á…á‹°á‰… áŠ áˆˆá‰¥á‹Žá‰µ!")
        elif lang == "or": await update.message.reply_text("âŒ Kitaaba galchuuf jalqaba barreessaa mirkanaa'e ta'uu qabdu!")
        else: await update.message.reply_text("âŒ You must be an approved author first before uploading books!")
        return ConversationHandler.END

    if lang == "am": await update.message.reply_text("ðŸ“ áŠ¥á‰£áŠ­á‹Ž á‹¨á‹­á‹˜á‰±áŠ• áˆ­á‹•áˆµ (Title) á‹«áˆµáŒˆá‰¡á¦", reply_markup=ReplyKeyboardRemove())
    elif lang == "or": await update.message.reply_text("ðŸ“ Maaloo mata duree kitaabaa galchaa:", reply_markup=ReplyKeyboardRemove())
    else: await update.message.reply_text("ðŸ“ Please enter the title of the content:", reply_markup=ReplyKeyboardRemove())
    return AWAITING_TITLE


async def save_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['upload_title'] = update.message.text
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    
    kb = am_cat_keyboard if lang == "am" else (or_cat_keyboard if lang == "or" else en_cat_keyboard)
    msg = "áŠ¥á‰£áŠ­á‹Ž á‰°áˆµáˆ›áˆš á‹¨á‹­á‹˜á‰µ á‹˜áˆ­á (Category) á‹­áˆáˆ¨áŒ¡á¦" if lang == "am" else ("Maaloo gosa kitaabaa filadha:" if lang == "or" else "Please select the category:")
    
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return AWAITING_CATEGORY


async def save_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    
    cat_map = {
        "ðŸ“– áˆµáŠ-áŒ½áˆá (Literature)": "Literature", "ðŸ“– áˆµáŠ-áŒ½áˆ‘á (Literature)": "Literature", "ðŸ“– Og-barruu (Literature)": "Literature", "ðŸ“– Literature": "Literature",
        "ðŸŽ“ á‰µáˆáˆ…áˆ­á‰µ (Education)": "Education", "ðŸŽ“ Barnoota (Education)": "Education", "ðŸŽ“ Education": "Education",
        "ðŸ“– áˆƒá‹­áˆ›áŠ–á‰µ (Religion)": "Religion", "ðŸ“– Amantiikaa (Religion)": "Religion", "ðŸ“– Religion": "Religion",
        "ðŸ“œ á‰³áˆªáŠ­ (History)": "History", "ðŸ“œ Seenaa (History)": "History", "ðŸ“œ History": "History",
        "ðŸ’¼ áŠ•áŒá‹µ (Business)": "Business", "ðŸ’¼ Daldala (Business)": "Business", "ðŸ’¼ Business": "Business",
        "ðŸ’» á‰´áŠ­áŠ–áˆŽáŒ‚ (Technology)": "Technology", "ðŸ’» Teeknoolojii (Technology)": "Technology", "ðŸ’» Technology": "Technology",
        "ðŸ“„ áˆ›áŒ á‰ƒáˆˆá‹«á‹Žá‰½ (Handouts)": "Handouts", "ðŸ“„ Qorannooslee (Handouts)": "Handouts", "ðŸ“„ Handouts": "Handouts",
        "ðŸ“ áˆ›áˆµá‰³á‹ˆáˆ»á‹Žá‰½ (Notes)": "Notes", "ðŸ“ Hubannoo (Notes)": "Notes", "ðŸ“ Notes": "Notes",
        "ðŸ“ á‹¨áŒ¥á‹«á‰„ á‰£áŠ•áŠ­ (Question Bank)": "QuestionBank", "ðŸ“ Baankii Gaaffii (Question Bank)": "QuestionBank", "ðŸ“ Question Bank": "QuestionBank"
    }
    
    context.user_data['upload_cat'] = cat_map.get(text, "Literature")
    
    msg = "ðŸ“ áˆµáˆˆ á‹­á‹˜á‰± áŠ áŒ­áˆ­ áˆ˜áŒáˆˆáŒ« (Description) á‹­áŒ»á‰á¦" if lang == "am" else ("Maaloo ibsa kitaabaa gabaabaan barreessaa:" if lang == "or" else "Please write a short description:")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return AWAITING_DESC


async def save_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['upload_desc'] = update.message.text
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    
    msg = "ðŸ’° á‹¨áˆ˜áˆ¸áŒ« á‹‹áŒ‹ á‰ á‰¥áˆ­ (ETB) á‹«áˆµáŒˆá‰¡ (á‰ áŠáƒ áˆˆáˆ›á‰…áˆ¨á‰¥ 0 á‹«áˆµáŒˆá‰¡)á¦" if lang == "am" else ("ðŸ’° Gatii kitaabaa birriidhaan galchaa (fkn: 150):" if lang == "or" else "ðŸ’° Enter the price in ETB (Enter 0 for Free):")
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
        msg = "âŒ áŠ¥á‰£áŠ­á‹Ž á‰ á‰µáŠ­áŠ­áˆ á‰áŒ¥áˆ­ á‰¥á‰» á‹«áˆµáŒˆá‰¡á¦" if lang == "am" else ("âŒ Maaloo lakkoofsa qofa galchaa:" if lang == "or" else "âŒ Please enter a valid number only:")
        await update.message.reply_text(msg)
        return AWAITING_PRICE

    msg = "ðŸ“„ áŠ áˆáŠ• á‹¨á‹­á‹˜á‰±áŠ• PDF á‹á‹­áˆ á‹­áŒ«áŠ‘ (Upload Document)á¦" if lang == "am" else ("ðŸ“„ Amma faayilii PDF kitaabichaa ergaa:" if lang == "or" else "ðŸ“„ Now please upload the PDF file:")
    await update.message.reply_text(msg)
    return AWAITING_FILE


async def save_file_and_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    
    if not update.message.document:
        msg = "âŒ áŠ¥á‰£áŠ­á‹Ž á‹á‹­áˆ‰áŠ• áŠ¥áŠ•á‹° Document (PDF) áŠ á‹µáˆ­áŒˆá‹ á‹­áŒ«áŠ‘á‰µá¦" if lang == "am" else ("âŒ Maaloo faayilii PDF qofa ergaa:" if lang == "or" else "âŒ Please upload the file as a Document (PDF):")
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
    if lang == "am": await update.message.reply_text("ðŸŽ‰ á‹­á‹˜á‰µá‹Ž á‰ á‰°áˆ³áŠ« áˆáŠ”á‰³ á‰°áŒ­áŠ—áˆ! á‰ áŠ á‹µáˆšáŠ• á‰°áŒˆáˆáŒáˆž áˆ²áŒ¸á‹µá‰… áˆˆá‰°áŒ á‰ƒáˆšá‹Žá‰½ á‹­á‰ á‰ƒáˆá¡á¡", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    elif lang == "or": await update.message.reply_text("ðŸŽ‰ Kitaabni keessan milkiyn galeera! Erga admin mirkaneesseen booda gabaaf dhiyaata.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    else: await update.message.reply_text("ðŸŽ‰ Content uploaded successfully! It will be available after admin approval.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    
    return ConversationHandler.END


async def cancel_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    msg = "á‹¨á‹­á‹˜á‰µ áŒ­áŠá‰± á‰°á‰‹áˆ­áŒ§áˆá¢" if lang == "am" else ("Galmeen kitaabaa addaan citeera." if lang == "or" else "Upload canceled.")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return ConversationHandler.END


# =====================================================================
# ðŸ” á‹¨ááˆˆáŒ‹ áˆ¥áˆ­á‹“á‰µ (SEARCH CONVERSATION)
# =====================================================================
async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    msg = "ðŸ” áˆˆáˆ˜áˆáˆˆáŒ á‹¨áˆáˆˆáŒ‰á‰µáŠ• áˆ˜áŒ½áˆá á‹ˆá‹­áˆ á‹­á‹˜á‰µ áˆ­á‹•áˆµ (Title) á‰ áŠ¨áŠáˆ á‹ˆá‹­áˆ áˆ™áˆ‰ á‰ áˆ™áˆ‰ á‹­áŒ»á‰áˆáŠá¦" if lang == "am" else ("ðŸ” Maaloo jecha qabiyyee barbaaddan barreessaa:" if lang == "or" else "ðŸ” Please enter the title or keyword you want to search for:")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return AWAITING_SEARCH_QUERY


async def execute_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_text = update.message.text.strip()
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    
    results = db.execute_search_query(query_text)
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    
    if not results:
        msg = "âŒ á‹­á‰…áˆ­á‰³á£ á‹«á‰€áˆ¨á‰¡á‰µáŠ• á‰ƒáˆ á‹¨áˆšáˆ˜áˆµáˆ áˆáŠ•áˆ áŠ á‹­áŠá‰µ á‹­á‹˜á‰µ áŠ áˆá‰°áŒˆáŠ˜áˆá¢" if lang == "am" else ("âŒ Dardon, waan argamu hin jiru." if lang == "or" else "âŒ No matching content found.")
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return ConversationHandler.END

    for item in results:
        caption = f"ðŸ“Œ **áˆ­á‹•áˆµ:** {item['title']}\nðŸ’° **á‹‹áŒ‹:** {item['price']} ETB\nðŸ“ **áˆ˜áŒáˆˆáŒ«:** {item['description']}"
        btn_text = "ðŸ“¥ á‰ áŠáƒ áŠ á‹áˆ­á‹µ" if item['price'] <= 0 else "ðŸ’³ á‰  Chapa / Telebirr áŠ­áˆáˆ"
        if lang == "or": btn_text = "ðŸ“¥ Buufadhu" if item['price'] <= 0 else "ðŸ’³ Kaffaltii Raawwadhu"
        elif lang == "en": btn_text = "ðŸ“¥ Download" if item['price'] <= 0 else "ðŸ’³ Pay Now"
        
        inline_kb = [[InlineKeyboardButton(btn_text, callback_data=f"buy_{item['id']}")]]
        await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(inline_kb), parse_mode="Markdown")
        
    await update.message.reply_text("ðŸ” á‹¨ááˆˆáŒ‹ á‹áŒ¤á‰¶á‰½ áŠ¥áŠá‹šáˆ… áŠ“á‰¸á‹á¢", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return ConversationHandler.END


# =====================================================================
# ðŸ“ á‹¨áŠ¥áŠ” áˆ‹á‹­á‰¥áˆ¨áˆª (MY LIBRARY SYSTEM)
# =====================================================================
async def view_library(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    
    my_contents = db.get_user_library(user_id)

    if not my_contents:
        msg = "ðŸ“ á‹¨áŠ¥áˆ­áˆµá‹Ž áˆ‹á‹­á‰¥áˆ¨áˆª á‰£á‹¶ áŠá‹! áŠ¥áˆµáŠ«áˆáŠ• á‹¨áŒˆá‹™á‰µ á‹­á‹˜á‰µ á‹¨áˆˆáˆá¢" if lang == "am" else ("ðŸ“ Kuusaan keessan duwwaa dha! Hanga ammaatti waan bitattan hin jiru." if lang == "or" else "ðŸ“ Your library is empty! You haven't purchased any items yet.")
        await update.message.reply_text(msg)
        return

    msg = "ðŸ“ á‹¨áŒˆá‹Ÿá‰¸á‹ áˆ˜áŒ»áˆ•áá‰µ áŠ¥áŠ“ áˆ›áŒ á‰ƒáˆˆá‹«á‹Žá‰½ á‹áˆ­á‹áˆ­ áŠ¥áŠáˆ†á¦\náˆˆáˆ›á‹áˆ¨á‹µ á‹¨áˆšáˆáˆáŒ‰á‰µáŠ• á‹á‹­áˆ á‹­áŒ«áŠ‘á¦" if lang == "am" else ("ðŸ“ Kuusaa qabiyyee keessanii, buufachuuf cuqaasaaá¦" if lang == "or" else "ðŸ“ Here is your purchased content library. Click to download:")
    
    keyboard = []
    for item in my_contents:
        keyboard.append([InlineKeyboardButton(f"ðŸ“¥ {item['title']}", callback_data=f"download_{item['id']}")])
        
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))


# =====================================================================
# ðŸ“ž á‹¨á‰´áˆŒá‰¥áˆ­ áˆ›áŠ‘á‹‹áˆ á‹¨á‹°áˆ¨áˆ°áŠ á‰áŒ¥áˆ­ áˆ˜á‰€á‰ á‹« (PROCESS TELEBIRR REF)
# =====================================================================
async def process_telebirr_ref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tx_ref = update.message.text.strip()
    user = update.effective_user
    lang = db.get_user_lang(user.id)
    # ðŸ“Œ [á‹‹áŠ“ áˆ›áˆµá‰°áŠ«áŠ¨á‹«] submit_ref_ áˆ‹á‹­ á‹¨á‰°á‰€áˆ˜áŒ á‹áŠ• á‰ á‰µáŠ­áŠ­áˆ buying_book_id á‰¥áˆŽ á‹«áŠá‰£áˆ
    content_id = context.user_data.get('buying_book_id')
    
    kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
    
    if not content_id:
        await update.message.reply_text("âŒ Error", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return ConversationHandler.END
        
    book = db.get_content_by_id(content_id)
    if not book:
        await update.message.reply_text("âŒ Error", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return ConversationHandler.END

    db.add_order(user.id, content_id, book['price'], tx_ref, status="pending")
    
    msg = "ðŸ™ á‹¨áŒá‰¥á‹­á‰µ á‰áŒ¥áˆ­á‹Ž á‰°áˆ˜á‹áŒá‰§áˆá¢ á‰ áŠ á‹µáˆšáŠ• á‰°áˆ¨áŒ‹áŒáŒ¦ á‹­á‹˜á‰± á‹ˆá‹²á‹«á‹áŠ‘ á‹­áˆ‹áŠ­áˆá‹Žá‰³áˆá¢"
    if lang == "or": msg = "ðŸ™ Lakkoofsi herrega keessanii galmeeffameera. Erga mirkanaa'ee booda isiniif ergama."
    elif lang == "en": msg = "ðŸ™ Your transaction reference has been recorded. Content will be sent after verification."
    
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    
    # áˆˆáŠ á‹µáˆšáŠ• áˆ›áˆ³á‹ˆá‰‚á‹« áˆ˜áˆ‹áŠ­
    admin_msg = f"ðŸ’³ **áŠ á‹²áˆµ á‹¨áŠ­áá‹« áˆ›áˆ¨áŒ‹áŒˆáŒ« á‰€áˆ­á‰§áˆ**\n\ná‰°áŒ á‰ƒáˆš: @{user.username} ({user.id})\ná‹­á‹˜á‰µ: {book['title']}\ná‹‹áŒ‹: {book['price']} ETB\ná‹¨á‰´áˆŒá‰¥áˆ­ Ref: `{tx_ref}`"
    admin_buttons = [[
        # ðŸ“Œ [á‹‹áŠ“ áˆ›áˆµá‰°áŠ«áŠ¨á‹«] áˆˆáŠ á‹µáˆšáŠ• áŠ á•áˆ©á‰«áˆ áˆáŠ•áŠ­áˆ½áŠ–á‰½ á‰µáŠ­áŠ­áˆˆáŠ›á‹áŠ• parameters áŠ¥áŠ•á‹²áˆáŠ­ á‰°á‹°áˆ­áŒ“áˆ
        InlineKeyboardButton("âœ… áŠ­áá‹«á‹áŠ• áŠ áŒ½á‹µá‰…", callback_data=f"pay_app_{user.id}_{book['id']}_{tx_ref}"),
        InlineKeyboardButton("âŒ á‹á‹µá‰… áŠ á‹µáˆ­áŒ", callback_data=f"pay_rej_{user.id}_{book['id']}")
    ]]
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, reply_markup=InlineKeyboardMarkup(admin_buttons), parse_mode="Markdown")
    return ConversationHandler.END


# =====================================================================
# ðŸ”„ áŠ áŒ á‰ƒáˆ‹á‹­ á‹¨áˆ˜áˆá‹•áŠ­á‰µ áˆ›áˆµá‰°áŠ“áŒˆáŒƒ (GENERAL MESSAGE HANDLER)
# =====================================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    
    if text in lang_keyboard[0]:
        lang = "am" if "áŠ áˆ›áˆ­áŠ›" in text else ("or" if "Oromoo" in text else "en")
        db.set_user_lang(user_id, lang)
        kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
        msg = "á‹‹áŠ“ áˆ›á‹áŒ«" if lang == "am" else ("Menuu Gurguddaa" if lang == "or" else "Main Menu")
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return

    lang = db.get_user_lang(user_id)

    # ðŸ“Œ á‹¨áŠ¥áŠ” áˆ‹á‹­á‰¥áˆ¨áˆª áŠ á‹áˆ«áˆ®á‰½ áˆ˜á‰†áŒ£áŒ áˆªá‹«
    if text in ["ðŸ“ á‹¨áŠ¥áŠ” áˆ‹á‹­á‰¥áˆ¨áˆª", "ðŸ“ Kuusaa Koo", "ðŸ“ My Library"]:
        await view_library(update, context)
        return

    if text in ["ðŸ“š áˆ˜áŒ»áˆ•áá‰µ", "ðŸ“š Kitaabota", "ðŸ“š Books"]:
        kb = am_cat_keyboard if lang == "am" else (or_cat_keyboard if lang == "or" else en_cat_keyboard)
        msg = "áŠ¥á‰£áŠ­á‹Ž á‹¨á‹­á‹˜á‰µ á‹˜áˆ­á á‹­áˆáˆ¨áŒ¡á¦" if lang == "am" else ("Maaloo gosa kitaboota arguu barbaaddan filadha:-" if lang == "or" else "Please select the content category:")
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return
        
    elif text in ["â¬…ï¸ á‹ˆá‹° á‹‹áŠ“á‹ áˆ›á‹áŒ«", "â¬…ï¸ Gara Menuu Gurguddaatti", "â¬…ï¸ Back to Main Menu"]:
        kb = am_main_keyboard if lang == "am" else (or_main_keyboard if lang == "or" else en_main_keyboard)
        msg = "á‹ˆá‹° á‹‹áŠ“á‹ áˆ›á‹áŒ« á‰°áˆ˜áˆáˆ°á‹‹áˆá¦" if lang == "am" else ("Gara menuu gurguddaatti debi'aniittu:-" if lang == "or" else "Returned to Main Menu:")
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return

    # ðŸ“Œ áˆˆá‹‹áŠ“ á‹‹áŠ“ áˆá‹µá‰¦á‰½ á‹¨á‰€áŒ¥á‰³ áŠ á‹áˆ«áˆ®á‰½ (Handouts, Notes, Question Bank)
    db_category = None
    if text in ["ðŸ“„ áˆ›áŒ á‰ƒáˆˆá‹«á‹Žá‰½/Handouts", "ðŸ“„ Qorannooslee/Handouts", "ðŸ“„ Handouts", "ðŸ“„ áˆ›áŒ á‰ƒáˆˆá‹«á‹Žá‰½ (Handouts)", "ðŸ“„ Qorannooslee (Handouts)"]:
        db_category = "Handouts"
    elif text in ["ðŸ“ áˆ›áˆµá‰³á‹ˆáˆ»á‹Žá‰½", "ðŸ“ Hubannoo/Notes", "ðŸ“ Notes", "ðŸ“ áˆ›áˆµá‰³á‹ˆáˆ»á‹Žá‰½ (Notes)", "ðŸ“ Hubannoo (Notes)"]:
        db_category = "Notes"
    elif text in ["ðŸ“ á‹¨áŒ¥á‹«á‰„ á‰£áŠ•áŠ­", "ðŸ“ Baankii Gaaffii", "ðŸ“ Question Bank", "ðŸ“ á‹¨áŒ¥á‹«á‰„ á‰£áŠ•áŠ­ (Question Bank)", "ðŸ“ Baankii Gaaffii (Question Bank)"]:
        db_category = "QuestionBank"
    # ðŸ“Œ áŠ•á‹‘áˆµ á‹¨áˆ˜áŒ½áˆá áˆá‹µá‰¦á‰½ áˆ›áŒ£áˆªá‹«
    elif "Literature" in text or "áˆµáŠ-áŒ½áˆá" in text or "áˆµáŠ-áŒ½áˆ‘á" in text or "Og-barruu" in text:
        db_category = "Literature"
    elif "Education" in text or "á‰µáˆáˆ…áˆ­á‰µ" in text or "Barnoota" in text:
        db_category = "Education"
    elif "Religion" in text or "áˆƒá‹­áˆ›áŠ–á‰µ" in text or "Amantiikaa" in text:
        db_category = "Religion"
    elif "History" in text or "á‰³áˆªáŠ­" in text or "Seenaa" in text:
        db_category = "History"
    elif "Business" in text or "áŠ•áŒá‹µ" in text or "Daldala" in text:
        db_category = "Business"
    elif "Technology" in text or "á‰´áŠ­áŠ–áˆŽáŒ‚" in text or "Teeknoolojii" in text:
        db_category = "Technology"

    if db_category:
        books = db.get_contents_by_category(db_category)
        
        if not books:
            if lang == "am": msg = f"ðŸ˜” á‹­á‰…áˆ­á‰³á£ á‰ á‹šáˆ… áˆ°á‹“á‰µ á‰ '{text}' á‹˜áˆ­á á‹¨á‰°áŒ«áŠ á‹­á‹˜á‰µ á‹¨áˆˆáˆá¢"
            elif lang == "or": msg = f"ðŸ˜” Dardon, gosa kanaan '{text}' qabiyyee argamu hin jiru."
            else: msg = f"ðŸ˜” Sorry, there are no items available in the '{text}' category right now."
            await update.message.reply_text(msg)
            return

        for book in books:
            caption = f"ðŸ“Œ **áˆ­á‹•áˆµ:** {book['title']}\nðŸ’° **á‹‹áŒ‹:** {book['price']} ETB\nðŸ“ **áˆ˜áŒáˆˆáŒ«:** {book['description']}"
            btn_text = "ðŸ“¥ á‰ áŠáƒ áŠ á‹áˆ­á‹µ" if book['price'] <= 0 else "ðŸ’³ á‰  Chapa / Telebirr áŠ­áˆáˆ"
            if lang == "or": btn_text = "ðŸ“¥ Buufadhu" if book['price'] <= 0 else "ðŸ’³ Kaffaltii Raawwadhu"
            elif lang == "en": btn_text = "ðŸ“¥ Download" if book['price'] <= 0 else "ðŸ’³ Pay Now"
            
            inline_kb = [[InlineKeyboardButton(btn_text, callback_data=f"buy_{book['id']}")]]
            await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(inline_kb), parse_mode="Markdown")
        return

    # ðŸ“Œ á‰ áˆµáˆ á‰ á‰€áŒ¥á‰³ áˆ²áˆáˆáŒ‰ (Exact matching)
    book = db.get_content_by_title(text)

    if book:
        if lang == "am":
            checkout_msg = f"ðŸ›’ **á‹¨áˆ˜áŒá‹£ áˆ›áŒ á‰ƒáˆˆá‹«**\n\nðŸ“š **áˆ­á‹•áˆµ:** {book['title']}\nðŸ’° **á‹‹áŒ‹:** {book['price']} ETB\nðŸ“ **áˆ˜áŒáˆˆáŒ«:** {book['description']}\n\ná‹­áˆ…áŠ•áŠ• á‹­á‹˜á‰µ áŒˆá‹á‰°á‹ á‰ á‰…áŒ½á‰ á‰µ áˆˆáˆ›á‹áˆ¨á‹µ áŠ¨á‰³á‰½ á‹«áˆˆá‹áŠ• á‹¨áŠ­áá‹« á‰áˆá á‹­áŒ«áŠ‘á¦"
            btn_text = "ðŸ’³ á‰  Chapa / Telebirr áŠ­áˆáˆ"
        elif lang == "or":
            checkout_msg = f"ðŸ›’ **Maamilummaa Bitataa**\n\nðŸ“š **Mata duree:** {book['title']}\nðŸ’° **Gatii:** {book['price']} ETB\nðŸ“ **Ibsa:** {book['description']}\n\nBitachuuf qabdoo gadii cuqaasaa:"
            btn_text = "ðŸ’³ Kaffaltii Raawwadhu"
        else:
            checkout_msg = f"ðŸ›’ **Purchase Order**\n\nðŸ“š **Title:** {book['title']}\nðŸ’° **Price:** {book['price']} ETB\nðŸ“ **Description:** {book['description']}\n\nClick the button below to complete your purchase:"
            btn_text = "ðŸ’³ Pay Now"

        keyboard = [[InlineKeyboardButton(btn_text, callback_data=f"buy_{book['id']}")]]
        await update.message.reply_text(checkout_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return


# =====================================================================
# ðŸ’³ á‹¨áŠ­áá‹« áŠ¥áŠ“ á‹¨áŠ á‹µáˆšáŠ• á‹áˆ³áŠ”á‹Žá‰½ áˆ›áˆµá‰°áŠ“áŒˆáŒƒ (CALLBACK QUERY HANDLER)
# =====================================================================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    
    # --- á‹¨áŠ­áá‹« ááˆ°á‰µ áˆ›áˆµá‰°áŠ“áŒˆáŒƒ ---
    if data.startswith("buy_"):
        row_id = data.split("_")[1]
        book = db.get_content_by_id(row_id)
        
        if book:
            # ðŸ“Œ á‹¨0 á‰¥áˆ­ (áŠáƒ) áŠ¨áˆ†áŠ á‹á‹­áˆ‰áŠ• á‰ á‰€áŒ¥á‰³ á‹­áˆ‹áŠ­
            if book['price'] <= 0:
                db.add_order(user_id, book['id'], 0, payment_ref="FREE_DOWNLOAD", status="approved")
                try:
                    file_path = book['file_path']
                    if os.path.exists(file_path):
                        if lang == "am": await context.bot.send_message(chat_id=user_id, text=f"âœ… á‹­á‹˜á‰± á‹ˆá‹° 'ðŸ“ á‹¨áŠ¥áŠ” áˆ‹á‹­á‰¥áˆ¨áˆª' á‰°áŒ¨áˆáˆ¯áˆá¢ á‹á‹­áˆ‰ áŠ¥áŠáˆ†á¦")
                        elif lang == "or": await context.bot.send_message(chat_id=user_id, text=f"âœ… Kuusaa keessanitti dabalamuun, á‹á‹­áˆ‰ á‰°áˆáŠ³áˆá¦")
                        else: await context.bot.send_message(chat_id=user_id, text=f"âœ… Saved to your library. Here is your file:")
                        
                        async with aiofiles.open(file_path, 'rb') as f:
                            file_data = await f.read()
                        await context.bot.send_document(chat_id=user_id, document=file_data, filename=os.path.basename(file_path))
                    else:
                        if lang == "am": await context.bot.send_message(chat_id=user_id, text="âŒ á‹­á‰…áˆ­á‰³á£ á‹¨á‹­á‹˜á‰± á‹á‹­áˆ á‰ áˆ²áˆµá‰°áˆ™ áˆ‹á‹­ áŠ áˆá‰°áŒˆáŠ˜áˆá¢")
                        else: await context.bot.send_message(chat_id=user_id, text="âŒ Sorry, the file was not found on the server.")
                except Exception as e:
                    logging.error(f"Error sending free file: {e}")
                return

            # ðŸ“Œ á‹¨áˆšáŠ¨áˆáˆá‰ á‰µ áŠ¨áˆ†áŠ á‹¨á‰´áˆŒá‰¥áˆ­ áˆ˜áˆ¨áŒƒ áˆ˜áˆµáŒ á‰µ
            pay_msg = (
                f"ðŸ’³ **á‹¨áŠ­áá‹« áˆ˜áˆ˜áˆªá‹« ({book['title']})**\n\n"
                f"áŠ¥á‰£áŠ­á‹Ž **{book['price']} ETB** á‹ˆá‹°áˆšáŠ¨á‰°áˆˆá‹ á‹¨á‰´áˆŒá‰¥áˆ­ (telebirr) áˆ‚áˆ³á‰¥ á‹«áˆµáŒˆá‰¡á¦\n\n"
                f"ðŸ“± **á‹¨áˆµáˆáŠ­ á‰áŒ¥áˆ­:** `0947843445`\n"
                f"ðŸ‘¤ **á‹¨áŠ áŠ«á‹áŠ•á‰µ áˆµáˆ:** `Dawit Megersa`\n\n"
                f"áŠ­áá‹«á‹áŠ• áŠ¨áˆáŒ¸áˆ™ á‰ áŠ‹áˆ‹ á‹¨á‹°áˆ¨áˆ°áŠ á‰áŒ¥áˆ©áŠ• (Transaction ID/Ref) áˆˆáˆ˜áˆ‹áŠ­ áŠ¨á‰³á‰½ á‹«áˆˆá‹áŠ• áŠ á‹áˆ«áˆ­ á‹­áŒ«áŠ‘á¦"
            )
            # ðŸ“Œ [á‹‹áŠ“ áˆ›áˆµá‰°áŠ«áŠ¨á‹«] submit_ref_ á‰ á‰µáŠ­áŠ­áˆ á‹¨áˆ˜áŒ½áˆá‰áŠ• ID áŠ¥áŠ•á‹²á‹­á‹ áŠ¢áŠ•á‹´áŠ­áˆµ 2 áˆ‹á‹­ áŠ¥áŠ“áˆµá‰€áˆáŒ á‹‹áˆˆáŠ•
            inline_kb = [[InlineKeyboardButton("ðŸ“© á‹¨á‹°áˆ¨áˆ°áŠ á‰áŒ¥áˆ­ (Ref) áŠ áˆµáŒˆá‰£", callback_data=f"submit_ref_{book['id']}")]]
            await context.bot.send_message(chat_id=user_id, text=pay_msg, reply_markup=InlineKeyboardMarkup(inline_kb), parse_mode="Markdown")

    elif data.startswith("submit_ref_"):
        book_id = data.split("_")[2]
        context.user_data['buying_book_id'] = book_id
        msg = "âœï¸ áŠ¥á‰£áŠ­á‹Ž á‹¨á‰´áˆŒá‰¥áˆ­ á‹¨áŒá‰¥á‹­á‰µ áˆ˜áˆˆá‹« á‰áŒ¥áˆ©áŠ• (Transaction Ref Number) áŠ¥á‹šáˆ… á‹­áŒ»á‰áˆáŠ•á¦"
        if lang == "or": msg = "âœï¸ Maaloo lakkoofsa heeregaa (Ref) barreessiá¦"
        elif lang == "en": msg = "âœï¸ Please type the Transaction Ref number here:"
        await context.bot.send_message(chat_id=user_id, text=msg)
        return AWAITING_TELEBIRR_REF

    elif data.startswith("download_"):
        content_id = data.split("_")[1]
        book = db.get_content_by_id(content_id)
        if book and os.path.exists(book['file_path']):
            async with aiofiles.open(book['file_path'], 'rb') as f:
                file_data = await f.read()
            await context.bot.send_document(chat_id=user_id, document=file_data, filename=os.path.basename(book['file_path']), caption=f"ðŸ“¥ {book['title']}")

    # --- ðŸ‘‘ áŠ á‹µáˆšáŠ• áŠ­áá‹« áˆ²á‹«áŒ¸á‹µá‰… (Approve Payment) ---
    elif data.startswith("pay_app_"):
        parts = data.split("_")
        target_uid = int(parts[2])
        book_id = int(parts[3])
        tx_ref = parts[4]
        
        db.approve_payment(target_uid, book_id, tx_ref)
        
        await query.edit_message_text(text="âœ… áŠ­áá‹«á‹ á‰°áˆ¨áŒ‹áŒáŒ§áˆá£ á‹á‹­áˆ‰ áˆˆá‰°áŒ á‰ƒáˆšá‹ á‰°áˆáŠ³áˆá¢")
        
        book = db.get_content_by_id(book_id)
        if book and os.path.exists(book['file_path']):
            await context.bot.send_message(chat_id=target_uid, text="âœ… áŠ­áá‹«á‹Ž á‰ áŠ á‹µáˆšáŠ• á‰°áˆ¨áŒ‹áŒáŒ§áˆ! á‹«á‹˜á‹™á‰µ á‹­á‹˜á‰µ áŠ¨á‰³á‰½ á‰°áˆáŠ®áˆá‹Žá‰³áˆá¢")
            async with aiofiles.open(book['file_path'], 'rb') as f:
                file_data = await f.read()
            await context.bot.send_document(chat_id=target_uid, document=file_data, filename=os.path.basename(book['file_path']))

    # --- ðŸ‘‘ áŠ á‹µáˆšáŠ• áŠ­áá‹« á‹á‹µá‰… áˆ²á‹«á‹°áˆ­áŒ (Reject Payment) ---
    elif data.startswith("pay_rej_"):
        target_uid = int(data.split("_")[2])
        book_id = int(data.split("_")[3])
        
        db.reject_payment(target_uid, book_id)
        
        await query.edit_message_text(text="âŒ áŠ­áá‹«á‹ á‹á‹µá‰… á‰°á‹°áˆ­áŒ“áˆá¢")
        await context.bot.send_message(chat_id=target_uid, text="âŒ á‹«áˆµáŒˆá‰¡á‰µ á‹¨áŠ­áá‹« áˆ›áˆ¨áŒ‹áŒˆáŒ« á‰áŒ¥áˆ­ á‰µáŠ­áŠ­áˆ á‰£áˆˆáˆ˜áˆ†áŠ‘ á‰ áŠ á‹µáˆšáŠ• á‹á‹µá‰… á‰°á‹°áˆ­áŒ“áˆá¢ áŠ¥á‰£áŠ­á‹Ž áŠ¥áŠ•á‹°áŒˆáŠ“ á‰ á‰µáŠ­áŠ­áˆ á‹«áˆµáŒˆá‰¡á¢")

    # --- ðŸ‘‘ áŠ á‹µáˆšáŠ• áˆ˜áŒ½áˆá áˆ²á‹«áŒ¸á‹µá‰… (Approve Content) ---
    elif data.startswith("approve_book_"):
        book_id = data.split("_")[2]
        res = db.approve_content(book_id)
        
        await query.edit_message_caption(caption="âœ… á‹­á‹˜á‰± á‰ á‰°áˆ³áŠ« áˆáŠ”á‰³ áŒ½á‹µá‰‹áˆ! áŠ áˆáŠ• áˆˆáˆáˆ‰áˆ á‰°áŒ á‰ƒáˆšá‹Žá‰½ á‹­á‰³á‹«áˆá¢", reply_markup=None)
        if res:
            author_id, book_title = res[0], res[1]
            author_lang = db.get_user_lang(author_id)
            if author_lang == "am": auth_msg = f"ðŸŽ‰ áŠ¥áŠ•áŠ³áŠ• á‹°áˆµ áŠ áˆˆá‹Žá‰µ! '{book_title}' á‹¨á‰°áˆ°áŠ˜á‹ á‹­á‹˜á‰µá‹Ž á‰ áŠ á‹µáˆšáŠ• á‰°áŒˆáˆáŒáˆž áŒ½á‹µá‰‹áˆá¢"
            elif author_lang == "or": auth_msg = f"ðŸŽ‰ Baga gammaddan! Qabiyyee keessan '{book_title}' adminiin mirkanaayeera."
            else: auth_msg = f"ðŸŽ‰ Congratulations! Your content '{book_title}' has been approved by the admin."
            try: await context.bot.send_message(chat_id=author_id, text=auth_msg)
            except: pass

    # --- ðŸ‘‘ áŠ á‹µáˆšáŠ• áˆ˜áŒ½áˆá áˆ²á‹«á‰€áˆ¨á‰…áˆ­/áˆ²áŠ¨áˆˆáŠ­áˆ (Reject Content) ---
    elif data.startswith("reject_book_"):
        book_id = data.split("_")[2]
        res = db.reject_content(book_id)
        
        await query.edit_message_caption(caption="âŒ á‹­á‹˜á‰± á‹á‹µá‰… (Rejected) á‰°á‹°áˆ­áŒ“áˆá¢", reply_markup=None)
        if res:
            author_id, book_title = res[0], res[1]
            author_lang = db.get_user_lang(author_id)
            if author_lang == "am": auth_msg = f"ðŸ˜” á‹­á‰…áˆ­á‰³á£ '{book_title}' á‹¨á‰°áˆ°áŠ˜á‹ á‹­á‹˜á‰µá‹Ž á‰ áˆ•áŒáŠ“ á‹°áŠ•á‰¥ áˆáŠ­áŠ•á‹«á‰µ á‰ áŠ á‹µáˆšáŠ• á‹á‹µá‰… á‰°á‹°áˆ­áŒ“áˆá¢"
            elif author_lang == "or": auth_msg = f"ðŸ˜” Gammachuun, qabiyyee keessan '{book_title}' adminiin fudhatama hin arganne."
            else: auth_msg = f"ðŸ˜” Sorry, your content '{book_title}' has been rejected by the admin."
            try: await context.bot.send_message(chat_id=author_id, text=auth_msg)
            except: pass

    # --- ðŸ‘‘ áŠ á‹µáˆšáŠ• á‹°áˆ«áˆ² áˆ²á‹«áŒ¸á‹µá‰… ---
    elif data.startswith("approve_auth_"):
        target_user_id = data.split("_")[2]
        db.approve_author(target_user_id)
        
        await query.edit_message_text(text="âœ… á‹°áˆ«áˆ²á‹ á‰ á‰°áˆ³áŠ« áˆáŠ”á‰³ áŒ½á‹µá‰‹áˆ!", reply_markup=None)
        
        author_lang = db.get_user_lang(target_user_id)
        kb = am_main_keyboard if author_lang == "am" else (or_main_keyboard if author_lang == "or" else en_main_keyboard)
        if author_lang == "am": auth_msg = "ðŸŽ‰ áŠ¥áŠ•áŠ³áŠ• á‹°áˆµ áŠ áˆˆá‹Žá‰µ! á‹¨á‹°áˆ«áˆ²áŠá‰µ áˆ›áˆ˜áˆáŠ¨á‰»á‹Ž á‰ áŠ á‹µáˆšáŠ• áŒ½á‹µá‰‹áˆá¢ áŠ áˆáŠ• á‹­á‹˜á‰¶á‰½áŠ• áˆ›áŠ¨áˆ á‹­á‰½áˆ‹áˆ‰!"
        elif author_lang == "or": auth_msg = "ðŸŽ‰ Baga gammaddan! Gafannoon barreessummaa keessan adminiin mirkanaayeera. Amma qabiyyee galchuu dandeessu!"
        else: auth_msg = "ðŸŽ‰ Congratulations! Your author application has been approved. You can now upload content!"
        try: await context.bot.send_message(chat_id=target_user_id, text=auth_msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        except: pass

    # --- ðŸ‘‘ áŠ á‹µáˆšáŠ• á‹°áˆ«áˆ² áˆ²áŠ¨áˆˆáŠ­áˆ ---
    elif data.startswith("reject_auth_"):
        target_user_id = data.split("_")[2]
        db.reject_author(target_user_id)
        await query.edit_message_text(text="âŒ á‹¨á‹°áˆ«áˆ²áŠá‰µ áŒ¥á‹«á‰„á‹ á‹á‹µá‰… á‰°á‹°áˆ­áŒ“áˆá¢", reply_markup=None)
        return ConversationHandler.END


# =====================================================================
# ðŸ á‹‹áŠ“á‹ á‹¨áˆ›áˆµáŠáˆ» áŠ­ááˆ (MAIN FUNCTION)
# =====================================================================
def main():
    # 'files' áŽáˆá‹°áˆ­ á‰ á•áˆ®áŒ€áŠ­á‰± áˆ›á‹áŒ« á‹áˆµáŒ¥ áˆ˜áŠ–áˆ©áŠ• áˆ›áˆ¨áŒ‹áŒˆáŒ¥á£ áŠ¨áˆŒáˆˆ áˆ˜ááŒ áˆ­á¢
    if not os.path.exists('files'):
        os.makedirs('files')
        logging.info("ðŸ“ 'files' á‹¨á‰°á‰£áˆˆá‹ áŽáˆá‹°áˆ­ á‰ áˆ«áˆµ-áˆ°áˆ­ á‰ á‰°áˆ³áŠ« áˆáŠ”á‰³ á‰°áˆáŒ¥áˆ¯áˆá¢")

    db.init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    
    # ðŸ” á‹¨ááˆˆáŒ‹ áˆ˜á‰†áŒ£áŒ áˆªá‹« ááˆ°á‰µ (Search Conversation) - r"" á‹¨áˆªáŒ…áŠ­áˆµ á‰…áŠ•áŽá‰½áŠ• áˆµáˆ…á‰°á‰µ á‹­áŠ¨áˆ‹áŠ¨áˆ‹áˆ
    search_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^(ðŸ” áˆáˆáŒ \(Search\)|ðŸ” Barbaadi \(Search\)|ðŸ” Search)$"), start_search)],
        states={AWAITING_SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, execute_search)]},
        fallbacks=[]
    )

    reg_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^(âœï¸ á‹°áˆ«áˆ² áˆ˜áˆ†áŠ• áŠ¥áˆáˆáŒ‹áˆˆáˆ|âœï¸ Barreessaa Ta'uu|âœï¸ Become an Author)$"), start_registration)],
        states={
            AWAITING_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_bio)],
            AWAITING_PHONE: [MessageHandler(filters.TEXT | filters.CONTACT, save_phone_and_finish)]
        },
        fallbacks=[CommandHandler("cancel", cancel_reg)]
    )
    
    upload_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^(âž• áŠ á‹²áˆµ á‹­á‹˜á‰µ áŠ áŠ­áˆ|âž• Kitaaba Haaraa Gali|âž• Add New Book)$"), start_book_upload)],
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
    
    print("Kitab Bot (á‹«áˆá‰°á‰€áŠáˆ° áŠ¥áŠ“ áˆ™áˆ‰ á‰ áˆ™áˆ‰ áˆ«áˆ±áŠ• á‹¨á‰»áˆˆ) á‰ á‰°áˆ³áŠ« áˆáŠ”á‰³ á‰°áŠáˆµá‰·áˆ...")
    app.run_polling()

if __name__ == "__main__":
    main()
