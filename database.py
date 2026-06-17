import sqlite3

DB_NAME = "kitab.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        username TEXT,
        first_name TEXT,
        language TEXT,
        phone TEXT, 
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 2. Authors Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS authors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        status TEXT DEFAULT 'pending', 
        biography TEXT,
        earnings REAL DEFAULT 0.0,
        FOREIGN KEY (user_id) REFERENCES users (telegram_id)
    )
    """)

    # 3. Contents Table
    # ማስታወሻ፡ category ውስጥ Literature, Education, Business ብቻ ሳይሆን Handouts, Notes, QuestionBank ይገባሉ
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        file_path TEXT NOT NULL,
        status TEXT DEFAULT 'pending', 
        FOREIGN KEY (author_id) REFERENCES authors (user_id)
    )
    """)

    # 4. Orders Table (ለግዢዎች እና ለ'እኔ ላይብረሪ' መቆጣጠሪያ የሚያገለግል)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        content_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        payment_reference TEXT UNIQUE,
        status TEXT DEFAULT 'pending', -- pending, approved, rejected
        purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (telegram_id),
        FOREIGN KEY (content_id) REFERENCES contents (id)
    )
    """)

    # 5. Withdrawals Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        status TEXT DEFAULT 'pending', 
        request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (author_id) REFERENCES authors (user_id)
    )
    """)

    conn.commit()
    conn.close()


# =====================================================================
# 🛠️ የዳታቤዝ ፈንክሽኖች (DATABASE FUNCTIONS)
# =====================================================================

def save_user(telegram_id, username, first_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR IGNORE INTO users
    (telegram_id, username, first_name)
    VALUES (?, ?, ?)
    """, (telegram_id, username, first_name))
    conn.commit()
    conn.close()


def set_language(telegram_id, language):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE users
    SET language = ?
    WHERE telegram_id = ?
    """, (language, telegram_id))
    conn.commit()
    conn.close()


def get_contents_by_category(category):
    """በምድብ የተለዩ ይዘቶችን (Books, Handouts, Notes ወዘተ) ለማውጣት"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM contents 
        WHERE category = ? AND status = 'approved'
    """, (category,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_content_by_id(content_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contents WHERE id = ?", (content_id,))
    row = cursor.fetchone()
    conn.close()
    return row


# =====================================================================
# ➕ አዲስ የተጨመሩ የሰርች እና የላይብረሪ ረዳት ፈንክሽኖች
# =====================================================================

def execute_search_query(query_text):
    """ተጠቃሚው በባዶ ፍለጋ (Search) ሲያደርግ በከፊልም ሆነ በሙሉ ስም የሚፈልግበት"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM contents 
        WHERE title LIKE ? AND status = 'approved'
    """, (f"%{query_text}%",))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_user_library(telegram_id):
    """ተጠቃሚው የገዛቸውን (orders ላይ status='approved' የሆኑ) ፋይሎች ዝርዝር ለማውጣት"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.title, c.file_path FROM contents c
        INNER JOIN orders o ON c.id = o.content_id
        WHERE o.user_id = ? AND o.status = 'approved'
    """, (telegram_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def add_order(user_id, content_id, amount, payment_ref="SAMPLE_REF", status="pending"):
    """አዲስ ትዕዛዝ/ግዢ ለመመዝገብ (ለሙከራ በቀጥታ approved ማድረግ ይቻላል)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO orders (user_id, content_id, amount, payment_reference, status)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, content_id, amount, payment_ref, status))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Reference ቁጥሩ ከተደጋገመ ችላ እንዲለው
    conn.close()


# =====================================================================
# 🌱 የሙከራ መረጃዎች (SEED SAMPLE DATA)
# =====================================================================
def seed_sample_data():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR IGNORE INTO users (telegram_id, username, first_name, language) 
        VALUES (9999, 'sample_author', 'Sample Author', 'am')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO authors (user_id, status, biography) 
        VALUES (9999, 'approved', 'የሙከራ ደራሲ')
    """)
    
    cursor.execute("DELETE FROM contents WHERE author_id = 9999")
    
    sample_items = [
        (9999, 'የቅኔ ጥበብ', 'Literature', 'ስለ አማርኛ ቅኔዎች የሚያስተምር መጽሐፍ', 150.0, 'files/qene.pdf', 'approved'),
        (9999, 'Maths Grade 12', 'QuestionBank', 'National Exam Preparation Question Bank', 80.0, 'files/math12.pdf', 'approved'),
        (9999, 'የንግድ ሥራ መመሪያ', 'Business', 'እንዴት ስኬታማ የንግድ ሰው መሆን ይቻላል?', 200.0, 'files/business.pdf', 'approved'),
        (9999, 'Civics Summary', 'Handouts', 'የ12ኛ ክፍል ሲቪክስ ማጠቃለያ ፎርም', 50.0, 'files/civics.pdf', 'approved'),
        (9999, 'Python Crash Course Notes', 'Notes', 'ለጀማሪዎች የተዘጋጀ አጭር ማስታወሻ', 0.0, 'files/python.pdf', 'approved')
    ]
    
    for item in sample_items:
        cursor.execute("""
            INSERT INTO contents (author_id, title, category, description, price, file_path, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, item)
        
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    try:
        seed_sample_data()
        print("Kitab ዳታቤዝ፣ ሁሉም ቴብሎች እና የሙከራ መረጃዎች በተሳካ ሁኔታ ተፈጥረዋል!")
    except Exception as e:
        print(f"ስህተት አጋጥሟል: {e}")
