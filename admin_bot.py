"""
👑 admin_bot.py — ለአድሚን ብቻ የሚሰራ ቦት
"""

import logging
import os
import shutil
import datetime
import asyncio
import aiofiles
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from config import ADMIN_BOT_TOKEN, ADMIN_ID, DB_NAME
import database as db
from utils import security

# የሎግ ማስተካከያ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


# =====================================================================
# 💾 DATABASE BACKUP FUNCTIONS
# =====================================================================

def create_database_backup():
    """
    💾 የውሂብ ጎታ ምትኬ (Backup) ይፈጥራል
    """
    os.makedirs("backups", exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"backup_{timestamp}.db"
    backup_path = f"backups/{backup_name}"
    
    shutil.copy2(DB_NAME, backup_path)
    logging.info(f"💾 ምትኬ ተወስዷል: {backup_path}")
    
    backups = sorted([f for f in os.listdir("backups") if f.endswith('.db')])
    if len(backups) > 30:
        for old_backup in backups[:-30]:
            os.remove(f"backups/{old_backup}")
            logging.info(f"🗑️ አሮጌ ምትኬ ተወግዷል: {old_backup}")
    
    return backup_path


# =====================================================================
# 👑 የአድሚን ቦት ዋና ትዕዛዞች
# =====================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """የአድሚን ቦት መጀመሪያ"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ይህ ቦት ለአድሚን ብቻ ነው!")
        return
    
    keyboard = [
        [InlineKeyboardButton("📚 ሁሉንም ይዘቶች", callback_data="admin_view_all")],
        [InlineKeyboardButton("📊 አጠቃላይ ሽያጭ", callback_data="admin_sales_report")],
        [InlineKeyboardButton("🏆 ከፍተኛ ደራሲያን", callback_data="admin_top_authors")],
        [InlineKeyboardButton("📈 በምድብ ስታቲስቲክስ", callback_data="admin_category_stats")],
        [InlineKeyboardButton("👤 የተጠቃሚ ዝርዝር", callback_data="admin_users_list")],
        [InlineKeyboardButton("👤 በግምገማ ላይ ያሉ ደራሲያን", callback_data="admin_pending_authors")],
        [InlineKeyboardButton("📝 በግምገማ ላይ ያሉ ይዘቶች", callback_data="admin_pending_books")],
        [InlineKeyboardButton("💳 በግምገማ ላይ ያሉ ክፍያዎች", callback_data="admin_pending_payments")],
        [InlineKeyboardButton("🔐 DRM ማመስጠር", callback_data="admin_encryption")],
        [InlineKeyboardButton("📊 የደራሲ ሽያጭ ፈልግ", callback_data="admin_find_author")],
        [InlineKeyboardButton("📥 ፋይል አውርድ (በID)", callback_data="admin_download_by_id")],
        [InlineKeyboardButton("💾 Database Backup", callback_data="admin_backup")],
        [InlineKeyboardButton("📢 መልእክት ላክ (Broadcast)", callback_data="admin_broadcast")],
    ]
    
    await update.message.reply_text(
        "👑 **Kitab Admin Bot**\n\n"
        "ከታች ካሉት አማራጮች ይምረጡ፦",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text="👑 **ዋና ሜኑ**"):
    """ወደ ዋና ሜኑ ይመልሳል"""
    query = update.callback_query if update.callback_query else None
    
    keyboard = [
        [InlineKeyboardButton("📚 ሁሉንም ይዘቶች", callback_data="admin_view_all")],
        [InlineKeyboardButton("📊 አጠቃላይ ሽያጭ", callback_data="admin_sales_report")],
        [InlineKeyboardButton("🏆 ከፍተኛ ደራሲያን", callback_data="admin_top_authors")],
        [InlineKeyboardButton("📈 በምድብ ስታቲስቲክስ", callback_data="admin_category_stats")],
        [InlineKeyboardButton("👤 የተጠቃሚ ዝርዝር", callback_data="admin_users_list")],
        [InlineKeyboardButton("👤 በግምገማ ላይ ያሉ ደራሲያን", callback_data="admin_pending_authors")],
        [InlineKeyboardButton("📝 በግምገማ ላይ ያሉ ይዘቶች", callback_data="admin_pending_books")],
        [InlineKeyboardButton("💳 በግምገማ ላይ ያሉ ክፍያዎች", callback_data="admin_pending_payments")],
        [InlineKeyboardButton("🔐 DRM ማመስጠር", callback_data="admin_encryption")],
        [InlineKeyboardButton("📊 የደራሲ ሽያጭ ፈልግ", callback_data="admin_find_author")],
        [InlineKeyboardButton("📥 ፋይል አውርድ (በID)", callback_data="admin_download_by_id")],
        [InlineKeyboardButton("💾 Database Backup", callback_data="admin_backup")],
        [InlineKeyboardButton("📢 መልእክት ላክ (Broadcast)", callback_data="admin_broadcast")],
    ]
    
    if query:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )


# =====================================================================
# 📞 Callback Handlers
# =====================================================================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """የአዝራር ጠቅታ አያያዥ"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await query.edit_message_text("⛔ ፈቃድ የሎትም")
        return
    
    # ወደ ዋና ሜኑ መመለስ
    if data == "admin_menu":
        await show_menu(update, context)
        return
    
    # ================================================================
    # 💾 DATABASE BACKUP
    # ================================================================
    if data == "admin_backup":
        try:
            backup_path = create_database_backup()
            
            async with aiofiles.open(backup_path, 'rb') as f:
                file_data = await f.read()
            
            await context.bot.send_document(
                chat_id=user_id,
                document=file_data,
                filename=os.path.basename(backup_path),
                caption=f"✅ Database Backup ተፈጥሯል!\n"
                       f"📅 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            await query.edit_message_text(
                f"✅ Database Backup ተፈጥሯል!\n"
                f"📁 {os.path.basename(backup_path)}"
            )
        except Exception as e:
            logging.error(f"Backup error: {e}")
            await query.edit_message_text(f"❌ ስህተት: {e}")

    # ================================================================
    # 🏆 ከፍተኛ ደራሲያን
    # ================================================================
    elif data == "admin_top_authors":
        try:
            top_authors = db.get_author_rankings(10)
            
            if not top_authors:
                await query.edit_message_text("📭 እስካሁን ምንም ሽያጭ የለም።")
                return
            
            msg = "🏆 **ከፍተኛ ደራሲያን**\n\n"
            for i, author in enumerate(top_authors, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                msg += (
                    f"{medal} **{author['first_name'] or author['username'] or author['user_id']}**\n"
                    f"   📚 {author['total_books']} መጻሕፍት\n"
                    f"   🛒 {author['total_sales']} ሽያጮች\n"
                    f"   💰 {author['total_income']} ETB\n\n"
                )
            
            keyboard = [[InlineKeyboardButton("🔙 ወደ ዋና ሜኑ", callback_data="admin_menu")]]
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Top authors error: {e}")
            await query.edit_message_text(f"❌ ስህተት: {e}")

    # ================================================================
    # 📈 በምድብ ስታቲስቲክስ
    # ================================================================
    elif data == "admin_category_stats":
        try:
            stats = db.get_category_stats()
            
            if not stats:
                await query.edit_message_text("📭 ምንም መረጃ የለም።")
                return
            
            msg = "📈 **በምድብ የሽያጭ ስታቲስቲክስ**\n\n"
            for stat in stats:
                emoji = "📚" if stat['category'] == "Literature" else "🎓" if stat['category'] == "Education" else "📖" if stat['category'] == "Religion" else "📜" if stat['category'] == "History" else "💼" if stat['category'] == "Business" else "💻"
                msg += (
                    f"{emoji} **{stat['category']}**\n"
                    f"   📖 {stat['total_books']} ይዘቶች\n"
                    f"   🛒 {stat['total_sales']} ሽያጮች\n"
                    f"   💰 {stat['total_income']} ETB\n\n"
                )
            
            keyboard = [[InlineKeyboardButton("🔙 ወደ ዋና ሜኑ", callback_data="admin_menu")]]
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Category stats error: {e}")
            await query.edit_message_text(f"❌ ስህተት: {e}")

    # ================================================================
    # 👤 የተጠቃሚ ዝርዝር
    # ================================================================
    elif data == "admin_users_list":
        try:
            stats = db.get_user_stats()
            users = db.get_all_users(10)
            
            msg = (
                "👤 **የተጠቃሚ ስታቲስቲክስ**\n\n"
                f"👥 ጠቅላላ ተጠቃሚዎች: **{stats['total_users']}**\n"
                f"✍️ ደራሲያን: **{stats['total_authors']}**\n"
                f"📚 ይዘቶች: **{stats['total_contents']}**\n"
                f"💳 ግብይቶች: **{stats['total_orders']}**\n\n"
                "📋 **የቅርብ ጊዜ ተጠቃሚዎች**\n"
            )
            
            for user in users:
                msg += f"• `{user['telegram_id']}` - {user['first_name'] or 'N/A'}\n"
            
            keyboard = [
                [InlineKeyboardButton("🔍 ተጠቃሚ ፈልግ", callback_data="admin_find_user")],
                [InlineKeyboardButton("🔙 ወደ ዋና ሜኑ", callback_data="admin_menu")]
            ]
            
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Users list error: {e}")
            await query.edit_message_text(f"❌ ስህተት: {e}")

    # ================================================================
    # 🔍 ተጠቃሚ ፈልግ
    # ================================================================
    elif data == "admin_find_user":
        await query.edit_message_text(
            "🔍 **ተጠቃሚ ፈልግ**\n\n"
            "የተጠቃሚውን ቴሌግራም ID፣ ስም ወይም የተጠቃሚ ስም ያስገቡ፦\n"
            "ወይም /cancel ይጫኑ።"
        )
        context.user_data['admin_action'] = 'find_user'
        return

    # ================================================================
    # 📢 Broadcast
    # ================================================================
    elif data == "admin_broadcast":
        await query.edit_message_text(
            "📢 **ለሁሉም ተጠቃሚዎች መልእክት መላክ**\n\n"
            "የሚልኩትን መልእክት ይጻፉ፦\n"
            "ወይም /cancel ይጫኑ።"
        )
        context.user_data['admin_action'] = 'broadcast'
        return

    # ================================================================
    # 🔐 DRM ማመስጠር ፓነል
    # ================================================================
    elif data == "admin_encryption":
        await query.edit_message_text(
            "🔐 **DRM ማመስጠር ፓነል**\n\n"
            "ከታች ካሉት አማራጮች ይምረጡ፦",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 ለመመስጠር የሚጠበቁ", callback_data="admin_pending_encryption")],
                [InlineKeyboardButton("📤 የተመሰጠረ ፋይል ጫን", callback_data="admin_upload_encrypted")],
                [InlineKeyboardButton("🔙 ወደ ዋና ሜኑ", callback_data="admin_menu")]
            ])
        )

    elif data == "admin_pending_encryption":
        try:
            pending = db.get_contents_pending_encryption(limit=20)
            
            if not pending:
                await query.edit_message_text(
                    "📭 ለመመስጠር የሚጠበቁ ይዘቶች የሉም።",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ወደ ሜኑ", callback_data="admin_encryption")]])
                )
                return
            
            msg = "🔐 **ለመመስጠር የሚጠበቁ ይዘቶች**\n\n"
            for book in pending:
                msg += (
                    f"📌 **ID:** `{book['id']}`\n"
                    f"📚 {book['title']}\n"
                    f"👤 {book['author_name']} (@{book['author_username']})\n"
                    f"💰 {book['price']} ETB\n"
                    f"📅 {book['created_at'][:16]}\n"
                    "---\n"
                )
            
            keyboard = []
            for book in pending[:10]:
                keyboard.append([
                    InlineKeyboardButton(f"📥 አውርድ #{book['id']}", callback_data=f"admin_download_original_{book['id']}"),
                    InlineKeyboardButton(f"📤 የተመሰጠረ ጫን #{book['id']}", callback_data=f"admin_upload_encrypted_{book['id']}")
                ])
            keyboard.append([InlineKeyboardButton("🔙 ወደ ሜኑ", callback_data="admin_encryption")])
            
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Pending encryption error: {e}")
            await query.edit_message_text(f"❌ ስህተት: {e}")

    elif data.startswith("admin_download_original_"):
        try:
            book_id = int(data.split("_")[3])
            security._validate_content_id(book_id)
            
            book = db.get_content_by_id(book_id)
            if not book or not os.path.exists(book['file_path']):
                await query.answer("❌ ፋይሉ አልተገኘም", show_alert=True)
                return
            
            async with aiofiles.open(book['file_path'], 'rb') as f:
                file_data = await f.read()
            
            await context.bot.send_document(
                chat_id=user_id,
                document=file_data,
                filename=f"original_{book_id}.pdf",
                caption=f"📚 {book['title']}\n"
                       f"📌 ዋናው ፋይል ለDRM መመስጠር\n\n"
                       f"✍️ እባክዎ ፋይሉን በVeryPDF (ወይም በሚፈለገው መሳሪያ) በመመስጠር "
                       f"ከዚያም የተመሰጠረውን ፋይል '📤 የተመሰጠረ ጫን' በመጫን ይመልሱ።"
            )
            await query.answer("✅ ፋይሉ ተልኳል")
        except Exception as e:
            logging.error(f"Download original error: {e}")
            await query.answer(f"❌ ስህተት: {e}", show_alert=True)

    elif data.startswith("admin_upload_encrypted_"):
        book_id = int(data.split("_")[3])
        context.user_data['encrypt_book_id'] = book_id
        context.user_data['admin_action'] = 'upload_encrypted'
        
        await query.edit_message_text(
            f"📤 የተመሰጠረ ፋይል ይጫኑ\n\n"
            f"📚 ይዘት ID: `{book_id}`\n\n"
            f"✍️ ፋይሉን ከVeryPDF (ወይም ከሚፈለገው መሳሪያ) ካመስጠሩ በኋላ "
            f"እንደ Document (PDF) አድርገው ይላኩ።"
        )
        return

    # ================================================================
    # 📚 ሁሉንም ይዘቶች ማየት
    # ================================================================
    elif data == "admin_view_all":
        try:
            page = context.user_data.get('content_page', 0)
            limit = 5
            result = db.get_all_contents(limit=limit, offset=page * limit)
            contents = result['items']
            total = result['total']
            
            if not contents:
                await query.edit_message_text("📭 ምንም ይዘት የለም።")
                return
            
            for content in contents:
                sales_count = db.get_content_sales_count(content['id'])
                status_emoji = "✅" if content['status'] == 'approved' else ("⏳" if content['status'] in ['pending_encryption', 'pending_author_approval'] else "❌")
                caption = (
                    f"📌 **{content['title']}**\n"
                    f"🆔 ID: `{content['id']}`\n"
                    f"👤 ደራሲ ID: {content['author_id']}\n"
                    f"💰 {content['price']} ETB\n"
                    f"📊 ሽያጭ: {sales_count}\n"
                    f"📝 ሁኔታ: {status_emoji} {content['status']}"
                )
                keyboard = [[
                    InlineKeyboardButton("📥 አውርድ", callback_data=f"admin_dl_{content['id']}")
                ]]
                await context.bot.send_message(
                    chat_id=user_id,
                    text=caption,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
            
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️ ቀዳሚ", callback_data="admin_view_page_prev"))
            if (page + 1) * limit < total:
                nav_buttons.append(InlineKeyboardButton("➡️ ቀጣይ", callback_data="admin_view_page_next"))
            
            nav_buttons.append(InlineKeyboardButton("🔙 ወደ ዋና ሜኑ", callback_data="admin_menu"))
            
            nav_msg = f"📄 ገጽ {page + 1}/{((total - 1) // limit) + 1} (📚 {total} ይዘቶች)"
            await context.bot.send_message(
                chat_id=user_id,
                text=nav_msg,
                reply_markup=InlineKeyboardMarkup([nav_buttons])
            )
            
            await query.delete_message()
        except Exception as e:
            logging.error(f"View all error: {e}")
            await query.edit_message_text(f"❌ ስህተት: {e}")

    # ================================================================
    # 📄 ገጽ መለያየት
    # ================================================================
    elif data == "admin_view_page_next":
        context.user_data['content_page'] = context.user_data.get('content_page', 0) + 1
        await handle_callback(update, context)
        
    elif data == "admin_view_page_prev":
        context.user_data['content_page'] = max(0, context.user_data.get('content_page', 0) - 1)
        await handle_callback(update, context)

    # ================================================================
    # 📥 ፋይል ማውረድ
    # ================================================================
    elif data.startswith("admin_dl_"):
        try:
            content_id = int(data.split("_")[2])
            security._validate_content_id(content_id)
            
            book = db.get_content_by_id(content_id)
            if book and os.path.exists(book['file_path']):
                async with aiofiles.open(book['file_path'], 'rb') as f:
                    file_data = await f.read()
                await context.bot.send_document(
                    chat_id=user_id,
                    document=file_data,
                    filename=os.path.basename(book['file_path']),
                    caption=f"📥 {book['title']}"
                )
                await query.answer("✅ ፋይሉ ተልኳል")
            else:
                await query.answer("❌ ፋይሉ አልተገኘም", show_alert=True)
        except (ValueError, TypeError) as e:
            await query.answer(f"❌ {e}", show_alert=True)
        except Exception as e:
            logging.error(f"Download error: {e}")
            await query.answer(f"❌ ስህተት: {e}", show_alert=True)

    # ================================================================
    # 📊 አጠቃላይ ሽያጭ ሪፖርት
    # ================================================================
    elif data == "admin_sales_report":
        try:
            result = db.get_all_contents(limit=100, offset=0)
            contents = result['items']
            total_income = 0.0
            lines = ["📊 **አጠቃላይ የሽያጭ ሪፖርት**", ""]
            for content in contents:
                sales = db.get_content_sales_count(content['id'])
                income = sales * content['price']
                total_income += income
                if sales > 0:
                    lines.append(f"📌 {content['title']} — {sales} ጊዜ — {income} ETB")
            lines.append("")
            lines.append(f"💰 **ጠቅላላ ገቢ:** {total_income} ETB")
            
            keyboard = [[InlineKeyboardButton("🔙 ወደ ዋና ሜኑ", callback_data="admin_menu")]]
            await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Sales report error: {e}")
            await query.edit_message_text(f"❌ ስህተት: {e}")

    # ================================================================
    # 👤 በግምገማ ላይ ያሉ ደራሲያን
    # ================================================================
    elif data == "admin_pending_authors":
        try:
            authors = db.get_pending_authors()
            
            if not authors:
                await query.edit_message_text(
                    "✅ በግምገማ ላይ ያሉ ደራሲያን የሉም።",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ወደ ዋና ሜኑ", callback_data="admin_menu")]])
                )
                return
            
            for author in authors:
                msg = (
                    f"👤 **ደራሲ ID:** `{author['user_id']}`\n"
                    f"📝 ባዮግራፊ: {author['biography']}\n"
                    f"📅 የተመዘገበ: {author['joined_at'][:16]}"
                )
                keyboard = [[
                    InlineKeyboardButton("✅ ፍቀድ", callback_data=f"admin_app_auth_{author['user_id']}"),
                    InlineKeyboardButton("❌ ከልክል", callback_data=f"admin_rej_auth_{author['user_id']}")
                ]]
                await context.bot.send_message(
                    chat_id=user_id,
                    text=msg,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
            await query.edit_message_text("✅ በግምገማ ላይ ያሉ ደራሲያን ተልከዋል።")
        except Exception as e:
            logging.error(f"Pending authors error: {e}")
            await query.edit_message_text(f"❌ ስህተት: {e}")

    # ================================================================
    # ✅/❌ ደራሲ ማጽደቅ/መከልከል
    # ================================================================
    elif data.startswith("admin_app_auth_"):
        try:
            target_id = int(data.split("_")[3])
            db.approve_author(target_id)
            await query.edit_message_text(f"✅ ደራሲ `{target_id}` ጽድቋል!")
            await context.bot.send_message(
                chat_id=target_id,
                text="🎉 የደራሲነት ማመልከቻዎ ተጽድቋል! አሁን ይዘቶችን መጫን ይችላሉ።"
            )
        except Exception as e:
            logging.error(f"Approve author error: {e}")
            await query.edit_message_text(f"❌ ስህተት: {e}")

    elif data.startswith("admin_rej_auth_"):
        try:
            target_id = int(data.split("_")[3])
            db.reject_author(target_id)
            await query.edit_message_text(f"❌ ደራሲ `{target_id}` ተከልክሏል።")
        except Exception as e:
            logging.error(f"Reject author error: {e}")
            await query.edit_message_text(f"❌ ስህተት: {e}")

    # ================================================================
    # 📝 በግምገማ ላይ ያሉ ይዘቶች
    # ================================================================
    elif data == "admin_pending_books":
        try:
            books = db.get_pending_books()
            
            if not books:
                await query.edit_message_text(
                    "✅ በግምገማ ላይ ያሉ ይዘቶች የሉም።",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ወደ ዋና ሜኑ", callback_data="admin_menu")]])
                )
                return
            
            for book in books:
                status_label = "🔐 ለመመስጠር" if book['status'] == 'pending_encryption' else "📝 ለማጽደቅ"
                caption = (
                    f"📌 **{book['title']}**\n"
                    f"🆔 ID: `{book['id']}`\n"
                    f"👤 ደራሲ: {book['author_name']} (@{book['author_username']})\n"
                    f"💰 {book['price']} ETB\n"
                    f"📝 {book['description']}\n"
                    f"📌 ሁኔታ: {status_label}"
                )
                keyboard = [[
                    InlineKeyboardButton("✅ ፍቀድ", callback_data=f"admin_app_book_{book['id']}"),
                    InlineKeyboardButton("❌ ከልክል", callback_data=f"admin_rej_book_{book['id']}")
                ]]
                await context.bot.send_message(
                    chat_id=user_id,
                    text=caption,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
            await query.edit_message_text("✅ በግምገማ ላይ ያሉ ይዘቶች ተልከዋል።")
        except Exception as e:
            logging.error(f"Pending books error: {e}")
            await query.edit_message_text(f"❌ ስህተት: {e}")

    # ================================================================
    # ✅/❌ ይዘት ማጽደቅ/መከልከል
    # ================================================================
    elif data.startswith("admin_app_book_"):
        try:
            book_id = int(data.split("_")[3])
            res = db.approve_content(book_id)
            await query.edit_message_text(f"✅ ይዘት `{book_id}` ጽድቋል!")
            if res:
                author_id, title = res
                await context.bot.send_message(
                    chat_id=author_id,
                    text=f"🎉 '{title}' የተሰኘው ይዘትዎ ተጽድቋል!"
                )
        except Exception as e:
            logging.error(f"Approve content error: {e}")
            await query.edit_message_text(f"❌ ስህተት: {e}")

    elif data.startswith("admin_rej_book_"):
        try:
            book_id = int(data.split("_")[3])
            res = db.reject_content(book_id)
            await query.edit_message_text(f"❌ ይዘት `{book_id}` ተከልክሏል።")
            if res:
                author_id, title = res
                await context.bot.send_message(
                    chat_id=author_id,
                    text=f"😔 '{title}' የተሰኘው ይዘትዎ ተከልክሏል።"
                )
        except Exception as e:
            logging.error(f"Reject content error: {e}")
            await query.edit_message_text(f"❌ ስህተት: {e}")

    # ================================================================
    # 💳 በግምገማ ላይ ያሉ ክፍያዎች
    # ================================================================
    elif data == "admin_pending_payments":
        try:
            author_payments = db.get_pending_author_payments(limit=10)
            admin_payments = db.get_pending_admin_payments(limit=10)
            all_payments = author_payments + admin_payments
            
            if not all_payments:
                await query.edit_message_text(
                    "✅ በግምገማ ላይ ያሉ ክፍያዎች የሉም።",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ወደ ዋና ሜኑ", callback_data="admin_menu")]])
                )
                return
            
            for payment in all_payments:
                payment_type = "📚 ደራሲ" if payment.get('author_id') else "👑 አድሚን"
                msg = (
                    f"💳 **ክፍያ** ({payment_type})\n"
                    f"🆔 ID: `{payment['id']}`\n"
                    f"📌 ይዘት: {payment.get('content_title', 'N/A')}\n"
                    f"👤 ተጠቃሚ ID: {payment['user_id']}\n"
                    f"💰 {payment['amount']} ETB\n"
                    f"📝 Ref: `{payment.get('receipt_ref', 'N/A')}`\n"
                    f"🔗 ሊንክ: {payment.get('receipt_link', 'N/A')}"
                )
                keyboard = [[
                    InlineKeyboardButton("✅ አጽድቅ", callback_data=f"admin_app_pay_{payment['id']}"),
                    InlineKeyboardButton("❌ ውድቅ", callback_data=f"admin_rej_pay_{payment['id']}")
                ]]
                await context.bot.send_message(
                    chat_id=user_id,
                    text=msg,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
            await query.edit_message_text("✅ በግምገማ ላይ ያሉ ክፍያዎች ተልከዋል።")
        except Exception as e:
            logging.error(f"Pending payments error: {e}")
            await query.edit_message_text(f"❌ ስህተት: {e}")

    # ================================================================
    # ✅/❌ ክፍያ ማጽደቅ/መከልከል
    # ================================================================
    elif data.startswith("admin_app_pay_"):
        try:
            payment_id = int(data.split("_")[3])
            
            # የክፍያ ዓይነት ለይቶ ማወቅ
            payment = db.get_author_payment_by_id(payment_id)
            if payment:
                success = db.admin_verify_author_payment(payment_id, "በአድሚን ጸድቋል")
            else:
                success = db.admin_verify_admin_payment(payment_id, "በአድሚን ጸድቋል")
                payment = db.get_admin_payment_by_id(payment_id)
            
            if success:
                await query.edit_message_text(f"✅ ክፍያ #{payment_id} ተጽድቋል!")
                
                # ለተጠቃሚው ማሳወቂያ
                if payment:
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
        except Exception as e:
            logging.error(f"Approve payment error: {e}")
            await query.edit_message_text(f"❌ ስህተት: {e}")

    elif data.startswith("admin_rej_pay_"):
        try:
            payment_id = int(data.split("_")[3])
            success = db.admin_reject_payment(payment_id, 'author', "በአድሚን ውድቅ ተደርጓል")
            
            if success:
                await query.edit_message_text(f"❌ ክፍያ #{payment_id} ውድቅ ተደርጓል።")
                payment = db.get_author_payment_by_id(payment_id)
                if payment:
                    await context.bot.send_message(
                        chat_id=payment['user_id'],
                        text="❌ ያስገቡት የክፍያ ማረጋገጫ ቁጥር ትክክል ባለመሆኑ በአድሚን ውድቅ ተደርጓል።"
                    )
            else:
                await query.edit_message_text(f"❌ ክፍያ #{payment_id} ውድቅ ማድረግ አልተቻለም")
        except Exception as e:
            logging.error(f"Reject payment error: {e}")
            await query.edit_message_text(f"❌ ስህተት: {e}")

    # ================================================================
    # 📊 የደራሲ ሽያጭ ፈልግ
    # ================================================================
    elif data == "admin_find_author":
        await query.edit_message_text(
            "👤 የደራሲውን ቴሌግራም መታወቂያ (ID) ያስገቡ፦\n\n"
            "ለምሳሌ: `123456789`\n\n"
            "ወይም /cancel በማለት ይቅሩ።"
        )
        context.user_data['admin_action'] = 'find_author'
        return

    # ================================================================
    # 📥 ፋይል በID አውርድ
    # ================================================================
    elif data == "admin_download_by_id":
        await query.edit_message_text(
            "📥 የሚወርዱትን ይዘት ID ያስገቡ፦\n\n"
            "ለምሳሌ: `15`\n\n"
            "ወይም /cancel በማለት ይቅሩ።"
        )
        context.user_data['admin_action'] = 'download_by_id'
        return


# =====================================================================
# 📝 Message Handlers
# =====================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """የአድሚን ቦት የጽሑፍ መልዕክት አያያዥ"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ፈቃድ የለዎትም")
        return
    
    text = update.message.text.strip()
    action = context.user_data.get('admin_action')
    
    # ================================================================
    # 📤 የተመሰጠረ ፋይል መላክ
    # ================================================================
    if action == 'upload_encrypted':
        try:
            book_id = context.user_data.get('encrypt_book_id')
            if not book_id:
                await update.message.reply_text("❌ ስህተት ተፈጥሯል። እባክዎ እንደገና ይሞክሩ")
                return
            
            if not update.message.document:
                await update.message.reply_text("❌ እባክዎ የተመሰጠረውን ፋይል እንደ Document (PDF) አድርገው ይላኩ")
                return
            
            doc = update.message.document
            if not doc.file_name.endswith('.pdf'):
                await update.message.reply_text("❌ እባክዎ የፒዲኤፍ (PDF) ፋይል ብቻ ይላኩ!")
                return
            
            os.makedirs("files/encrypted", exist_ok=True)
            
            encrypted_file_path = f"files/encrypted/encrypted_{book_id}.pdf"
            telegram_file = await context.bot.get_file(doc.file_id)
            await telegram_file.download_to_drive(encrypted_file_path)
            
            # ውሂብ ጎታ ማዘመን
            success = db.update_content_with_encrypted_file(book_id, encrypted_file_path, user_id, "በአድሚን ተመስጥሯል")
            
            if success:
                book = db.get_content_by_id(book_id)
                await update.message.reply_text(
                    f"✅ የተመሰጠረ ፋይል በተሳካ ሁኔታ ተጭኗል!\n"
                    f"📚 {book['title'] if book else ''}\n"
                    f"📌 ለደራሲ ማጽደቅ ተልኳል"
                )
                # ደራሲውን ማሳወቅ
                if book:
                    await context.bot.send_message(
                        chat_id=book['author_id'],
                        text=f"🔔 ይዘትዎ '{book['title']}' ተመስጥሯል!\n"
                             f"📌 እባክዎ በ'📊 የሽያጭ ሪፖርት' በኩል ያጽድቁ ወይም ውድቅ ያድርጉ።"
                    )
            else:
                await update.message.reply_text(f"❌ ይዘት ID {book_id} ማዘመን አልተቻለም")
            
            context.user_data['admin_action'] = None
            await show_menu(update, context)
            
        except Exception as e:
            logging.error(f"Upload encrypted error: {e}")
            await update.message.reply_text(f"❌ ስህተት: {e}")

    # ================================================================
    # 🔍 ተጠቃሚ ፈልግ
    # ================================================================
    elif action == 'find_user':
        try:
            users = db.search_users(text)
            if not users:
                await update.message.reply_text("❌ ምንም ተጠቃሚ አልተገኘም።")
            else:
                msg = "🔍 **የተገኙ ተጠቃሚዎች**\n\n"
                for user in users:
                    msg += f"• `{user['telegram_id']}` - {user['first_name'] or 'N/A'} (@{user['username'] or 'N/A'})\n"
                await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Find user error: {e}")
            await update.message.reply_text(f"❌ ስህተት: {e}")
        
        context.user_data['admin_action'] = None
        await show_menu(update, context)

    # ================================================================
    # 📢 Broadcast
    # ================================================================
    elif action == 'broadcast':
        try:
            users = db.get_all_users(limit=1000)
            total_users = len(users)
            
            await update.message.reply_text(f"⏳ ለ {total_users} ተጠቃሚዎች እየተላከ ነው...")
            
            success = 0
            failed = 0
            
            for i, user in enumerate(users):
                try:
                    await context.bot.send_message(
                        chat_id=user['telegram_id'],
                        text=f"📢 **ከአስተዳዳሪ**\n\n{text}",
                        parse_mode="Markdown"
                    )
                    success += 1
                except Exception as e:
                    failed += 1
                    logging.warning(f"Failed to send to {user['telegram_id']}: {e}")
                
                if (i + 1) % 20 == 0:
                    await asyncio.sleep(0.5)
            
            await update.message.reply_text(
                f"✅ መልእክቱ ተልኳል!\n"
                f"📤 የተሳካ: {success}\n"
                f"❌ ያልተሳካ: {failed}"
            )
        except Exception as e:
            logging.error(f"Broadcast error: {e}")
            await update.message.reply_text(f"❌ ስህተት: {e}")
        
        context.user_data['admin_action'] = None
        await show_menu(update, context)

    # ================================================================
    # 📊 የደራሲ ሽያጭ ፈልግ
    # ================================================================
    elif action == 'find_author':
        try:
            author_id = int(text)
            
            # የደራሲ መረጃ ማግኘት
            author = db.get_author_by_user_id(author_id)
            if not author:
                await update.message.reply_text(f"❌ ደራሲ `{author_id}` አልተገኘም")
                return
            
            sales_data = db.get_author_sales(author_id)
            
            if not sales_data['contents']:
                await update.message.reply_text(f"📭 ደራሲ `{author_id}` ምንም ይዘት የለውም።")
            else:
                lines = [f"📊 **የደራሲ {author_id} ሽያጭ ሪፖርት**", ""]
                for item in sales_data['contents']:
                    lines.append(f"📌 **{item['title']}**")
                    lines.append(f"   💰 {item['price']} ETB")
                    lines.append(f"   🛒 {item['sales_count']} ጊዜ")
                    lines.append(f"   💵 {item['income']} ETB")
                    lines.append("")
                lines.append(f"💰 **ጠቅላላ ገቢ:** {sales_data['total_income']} ETB")
                await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("❌ እባክዎ ትክክለኛ ቁጥር ያስገቡ።")
        except Exception as e:
            logging.error(f"Find author error: {e}")
            await update.message.reply_text(f"❌ ስህተት: {e}")
        
        context.user_data['admin_action'] = None
        await show_menu(update, context)

    # ================================================================
    # 📥 ፋይል በID አውርድ
    # ================================================================
    elif action == 'download_by_id':
        try:
            content_id = int(text)
            security._validate_content_id(content_id)
            
            book = db.get_content_by_id(content_id)
            if book and os.path.exists(book['file_path']):
                async with aiofiles.open(book['file_path'], 'rb') as f:
                    file_data = await f.read()
                await context.bot.send_document(
                    chat_id=user_id,
                    document=file_data,
                    filename=os.path.basename(book['file_path']),
                    caption=f"📥 {book['title']}"
                )
            else:
                await update.message.reply_text(f"❌ ይዘት ID `{text}` አልተገኘም ወይም ፋይሉ የለም።")
        except ValueError:
            await update.message.reply_text("❌ እባክዎ ትክክለኛ ቁጥር ያስገቡ።")
        except Exception as e:
            logging.error(f"Download by ID error: {e}")
            await update.message.reply_text(f"❌ ስህተት: {e}")
        
        context.user_data['admin_action'] = None
        await show_menu(update, context)
    
    else:
        await update.message.reply_text("❌ ያልታወቀ ትዕዛዝ። እባክዎ /start ይጫኑ።")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """የአሁኑን ድርጊት ይሰርዛል"""
    context.user_data['admin_action'] = None
    context.user_data['content_page'] = 0
    await update.message.reply_text("✅ ተሰርዟል።")
    await start(update, context)


# =====================================================================
# 🏁 ዋናው የማስነሻ ክፍል
# =====================================================================

def main():
    app = Application.builder().token(ADMIN_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL & ~filters.COMMAND, handle_message))
    
    print("👑 Admin Bot በተሳካ ሁኔታ ተነስቷል...")
    app.run_polling()


if __name__ == "__main__":
    main()
