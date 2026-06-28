"""
🔄 migrate.py — ነባር ውሂብ ወደ አዲሱ መዋቅር ለማስደድ
"""

import os
import sys
import shutil
import sqlite3
import datetime
import logging
from config import DB_NAME

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# =====================================================================
# 🔍 የነባር ውሂብ ጎታ መፈተሽ
# =====================================================================

def check_existing_database():
    """
    ነባር ውሂብ ጎታ መኖሩን እና ሁኔታውን ያረጋግጣል
    """
    if not os.path.exists(DB_NAME):
        print("📭 ምንም ነባር ውሂብ ጎታ አልተገኘም")
        return None
    
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # ሠንጠረዦችን ማረጋገጥ
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [t[0] for t in tables]
        
        print(f"📊 የተገኙ ሠንጠረዦች: {', '.join(table_names)}")
        
        # የመዝገቦች ብዛት
        counts = {}
        for table in ['users', 'authors', 'contents', 'orders']:
            if table in table_names:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]
            else:
                counts[table] = 0
        
        print(f"📈 የመዝገቦች ብዛት: {counts}")
        
        conn.close()
        return {
            'tables': table_names,
            'counts': counts,
            'has_data': any(counts.values())
        }
        
    except sqlite3.OperationalError as e:
        print(f"❌ ውሂብ ጎታ ማንበብ አልተቻለም: {e}")
        return None


# =====================================================================
# 💾 ምትኬ መውሰድ
# =====================================================================

def create_backup():
    """
    ነባር ውሂብ ጎታ ምትኬ ይወስዳል
    """
    if not os.path.exists(DB_NAME):
        return None
    
    # backups ፎልደር መፍጠር
    os.makedirs("backups", exist_ok=True)
    
    # የምትኬ ስም
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"backup_{timestamp}.db"
    backup_path = f"backups/{backup_name}"
    
    # ምትኬ መውሰድ
    shutil.copy2(DB_NAME, backup_path)
    print(f"💾 ምትኬ ተወስዷል: {backup_path}")
    
    return backup_path


# =====================================================================
# 📥 ውሂብ ማስደድ
# =====================================================================

def migrate_data():
    """
    ነባር ውሂብ ወደ አዲሱ መዋቅር ያስደዳል
    """
    print("\n" + "="*60)
    print("🔄 የውሂብ ስደት መጀመሪያ")
    print("="*60)
    
    # 1. ነባር ውሂብ መፈተሽ
    print("\n📊 ነባር ውሂብ እየተፈተሸ ነው...")
    existing = check_existing_database()
    
    if existing is None:
        print("📭 ምንም ነባር ውሂብ ስለሌለ አዲስ ውሂብ ጎታ ይፈጠራል")
        return True
    
    if not existing['has_data']:
        print("📭 ነባር ውሂብ ጎታ ባዶ ነው")
        return True
    
    # 2. ምትኬ መውሰድ
    print("\n💾 ምትኬ እየተወሰደ ነው...")
    backup_path = create_backup()
    if not backup_path:
        print("❌ ምትኬ መውሰድ አልተቻለም")
        return False
    
    # 3. አዲስ ውሂብ ጎታ መፍጠር
    print("\n🏗️ አዲስ ውሂብ ጎታ እየተፈጠረ ነው...")
    import database as db
    db.init_db()
    
    # 4. ውሂብ ማስደድ
    print("\n📥 ውሂብ እየተስደደ ነው...")
    
    conn_old = sqlite3.connect(backup_path)
    conn_old.row_factory = sqlite3.Row
    conn_new = sqlite3.connect(DB_NAME)
    
    cursor_old = conn_old.cursor()
    cursor_new = conn_new.cursor()
    
    # 4.1 Users
    if 'users' in existing['tables']:
        print("👤 ተጠቃሚዎችን በማስደድ ላይ...")
        cursor_old.execute("SELECT * FROM users")
        users = cursor_old.fetchall()
        for user in users:
            cursor_new.execute("""
                INSERT OR IGNORE INTO users (telegram_id, username, first_name, language, phone)
                VALUES (?, ?, ?, ?, ?)
            """, (user['telegram_id'], user['username'], user['first_name'], 
                  user['language'], user['phone']))
        print(f"✅ {len(users)} ተጠቃሚዎች ተስደዋል")
    
    # 4.2 Authors
    if 'authors' in existing['tables']:
        print("✍️ ደራሲያንን በማስደድ ላይ...")
        cursor_old.execute("SELECT * FROM authors")
        authors = cursor_old.fetchall()
        for author in authors:
            cursor_new.execute("""
                INSERT OR IGNORE INTO authors (user_id, status, biography)
                VALUES (?, ?, ?)
            """, (author['user_id'], author['status'], author['biography']))
        print(f"✅ {len(authors)} ደራሲያን ተስደዋል")
    
    # 4.3 Contents
    if 'contents' in existing['tables']:
        print("📚 ይዘቶችን በማስደድ ላይ...")
        cursor_old.execute("SELECT * FROM contents")
        contents = cursor_old.fetchall()
        for content in contents:
            cursor_new.execute("""
                INSERT OR IGNORE INTO contents 
                (id, author_id, title, category, description, price, file_path, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (content['id'], content['author_id'], content['title'], 
                  content['category'], content['description'], content['price'], 
                  content['file_path'], content['status']))
        print(f"✅ {len(contents)} ይዘቶች ተስደዋል")
    
    # 4.4 Orders
    if 'orders' in existing['tables']:
        print("🛒 ትዕዛዞችን በማስደድ ላይ...")
        cursor_old.execute("SELECT * FROM orders")
        orders = cursor_old.fetchall()
        for order in orders:
            cursor_new.execute("""
                INSERT OR IGNORE INTO orders 
                (id, user_id, content_id, amount, payment_ref, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (order['id'], order['user_id'], order['content_id'], 
                  order['amount'], order['payment_ref'], order['status']))
        print(f"✅ {len(orders)} ትዕዛዞች ተስደዋል")
    
    # 5. ሠንጠረዥ መታወቂያዎችን መቀጠል
    print("\n🔢 መታወቂያዎችን በማስተካከል ላይ...")
    
    # ለ contents ሠንጠረዥ
    cursor_new.execute("SELECT MAX(id) FROM contents")
    max_content = cursor_new.fetchone()[0]
    if max_content:
        cursor_new.execute(f"UPDATE sqlite_sequence SET seq={max_content} WHERE name='contents'")
    
    # ለ orders ሠንጠረዥ
    cursor_new.execute("SELECT MAX(id) FROM orders")
    max_order = cursor_new.fetchone()[0]
    if max_order:
        cursor_new.execute(f"UPDATE sqlite_sequence SET seq={max_order} WHERE name='orders'")
    
    conn_new.commit()
    
    # 6. ማጠቃለያ
    conn_old.close()
    conn_new.close()
    
    print("\n" + "="*60)
    print("✅ ውሂብ በተሳካ ሁኔታ ተስደዋል!")
    print(f"💾 ምትኬ በ: {backup_path}")
    print("="*60)
    
    return True


# =====================================================================
# 🔍 የስደት ማረጋገጫ
# =====================================================================

def verify_migration():
    """
    የስደት ስራው በትክክል መስራቱን ያረጋግጣል
    """
    print("\n🔍 የስደት ማረጋገጫ እየተሰራ ነው...")
    
    import database as db
    
    # 1. FOREIGN KEY ማረጋገጫ
    print("🔗 FOREIGN KEY ማረጋገጫ...")
    if not db.verify_foreign_keys():
        print("❌ FOREIGN KEY ችግር አለ")
        return False
    print("✅ FOREIGN KEY በትክክል ይሰራል")
    
    # 2. ውሂብ መኖሩን ማረጋገጥ
    print("📊 ውሂብ ማረጋገጫ...")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    tables = ['users', 'authors', 'contents', 'orders']
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count} መዝገቦች")
    
    conn.close()
    
    print("✅ የስደት ማረጋገጫ ተሳክቷል")
    return True


# =====================================================================
# 🚀 ሙሉ ስደት ማስኬድ
# =====================================================================

def run_migration():
    """
    ሙሉ የስደት ሂደት ያስኬዳል
    """
    print("\n" + "="*60)
    print("🔄 የውሂብ ስደት ሂደት")
    print("="*60)
    
    # 1. የስደት ማስጠንቀቂያ
    print("\n⚠️ ማስጠንቀቂያ: ይህ ሂደት ነባር ውሂብ ጎታን ይለውጣል!")
    print("📌 ምትኬ በራስ-ሰር ይወሰዳል")
    
    response = input("\nቀጥለህ ለመቀጠል ፈቃደኛ ነህ? (y/n): ")
    if response.lower() != 'y':
        print("❌ ስደቱ ተቋርጧል")
        return
    
    # 2. ስደት ማስኬድ
    if not migrate_data():
        print("❌ ውሂብ ማስደድ አልተሳካም")
        return
    
    # 3. ማረጋገጫ
    if not verify_migration():
        print("❌ የስደት ማረጋገጫ አልተሳካም")
        return
    
    print("\n🎉 ውሂብ በተሳካ ሁኔታ ተስደዋል! አሁን አዲሱን ስርዓት መጠቀም ትችላለህ.")


# =====================================================================
# 🏁 ዋናው የማስነሻ ክፍል
# =====================================================================

if __name__ == "__main__":
    # የሙከራ አካባቢ መዘጋጀት
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # ስደቱን ማስኬድ
    run_migration()
