import logging
import os
import shutil
import datetime
import aiofiles
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from config import ADMIN_BOT_TOKEN, ADMIN_ID
import database as db

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


# =====================================================================
# 💾 DATABASE BACKUP FUNCTIONS
# =====================================================================

def create_database_backup():
    """
    💾 Database Backup ይፈጥራል
    - backups ፎልደር ውስጥ ከቀን እና ሰዓት ጋር ያስቀምጣል
    - ከ30 በላይ backup ካለ አሮጌዎቹን ያጥፋል
    """
    # backups ፎልደር መፍጠር
    os.makedirs("backups", exist_ok=True)
    
    # የBackup ስም ከቀን እና ሰዓት ጋር
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"backup_{timestamp}.db"
    backup_path = f"backups/{backup_name}"
    
    # database.db መቅዳት
    shutil.copy2("database.db", backup_path)
    
    # ከ30 በላይ ካሉ አሮጌዎቹን ማጥፋት
    backups = sorted([f for f in os.listdir("backups") if f.endswith('.db')])
    if len(backups) > 30:
        for old_backup in backups[:-30]:
            os.remove(f"backups/{old_backup}")
    
    return backup_path


# =====================================================================
# 👑 የአድሚን ቦት ዋና ትዕዛዞች
# =====================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """የአድሚን ቦት መጀመሪያ"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ ይህ ቦት ለአድሚን ብቻ ነው!")
        return
    
    keyboard = [
        [InlineKeyboardButton("📚 ሁሉንም ይዘቶች ይመልከቱ", callback_data="admin_view_all")],
        [InlineKeyboardButton("📊 አጠቃላይ ሽያጭ ሪፖርት", callback_data="admin_sales_report")],
        [InlineKeyboardButton("🏆 ከፍተኛ ደራሲያን", callback_data="admin_top_authors")],
        [InlineKeyboardButton("📈 በምድብ ስታቲስቲክስ", callback_data="admin_category_stats")],
        [InlineKeyboardButton("👤 የተጠቃሚ ዝርዝር", callback_data="admin_users_list")],
        [InlineKeyboardButton("👤 በግምገማ ላይ ያሉ ደራሲያን", callback_data="admin_pending_authors")],
        [InlineKeyboardButton("📝 በግምገማ ላይ ያሉ ይዘቶች", callback_data="admin_pending_books")],
        [InlineKeyboardButton("💳 በግምገማ ላይ ያሉ ክፍያዎች", callback_data="admin_pending_payments")],
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


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """የአድሚን ቦት ካልባክ አያያዥ"""
    query = update.callback_query
    data = query.data
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await query.answer("⛔ ፈቃድ የለዎትም", show_alert=True)
        return
    
    await query.answer()

    # ================================================================
    # 💾 DATABASE BACKUP
    # ================================================================
    if data == "admin_backup":
        try:
            backup_path = create_database_backup()
            
            # Backup ፋይሉን ለአድሚን መላክ
            await context.bot.send_document(
                chat_id=user_id,
                document=open(backup_path, 'rb'),
                caption=f"✅ Database Backup ተፈጥሯል!\n"
                       f"📅 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                       f"📁 {os.path.basename(backup_path)}"
            )
            await query.edit_message_text(
                f"✅ Database Backup ተፈጥሯል!\n"
                f"📁 {os.path.basename(backup_path)}\n"
                f"📅 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Database Backup መፍጠር አልተቻለም: {e}")

    # ================================================================
    # 🏆 ከፍተኛ ደራሲያን
    # ================================================================
    elif data == "admin_top_authors":
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
        
        await query.edit_message_text(msg, parse_mode="Markdown")

    # ================================================================
    # 📈 በምድብ ስታቲስቲክስ
    # ================================================================
    elif data == "admin_category_stats":
        stats = db.get_category_stats()
        
        if not stats:
            await query.edit_message_text("📭 ምንም መረጃ የለም።")
            return
        
        msg = "📈 **በምድብ የሽያጭ ስታቲስቲክስ**\n\n"
        for stat in stats:
            emoji = "📚" if stat['category'] == "Books" else "📄" if stat['category'] == "Handouts" else "📝" if stat['category'] == "QuestionBank" else "📁"
            msg += (
                f"{emoji} **{stat['category']}**\n"
                f"   📖 {stat['total_books']} ይዘቶች\n"
                f"   🛒 {stat['total_sales']} ሽያጮች\n"
                f"   💰 {stat['total_income']} ETB\n\n"
            )
        
        await query.edit_message_text(msg, parse_mode="Markdown")

    # ================================================================
    # 👤 የተጠቃሚ ዝርዝር
    # ================================================================
    elif data == "admin_users_list":
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
        ]
        
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

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
    # 📚 ሁሉንም ይዘቶች ማየት
    # ================================================================
    elif data == "admin_view_all":
        all_contents = db.get_all_contents()
        if not all_contents:
            await query.edit_message_text("📭 ምንም ይዘት የለም።")
            return
        
        for content in all_contents:
            sales_count = db.get_content_sales_count(content['id'])
            status_emoji = "✅" if content['status'] == 'approved' else ("⏳" if content['status'] == 'pending' else "❌")
            caption = (
                f"📌 **{content['title']}**\n"
                f"🆔 ID: `{content['id']}`\n"
                f"👤 ደራሲ ID: {content['author_id']}\n"
                f"💰 {content['price']} ETB\n"
                f"📊 ሽያጭ: {sales_count}\n"
                f"📝 ሁኔታ: {status_emoji} {content['status']}\n"
                f"📄 ፋይል: `{content['file_path']}`"
            )
            keyboard = [[
                InlineKeyboardButton("📥 አውርድ", callback_data=f"admin_dl_{content['id']}"),
                InlineKeyboardButton("📝 አርትዕ", callback_data=f"admin_edit_{content['id']}")
            ]]
            await context.bot.send_message(
                chat_id=user_id,
                text=caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        await query.edit_message_text("✅ ሁሉም ይዘቶች ተልከዋል።")

    # ================================================================
    # 📥 ፋይል ማውረድ
    # ================================================================
    elif data.startswith("admin_dl_"):
        content_id = data.split("_")[2]
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

    # ================================================================
    # 📊 አጠቃላይ ሽያጭ ሪፖርት
    # ================================================================
    elif data == "admin_sales_report":
        all_contents = db.get_all_contents()
        total_income = 0.0
        lines = ["📊 **አጠቃላይ የሽያጭ ሪፖርት**", ""]
        for content in all_contents:
            sales = db.get_content_sales_count(content['id'])
            income = sales * content['price']
            total_income += income
            lines.append(f"📌 {content['title']} — {sales} ጊዜ — {income} ETB")
        lines.append("")
        lines.append(f"💰 **ጠቅላላ ገቢ:** {total_income} ETB")
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown")

    # ================================================================
    # 👤 በግምገማ ላይ ያሉ ደራሲያን
    # ================================================================
    elif data == "admin_pending_authors":
        conn = db._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, biography FROM authors WHERE status = 'pending'")
        authors = cursor.fetchall()
        conn.close()
        
        if not authors:
            await query.edit_message_text("✅ በግምገማ ላይ ያሉ ደራሲያን የሉም።")
            return
        
        for author in authors:
            msg = (
                f"👤 **ደራሲ ID:** `{author['user_id']}`\n"
                f"📝 ባዮግራፊ: {author['biography']}"
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

    # ================================================================
    # ✅/❌ ደራሲ ማጽደቅ/መከልከል
    # ================================================================
    elif data.startswith("admin_app_auth_"):
        target_id = int(data.split("_")[3])
        db.approve_author(target_id)
        await query.edit_message_text(f"✅ ደራሲ `{target_id}` ጽድቋል!")
        await context.bot.send_message(
            chat_id=target_id,
            text="🎉 የደራሲነት ማመልከቻዎ ተጽድቋል! አሁን ይዘቶችን መጫን ይችላሉ።"
        )

    elif data.startswith("admin_rej_auth_"):
        target_id = int(data.split("_")[3])
        db.reject_author(target_id)
        await query.edit_message_text(f"❌ ደራሲ `{target_id}` ተከልክሏል።")

    # ================================================================
    # 📝 በግምገማ ላይ ያሉ ይዘቶች
    # ================================================================
    elif data == "admin_pending_books":
        conn = db._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM contents WHERE status = 'pending'")
        books = cursor.fetchall()
        conn.close()
        
        if not books:
            await query.edit_message_text("✅ በግምገማ ላይ ያሉ ይዘቶች የሉም።")
            return
        
        for book in books:
            caption = (
                f"📌 **{book['title']}**\n"
                f"🆔 ID: `{book['id']}`\n"
                f"👤 ደራሲ ID: {book['author_id']}\n"
                f"💰 {book['price']} ETB\n"
                f"📝 {book['description']}"
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

    # ================================================================
    # ✅/❌ ይዘት ማጽደቅ/መከልከል
    # ================================================================
    elif data.startswith("admin_app_book_"):
        book_id = int(data.split("_")[3])
        res = db.approve_content(book_id)
        await query.edit_message_text(f"✅ ይዘት `{book_id}` ጽድቋል!")
        if res:
            author_id, title = res
            await context.bot.send_message(
                chat_id=author_id,
                text=f"🎉 '{title}' የተሰኘው ይዘትዎ ተጽድቋል!"
            )

    elif data.startswith("admin_rej_book_"):
        book_id = int(data.split("_")[3])
        res = db.reject_content(book_id)
        await query.edit_message_text(f"❌ ይዘት `{book_id}` ተከልክሏል።")
        if res:
            author_id, title = res
            await context.bot.send_message(
                chat_id=author_id,
                text=f"😔 '{title}' የተሰኘው ይዘትዎ ተከልክሏል።"
            )

    # ================================================================
    # 💳 በግምገማ ላይ ያሉ ክፍያዎች
    # ================================================================
    elif data == "admin_pending_payments":
        conn = db._connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.*, c.title FROM orders o
            JOIN contents c ON o.content_id = c.id
            WHERE o.status = 'pending'
        """)
        payments = cursor.fetchall()
        conn.close()
        
        if not payments:
            await query.edit_message_text("✅ በግምገማ ላይ ያሉ ክፍያዎች የሉም።")
            return
        
        for payment in payments:
            msg = (
                f"💳 **ክፍያ**\n"
                f"📌 ይዘት: {payment['title']}\n"
                f"👤 ተጠቃሚ ID: {payment['user_id']}\n"
                f"💰 {payment['amount']} ETB\n"
                f"📝 Ref: `{payment['payment_ref']}`"
            )
            keyboard = [[
                InlineKeyboardButton("✅ አጽድቅ", callback_data=f"admin_app_pay_{payment['user_id']}_{payment['content_id']}_{payment['payment_ref']}"),
                InlineKeyboardButton("❌ ውድቅ", callback_data=f"admin_rej_pay_{payment['user_id']}_{payment['content_id']}")
            ]]
            await context.bot.send_message(
                chat_id=user_id,
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        await query.edit_message_text("✅ በግምገማ ላይ ያሉ ክፍያዎች ተልከዋል።")

    # ================================================================
    # ✅/❌ ክፍያ ማጽደቅ/መከልከል
    # ================================================================
    elif data.startswith("admin_app_pay_"):
        parts = data.split("_")
        target_uid = int(parts[3])
        content_id = int(parts[4])
        tx_ref = parts[5]
        
        db.approve_payment(target_uid, content_id, tx_ref)
        await query.edit_message_text(f"✅ ክፍያ ጽድቋል!")
        
        book = db.get_content_by_id(content_id)
        if book and os.path.exists(book['file_path']):
            async with aiofiles.open(book['file_path'], 'rb') as f:
                file_data = await f.read()
            await context.bot.send_document(
                chat_id=target_uid,
                document=file_data,
                filename=os.path.basename(book['file_path']),
                caption="✅ ክፍያዎ ጽድቋል! ይህንን ይዘት በደህና ያውርዱ።"
            )

    elif data.startswith("admin_rej_pay_"):
        target_uid = int(data.split("_")[3])
        content_id = int(data.split("_")[4])
        db.reject_payment(target_uid, content_id)
        await query.edit_message_text(f"❌ ክፍያ ውድቅ ተደርጓል።")
        await context.bot.send_message(
            chat_id=target_uid,
            text="❌ ያስገቡት የክፍያ ማረጋገጫ ቁጥር ተከልክሏል። እባክዎ እንደገና ይሞክሩ።"
        )

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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """የአድሚን ቦት የጽሑፍ መልዕክት አያያዥ"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ፈቃድ የለዎትም")
        return
    
    text = update.message.text.strip()
    action = context.user_data.get('admin_action')
    
    # ================================================================
    # 🔍 ተጠቃሚ ፈልግ
    # ================================================================
    if action == 'find_user':
        users = db.search_users(text)
        if not users:
            await update.message.reply_text("❌ ምንም ተጠቃሚ አልተገኘም።")
        else:
            msg = "🔍 **የተገኙ ተጠቃሚዎች**\n\n"
            for user in users:
                msg += f"• `{user['telegram_id']}` - {user['first_name'] or 'N/A'} (@{user['username'] or 'N/A'})\n"
            await update.message.reply_text(msg, parse_mode="Markdown")
        
        context.user_data['admin_action'] = None
        await start(update, context)

    # ================================================================
    # 📢 Broadcast
    # ================================================================
    elif action == 'broadcast':
        import asyncio
        users = db.get_all_users()
        
        await update.message.reply_text(f"⏳ ለ {len(users)} ተጠቃሚዎች እየተላከ ነው...")
        
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
            except:
                failed += 1
            
            # የሬቲት ሊሚት ለማስወገድ
            if i % 30 == 0:
                await asyncio.sleep(1)
        
        await update.message.reply_text(
            f"✅ መልእክቱ ተልኳል!\n"
            f"📤 የተሳካ: {success}\n"
            f"❌ ያልተሳካ: {failed}"
        )
        context.user_data['admin_action'] = None
        await start(update, context)

    # ================================================================
    # 📊 የደራሲ ሽያጭ ፈልግ
    # ================================================================
    elif action == 'find_author':
        try:
            author_id = int(text)
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
        
        context.user_data['admin_action'] = None
        await start(update, context)

    # ================================================================
    # 📥 ፋይል በID አውርድ
    # ================================================================
    elif action == 'download_by_id':
        try:
            content_id = int(text)
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
        
        context.user_data['admin_action'] = None
        await start(update, context)
    
    else:
        await update.message.reply_text("❌ ያልታወቀ ትዕዛዝ። እባክዎ /start ይጫኑ።")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """የአሁኑን ድርጊት ይሰርዛል"""
    context.user_data['admin_action'] = None
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
    
    print("👑 Admin Bot በተሳካ ሁኔታ ተነስቷል...")
    app.run_polling()

if __name__ == "__main__":
    main()
