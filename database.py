"""
🗄️ database.py — የKitab ቦት ብቸኛ የዳታቤዝ ምንጭ (Single Source of Truth)

ይህ ፋይል የሚከተሉትን ሁሉም የውሂብ ጎታ ተግባራት ይይዛል፦
1. መሰረታዊ ሠንጠረዦች (ተጠቃሚ፣ ደራሲ፣ ይዘት፣ ትዕዛዝ)
2. DRM ማመስጠር ስርዓት (አድሚኑ ከቦቱ ውጪ የሚያመስጥርበት)
3. የክፍያ ስርዓት (ቀጥታ ወደ ደራሲ እና ወደ አድሚን)
4. የአገልግሎት ክፍያ ስርዓት (በየ50 ሽያጭ)
"""

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
    ሁሉንም ጠረጴዛዎች ይፈጥራል።
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

    # ================================================================
    # 1. መሰረታዊ ሠንጠረዦች (Core Tables)
    # ================================================================

    # 1.1 Users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            language TEXT DEFAULT 'am',
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 1.2 Authors
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS authors (
            user_id INTEGER PRIMARY KEY,
            status TEXT DEFAULT 'pending',
            biography TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 1.3 Contents (ዋናው ይዘት ሠንጠረዥ)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            price REAL DEFAULT 0,
            file_path TEXT,
            encrypted_file_path TEXT,
            status TEXT DEFAULT 'pending_encryption',
            -- status values:
            -- pending_encryption: ለአድሚን መመስጠር ይጠበቃል
            -- pending_author_approval: ተመስጥሮ ለደራሲ ማጽደቅ ይጠበቃል
            -- approved: ጸድቋል እና ለሽያጭ ዝግጁ ነው
            -- rejected: ውድቅ ተደርጓል
            -- blocked: በአገልግሎት ክፍያ ምክንያት ታግዷል
            encryption_date TIMESTAMP,
            author_approval_date TIMESTAMP,
            author_approval_notes TEXT,
            sales_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 1.4 Orders (ትዕዛዞች)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_ref TEXT,
            status TEXT DEFAULT 'pending',
            -- status values: pending, paid, rejected, cancelled
            payment_type TEXT DEFAULT 'author',
            -- payment_type: 'author' (ወደ ደራሲ ቀጥታ), 'admin' (ወደ አድሚን)
            paid_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # UNIQUE INDEX for payment_ref
    try:
        cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_unique_payment_ref
            ON orders(payment_ref)
            WHERE payment_ref != 'FREE_DOWNLOAD'
        ''')
    except sqlite3.IntegrityError:
        logging.warning(
            "⚠️ payment_ref ላይ የተደጋገመ ውሂብ ስላለ UNIQUE INDEX መፍጠር አልተቻለም።"
        )

    # ================================================================
    # 2. DRM ማመስጠር ስርዓት ሠንጠረዦች
    # ================================================================

    # 2.1 Encryption Logs (የማመስጠር ታሪክ)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS encryption_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER NOT NULL,
            admin_id INTEGER NOT NULL,
            original_file_path TEXT,
            encrypted_file_path TEXT,
            encrypted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
    ''')

    # ================================================================
    # 3. የክፍያ ስርዓት ሠንጠረዦች
    # ================================================================

    # 3.1 Author Payments (ቀጥታ ወደ ደራሲ ክፍያ - ለመጻሕፍት)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS author_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            author_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            receipt_link TEXT,
            receipt_ref TEXT,
            admin_verified BOOLEAN DEFAULT 0,
            admin_verified_at TIMESTAMP,
            admin_notes TEXT,
            status TEXT DEFAULT 'pending',
            -- status: pending, pending_admin, verified, rejected, completed
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 3.2 Admin Payments (ወደ አድሚን ክፍያ - ለHandouts እና Question Bank)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            receipt_link TEXT,
            receipt_ref TEXT,
            admin_verified BOOLEAN DEFAULT 0,
            admin_verified_at TIMESTAMP,
            admin_notes TEXT,
            status TEXT DEFAULT 'pending',
            -- status: pending, pending_admin, verified, rejected, completed
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ================================================================
    # 4. የአገልግሎት ክፍያ ስርዓት ሠንጠረዦች
    # ================================================================

    # 4.1 Service Fees (የአገልግሎት ክፍያ መከታተያ)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS service_fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_id INTEGER NOT NULL,
            content_id INTEGER NOT NULL,
            sales_count INTEGER DEFAULT 0,
            fee_due INTEGER DEFAULT 50,
            -- fee_due: ክፍያ የሚጠበቀው የሽያጭ ብዛት (ቀጣዩ 50 ገደብ)
            fee_paid BOOLEAN DEFAULT 0,
            fee_amount REAL DEFAULT 0,
            fee_paid_at TIMESTAMP,
            content_blocked BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 4.2 Content Blocks (የታገዱ ይዘቶች ታሪክ)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS content_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER NOT NULL,
            author_id INTEGER NOT NULL,
            blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            unblocked_at TIMESTAMP,
            reason TEXT,
            blocked_by INTEGER
        )
    ''')

    # 4.3 Service Fee Payments (የአገልግሎት ክፍያ ክፍያ ታሪክ)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS service_fee_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_id INTEGER NOT NULL,
            content_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            receipt_link TEXT,
            receipt_ref TEXT,
            verified_by_admin BOOLEAN DEFAULT 0,
            verified_at TIMESTAMP,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ================================================================
    # 5. ሌሎች ረዳት ሠንጠረዦች
    # ================================================================

    # 5.1 Categories (ምድቦች)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 5.2 Notifications (ማሳወቂያዎች)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            title TEXT,
            content TEXT,
            is_read BOOLEAN DEFAULT 0,
            data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ================================================================
    # 📊 ማውጫዎች (Indexes)
    # ================================================================

    # ለፍለጋ ፍጥነት
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_contents_status ON contents(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_contents_author_id ON contents(author_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_contents_category ON contents(category)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_content_id ON orders(content_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_author_payments_status ON author_payments(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_author_payments_author_id ON author_payments(author_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_admin_payments_status ON admin_payments(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_service_fees_author_id ON service_fees(author_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_service_fees_content_blocked ON service_fees(content_blocked)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_content_blocks_content_id ON content_blocks(content_id)')

    conn.commit()
    conn.close()
    logging.info("✅ የውሂብ ጎታ ሁሉም ሠንጠረዦች በተሳካ ሁኔታ ተፈጥረዋል ወይም አሉ።")


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
    cursor.execute("UPDATE users SET language = ?, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?", (lang, telegram_id))
    conn.commit()
    conn.close()


def save_user_info(telegram_id, username, first_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (telegram_id, username, first_name)
        VALUES (?, ?, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET 
            username = EXCLUDED.username, 
            first_name = EXCLUDED.first_name,
            updated_at = CURRENT_TIMESTAMP
    """, (telegram_id, username, first_name))
    conn.commit()
    conn.close()


def set_user_phone(telegram_id, phone):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET phone = ?, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?", (phone, telegram_id))
    conn.commit()
    conn.close()


def get_user_by_id(telegram_id):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


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
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM authors WHERE user_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def register_author_pending(user_id, bio):
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
    cursor.execute("UPDATE authors SET status = 'approved', updated_at = CURRENT_TIMESTAMP WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def reject_author(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE authors SET status = 'rejected', updated_at = CURRENT_TIMESTAMP WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_author_by_user_id(user_id):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM authors WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# =====================================================================
# 📚 የይዘት ፈንክሽኖች (CONTENT FUNCTIONS)
# =====================================================================

def add_content(author_id, title, category, description, price, file_path):
    """
    አዲስ ይዘት በ'pending_encryption' ሁኔታ ይመዘግባል
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO contents (author_id, title, category, description, price, file_path, status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending_encryption')
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


def get_all_contents():
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contents ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_author_contents(author_id):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contents WHERE author_id = ? ORDER BY id DESC", (author_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# =====================================================================
# 🔐 DRM ማመስጠር ስርዓት ፈንክሽኖች (ADMIN HANDLES ENCRYPTION)
# =====================================================================

def get_contents_pending_encryption(limit=50):
    """
    ለመመስጠር የሚጠበቁ ይዘቶችን ይመልሳል (ለአድሚን)
    """
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, u.first_name as author_name, u.username as author_username
        FROM contents c
        JOIN authors a ON c.author_id = a.user_id
        JOIN users u ON a.user_id = u.telegram_id
        WHERE c.status = 'pending_encryption'
        ORDER BY c.created_at ASC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_content_with_encrypted_file(content_id, encrypted_file_path, admin_id, notes=""):
    """
    አድሚኑ የተመሰጠረውን ፋይል ከጫነ በኋላ ሁኔታውን ያዘምናል
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # ይዘቱን አዘምን
    cursor.execute("""
        UPDATE contents 
        SET encrypted_file_path = ?,
            encryption_date = CURRENT_TIMESTAMP,
            status = 'pending_author_approval',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND status = 'pending_encryption'
    """, (encrypted_file_path, content_id))
    affected = cursor.rowcount
    
    # በ encryption_logs ውስጥ መዝግብ
    cursor.execute("""
        INSERT INTO encryption_logs (content_id, admin_id, original_file_path, encrypted_file_path, notes)
        SELECT ?, ?, file_path, ?, ?
        FROM contents WHERE id = ?
    """, (content_id, admin_id, encrypted_file_path, notes, content_id))
    
    conn.commit()
    conn.close()
    return affected > 0


def get_contents_pending_author_approval(author_user_id, limit=50):
    """
    ለደራሲ ማጽደቅ የሚጠበቁ ይዘቶችን ይመልሳል
    """
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, u.first_name as author_name
        FROM contents c
        JOIN authors a ON c.author_id = a.user_id
        JOIN users u ON a.user_id = u.telegram_id
        WHERE c.status = 'pending_author_approval' AND a.user_id = ?
        ORDER BY c.encryption_date ASC
        LIMIT ?
    """, (author_user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def author_approve_content(content_id, notes=""):
    """
    ደራሲው ይዘቱን ያጸድቃል
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE contents 
        SET status = 'approved',
            author_approval_date = CURRENT_TIMESTAMP,
            author_approval_notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND status = 'pending_author_approval'
    """, (notes, content_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def author_reject_content(content_id, reason=""):
    """
    ደራሲው ይዘቱን ውድቅ ያደርጋል
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE contents 
        SET status = 'rejected',
            author_approval_date = CURRENT_TIMESTAMP,
            author_approval_notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND status = 'pending_author_approval'
    """, (reason, content_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def get_content_encryption_status(content_id):
    """
    የአንድ ይዘት የማመስጠር ሁኔታ ይመልሳል
    """
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT status, encrypted_file_path, encryption_date, author_approval_date
        FROM contents WHERE id = ?
    """, (content_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_original_file_path(content_id):
    """
    የዋናውን ፋይል መንገድ ይመልሳል (ለአድሚን ማውረድ)
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM contents WHERE id = ?", (content_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


# =====================================================================
# 💰 የክፍያ ስርዓት ፈንክሽኖች
# =====================================================================

# ---------- ጠቅላላ ተግባራት ----------

def is_book_content(content_id):
    """
    ይዘቱ መጽሐፍ (Book) መሆኑን ያረጋግጣል
    (Handouts እና Question Bank ሳይሆን)
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT category FROM contents WHERE id = ?", (content_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return False
    category = row[0]
    # መጽሐፍት: Literature, Education, Religion, History, Business, Technology
    book_categories = ['Literature', 'Education', 'Religion', 'History', 'Business', 'Technology']
    return category in book_categories


# ---------- የደራሲ ቀጥታ ክፍያ ----------

def create_author_payment(order_id, author_id, user_id, content_id, amount):
    """
    አዲስ የደራሲ ቀጥታ ክፍያ ይመዘግባል
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO author_payments (order_id, author_id, user_id, content_id, amount, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
    """, (order_id, author_id, user_id, content_id, amount))
    payment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return payment_id


def create_admin_payment(order_id, user_id, content_id, amount):
    """
    አዲስ የአድሚን ክፍያ ይመዘግባል (ለHandouts እና Question Bank)
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO admin_payments (order_id, user_id, content_id, amount, status)
        VALUES (?, ?, ?, ?, 'pending')
    """, (order_id, user_id, content_id, amount))
    payment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return payment_id


def submit_receipt_link(payment_id, receipt_link, receipt_ref, payment_type='author'):
    """
    ገዢው የቴሌብር ሪሲት ሊንክ ያስገባል
    payment_type: 'author' ወይም 'admin'
    """
    table = 'author_payments' if payment_type == 'author' else 'admin_payments'
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"""
        UPDATE {table}
        SET receipt_link = ?,
            receipt_ref = ?,
            status = 'pending_admin',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND status = 'pending'
    """, (receipt_link, receipt_ref, payment_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def get_pending_author_payments(limit=50):
    """
    አድሚን ሊያረጋግጣቸው የሚጠበቁ የደራሲ ክፍያዎች
    """
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ap.*, 
               u.first_name as buyer_name,
               u.username as buyer_username,
               c.title as content_title,
               c.category as content_category,
               a.user_id as author_user_id
        FROM author_payments ap
        JOIN users u ON ap.user_id = u.telegram_id
        JOIN contents c ON ap.content_id = c.id
        JOIN authors a ON ap.author_id = a.user_id
        WHERE ap.status = 'pending_admin'
        ORDER BY ap.created_at DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_pending_admin_payments(limit=50):
    """
    አድሚን ሊያረጋግጣቸው የሚጠበቁ የአድሚን ክፍያዎች (Handouts/Question Bank)
    """
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ap.*, 
               u.first_name as buyer_name,
               u.username as buyer_username,
               c.title as content_title,
               c.category as content_category
        FROM admin_payments ap
        JOIN users u ON ap.user_id = u.telegram_id
        JOIN contents c ON ap.content_id = c.id
        WHERE ap.status = 'pending_admin'
        ORDER BY ap.created_at DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def admin_verify_author_payment(payment_id, admin_notes=""):
    """
    አድሚኑ የደራሲ ክፍያውን ያረጋግጣል
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE author_payments 
        SET admin_verified = 1,
            admin_verified_at = CURRENT_TIMESTAMP,
            admin_notes = ?,
            status = 'verified',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND status = 'pending_admin'
    """, (admin_notes, payment_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    if affected > 0:
        _complete_payment(payment_id, 'author')
    return affected > 0


def admin_verify_admin_payment(payment_id, admin_notes=""):
    """
    አድሚኑ የአድሚን ክፍያውን ያረጋግጣል (Handouts/Question Bank)
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE admin_payments 
        SET admin_verified = 1,
            admin_verified_at = CURRENT_TIMESTAMP,
            admin_notes = ?,
            status = 'verified',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND status = 'pending_admin'
    """, (admin_notes, payment_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    if affected > 0:
        _complete_payment(payment_id, 'admin')
    return affected > 0


def admin_reject_payment(payment_id, payment_type='author', reason=""):
    """
    አድሚኑ ክፍያውን ውድቅ ያደርጋል
    """
    table = 'author_payments' if payment_type == 'author' else 'admin_payments'
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"""
        UPDATE {table}
        SET status = 'rejected',
            admin_notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND status = 'pending_admin'
    """, (reason, payment_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    if affected > 0:
        _reject_payment(payment_id, payment_type)
    return affected > 0


def _complete_payment(payment_id, payment_type):
    """
    ክፍያ ከተረጋገጠ በኋላ የሚሰራ (ውስጣዊ ተግባር)
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    table = 'author_payments' if payment_type == 'author' else 'admin_payments'
    
    # ትዕዛዙን ማዘመን
    cursor.execute(f"""
        UPDATE orders 
        SET status = 'paid', paid_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
        WHERE id = (SELECT order_id FROM {table} WHERE id = ?)
    """, (payment_id,))
    
    # የክፍያ ሁኔታ ማዘመን
    cursor.execute(f"""
        UPDATE {table} 
        SET status = 'completed', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (payment_id,))
    
    # የሽያጭ ብዛት መጨመር እና የአገልግሎት ክፍያ ማረጋገጥ (ለመጻሕፍት ብቻ)
    cursor.execute(f"""
        SELECT content_id, author_id FROM {table} WHERE id = ?
    """, (payment_id,))
    row = cursor.fetchone()
    if row:
        content_id, author_id = row
        # ይዘቱ መጽሐፍ መሆኑን ማረጋገጥ
        if is_book_content(content_id):
            increment_sales_count_and_check_fee(content_id, author_id)
    
    conn.commit()
    conn.close()


def _reject_payment(payment_id, payment_type):
    """
    ክፍያ ውድቅ ሲደረግ የሚሰራ (ውስጣዊ ተግባር)
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    table = 'author_payments' if payment_type == 'author' else 'admin_payments'
    
    cursor.execute(f"""
        UPDATE orders 
        SET status = 'rejected', updated_at = CURRENT_TIMESTAMP
        WHERE id = (SELECT order_id FROM {table} WHERE id = ?)
    """, (payment_id,))
    
    conn.commit()
    conn.close()


def get_author_payment_by_id(payment_id):
    """
    በመታወቂያ የደራሲ ክፍያ ያገኛል
    """
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM author_payments WHERE id = ?", (payment_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_admin_payment_by_id(payment_id):
    """
    በመታወቂያ የአድሚን ክፍያ ያገኛል
    """
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin_payments WHERE id = ?", (payment_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ---------- ትዕዛዞች ----------

def add_order(user_id, content_id, amount, payment_ref, payment_type='author', status="pending"):
    """
    አዲስ ትዕዛዝ ይመዘግባል
    payment_type: 'author' (ወደ ደራሲ) ወይም 'admin' (ወደ አድሚን)
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO orders (user_id, content_id, amount, payment_ref, status, payment_type)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, content_id, amount, payment_ref, status, payment_type))
        order_id = cursor.lastrowid
        conn.commit()
        return order_id
    except sqlite3.IntegrityError:
        conn.rollback()
        return None
    finally:
        conn.close()


def approve_payment(user_id, content_id, payment_ref):
    """
    ክፍያን ያጸድቃል (የቆየ ተግባር - ለኋላ ተኳሃኝነት)
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE orders SET status = 'approved' WHERE user_id = ? AND content_id = ? AND payment_ref = ?",
        (user_id, content_id, payment_ref)
    )
    conn.commit()
    conn.close()


def reject_payment(user_id, content_id):
    """
    ክፍያን ውድቅ ያደርጋል (የቆየ ተግባር - ለኋላ ተኳሃኝነት)
    """
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
        WHERE o.user_id = ? AND o.status = 'paid'
    """, (telegram_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def user_owns_content(telegram_id, content_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM orders WHERE user_id = ? AND content_id = ? AND status = 'paid' LIMIT 1",
        (telegram_id, content_id)
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None


def get_content_sales_count(content_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM orders WHERE content_id = ? AND status = 'paid'",
        (content_id,)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count


# =====================================================================
# 📊 የአገልግሎት ክፍያ ስርዓት ፈንክሽኖች
# =====================================================================

FEE_THRESHOLD = 50      # በየ50 ሽያጭ ክፍያ ይጠየቃል
DEFAULT_FEE_AMOUNT = 0  # ለሙከራ 0 ነው፣ በእውነተኛ ስርዓት መጠን ይወሰናል


def increment_sales_count_and_check_fee(content_id, author_id):
    """
    የሽያጭ ብዛት ይጨምራል እና የአገልግሎት ክፍያ ገደብ ላይ ከደረሰ ያሳውቃል
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # የአሁኑን ሁኔታ ማግኘት
    cursor.execute("""
        SELECT id, sales_count, fee_due, fee_paid, content_blocked 
        FROM service_fees 
        WHERE content_id = ? AND author_id = ?
    """, (content_id, author_id))
    row = cursor.fetchone()
    
    # የይዘቱን ሽያጭ ብዛት አዘምን
    cursor.execute("UPDATE contents SET sales_count = sales_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (content_id,))
    
    if row:
        fee_id, sales_count, fee_due, fee_paid, content_blocked = row
        new_count = sales_count + 1
        
        # አዲስ ሽያጭ ሲጨመር fee_due ን አዘምን
        if new_count >= fee_due:
            if fee_paid:
                # ክፍያ ተከፍሏል, ስለዚህ fee_due ን ወደ አሁኑ ሽያጭ አዘምን (ቀጣዩ 50 ገደብ)
                new_fee_due = new_count + FEE_THRESHOLD
                cursor.execute("""
                    UPDATE service_fees 
                    SET sales_count = ?, fee_due = ?, fee_paid = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_count, new_fee_due, fee_id))
            else:
                # ክፍያ አልተከፈለም, መጽሐፉን አግድ
                cursor.execute("""
                    UPDATE service_fees 
                    SET sales_count = ?, content_blocked = 1, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_count, fee_id))
                # የይዘቱን ሁኔታ ወደ 'blocked' ቀይር
                cursor.execute("""
                    UPDATE contents SET status = 'blocked', updated_at = CURRENT_TIMESTAMP WHERE id = ?
                """, (content_id,))
                # በ content_blocks ውስጥ መዝግብ
                cursor.execute("""
                    INSERT INTO content_blocks (content_id, author_id, reason)
                    VALUES (?, ?, ?)
                """, (content_id, author_id, f"Service fee not paid after {FEE_THRESHOLD} sales"))
        else:
            # ገደብ አልደረሰም, ሽያጭ ብቻ ጨምር
            cursor.execute("""
                UPDATE service_fees 
                SET sales_count = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_count, fee_id))
    else:
        # አዲስ መዝገብ ፍጠር
        sales_count = 1
        fee_due = FEE_THRESHOLD  # የመጀመሪያው 50 ሽያጭ ላይ ክፍያ
        cursor.execute("""
            INSERT INTO service_fees (author_id, content_id, sales_count, fee_due, fee_amount)
            VALUES (?, ?, ?, ?, ?)
        """, (author_id, content_id, sales_count, fee_due, DEFAULT_FEE_AMOUNT))
    
    conn.commit()
    conn.close()
    return True


def get_author_service_fees(author_id):
    """
    የአንድ ደራሲ ሁሉንም የአገልግሎት ክፍያ ሪፖርቶች ይመልሳል
    """
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sf.*, c.title as book_title
        FROM service_fees sf
        JOIN contents c ON sf.content_id = c.id
        WHERE sf.author_id = ?
        ORDER BY sf.created_at DESC
    """, (author_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def pay_service_fee(author_id, content_id, fee_amount):
    """
    የአገልግሎት ክፍያ ተከፍሏል ተብሎ ይመዘገባል
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # በ service_fees ውስጥ አዘምን
    cursor.execute("""
        UPDATE service_fees 
        SET fee_paid = 1, fee_paid_at = CURRENT_TIMESTAMP, fee_amount = ?, updated_at = CURRENT_TIMESTAMP
        WHERE author_id = ? AND content_id = ? AND content_blocked = 1
    """, (fee_amount, author_id, content_id))
    affected = cursor.rowcount
    
    # በ service_fee_payments ውስጥ መዝግብ
    if affected > 0:
        cursor.execute("""
            INSERT INTO service_fee_payments (author_id, content_id, amount, status)
            VALUES (?, ?, ?, 'pending')
        """, (author_id, content_id, fee_amount))
    
    conn.commit()
    conn.close()
    return affected > 0


def admin_verify_service_fee_payment(fee_payment_id, admin_notes=""):
    """
    አድሚኑ የአገልግሎት ክፍያ ክፍያን ያረጋግጣል
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE service_fee_payments 
        SET verified_by_admin = 1,
            verified_at = CURRENT_TIMESTAMP,
            status = 'verified'
        WHERE id = ? AND status = 'pending'
    """, (fee_payment_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def unblock_author_content(author_id, content_id):
    """
    የታገደ ይዘት እግዱን ይነሳል
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # የይዘቱን ሁኔታ 'approved' አድርግ
    cursor.execute("""
        UPDATE contents SET status = 'approved', updated_at = CURRENT_TIMESTAMP 
        WHERE id = ? AND author_id = ?
    """, (content_id, author_id))
    
    # በ service_fees ውስጥ content_blocked ን አስወግድ
    cursor.execute("""
        UPDATE service_fees 
        SET content_blocked = 0, updated_at = CURRENT_TIMESTAMP
        WHERE content_id = ? AND author_id = ?
    """, (content_id, author_id))
    
    # በ content_blocks ውስጥ ማስታወሻ
    cursor.execute("""
        UPDATE content_blocks 
        SET unblocked_at = CURRENT_TIMESTAMP
        WHERE content_id = ? AND author_id = ? AND unblocked_at IS NULL
    """, (content_id, author_id))
    
    conn.commit()
    conn.close()
    return True


def get_blocked_contents():
    """
    ሁሉንም የታገዱ ይዘቶች ዝርዝር ይመልሳል
    """
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.title, c.author_id, u.first_name as author_name, 
               sf.sales_count, sf.fee_due, sf.fee_amount,
               cb.blocked_at, cb.reason
        FROM contents c
        JOIN service_fees sf ON c.id = sf.content_id
        JOIN authors a ON c.author_id = a.user_id
        JOIN users u ON a.user_id = u.telegram_id
        JOIN content_blocks cb ON c.id = cb.content_id AND c.author_id = cb.author_id AND cb.unblocked_at IS NULL
        WHERE c.status = 'blocked'
        ORDER BY cb.blocked_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# =====================================================================
# 👑 የአድሚን ፓነል ረዳቶች (ADMIN PANEL HELPERS)
# =====================================================================

def get_pending_counts():
    """
    በግምገማ ላይ ያሉ ይዘቶችን እና ክፍያዎችን ብዛት ይመልሳል
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM contents WHERE status = 'pending_encryption'")
    pending_encryption = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM contents WHERE status = 'pending_author_approval'")
    pending_author_approval = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM author_payments WHERE status = 'pending_admin'")
    pending_author_payments = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM admin_payments WHERE status = 'pending_admin'")
    pending_admin_payments = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM authors WHERE status = 'pending'")
    pending_authors = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM contents WHERE status = 'blocked'")
    blocked_contents = cursor.fetchone()[0]

    conn.close()
    return {
        'pending_encryption': pending_encryption,
        'pending_author_approval': pending_author_approval,
        'pending_author_payments': pending_author_payments,
        'pending_admin_payments': pending_admin_payments,
        'pending_authors': pending_authors,
        'blocked_contents': blocked_contents
    }


# =====================================================================
# 📊 ስታቲስቲክስ እና ሪፖርቶች
# =====================================================================

def get_author_sales(author_id):
    """
    የአንድ ደራሲ አጠቃላይ የሽያጭ መረጃ ይመልሳል
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, title, price, sales_count FROM contents WHERE author_id = ?
    """, (author_id,))
    contents = cursor.fetchall()
    
    result = []
    total_income = 0.0
    total_sales = 0
    
    for content in contents:
        content_id = content[0]
        title = content[1]
        price = content[2]
        sales_count = content[3] or 0
        income = sales_count * price
        total_income += income
        total_sales += sales_count
        result.append({
            "title": title,
            "price": price,
            "sales_count": sales_count,
            "income": income
        })
    
    conn.close()
    return {
        "contents": result,
        "total_sales": total_sales,
        "total_income": total_income
    }


def get_author_rankings(limit=10):
    """
    🏆 ከፍተኛ ገቢ ያላቸውን ደራሲያን ይመልሳል
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            a.user_id,
            u.first_name,
            u.username,
            SUM(c.sales_count) as total_sales,
            SUM(c.sales_count * c.price) as total_income,
            COUNT(c.id) as total_books
        FROM authors a
        JOIN contents c ON a.user_id = c.author_id
        JOIN users u ON a.user_id = u.telegram_id
        WHERE c.status IN ('approved', 'blocked')
        GROUP BY a.user_id
        ORDER BY total_income DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_category_stats():
    """
    📈 በምድብ የሽያጭ ስታቲስቲክስ
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            category,
            COUNT(*) as total_books,
            SUM(sales_count) as total_sales,
            SUM(sales_count * price) as total_income
        FROM contents
        WHERE status IN ('approved', 'blocked')
        GROUP BY category
        ORDER BY total_income DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_user_stats():
    """
    👤 የተጠቃሚ ስታቲስቲክስ
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM authors WHERE status = 'approved'")
    total_authors = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'paid'")
    total_orders = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM contents WHERE status IN ('approved', 'blocked')")
    total_contents = cursor.fetchone()[0]
    
    conn.close()
    return {
        "total_users": total_users,
        "total_authors": total_authors,
        "total_orders": total_orders,
        "total_contents": total_contents
    }


def get_all_users(limit=50, offset=0):
    """👤 የተጠቃሚ ዝርዝር ይመልሳል"""
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT telegram_id, username, first_name, language, phone, created_at
        FROM users 
        ORDER BY telegram_id 
        LIMIT ? OFFSET ?
    """, (limit, offset))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def search_users(query):
    """👤 ተጠቃሚዎችን በስም ወይም በID ይፈልጋል"""
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT telegram_id, username, first_name, language, phone 
        FROM users 
        WHERE telegram_id LIKE ? OR username LIKE ? OR first_name LIKE ?
        ORDER BY telegram_id
        LIMIT 20
    """, (f"%{query}%", f"%{query}%", f"%{query}%"))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_author_sales_report(author_id, period='all'):
    """
    የደራሲውን የሽያጭ ሪፖርት በጊዜ ይመልሳል
    period: 'day', 'week', 'month', 'year', 'all'
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # የጊዜ ሁኔታ ማዘጋጀት
    time_filter = ""
    if period == 'day':
        time_filter = "AND o.paid_at >= date('now', '-1 day')"
    elif period == 'week':
        time_filter = "AND o.paid_at >= date('now', '-7 days')"
    elif period == 'month':
        time_filter = "AND o.paid_at >= date('now', '-30 days')"
    elif period == 'year':
        time_filter = "AND o.paid_at >= date('now', '-365 days')"
    
    # አጠቃላይ ስታቲስቲክስ
    cursor.execute(f"""
        SELECT 
            COUNT(*) as total_transactions,
            SUM(o.amount) as total_revenue,
            COUNT(DISTINCT o.user_id) as unique_buyers
        FROM orders o
        JOIN contents c ON o.content_id = c.id
        WHERE c.author_id = ? AND o.status = 'paid'
        {time_filter}
    """, (author_id,))
    
    stats = cursor.fetchone()
    
    # የገዢዎች ዝርዝር
    cursor.execute(f"""
        SELECT 
            u.telegram_id,
            u.first_name,
            u.username,
            u.phone,
            o.amount,
            o.paid_at as purchase_date,
            o.payment_ref,
            c.title as book_title
        FROM orders o
        JOIN contents c ON o.content_id = c.id
        JOIN users u ON o.user_id = u.telegram_id
        WHERE c.author_id = ? AND o.status = 'paid'
        {time_filter}
        ORDER BY o.paid_at DESC
    """, (author_id,))
    
    buyers = cursor.fetchall()
    
    conn.close()
    
    return {
        'stats': {
            'total_transactions': stats[0] if stats else 0,
            'total_revenue': stats[1] if stats else 0,
            'unique_buyers': stats[2] if stats else 0
        },
        'buyers': [dict(row) for row in buyers]
    }
