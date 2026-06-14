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

    # 4. Orders Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        content_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        payment_reference TEXT UNIQUE,
        status TEXT DEFAULT 'pending', 
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


def get_contents_by_category(content_type, category):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # <--- መረጃዎችን በቁልፍ ስማቸው ለመጥራት የተጨመረች
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
    conn.row_factory = sqlite3.Row  # <--- ለDetail Page መረጃን በስም ለመጥራት የተጨመረች
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contents WHERE id = ?", (content_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def seed_sample_data():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # እዚህ ጋር 'name' የነበረው ወደ 'username' እና 'first_name' ተስተካክሏል
    cursor.execute("""
        INSERT OR IGNORE INTO users (telegram_id, username, first_name, language) 
        VALUES (9999, 'sample_author', 'Sample Author', 'am')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO authors (user_id, status, biography) 
        VALUES (9999, 'approved', 'የሙከራ ደራሲ')
    """)
    
    # በየጊዜው ስናስነሳው መጻሕፍቱ ደጋግመው እንዳይሞሉ መጀመሪያ ማጽጃ መስመር
    cursor.execute("DELETE FROM contents WHERE author_id = 9999")
    
    sample_books = [
        (9999, 'የቅኔ ጥበብ', 'Literature', 'ስለ አማርኛ ቅኔዎች የሚያስተምር መጽሐፍ', 150.0, 'files/qene.pdf', 'approved'),
        (9999, 'Maths Grade 12', 'Education', 'National Exam Preparation Question Bank', 80.0, 'files/math12.pdf', 'approved'),
        (9999, 'የንግድ ሥራ መመሪያ', 'Business', 'እንዴት ስኬታማ የንግድ ሰው መሆን ይቻላል?', 200.0, 'files/business.pdf', 'approved')
    ]
    
    for book in sample_books:
        cursor.execute("""
            INSERT INTO contents (author_id, title, category, description, price, file_path, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, book)
        
    conn.commit()
    conn.close()


# ፋይሉን በቀጥታ ስናስነሳው ሁሉንም ነገር በንጽህና የሚያስጀምረው ክፍል
if __name__ == "__main__":
    init_db()
    try:
        seed_sample_data()
        print("Kitab ዳታቤዝ፣ ሁሉም ቴብሎች እና የሙከራ መረጃዎች በተሳካ ሁኔታ ተፈጥረዋል!")
    except Exception as e:
        print(f"ስህተት አጋጥሟል: {e}")
