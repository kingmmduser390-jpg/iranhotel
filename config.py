# ============================================
# config.py — تنظیمات اصلی پروژه هتل ایران
# ============================================
# این فایل اطلاعات حساس و تنظیمات کلی رو نگه می‌داره
# هرگز این فایل رو توی گیت‌هاب پابلیک آپلود نکن!

import os
from datetime import timedelta


class Config:
    """کلاس تنظیمات اصلی اپلیکیشن"""

    # ============ امنیت ============
    # کلید مخفی برای session و فرم‌ها
    # ⚠️ در production حتماً عوضش کن
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'iran-hotel-super-secret-key-2024-change-me'

    # ============ مسیرهای اصلی ============
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATABASE = os.path.join(BASE_DIR, 'database.db')

    # ============ آپلود فایل ============
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # ============ سشن ============
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # ============ ادمین پیش‌فرض ============
    DEFAULT_ADMIN_USERNAME = 'admin'
    DEFAULT_ADMIN_PASSWORD = 'admin123'

    # ============ اطلاعات پیش‌فرض هتل ============
    DEFAULT_HOTEL_NAME = 'هتل ایران'
    DEFAULT_HOTEL_SLOGAN = 'تجربه‌ای بی‌نظیر از اقامت لوکس در قلب پایتخت'
    DEFAULT_HOTEL_DESCRIPTION = 'هتل ایران با بیش از یک دهه تجربه در زمینه مهمان‌نوازی، محیطی آرام و لوکس را برای اقامت شما فراهم کرده است. ما با تیمی مجرب و امکانات مدرن، تلاش می‌کنیم تجربه‌ای به‌یادماندنی برای شما بسازیم.'
    DEFAULT_HOTEL_PHONE = '021-12345678'
    DEFAULT_HOTEL_EMAIL = 'info@iranhotel.com'
    DEFAULT_HOTEL_ADDRESS = 'تهران، خیابان ولیعصر، پلاک ۱۲۳'