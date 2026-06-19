import logging
import os
import aiofiles
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from config import ADMIN_BOT_TOKEN, ADMIN_ID
import database as db

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


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
        [InlineKeyboardButton("👤 በግምገማ ላይ ያሉ ደራሲያን", callback_data="admin_pending_authors")],
        [InlineKeyboardButton("📝 በግምገማ ላይ ያሉ ይዘቶች", callback_data="admin_pending_books")],
        [InlineKeyboardButton("💳 በግምገማ ላይ ያሉ ክፍያዎች", callback_data="admin_pending_payments")],
        [InlineKeyboardButton("📊 የደራሲ ሽያጭ ፈልግ", callback_data="admin_find_author")],
        [InlineKeyboardButton("📥 ፋይል አውርድ (በID)", callback_data="admin_download_by_id")],
    ]
    await update.message.reply_text(
        "👑 **Kitab Admin Bot**\n\nከታች ካሉት አማራጮች ይምረጡ፦",
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

    # --- ሁሉንም ይዘቶች ማየት ---
    if data == "admin_view_all":
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

    # --- ፋይል ማውረድ ---
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

    # --- አጠቃላይ ሽያጭ ሪፖርት ---
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

    # --- በግምገማ ላይ ያሉ ደራሲያን ---
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

    # --- ደራሲ ማጽደቅ/መከልከል ---
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

    # --- በግምገማ ላይ ያሉ ይዘቶች ---
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

    # --- ይዘት ማጽደቅ/መከልከል ---
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

    # --- በግምገማ ላይ ያሉ ክፍያዎች ---
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

    # --- ክፍያ ማጽደቅ/መከልከል ---
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

    # --- የደራሲ ሽያጭ ፈልግ ---
    elif data == "admin_find_author":
        await query.edit_message_text(
            "👤 የደራሲውን ቴሌግራም መታወቂያ (ID) ያስገቡ፦\n\n"
            "ለምሳሌ: `123456789`\n\n"
            "ወይም /cancel በማለት ይቅሩ።"
        )
        context.user_data['admin_action'] = 'find_author'
        return

    # --- ፋይል በID አውርድ ---
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
    
    if action == 'find_author':
        try:
            author_id = int(text)
            sales_data = db.get_author_sales(author_id)
            
            if not sales_data['contents']:
                await update.message.reply_text(f"📭 ደራሲ `{author_id}` ምንም ይዘት የለውም።")
            else:
                lines = [f"📊 **የደራሲ {author_id} ሽያጭ ሪፖርት**", ""]
                for item in sales_data['contents']:
                    lines.append(f"📌 {item['title']} — {item['sales_count']} ጊዜ — {item['income']} ETB")
                lines.append("")
                lines.append(f"💰 **ጠቅላላ ገቢ:** {sales_data['total_income']} ETB")
                await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("❌ እባክዎ ትክክለኛ ቁጥር ያስገቡ።")
        
        context.user_data['admin_action'] = None
        await start(update, context)
    
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
