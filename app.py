# ============================================
# app.py — فایل اصلی پروژه هتل ایران
# ============================================
# تمام مسیرها (routes) اینجا تعریف شدن

import os
import uuid
from functools import wraps
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, abort
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from config import Config
from db import get_db, init_db, seed_defaults, get_setting, get_all_settings, update_setting


# ============ ساخت اپلیکیشن ============
app = Flask(__name__)
app.config.from_object(Config)


# ============ ساخت پوشه‌های آپلود ============
for folder in ['rooms', 'foods', 'gallery']:
    os.makedirs(os.path.join(Config.UPLOAD_FOLDER, folder), exist_ok=True)


# ============================================
# توابع کمکی
# ============================================

def allowed_file(filename):
    """چک کردن پسوند فایل"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def save_upload(file, folder):
    """ذخیره فایل آپلودی و برگرداندن اسم فایل"""
    if not file or not file.filename:
        return None
    if not allowed_file(file.filename):
        return None

    # اسم یکتا برای فایل
    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(Config.UPLOAD_FOLDER, folder, unique_name)
    file.save(filepath)
    return f"{folder}/{unique_name}"


def delete_upload(rel_path):
    """پاک کردن فایل آپلودی"""
    if not rel_path:
        return
    filepath = os.path.join(Config.UPLOAD_FOLDER, rel_path)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception:
            pass


def login_required(f):
    """دکوراتور محافظت از پنل ادمین"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            flash('برای ورود به پنل مدیریت باید لاگین کنی.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def get_hotel_info():
    """گرفتن اطلاعات هتل برای قالب‌ها"""
    return get_all_settings()


# ============================================
# صفحات عمومی
# ============================================

@app.route('/')
def index():
    """صفحه اصلی"""
    db = get_db()
    rooms = db.execute(
        'SELECT * FROM rooms WHERE is_active=1 ORDER BY created_at DESC LIMIT 3'
    ).fetchall()
    foods = db.execute(
        'SELECT * FROM foods WHERE is_active=1 ORDER BY created_at DESC LIMIT 6'
    ).fetchall()
    gallery_items = db.execute(
        'SELECT * FROM gallery ORDER BY sort_order ASC, created_at DESC LIMIT 8'
    ).fetchall()
    db.close()

    return render_template(
        'index.html',
        rooms=rooms,
        foods=foods,
        gallery_items=gallery_items,
        hotel=get_hotel_info()
    )


@app.route('/rooms')
def rooms():
    """صفحه لیست اتاق‌ها"""
    db = get_db()
    all_rooms = db.execute(
        'SELECT * FROM rooms WHERE is_active=1 ORDER BY price ASC'
    ).fetchall()
    db.close()
    return render_template('rooms.html', rooms=all_rooms, hotel=get_hotel_info())


@app.route('/room/<int:room_id>')
def room_detail(room_id):
    """صفحه جزئیات اتاق"""
    db = get_db()
    room = db.execute('SELECT * FROM rooms WHERE id=? AND is_active=1', (room_id,)).fetchone()
    db.close()
    if not room:
        abort(404)
    return render_template('room_detail.html', room=room, hotel=get_hotel_info())


@app.route('/reserve/<int:room_id>', methods=['GET', 'POST'])
def reserve(room_id):
    """فرم رزرو اتاق"""
    db = get_db()
    room = db.execute('SELECT * FROM rooms WHERE id=? AND is_active=1', (room_id,)).fetchone()

    if not room:
        db.close()
        flash('اتاق مورد نظر یافت نشد.', 'danger')
        return redirect(url_for('rooms'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        national_id = request.form.get('national_id', '').strip()
        check_in = request.form.get('check_in', '').strip()
        check_out = request.form.get('check_out', '').strip()
        guests = request.form.get('guests', 1)
        note = request.form.get('note', '').strip()

        # اعتبارسنجی
        if not (full_name and phone and check_in and check_out):
            flash('لطفاً فیلدهای ضروری رو پر کن.', 'danger')
            db.close()
            return render_template('reserve.html', room=room, hotel=get_hotel_info())

        # محاسبه تعداد شب و قیمت کل
        try:
            d1 = datetime.strptime(check_in, '%Y-%m-%d')
            d2 = datetime.strptime(check_out, '%Y-%m-%d')
            nights = (d2 - d1).days
            if nights <= 0:
                flash('تاریخ خروج باید بعد از تاریخ ورود باشه.', 'danger')
                db.close()
                return render_template('reserve.html', room=room, hotel=get_hotel_info())
        except Exception:
            flash('تاریخ وارد شده معتبر نیست.', 'danger')
            db.close()
            return render_template('reserve.html', room=room, hotel=get_hotel_info())

        total_price = nights * room['price']
        code = f"RES-{uuid.uuid4().hex[:8].upper()}"

        # ذخیره رزرو
        db.execute('''
            INSERT INTO reservations
            (code, room_id, full_name, phone, email, national_id,
             check_in, check_out, guests, nights, total_price, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (code, room_id, full_name, phone, email, national_id,
              check_in, check_out, guests, nights, total_price, note))

        # پیام به ادمین
        db.execute('''
            INSERT INTO messages (type, name, phone, subject, message)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            'reservation',
            full_name,
            phone,
            f'رزرو جدید — کد {code}',
            f'رزرو اتاق «{room["name"]}»\n'
            f'از {check_in} تا {check_out} ({nights} شب)\n'
            f'تعداد مهمان: {guests}\n'
            f'قیمت کل: {total_price:,} تومان'
        ))

        db.commit()
        db.close()

        flash(f'رزرو شما با کد {code} با موفقیت ثبت شد. به‌زودی با شما تماس می‌گیریم.', 'success')
        return redirect(url_for('rooms'))

    db.close()
    return render_template('reserve.html', room=room, hotel=get_hotel_info())


@app.route('/restaurant')
def restaurant():
    """صفحه رستوران"""
    db = get_db()
    foods = db.execute(
        'SELECT * FROM foods WHERE is_active=1 ORDER BY category, name'
    ).fetchall()
    db.close()

    # گروه‌بندی بر اساس دسته
    categories = {}
    for f in foods:
        cat = f['category'] or 'other'
        categories.setdefault(cat, []).append(f)

    return render_template('restaurant.html', categories=categories, hotel=get_hotel_info())


@app.route('/gallery')
def gallery():
    """صفحه گالری"""
    db = get_db()
    items = db.execute(
        'SELECT * FROM gallery ORDER BY sort_order ASC, created_at DESC'
    ).fetchall()
    db.close()
    return render_template('gallery.html', items=items, hotel=get_hotel_info())


@app.route('/rules')
def rules():
    """صفحه قوانین"""
    return render_template('rules.html', hotel=get_hotel_info())


@app.route('/about')
def about():
    """صفحه درباره ما"""
    return render_template('about.html', hotel=get_hotel_info())


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """صفحه تماس با ما"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()

        if not (name and message):
            flash('نام و متن پیام الزامی است.', 'danger')
        else:
            db = get_db()
            db.execute('''
                INSERT INTO messages (type, name, email, phone, subject, message)
                VALUES ('contact', ?, ?, ?, ?, ?)
            ''', (name, email, phone, subject, message))
            db.commit()
            db.close()
            flash('پیام شما دریافت شد. به‌زودی پاسخ می‌دهیم.', 'success')
            return redirect(url_for('contact'))

    return render_template('contact.html', hotel=get_hotel_info())


# ============================================
# احراز هویت
# ============================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """ورود به پنل مدیریت"""
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        db = get_db()
        admin = db.execute('SELECT * FROM admin WHERE username=?', (username,)).fetchone()
        db.close()

        if admin and check_password_hash(admin['password'], password):
            session.permanent = True
            session['admin_id'] = admin['id']
            session['admin_username'] = admin['username']
            flash(f'خوش آمدی {admin["full_name"] or admin["username"]}!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('نام کاربری یا رمز عبور اشتباه است.', 'danger')

    return render_template('login.html', hotel=get_hotel_info())


@app.route('/logout')
def logout():
    """خروج از پنل"""
    session.clear()
    flash('از پنل خارج شدی.', 'info')
    return redirect(url_for('index'))


# ============================================
# پنل مدیریت — داشبورد
# ============================================

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """داشبورد ادمین"""
    db = get_db()
    stats = {
        'reservations': db.execute('SELECT COUNT(*) FROM reservations').fetchone()[0],
        'pending': db.execute("SELECT COUNT(*) FROM reservations WHERE status='pending'").fetchone()[0],
        'confirmed': db.execute("SELECT COUNT(*) FROM reservations WHERE status='confirmed'").fetchone()[0],
        'messages': db.execute("SELECT COUNT(*) FROM messages WHERE type='contact'").fetchone()[0],
        'unread': db.execute('SELECT COUNT(*) FROM messages WHERE is_read=0').fetchone()[0],
        'rooms': db.execute('SELECT COUNT(*) FROM rooms WHERE is_active=1').fetchone()[0],
        'foods': db.execute('SELECT COUNT(*) FROM foods WHERE is_active=1').fetchone()[0],
        'gallery': db.execute('SELECT COUNT(*) FROM gallery').fetchone()[0],
    }
    recent_reservations = db.execute('''
        SELECT r.*, rm.name as room_name
        FROM reservations r
        JOIN rooms rm ON r.room_id = rm.id
        ORDER BY r.created_at DESC LIMIT 8
    ''').fetchall()
    recent_messages = db.execute('''
        SELECT * FROM messages
        ORDER BY created_at DESC LIMIT 5
    ''').fetchall()
    db.close()

    return render_template(
        'admin/dashboard.html',
        stats=stats,
        reservations=recent_reservations,
        messages=recent_messages,
        hotel=get_hotel_info()
    )


# ============================================
# پنل مدیریت — اتاق‌ها
# ============================================

@app.route('/admin/rooms')
@login_required
def admin_rooms():
    """لیست اتاق‌ها"""
    db = get_db()
    rooms = db.execute('SELECT * FROM rooms ORDER BY created_at DESC').fetchall()
    db.close()
    return render_template('admin/rooms.html', rooms=rooms, hotel=get_hotel_info())


@app.route('/admin/rooms/new', methods=['GET', 'POST'])
@login_required
def admin_room_new():
    """افزودن اتاق جدید"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price = request.form.get('price', 0)
        capacity = request.form.get('capacity', 2)
        size = request.form.get('size', '')
        bed_type = request.form.get('bed_type', '').strip()
        description = request.form.get('description', '').strip()
        features = request.form.get('features', '').strip()

        if not (name and price):
            flash('نام و قیمت الزامی است.', 'danger')
        else:
            image_path = save_upload(request.files.get('image'), 'rooms')
            slug = name.replace(' ', '-').lower()

            db = get_db()
            db.execute('''
                INSERT INTO rooms (name, slug, price, capacity, size, bed_type,
                                   description, features, image)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, slug, int(price), int(capacity), size or None,
                  bed_type, description, features, image_path))
            db.commit()
            db.close()
            flash('اتاق با موفقیت اضافه شد.', 'success')
            return redirect(url_for('admin_rooms'))

    return render_template('admin/room_form.html', room=None, hotel=get_hotel_info())


@app.route('/admin/rooms/<int:room_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_room_edit(room_id):
    """ویرایش اتاق"""
    db = get_db()
    room = db.execute('SELECT * FROM rooms WHERE id=?', (room_id,)).fetchone()
    if not room:
        db.close()
        flash('اتاق یافت نشد.', 'danger')
        return redirect(url_for('admin_rooms'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price = request.form.get('price', 0)
        capacity = request.form.get('capacity', 2)
        size = request.form.get('size', '')
        bed_type = request.form.get('bed_type', '').strip()
        description = request.form.get('description', '').strip()
        features = request.form.get('features', '').strip()

        if not (name and price):
            flash('نام و قیمت الزامی است.', 'danger')
        else:
            new_image = save_upload(request.files.get('image'), 'rooms')
            image_path = new_image if new_image else room['image']
            if new_image and room['image']:
                delete_upload(room['image'])

            db.execute('''
                UPDATE rooms SET name=?, price=?, capacity=?, size=?, bed_type=?,
                                 description=?, features=?, image=?
                WHERE id=?
            ''', (name, int(price), int(capacity), size or None, bed_type,
                  description, features, image_path, room_id))
            db.commit()
            db.close()
            flash('اتاق بروزرسانی شد.', 'success')
            return redirect(url_for('admin_rooms'))

    db.close()
    return render_template('admin/room_form.html', room=room, hotel=get_hotel_info())


@app.route('/admin/rooms/<int:room_id>/delete', methods=['POST'])
@login_required
def admin_room_delete(room_id):
    """حذف اتاق"""
    db = get_db()
    room = db.execute('SELECT * FROM rooms WHERE id=?', (room_id,)).fetchone()
    if room:
        if room['image']:
            delete_upload(room['image'])
        db.execute('DELETE FROM rooms WHERE id=?', (room_id,))
        db.commit()
        flash('اتاق حذف شد.', 'success')
    db.close()
    return redirect(url_for('admin_rooms'))


@app.route('/admin/rooms/<int:room_id>/toggle', methods=['POST'])
@login_required
def admin_room_toggle(room_id):
    """فعال/غیرفعال کردن اتاق"""
    db = get_db()
    db.execute('UPDATE rooms SET is_active = 1 - is_active WHERE id=?', (room_id,))
    db.commit()
    db.close()
    flash('وضعیت اتاق تغییر کرد.', 'success')
    return redirect(url_for('admin_rooms'))


# ============================================
# پنل مدیریت — غذاها
# ============================================

@app.route('/admin/foods')
@login_required
def admin_foods():
    """لیست غذاها"""
    db = get_db()
    foods = db.execute('SELECT * FROM foods ORDER BY category, name').fetchall()
    db.close()
    return render_template('admin/foods.html', foods=foods, hotel=get_hotel_info())


@app.route('/admin/foods/new', methods=['GET', 'POST'])
@login_required
def admin_food_new():
    """افزودن غذای جدید"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', 'main').strip()
        price = request.form.get('price', 0)
        description = request.form.get('description', '').strip()
        ingredients = request.form.get('ingredients', '').strip()

        if not (name and price):
            flash('نام و قیمت الزامی است.', 'danger')
        else:
            image_path = save_upload(request.files.get('image'), 'foods')
            db = get_db()
            db.execute('''
                INSERT INTO foods (name, category, price, description, ingredients, image)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, category, int(price), description, ingredients, image_path))
            db.commit()
            db.close()
            flash('غذا با موفقیت اضافه شد.', 'success')
            return redirect(url_for('admin_foods'))

    return render_template('admin/food_form.html', food=None, hotel=get_hotel_info())


@app.route('/admin/foods/<int:food_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_food_edit(food_id):
    """ویرایش غذا"""
    db = get_db()
    food = db.execute('SELECT * FROM foods WHERE id=?', (food_id,)).fetchone()
    if not food:
        db.close()
        flash('غذا یافت نشد.', 'danger')
        return redirect(url_for('admin_foods'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', 'main').strip()
        price = request.form.get('price', 0)
        description = request.form.get('description', '').strip()
        ingredients = request.form.get('ingredients', '').strip()

        if not (name and price):
            flash('نام و قیمت الزامی است.', 'danger')
        else:
            new_image = save_upload(request.files.get('image'), 'foods')
            image_path = new_image if new_image else food['image']
            if new_image and food['image']:
                delete_upload(food['image'])

            db.execute('''
                UPDATE foods SET name=?, category=?, price=?, description=?,
                                 ingredients=?, image=?
                WHERE id=?
            ''', (name, category, int(price), description, ingredients, image_path, food_id))
            db.commit()
            db.close()
            flash('غذا بروزرسانی شد.', 'success')
            return redirect(url_for('admin_foods'))

    db.close()
    return render_template('admin/food_form.html', food=food, hotel=get_hotel_info())


@app.route('/admin/foods/<int:food_id>/delete', methods=['POST'])
@login_required
def admin_food_delete(food_id):
    """حذف غذا"""
    db = get_db()
    food = db.execute('SELECT * FROM foods WHERE id=?', (food_id,)).fetchone()
    if food:
        if food['image']:
            delete_upload(food['image'])
        db.execute('DELETE FROM foods WHERE id=?', (food_id,))
        db.commit()
        flash('غذا حذف شد.', 'success')
    db.close()
    return redirect(url_for('admin_foods'))


@app.route('/admin/foods/<int:food_id>/toggle', methods=['POST'])
@login_required
def admin_food_toggle(food_id):
    """فعال/غیرفعال کردن غذا"""
    db = get_db()
    db.execute('UPDATE foods SET is_active = 1 - is_active WHERE id=?', (food_id,))
    db.commit()
    db.close()
    flash('وضعیت غذا تغییر کرد.', 'success')
    return redirect(url_for('admin_foods'))


# ============================================
# پنل مدیریت — گالری
# ============================================

@app.route('/admin/gallery', methods=['GET', 'POST'])
@login_required
def admin_gallery():
    """مدیریت گالری"""
    if request.method == 'POST':
        files = request.files.getlist('images')
        title = request.form.get('title', '').strip()
        category = request.form.get('category', 'general').strip()

        count = 0
        db = get_db()
        for f in files:
            if f and f.filename:
                path = save_upload(f, 'gallery')
                if path:
                    db.execute('''
                        INSERT INTO gallery (title, category, image)
                        VALUES (?, ?, ?)
                    ''', (title, category, path))
                    count += 1
        db.commit()
        db.close()

        if count:
            flash(f'{count} تصویر با موفقیت اضافه شد.', 'success')
        else:
            flash('تصویری آپلود نشد.', 'danger')
        return redirect(url_for('admin_gallery'))

    db = get_db()
    items = db.execute('SELECT * FROM gallery ORDER BY sort_order ASC, created_at DESC').fetchall()
    db.close()
    return render_template('admin/gallery.html', items=items, hotel=get_hotel_info())


@app.route('/admin/gallery/<int:item_id>/delete', methods=['POST'])
@login_required
def admin_gallery_delete(item_id):
    """حذف تصویر از گالری"""
    db = get_db()
    item = db.execute('SELECT * FROM gallery WHERE id=?', (item_id,)).fetchone()
    if item:
        if item['image']:
            delete_upload(item['image'])
        db.execute('DELETE FROM gallery WHERE id=?', (item_id,))
        db.commit()
        flash('تصویر حذف شد.', 'success')
    db.close()
    return redirect(url_for('admin_gallery'))


# ============================================
# پنل مدیریت — رزروها
# ============================================

@app.route('/admin/reservations')
@login_required
def admin_reservations():
    """لیست رزروها"""
    status_filter = request.args.get('status', 'all')
    db = get_db()

    if status_filter == 'all':
        reservations = db.execute('''
            SELECT r.*, rm.name as room_name
            FROM reservations r
            JOIN rooms rm ON r.room_id = rm.id
            ORDER BY r.created_at DESC
        ''').fetchall()
    else:
        reservations = db.execute('''
            SELECT r.*, rm.name as room_name
            FROM reservations r
            JOIN rooms rm ON r.room_id = rm.id
            WHERE r.status = ?
            ORDER BY r.created_at DESC
        ''', (status_filter,)).fetchall()

    db.close()
    return render_template(
        'admin/reservations.html',
        reservations=reservations,
        status_filter=status_filter,
        hotel=get_hotel_info()
    )


@app.route('/admin/reservations/<int:res_id>/status/<status>', methods=['POST'])
@login_required
def admin_reservation_status(res_id, status):
    """تغییر وضعیت رزرو"""
    if status not in ['pending', 'confirmed', 'cancelled']:
        flash('وضعیت نامعتبر.', 'danger')
        return redirect(url_for('admin_reservations'))

    db = get_db()
    db.execute('UPDATE reservations SET status=? WHERE id=?', (status, res_id))
    db.commit()
    db.close()
    flash('وضعیت رزرو بروزرسانی شد.', 'success')
    return redirect(url_for('admin_reservations'))


@app.route('/admin/reservations/<int:res_id>/delete', methods=['POST'])
@login_required
def admin_reservation_delete(res_id):
    """حذف رزرو"""
    db = get_db()
    db.execute('DELETE FROM reservations WHERE id=?', (res_id,))
    db.commit()
    db.close()
    flash('رزرو حذف شد.', 'success')
    return redirect(url_for('admin_reservations'))


# ============================================
# پنل مدیریت — پیام‌ها
# ============================================

@app.route('/admin/messages')
@login_required
def admin_messages():
    """لیست پیام‌ها"""
    db = get_db()
    messages = db.execute('SELECT * FROM messages ORDER BY created_at DESC').fetchall()
    db.execute('UPDATE messages SET is_read=1 WHERE type="contact"')
    db.commit()
    db.close()
    return render_template('admin/messages.html', messages=messages, hotel=get_hotel_info())


@app.route('/admin/messages/<int:msg_id>/delete', methods=['POST'])
@login_required
def admin_message_delete(msg_id):
    """حذف پیام"""
    db = get_db()
    db.execute('DELETE FROM messages WHERE id=?', (msg_id,))
    db.commit()
    db.close()
    flash('پیام حذف شد.', 'success')
    return redirect(url_for('admin_messages'))


# ============================================
# پنل مدیریت — تنظیمات
# ============================================

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    """تنظیمات هتل"""
    if request.method == 'POST':
        keys = ['hotel_name', 'hotel_slogan', 'hotel_description',
                'hotel_phone', 'hotel_email', 'hotel_address',
                'instagram', 'telegram', 'whatsapp']
        for key in keys:
            value = request.form.get(key, '').strip()
            update_setting(key, value)
        flash('تنظیمات بروزرسانی شد.', 'success')
        return redirect(url_for('admin_settings'))

    return render_template('admin/settings.html', hotel=get_hotel_info())


@app.route('/admin/change-password', methods=['POST'])
@login_required
def admin_change_password():
    """تغییر رمز عبور ادمین"""
    current = request.form.get('current_password', '')
    new_pass = request.form.get('new_password', '')
    confirm = request.form.get('confirm_password', '')

    if not (current and new_pass and confirm):
        flash('همه فیلدها الزامی است.', 'danger')
        return redirect(url_for('admin_settings'))

    if new_pass != confirm:
        flash('رمز جدید و تکرارش یکسان نیست.', 'danger')
        return redirect(url_for('admin_settings'))

    if len(new_pass) < 6:
        flash('رمز جدید باید حداقل ۶ کاراکتر باشه.', 'danger')
        return redirect(url_for('admin_settings'))

    db = get_db()
    admin = db.execute('SELECT * FROM admin WHERE id=?', (session['admin_id'],)).fetchone()

    if not check_password_hash(admin['password'], current):
        db.close()
        flash('رمز فعلی اشتباه است.', 'danger')
        return redirect(url_for('admin_settings'))

    new_hash = generate_password_hash(new_pass)
    db.execute('UPDATE admin SET password=? WHERE id=?', (new_hash, session['admin_id']))
    db.commit()
    db.close()

    flash('رمز عبور با موفقیت تغییر کرد.', 'success')
    return redirect(url_for('admin_settings'))


# ============================================
# مدیریت خطاها
# ============================================

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html', hotel=get_hotel_info()), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('404.html', hotel=get_hotel_info()), 500


# ============================================
# اجرای برنامه
# ============================================

if __name__ == '__main__':
    # اگه دیتابیس وجود نداشت، بساز
    if not os.path.exists(Config.DATABASE):
        init_db()
        seed_defaults()
    else:
        # مطمئن شو جداول هستن
        try:
            init_db()
            seed_defaults()
        except Exception as e:
            print(f'خطا در ساخت دیتابیس: {e}')

    print()
    print('=' * 50)
    print('  هتل ایران — سرور در حال اجراست')
    print('=' * 50)
    print(f'  آدرس سایت:   http://127.0.0.1:5000')
    print(f'  پنل ادمین:   http://127.0.0.1:5000/login')
    print(f'  یوزر: admin | پس: admin123')
    print('=' * 50)
    print()

    app.run(debug=True, host='0.0.0.0', port=5000)