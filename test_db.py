"""
🧪 test_db.py — የውሂብ ጎታ ሙከራ ፋይል
"""

import os
import sys
import sqlite3
import logging
import time

# ሎግ ማስተካከያ
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# የሙከራ ውሂብ ጎታ ስም
TEST_DB = "test_database.db"


# =====================================================================
# 🔧 የሙከራ ውሂብ ጎታ ማዘጋጀት
# =====================================================================

def setup_test_db():
    """የሙከራ ውሂብ ጎታ ያዘጋጃል"""
    import database as db
    
    # ነባር የሙከራ ውሂብ ጎታ ካለ ማጥፋት
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
            print("🧹 የሙከራ ውሂብ ጎታ ተጽድቷል")
        except:
            pass
    
    # የውሂብ ጎታ ስም መቀየር
    db.DB_NAME = TEST_DB
    
    # ውሂብ ጎታ መፍጠር
    db.init_db()
    print("✅ የሙከራ ውሂብ ጎታ ተፈጥሯል")
    
    # FOREIGN KEY መስራቱን ማረጋገጥ
    print("🔗 FOREIGN KEY ማረጋገጫ...")
    if db.verify_foreign_keys():
        print("✅ FOREIGN KEY በትክክል ይሰራል")
    else:
        print("❌ FOREIGN KEY ችግር አለ")
        return False
    
    return True


# =====================================================================
# 🧪 ሙከራ 1: የተጠቃሚ ፈንክሽኖች
# =====================================================================

def test_user_functions():
    """የተጠቃሚ ተግባራትን ይፈትሻል"""
    print("\n" + "="*50)
    print("👤 ሙከራ 1: የተጠቃሚ ፈንክሽኖች")
    print("="*50)
    
    import database as db
    
    try:
        # 1. ተጠቃሚ መጨመር
        print("📝 ተጠቃሚ መጨመር...")
        db.save_user_info(12345, "testuser", "Test User")
        print("✅ ተጠቃሚ ተጨምሯል")
        
        # 2. ተጠቃሚ ማግኘት
        print("🔍 ተጠቃሚ ማግኘት...")
        user = db.get_user_by_id(12345)
        if user and user['username'] == "testuser":
            print(f"✅ ተጠቃሚ ተገኝቷል: {user['first_name']}")
        else:
            print("❌ ተጠቃሚ አልተገኘም")
            return False
        
        # 3. የተሳሳተ መታወቂያ መፈተሽ
        print("🔍 የተሳሳተ መታወቂያ መፈተሽ...")
        user = db.get_user_by_id(99999)
        if user is None:
            print("✅ የተሳሳተ መታወቂያ በትክክል ተይዟል")
        else:
            print("❌ የተሳሳተ መታወቂያ አልተያዘም")
            return False
        
        print("🎉 ሁሉም የተጠቃሚ ሙከራዎች ተሳክተዋል!")
        return True
        
    except Exception as e:
        print(f"❌ ስህተት: {e}")
        import traceback
        traceback.print_exc()
        return False


# =====================================================================
# 🧪 ሙከራ 2: የደራሲ ፈንክሽኖች
# =====================================================================

def test_author_functions():
    """የደራሲ ተግባራትን ይፈትሻል"""
    print("\n" + "="*50)
    print("✍️ ሙከራ 2: የደራሲ ፈንክሽኖች")
    print("="*50)
    
    import database as db
    
    try:
        # 1. ተጠቃሚ መፍጠር (ለደራሲ)
        db.save_user_info(54321, "authoruser", "Test Author")
        
        # 2. ደራሲ ምዝገባ
        print("📝 ደራሲ ምዝገባ...")
        db.register_author_pending(54321, "This is a test biography")
        status = db.get_author_application_status(54321)
        if status == "pending":
            print("✅ ደራሲ ምዝገባ ተሳክቷል (pending)")
        else:
            print(f"❌ ደራሲ ምዝገባ አልተሳካም: {status}")
            return False
        
        # 3. ደራሲ ማጽደቅ
        print("✅ ደራሲ ማጽደቅ...")
        db.approve_author(54321)
        is_author = db.is_user_author(54321)
        if is_author:
            print("✅ ደራሲ ተጽድቋል")
        else:
            print("❌ ደራሲ አልተጸደቀም")
            return False
        
        print("🎉 ሁሉም የደራሲ ሙከራዎች ተሳክተዋል!")
        return True
        
    except Exception as e:
        print(f"❌ ስህተት: {e}")
        import traceback
        traceback.print_exc()
        return False


# =====================================================================
# 🧪 ሙከራ 3: የይዘት ፈንክሽኖች
# =====================================================================

def test_content_functions():
    """የይዘት ተግባራትን ይፈትሻል"""
    print("\n" + "="*50)
    print("📚 ሙከራ 3: የይዘት ፈንክሽኖች")
    print("="*50)
    
    import database as db
    
    try:
        # 1. ይዘት መጨመር
        print("📝 ይዘት መጨመር...")
        content_id = db.add_content(
            author_id=54321,
            title="Test Book",
            category="Literature",
            description="This is a test book",
            price=100.0,
            file_path="files/test_book.pdf"
        )
        if content_id:
            print(f"✅ ይዘት ተጨምሯል: ID={content_id}")
        else:
            print("❌ ይዘት አልተጨመረም")
            return False
        
        # 2. ይዘት ማግኘት
        print("🔍 ይዘት ማግኘት...")
        content = db.get_content_by_id(content_id)
        if content and content['title'] == "Test Book":
            print(f"✅ ይዘት ተገኝቷል: {content['title']}")
        else:
            print("❌ ይዘት አልተገኘም")
            return False
        
        print("🎉 ሁሉም የይዘት ሙከራዎች ተሳክተዋል!")
        return True
        
    except Exception as e:
        print(f"❌ ስህተት: {e}")
        import traceback
        traceback.print_exc()
        return False


# =====================================================================
# 🧪 ሙከራ 4: የክፍያ ስርዓት
# =====================================================================

def test_payment_functions():
    """የክፍያ ተግባራትን ይፈትሻል"""
    print("\n" + "="*50)
    print("💳 ሙከራ 4: የክፍያ ስርዓት")
    print("="*50)
    
    import database as db
    
    try:
        # 1. ትዕዛዝ መፍጠር
        print("📝 ትዕዛዝ መፍጠር...")
        order_id = db.add_order(
            user_id=12345,
            content_id=1,
            amount=100.0,
            payment_ref="TEST-REF-001"
        )
        if order_id:
            print(f"✅ ትዕዛዝ ተፈጥሯል: ID={order_id}")
        else:
            print("❌ ትዕዛዝ አልተፈጠረም")
            return False
        
        # 2. የደራሲ ክፍያ መፍጠር
        print("📝 የደራሲ ክፍያ መፍጠር...")
        payment_id = db.create_author_payment(
            order_id=order_id,
            author_id=54321,
            user_id=12345,
            content_id=1,
            amount=100.0
        )
        if payment_id:
            print(f"✅ የደራሲ ክፍያ ተፈጥሯል: ID={payment_id}")
        else:
            print("❌ የደራሲ ክፍያ አልተፈጠረም")
            return False
        
        print("🎉 ሁሉም የክፍያ ሙከራዎች ተሳክተዋል!")
        return True
        
    except Exception as e:
        print(f"❌ ስህተት: {e}")
        import traceback
        traceback.print_exc()
        return False


# =====================================================================
# 🚀 ሁሉንም ሙከራዎች ማስኬድ
# =====================================================================

def run_all_tests():
    """ሁሉንም ሙከራዎች ያስኬዳል"""
    print("\n" + "="*60)
    print("🧪 የውሂብ ጎታ ሙከራ መጀመሪያ")
    print("="*60)
    
    # የሙከራ ውሂብ ጎታ ማዘጋጀት
    if not setup_test_db():
        print("❌ የሙከራ ውሂብ ጎታ አልተዘጋጀም")
        return False
    
    # ሁሉንም ሙከራዎች ማስኬድ
    tests = [
        ("የተጠቃሚ ፈንክሽኖች", test_user_functions),
        ("የደራሲ ፈንክሽኖች", test_author_functions),
        ("የይዘት ፈንክሽኖች", test_content_functions),
        ("የክፍያ ስርዓት", test_payment_functions),
    ]
    
    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))
    
    # ውጤት ማሳየት
    print("\n" + "="*60)
    print("📊 የሙከራ ውጤቶች")
    print("="*60)
    
    all_passed = True
    for name, result in results:
        status = "✅ ተሳክቷል" if result else "❌ አልተሳካም"
        print(f"{name}: {status}")
        if not result:
            all_passed = False
    
    # የሙከራ ውሂብ ጎታ ማጥፋት
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
            print("\n🧹 የሙከራ ውሂብ ጎታ ተጽድቷል")
        except:
            pass
    
    if all_passed:
        print("\n🎉 ሁሉም ሙከራዎች ተሳክተዋል!")
    else:
        print("\n❌ አንዳንድ ሙከራዎች አልተሳኩም!")
    
    return all_passed


# =====================================================================
# 🏁 ዋናው የማስነሻ ክፍል
# =====================================================================

if __name__ == "__main__":
    # የሙከራ አካባቢ መዘጋጀት
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # ሙከራዎችን ማስኬድ
    run_all_tests()
