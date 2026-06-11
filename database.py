import sqlite3


def init_db():
    conn = sqlite3.connect("kitab.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        username TEXT,
        first_name TEXT,
        language TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def save_user(telegram_id, username, first_name):
    conn = sqlite3.connect("kitab.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO users
    (telegram_id, username, first_name)
    VALUES (?, ?, ?)
    """, (telegram_id, username, first_name))

    conn.commit()
    conn.close()


def set_language(telegram_id, language):
    conn = sqlite3.connect("kitab.db")
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE users
    SET language = ?
    WHERE telegram_id = ?
    """, (language, telegram_id))

    conn.commit()
    conn.close()
