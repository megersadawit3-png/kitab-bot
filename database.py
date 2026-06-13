import sqlite3

DB_NAME = "kitab.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Users Table (ያንተን ኮድ ከነ 'phone' አሻሽለነዋል)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        username TEXT,
        first_name TEXT,
        language TEXT,
        phone TEXT, -- ለደራሲያን ምዝገባና ለክፍያ ይረዳል
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 2. Authors Table (የደራሲያን መረጃ)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS authors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        status TEXT DEFAULT 'pending', -- pending, approved, rejected
        biography TEXT,
        earnings REAL DEFAULT 0.0,
        FOREIGN KEY (user_id) REFERENCES users (telegram_id)
    )
    """)

    # 3. Contents Table (የመጻሕፍትና ማስታወሻዎች መረጃ)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        file_path TEXT NOT NULL,
        status TEXT DEFAULT 'pending', -- pending, approved, rejected
        FOREIGN KEY (author_id) REFERENCES authors (user_id)
    )
    """)

    # 4. Orders Table (የክፍያና የትዕዛዝ መረጃ)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        content_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        payment_reference TEXT UNIQUE,
        status TEXT DEFAULT 'pending', -- pending, verified, rejected
        purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (telegram_id),
        FOREIGN KEY (content_id) REFERENCES contents (id)
    )
    """)

    # 5. Withdrawals Table (የገንዘብ ወጪ መጠየቂያ)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        status TEXT DEFAULT 'pending', -- pending, approved, completed
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

# ፋይሉን በቀጥታ ስናስነሳው ዳታቤዙን እንዲፈጥርልን
if __name__ == "__main__":
    init_db()
    print("Kitab ዳታቤዝ እና ሁሉም ቴብሎች በተሳካ ሁኔታ ተፈጥረዋል!")
