"""
🔐 security.py — የደህንነት ተግባራት
"""

import re
import uuid

# =====================================================================
# 🛡️ የሠንጠረዥ ስም ማረጋገጫ (Table Name Validation)
# =====================================================================

ALLOWED_TABLES = {
    'author': 'author_payments',
    'admin': 'admin_payments'
}

ALLOWED_STATUSES = {
    'order': ['pending', 'paid', 'rejected', 'cancelled'],
    'payment': ['pending', 'pending_admin', 'verified', 'rejected', 'completed'],
    'author': ['pending', 'approved', 'rejected'],
    'content': ['pending_encryption', 'pending_author_approval', 'approved', 'rejected', 'blocked']
}

def get_payment_table(payment_type):
    """
    🛡️ ደህንነቱ የተጠበቀ የሠንጠረዥ ስም መመለስ
    """
    table = ALLOWED_TABLES.get(payment_type)
    if not table:
        raise ValueError(f"Invalid payment type: {payment_type}. Allowed: {list(ALLOWED_TABLES.keys())}")
    return table

def validate_status(status, status_type='order'):
    """
    🛡️ የሁኔታ እሴት ማረጋገጫ
    """
    allowed = ALLOWED_STATUSES.get(status_type)
    if not allowed:
        raise ValueError(f"Invalid status type: {status_type}")
    if status not in allowed:
        raise ValueError(f"Invalid status: {status}. Allowed: {allowed}")
    return True

# =====================================================================
# 🛡️ የግቤት ማጽዳት (Input Sanitization)
# =====================================================================

def sanitize_filename(filename):
    """🛡️ የፋይል ስም ደህንነቱ የተጠበቀ ለማድረግ"""
    if not filename:
        return f"file_{uuid.uuid4().hex[:8]}.pdf"
    sanitized = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    if not sanitized or sanitized == '_' * len(sanitized):
        return f"file_{uuid.uuid4().hex[:8]}.pdf"
    return sanitized

def get_safe_file_path(doc_filename):
    """🛡️ ደህንነቱ የተጠበቀ የፋይል መንገድ ይመልሳል"""
    safe_name = sanitize_filename(doc_filename)
    unique_id = uuid.uuid4().hex[:8]
    return f"files/{unique_id}_{safe_name}"

def sanitize_receipt_link(link):
    """🛡️ የሪሲት ሊንክ ማጽዳት"""
    if not link:
        return None
    if not link.startswith(('http://', 'https://')):
        link = 'https://' + link
    link = re.sub(r'[^a-zA-Z0-9/:._-]', '', link)
    return link

# =====================================================================
# 🛡️ የውሂብ ማረጋገጫ (Data Validation)
# =====================================================================

def validate_content_id(content_id):
    """🛡️ የይዘት መታወቂያ ማረጋገጫ"""
    if not isinstance(content_id, int):
        raise TypeError(f"Content ID must be an integer, got {type(content_id).__name__}")
    if content_id <= 0:
        raise ValueError(f"Content ID must be positive, got {content_id}")
    return True

def validate_user_id(user_id):
    """🛡️ የተጠቃሚ መታወቂያ ማረጋገጫ"""
    if not isinstance(user_id, int):
        raise TypeError(f"User ID must be an integer, got {type(user_id).__name__}")
    if user_id <= 0:
        raise ValueError(f"User ID must be positive, got {user_id}")
    return True

def validate_amount(amount):
    """🛡️ የገንዘብ መጠን ማረጋገጫ"""
    if not isinstance(amount, (int, float)):
        raise TypeError(f"Amount must be a number, got {type(amount).__name__}")
    if amount < 0:
        raise ValueError(f"Amount cannot be negative, got {amount}")
    if amount > 1000000:
        raise ValueError(f"Amount too large: {amount}")
    return True

def validate_payment_id(payment_id):
    """🛡️ የክፍያ መታወቂያ ማረጋገጫ"""
    if not isinstance(payment_id, int):
        raise TypeError(f"Payment ID must be an integer, got {type(payment_id).__name__}")
    if payment_id <= 0:
        raise ValueError(f"Payment ID must be positive, got {payment_id}")
    return True

def validate_order_id(order_id):
    """🛡️ የትዕዛዝ መታወቂያ ማረጋገጫ"""
    if not isinstance(order_id, int):
        raise TypeError(f"Order ID must be an integer, got {type(order_id).__name__}")
    if order_id <= 0:
        raise ValueError(f"Order ID must be positive, got {order_id}")
    return True
