# ============================================
# reset_db.py — بازنشانی دیتابیس
# ============================================
# این فایل دیتابیس رو از صفر می‌سازه
# ⚠️ هشدار: همه داده‌های قبلی پاک می‌شن!

import os
from config import Config
from db import init_db, seed_defaults


def main():
    print('=' * 50)
    print('بازنشانی دیتابیس هتل ایران')
    print('=' * 50)
    print()

    # ============ پاک کردن دیتابیس قبلی ============
    if os.path.exists(Config.DATABASE):
        os.remove(Config.DATABASE)
        print('[OK] دیتابیس قدیمی پاک شد.')
    else:
        print('[--] دیتابیس قبلی وجود نداشت.')

    # ============ ساخت پوشه‌های آپلود ============
    for folder in ['rooms', 'foods', 'gallery']:
        path = os.path.join(Config.UPLOAD_FOLDER, folder)
        os.makedirs(path, exist_ok=True)
        print(f'[OK] پوشه ساخته شد: {folder}')

    # ============ ساخت جداول ============
    print()
    print('در حال ساخت جداول...')
    init_db()

    # ============ درج مقادیر پیش‌فرض ============
    print('در حال درج مقادیر پیش‌فرض...')
    seed_defaults()

    print()
    print('=' * 50)
    print('[OK] همه‌چیز با موفقیت آماده شد!')
    print('=' * 50)
    print()
    print('اطلاعات ورود به پنل ادمین:')
    print('   نام کاربری: admin')
    print('   رمز عبور:   admin123')
    print()
    print('حالا می‌تونی app.py رو اجرا کنی.')


if __name__ == '__main__':
    main()