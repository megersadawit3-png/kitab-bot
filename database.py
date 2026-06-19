"""
ðŸ—„ï¸ database.py â€” á‹¨Kitab á‰¦á‰µ á‰¥á‰¸áŠ› á‹¨á‹³á‰³á‰¤á‹ áˆáŠ•áŒ­ (Single Source of Truth)

á‹­áˆ… á‹á‹­áˆ á‰€á‹°áˆ áˆ²áˆ á‰  bot.py á‹áˆµáŒ¥ á‰°á‰ á‰³á‰µáŠá‹ á‹¨áŠá‰ áˆ©á‰µáŠ• áˆáˆ‰áŠ•áˆ á‹¨ SQLite áˆáŠ•áŠ­áˆ½áŠ–á‰½ á‹­á‹­á‹›áˆá¢
bot.py áˆáŠ•áˆ áŠ á‹­áŠá‰µ á‰€áŒ¥á‰°áŠ› sqlite3.connect() áŒ¥áˆª áˆ˜á‹«á‹ á‹¨áˆˆá‰ á‰µáˆ â€” áˆáˆ‰áˆ á‰ á‹šáˆ… á‹á‹­áˆ
á‰ áŠ©áˆ á‰¥á‰» á‹«áˆá‹áˆá¢ á‹­áˆ…áˆá¦
  â€¢ á‹¨áˆµáŠªáˆ› áˆáŠ•áŒ­ áŠ áŠ•á‹µ á‰¥á‰» áŠ¥áŠ•á‹²áˆ†áŠ• (á‹µáˆ­á‰¥áˆ­á‰¥/áŒáŒ­á‰µ áŠ¥áŠ•á‹³á‹­áˆáŒ áˆ­)
  â€¢ á‰¦á‰µ-áˆŽáŒ‚áŠ­ áŠ¨ DB-áˆŽáŒ‚áŠ­ áŠ¥áŠ•á‹²áˆˆá‹­
  â€¢ áˆˆá‹ˆá‹°áŠá‰µ áˆˆá‹áŒ¥/áˆ™áŠ¨áˆ« (testing) á‰€áˆ‹áˆ áŠ¥áŠ•á‹²áˆ†áŠ• á‹«á‹°áˆ­áŒ‹áˆá¢

ðŸ“Œ áˆ›áˆµá‰³á‹ˆáˆ»á¦ á‹­áˆ… áŠ•áŒ¹áˆ… "Refactor" á‰¥á‰» áŠá‹ â€” áˆáŠ•áˆ áŠ á‹²áˆµ á‰£áˆ…áˆª (feature) á‹ˆá‹­áˆ á‹¨áˆ´áŠ©áˆªá‰²
áˆ›áˆµá‰°áŠ«áŠ¨á‹« áŠ áˆá‰°áŒ¨áˆ˜áˆ¨áˆá¢ á‰¦á‰± áˆáŠ­ áŠ¨á‹šáˆ… á‰ áŠá‰µ áŠ¥áŠ•á‹°áŠá‰ áˆ¨á‹ á‰ á‰°áˆ˜áˆ³áˆ³á‹­ áˆ˜áŠ•áŒˆá‹µ á‹­áˆ°áˆ«áˆá¢
"""

import sqlite3
import os
import logging
from config import DB_NAME


# =====================================================================
# ðŸ”Œ á‹¨áŒáŠ•áŠ™áŠá‰µ áˆ¨á‹³á‰µ (CONNECTION HELPER)
# =====================================================================
def _connect():
    """Row factory á‹¨á‰°á‹˜áŒ‹áŒ€áˆˆá‰µ connection á‹­áˆ˜áˆáˆ³áˆ (dict-like access áˆˆ rows)."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# =====================================================================
# ðŸ—ï¸ áˆµáŠªáˆ› áˆ˜ááŒ áˆªá‹« (SCHEMA INITIALIZATION)
# =====================================================================
def init_db():
    """
    áˆáˆ‰áŠ•áˆ áŒ áˆ¨áŒ´á‹›á‹Žá‰½ á‹­áˆáŒ¥áˆ«áˆá¢ áŠ¨á‹šáˆ… á‰€á‹°áˆ bot.py áˆ‹á‹­ á‹¨áŠá‰ áˆ¨á‹ "á‹¨á‹µáˆ®/á‹¨á‰°á‰ áˆ‹áˆ¸ áˆµáŠªáˆ› áŠ«áˆˆ
    áŠ áŒ¥á‹á‹" áˆŽáŒ‚áŠ­ áŠ¥áŠ•á‹³áˆˆ á‰°áŒ á‰¥á‰‹áˆá¢
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
                logging.info("ðŸ§¹ á‹¨á‹µáˆ®á‹ á‹¨á‰°áˆ³áˆ³á‰° á‹¨á‹³á‰³á‰¤á‹ áŠ á‹ˆá‰ƒá‰€áˆ­ á‰ á‰°áˆ³áŠ« áˆáŠ”á‰³ á‰°á‹ˆáŒá‹·áˆá¢")
            except Exception as e:
                logging.error(f"á‹¨á‹µáˆ®á‹áŠ• á‹³á‰³á‰¤á‹ áˆ›áŒ¥á‹á‰µ áŠ áˆá‰°á‰»áˆˆáˆ: {e}")

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
    # ðŸ“Œ payment_ref áˆ‹á‹­ UNIQUE áˆ›á‹µáˆ¨áŒ á‹¨áŠá‰ áˆ¨á‰¥áŠ• á‰¢áˆ†áŠ•áˆá£ á‹­áˆ… á‹¨á‰£áˆ…áˆª áˆˆá‹áŒ¥ áˆµáˆˆáˆšá‹«áˆµáŠ¨á‰µáˆ
    # (á‹«á‹ refactor á‰¥á‰» áŠ¥áŠ•á‹²áˆ†áŠ• áˆµáˆˆáˆáˆˆáŒáˆ…) áˆ†áŠ• á‰¥áˆˆáŠ• áŠ¥áŠ•á‹³áˆˆ "non-unique" á‰µá‰°áŠá‹‹áˆá¢
    # áˆˆá‹ˆá‹°áŠá‰µ security pass áˆµáŠ•áˆ°áˆ« áŠ á‰¥áˆ¨áŠ• áŠ¥áŠ•áŒ¨áˆáˆ¨á‹‹áˆˆáŠ•á¢
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
    conn.commit()
    conn.close()


# =====================================================================
# ðŸ‘¤ á‹¨á‰°áŒ á‰ƒáˆš áˆáŠ•áŠ­áˆ½áŠ–á‰½ (USER FUNCTIONS)
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
# âœï¸ á‹¨á‹°áˆ«áˆ² áˆáŠ•áŠ­áˆ½áŠ–á‰½ (AUTHOR FUNCTIONS)
# =====================================================================
def is_user_author(telegram_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM authors WHERE user_id = ? AND status = 'approved'", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def get_author_application_status(telegram_id):
    """á‹°áˆ«áˆ²á‹ 'pending'/'approved'/'rejected' á‹ˆá‹­áˆ áŒ¨áˆ­áˆ¶ á‹«áˆ‹áˆ˜áˆˆáŠ¨á‰° áŠ¨áˆ†áŠ None á‹­áˆ˜áˆáˆ³áˆá¢"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM authors WHERE user_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def register_author_pending(user_id, bio):
    """áŠ á‹²áˆµ á‹¨á‹°áˆ«áˆ²áŠá‰µ áˆ›áˆ˜áˆáŠ¨á‰» á‰ 'pending' áˆáŠ”á‰³ á‹­áˆ˜á‹˜áŒá‰£áˆ (á‰€á‹µáˆž áŠ«áˆˆ á‰½áˆ‹ á‹­áˆˆá‹‹áˆ)."""
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
# ðŸ“š á‹¨á‹­á‹˜á‰µ áˆáŠ•áŠ­áˆ½áŠ–á‰½ (CONTENT FUNCTIONS)
# =====================================================================
def add_content(author_id, title, category, description, price, file_path):
    """áŠ á‹²áˆµ á‹­á‹˜á‰µ (pending áˆáŠ”á‰³) á‹­áˆ˜á‹˜áŒá‰£áˆ áŠ¥áŠ“ á‹¨á‰°áˆáŒ áˆ¨á‹áŠ• id á‹­áˆ˜áˆáˆ³áˆá¢"""
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
    """áˆˆ 'handle_message' exact-match ááˆˆáŒ‹ (áˆµáˆ á‰¥á‰» á‰ á‰µáŠ­áŠ­áˆ áˆ²áŒ»á)."""
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
    """á‹­á‹˜á‰±áŠ• 'approved' á‹«á‹°áˆ­áŒ‹áˆ áŠ¥áŠ“ (author_id, title) á‹­áˆ˜áˆáˆ³áˆ (áˆˆáˆ›áˆ³á‹ˆá‰‚á‹«)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE contents SET status = 'approved' WHERE id = ?", (content_id,))
    cursor.execute("SELECT author_id, title FROM contents WHERE id = ?", (content_id,))
    res = cursor.fetchone()
    conn.commit()
    conn.close()
    return res  # (author_id, title) á‹ˆá‹­áˆ None


def reject_content(content_id):
    """á‹­á‹˜á‰±áŠ• 'rejected' á‹«á‹°áˆ­áŒ‹áˆ áŠ¥áŠ“ (author_id, title) á‹­áˆ˜áˆáˆ³áˆ (áˆˆáˆ›áˆ³á‹ˆá‰‚á‹«)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE contents SET status = 'rejected' WHERE id = ?", (content_id,))
    cursor.execute("SELECT author_id, title FROM contents WHERE id = ?", (content_id,))
    res = cursor.fetchone()
    conn.commit()
    conn.close()
    return res


# =====================================================================
# ðŸ›’ á‹¨áŒá‹¢/á‰µá‹•á‹›á‹ áˆáŠ•áŠ­áˆ½áŠ–á‰½ (ORDER FUNCTIONS)
# =====================================================================
def add_order(user_id, content_id, amount, payment_ref, status="pending"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orders (user_id, content_id, amount, payment_ref, status)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, content_id, amount, payment_ref, status))
    conn.commit()
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


# =====================================================================
# ðŸ‘‘ á‹¨áŠ á‹µáˆšáŠ• á“áŠáˆ áˆ¨á‹³á‰¶á‰½ (ADMIN PANEL HELPERS)
# =====================================================================
def get_pending_counts():
    """(pending_books, pending_authors, pending_payments) á‹­áˆ˜áˆáˆ³áˆ â€” áˆˆ admin_panel."""
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
