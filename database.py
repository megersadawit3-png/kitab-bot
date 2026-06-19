
import sqlite3
import os
import logging
from config import DB_NAME


# =====================================================================
# 🔌 የግንኙነት ረዳት (CONNECTION HELPER)
# =====================================================================
def _connect():
    """Row factory የተዘጋጀለት connection ይመልሳል (dict-like access ለ rows)."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# =====================================================================
# 🏗️ ስኪማ መፍጠሪያ (SCHEMA INITIALIZATION)
# =====================================================================
def init_db():
    """
    ሁሉንም ጠረጴዛዎች ይፈጥራል። ከዚህ ቀደም bot.py ላይ የነበረው "የድሮ/የተበላሸ ስኪማ ካለ
    አጥፋው" ሎጂክ እንዳለ ተጠብቋል።
    """
    if os.path.exists(DB_NAME):
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT telegram_id FROM users LIMIT 1")
            conn.close()
        except sqlite3.OperationalError:
            conn.close()
            try:
                os.remove(DB_NAME)
                logging.info("🧹 የድሮው የተሳሳተ የዳታቤዝ አወቃቀር በተሳካ ሁኔታ ተወግዷል።")
            except Exception as e:
                logging.error(f"የድሮውን ዳታቤዝ ማጥፋት አልተቻለም: {e}")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            language TEXT DEFAULT 'am',
            phone TEXT
        )
    ''')

    # 2. Authors
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS authors (
            user_id INTEGER PRIMARY KEY,
            status TEXT DEFAULT 'pending',
            biography TEXT
        )
    ''')

    # 3. Contents
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_id INTEGER,
            title TEXT,
            category TEXT,
            description TEXT,
            price REAL,
            file_path TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')

    # 4. Orders
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content_id INTEGER,
            amount REAL,
            payment_ref TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')

    # 📌 [Security Fix] payment_ref (የቴሌብር ግብይት ቁጥር) ድግግሞሽ/ስርቆት እንዳይፈጠር
    # UNIQUE INDEX እንጨምራለን። 'FREE_DOWNLOAD' ግን በብዙ ተጠቃሚዎች ስለሚደጋገም ከዚህ
    # ውጪ እናደርገዋለን (partial index)። CREATE UNIQUE INDEX ቀደም ሲል በነበረ
    # ዳታቤዝ ላይም ደህንነቱ በተጠበቀ መንገድ ይሰራል (migration-safe)።
    try:
        cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_unique_payment_ref
            ON orders(payment_ref)
            WHERE payment_ref != 'FREE_DOWNLOAD'
        ''')
    except sqlite3.IntegrityError:
        logging.warning(
            "⚠️ payment_ref ላይ የተደጋገመ ውሂብ ስላለ UNIQUE INDEX መፍጠር አልተቻለም። "
            "እባክዎ orders ጠረጴዛ ላይ ያሉ duplicate payment_ref ዎችን በእጅ ያጽዱ።"
        )

    conn.commit()
    conn.close()


# =====================================================================
# 👤 የተጠቃሚ ፈንክሽኖች (USER FUNCTIONS)
# =====================================================================
def get_user_lang(telegram_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT language FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if (row and row[0]) else "am"


def set_user_lang(telegram_id, lang):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET language = ? WHERE telegram_id = ?", (lang, telegram_id))
    conn.commit()
    conn.close()


def save_user_info(telegram_id, username, first_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (telegram_id, username, first_name)
        VALUES (?, ?, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET username=EXCLUDED.username, first_name=EXCLUDED.first_name
    """, (telegram_id, username, first_name))
    conn.commit()
    conn.close()


def set_user_phone(telegram_id, phone):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET phone = ? WHERE telegram_id = ?", (phone, telegram_id))
    conn.commit()
    conn.close()


# =====================================================================
# ✍️ የደራሲ ፈንክሽኖች (AUTHOR FUNCTIONS)
# =====================================================================
def is_user_author(telegram_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM authors WHERE user_id = ? AND status = 'approved'", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def get_author_application_status(telegram_id):
    """ደራሲው 'pending'/'approved'/'rejected' ወይም ጨርሶ ያላመለከተ ከሆነ None ይመልሳል።"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM authors WHERE user_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def register_author_pending(user_id, bio):
    """አዲስ የደራሲነት ማመልከቻ በ'pending' ሁኔታ ይመዘግባል (ቀድሞ ካለ ችላ ይለዋል)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO authors (user_id, status, biography) VALUES (?, 'pending', ?)",
        (user_id, bio)
    )
    conn.commit()
    conn.close()


def approve_author(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE authors SET status = 'approved' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def reject_author(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE authors SET status = 'rejected' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


# =====================================================================
# 📚 የይዘት ፈንክሽኖች (CONTENT FUNCTIONS)
# =====================================================================
def add_content(author_id, title, category, description, price, file_path):
    """አዲስ ይዘት (pending ሁኔታ) ይመዘግባል እና የተፈጠረውን id ይመልሳል።"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO contents (author_id, title, category, description, price, file_path, status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending')
    """, (author_id, title, category, description, price, file_path))
    inserted_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return inserted_id


def get_contents_by_category(category):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contents WHERE category = ? AND status = 'approved'", (category,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_content_by_id(content_id):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contents WHERE id = ?", (content_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_content_by_title(title):
    """ለ 'handle_message' exact-match ፍለጋ (ስም ብቻ በትክክል ሲጻፍ)."""
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contents WHERE LOWER(title) = LOWER(?) AND status = 'approved'", (title,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def execute_search_query(query_text):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM contents WHERE (title LIKE ? OR description LIKE ?) AND status = 'approved'",
        (f"%{query_text}%", f"%{query_text}%")
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def approve_content(content_id):
    """ይዘቱን 'approved' ያደርጋል እና (author_id, title) ይመልሳል (ለማሳወቂያ)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE contents SET status = 'approved' WHERE id = ?", (content_id,))
    cursor.execute("SELECT author_id, title FROM contents WHERE id = ?", (content_id,))
    res = cursor.fetchone()
    conn.commit()
    conn.close()
    return res  # (author_id, title) ወይም None


def reject_content(content_id):
    """ይዘቱን 'rejected' ያደርጋል እና (author_id, title) ይመልሳል (ለማሳወቂያ)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE contents SET status = 'rejected' WHERE id = ?", (content_id,))
    cursor.execute("SELECT author_id, title FROM contents WHERE id = ?", (content_id,))
    res = cursor.fetchone()
    conn.commit()
    conn.close()
    return res


# =====================================================================
# 🛒 የግዢ/ትዕዛዝ ፈንክሽኖች (ORDER FUNCTIONS)
# =====================================================================
def add_order(user_id, content_id, amount, payment_ref, status="pending"):
    """
    አዲስ ትዕዛዝ ይመዘግባል። payment_ref ቀድሞ ጥቅም ላይ ከዋለ (UNIQUE constraint ቢጣስ)
    False ይመልሳል፣ ካልሆነ True ይመልሳል — ጠሪው (caller) ለተጠቃሚው "ይህ ቁጥር ቀድሞ
    ጥቅም ላይ ውሏል" ብሎ ማሳወቅ ይችላል።
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO orders (user_id, content_id, amount, payment_ref, status)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, content_id, amount, payment_ref, status))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        conn.rollback()
        return False
    finally:
        conn.close()


def approve_payment(user_id, content_id, payment_ref):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE orders SET status = 'approved' WHERE user_id = ? AND content_id = ? AND payment_ref = ?",
        (user_id, content_id, payment_ref)
    )
    conn.commit()
    conn.close()


def reject_payment(user_id, content_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE orders SET status = 'rejected' WHERE user_id = ? AND content_id = ?",
        (user_id, content_id)
    )
    conn.commit()
    conn.close()


def get_user_library(telegram_id):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.* FROM contents c
        JOIN orders o ON c.id = o.content_id
        WHERE o.user_id = ? AND o.status = 'approved'
    """, (telegram_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def user_owns_content(telegram_id, content_id):
    """
    📌 [Security Fix] ተጠቃሚው ይህን ይዘት በትክክል መግዛቱን (orders ላይ
    status='approved' ያለው መሆኑን) ያረጋግጣል። ለ 'download_' callback
    ownership ማረጋገጫ ይጠቅማል።
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM orders WHERE user_id = ? AND content_id = ? AND status = 'approved' LIMIT 1",
        (telegram_id, content_id)
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None


# =====================================================================
# 👑 የአድሚን ፓነል ረዳቶች (ADMIN PANEL HELPERS)
# =====================================================================
def get_pending_counts():
    """(pending_books, pending_authors, pending_payments) ይመልሳል — ለ admin_panel."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM contents WHERE status = 'pending'")
    pending_books = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM authors WHERE status = 'pending'")
    pending_authors = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
    pending_payments = cursor.fetchone()[0]

    conn.close()
    return pending_books, pending_authors, pending_payments
  
