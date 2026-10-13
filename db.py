# ============================================
# db.py — مدیریت دیتابیس SQLite
# ============================================
# این فایل جداول رو می‌سازه و توابع کمکی دیتابیس رو داره

import sqlite3
from werkzeug.security import generate_password_hash
from config import Config


def get_db():
    """
    اتصال به دیتابیس
    row_factory=sqlite3.Row → نتیجه‌ها رو مثل دیکشنری برمی‌گردونه
    """
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')  # فعال‌سازی کلیدهای خارجی
    return conn


def init_db():
    """ساخت تمام جداول دیتابیس"""
    conn = get_db()
    cur = conn.cursor()

    # ============ جدول ادمین ============
    cur.execute('''
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ============ جدول تنظیمات سایت ============
    cur.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    # ============ جدول اتاق‌ها ============
    cur.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT UNIQUE,
            price INTEGER NOT NULL,
            capacity INTEGER DEFAULT 2,
            size INTEGER,
            bed_type TEXT,
            description TEXT,
            features TEXT,
            image TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ============ جدول غذاها ============
    cur.execute('''
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'main',
            price INTEGER NOT NULL,
            description TEXT,
            ingredients TEXT,
            image TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ============ جدول گالری ============
    cur.execute('''
        CREATE TABLE IF NOT EXISTS gallery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            category TEXT DEFAULT 'general',
            image TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ============ جدول رزروها ============
    cur.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            room_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            national_id TEXT,
            check_in TEXT NOT NULL,
            check_out TEXT NOT NULL,
            guests INTEGER DEFAULT 1,
            nights INTEGER DEFAULT 1,
            total_price INTEGER DEFAULT 0,
            note TEXT,
            status TEXT DEFAULT 'pending',
            payment_status TEXT DEFAULT 'unpaid',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
        )
    ''')

    # ============ جدول پیام‌ها ============
    cur.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT DEFAULT 'contact',
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            subject TEXT,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print('دیتابیس ساخته شد.')


def seed_defaults():
    """درج مقادیر پیش‌فرض (فقط بار اول)"""
    conn = get_db()
    cur = conn.cursor()

    # ============ ادمین پیش‌فرض ============
    cur.execute('SELECT COUNT(*) FROM admin')
    if cur.fetchone()[0] == 0:
        hashed = generate_password_hash(Config.DEFAULT_ADMIN_PASSWORD)
        cur.execute(
            'INSERT INTO admin (username, password, full_name) VALUES (?, ?, ?)',
            (Config.DEFAULT_ADMIN_USERNAME, hashed, 'مدیر سیستم')
        )
        print('ادمین پیش‌فرض ساخته شد (admin / admin123)')

    # ============ تنظیمات پیش‌فرض ============
    defaults = {
        'hotel_name': Config.DEFAULT_HOTEL_NAME,
        'hotel_slogan': Config.DEFAULT_HOTEL_SLOGAN,
        'hotel_description': Config.DEFAULT_HOTEL_DESCRIPTION,
        'hotel_phone': Config.DEFAULT_HOTEL_PHONE,
        'hotel_email': Config.DEFAULT_HOTEL_EMAIL,
        'hotel_address': Config.DEFAULT_HOTEL_ADDRESS,
        'instagram': '',
        'telegram': '',
        'whatsapp': '',
    }

    for key, value in defaults.items():
        cur.execute(
            'INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)',
            (key, value)
        )

    conn.commit()
    conn.close()


def get_setting(key, default=''):
    """گرفتن یه تنظیم خاص"""
    conn = get_db()
    row = conn.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
    conn.close()
    return row['value'] if row else default


def get_all_settings():
    """گرفتن همه تنظیمات به صورت دیکشنری"""
    conn = get_db()
    rows = conn.execute('SELECT key, value FROM settings').fetchall()
    conn.close()
    return {row['key']: row['value'] for row in rows}


def update_setting(key, value):
    """بروزرسانی یا درج یه تنظیم"""
    conn = get_db()
    conn.execute(
        'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
        (key, value)
    )
    conn.commit()
    conn.close()