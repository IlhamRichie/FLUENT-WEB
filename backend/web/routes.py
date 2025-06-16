# FLUENTSERVICE/backend/web/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from datetime import datetime, timedelta, timezone
from bson.objectid import ObjectId
from flask import send_from_directory
import os
import uuid # <-- TAMBAHKAN
from ua_parser import user_agent_parser
import jwt


from backend.auth.services import (
    get_google_client,
    process_google_oauth_callback_service,
    generate_otp_service,
    send_otp_email_service,
    get_user_by_email,
    get_user_by_id,
    generate_reset_token_service,
    send_reset_password_email_service
)
from backend.database import get_users_collection
from backend.utils.decorators import web_login_required
# Placeholder JWT (jika belum ada, untuk API)
def create_access_token(identity):
    """Membuat Access Token JWT yang valid."""
    try:
        payload = {
            'exp': datetime.now(timezone.utc) + current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', timedelta(minutes=15)),
            'iat': datetime.now(timezone.utc),
            'identity': identity # identity adalah dictionary berisi id, username, dll.
        }
        token = jwt.encode(
            payload,
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        return token
    except Exception as e:
        current_app.logger.error(f"Error creating access token: {e}")
        return None
    
def create_refresh_token(identity_id):
    """Membuat Refresh Token JWT yang valid."""
    try:
        payload = {
            'exp': datetime.now(timezone.utc) + current_app.config.get('JWT_REFRESH_TOKEN_EXPIRES', timedelta(days=30)),
            'iat': datetime.now(timezone.utc),
            'identity': {'id': identity_id} # Refresh token cukup berisi id
        }
        token = jwt.encode(
            payload,
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        return token
    except Exception as e:
        current_app.logger.error(f"Error creating refresh token: {e}")
        return None


web_bp = Blueprint('web', __name__, template_folder='../templates')

# --- ROUTE HALAMAN STATIS (Tidak berubah) ---
@web_bp.route('/')
def index_route():
    return render_template('web/index.html')

@web_bp.route('/features')
def features_route():
    return render_template('web/features.html')

@web_bp.route('/api-docs-page')
def api_docs_page_route():
    return render_template('web/api_docs.html')

# --- WEB AUTHENTICATION ---

@web_bp.route('/login', methods=['GET'])
def web_login_page_route():
    if 'user_id' in session and session.get('is_web_user'):
        return redirect(url_for('web.web_profile_route'))
    return render_template('auth/login_web.html')

@web_bp.route('/register', methods=['GET'])
def web_register_page_route():
    if 'user_id' in session and session.get('is_web_user'):
        return redirect(url_for('web.web_profile_route'))
    return render_template('auth/register_web.html')

@web_bp.route('/register/submit', methods=['POST'])
def web_register_submit_route():
    # MODIFIKASI: Registrasi WEB sekarang akan mengirim OTP dan mengarahkan ke verifikasi OTP
    if 'user_id' in session and session.get('is_web_user'): # Jika sudah login, redirect
        return redirect(url_for('web.web_profile_route'))

    form = request.form
    username = form.get('username')
    email = form.get('email', '').lower()
    password = form.get('password')
    confirm_password = form.get('confirm_password')
    gender = form.get('gender') or "Not specified"
    occupation = form.get('occupation') or "Not specified"

    if not all([username, email, password, confirm_password]):
        flash('Semua field (kecuali jenis kelamin dan pekerjaan) wajib diisi.', 'danger')
        return redirect(url_for('web.web_register_page_route'))
    if password != confirm_password:
        flash('Password tidak cocok.', 'danger')
        return redirect(url_for('web.web_register_page_route'))
    if len(password) < 6:
        flash('Password minimal 6 karakter.', 'danger')
        return redirect(url_for('web.web_register_page_route'))

    users_coll = get_users_collection()
    existing_user = users_coll.find_one({"email": email})

    if existing_user:
        if not existing_user.get("email_verified"): # Pengguna ada tapi belum verifikasi (mungkin dari API atau percobaan web sebelumnya)
            # Kirim ulang OTP untuk pengguna web yang belum terverifikasi
            otp_code_session = generate_otp_service()
            session['otp_for_verification'] = otp_code_session
            session['email_for_verification'] = email # Email yang akan diverifikasi
            session['otp_timestamp'] = datetime.now(timezone.utc).isoformat() # Simpan timestamp OTP
            session.modified = True

            # Update data pengguna jika diperlukan (misal password diubah)
            update_fields = {
                "username": username,
                "password": current_app.bcrypt.generate_password_hash(password).decode('utf-8'),
                "gender": gender,
                "occupation": occupation,
                "is_active": False, # Pastikan tetap tidak aktif
                "email_verified": False # Pastikan tetap belum terverifikasi
            }
            # Jika Anda menyimpan OTP di DB untuk API, Anda bisa update juga di sini, tapi untuk web session sudah cukup
            # update_fields["otp_code"] = otp_code_session # Opsional jika mau konsisten dgn API
            # update_fields["otp_expiry"] = datetime.now(timezone.utc) + timedelta(minutes=current_app.config.get('OTP_EXPIRY_MINUTES', 10))

            users_coll.update_one({"_id": existing_user["_id"]}, {"$set": update_fields})

            if send_otp_email_service(email, otp_code_session):
                flash(f'Email sudah terdaftar namun belum diverifikasi. OTP baru telah dikirim ke {email}.', 'info')
                return redirect(url_for('web.web_verify_otp_page_route')) # Arahkan ke halaman verifikasi OTP
            else:
                flash('Gagal mengirim ulang OTP. Coba lagi nanti atau hubungi support.', 'danger')
                return redirect(url_for('web.web_register_page_route'))
        else: # Email sudah terdaftar DAN terverifikasi
            flash('Email sudah terdaftar dan terverifikasi. Silakan login.', 'danger')
            return redirect(url_for('web.web_register_page_route'))

    # Pengguna baru
    hashed_password = current_app.bcrypt.generate_password_hash(password).decode('utf-8')
    user_data = {
        "email": email, "username": username, "password": hashed_password,
        "gender": gender, "occupation": occupation,
        "is_active": False, # Pengguna TIDAK aktif sampai verifikasi OTP
        "email_verified": False, # Email TIDAK terverifikasi
        # Tidak perlu simpan otp_code/otp_expiry di DB untuk alur web session-based,
        # Tapi jika ingin sinkron dengan API, bisa ditambahkan.
        # "otp_code": None, "otp_expiry": None,
        "last_login": None, "created_at": datetime.now(timezone.utc),
        "is_admin": False, "auth_provider": "local"
    }
    try:
        users_coll.insert_one(user_data)

        # Generate dan kirim OTP, simpan di session untuk verifikasi web
        otp_code_session = generate_otp_service()
        session['otp_for_verification'] = otp_code_session
        session['email_for_verification'] = email # Email yang akan diverifikasi
        session['otp_timestamp'] = datetime.now(timezone.utc).isoformat() # Simpan timestamp OTP
        session.modified = True

        if send_otp_email_service(email, otp_code_session):
            flash(f'Registrasi berhasil! Kode OTP telah dikirim ke {email}. Silakan verifikasi.', 'success')
            return redirect(url_for('web.web_verify_otp_page_route')) # Arahkan ke halaman verifikasi OTP
        else:
            # Jika gagal kirim OTP, idealnya user dihapus atau diberi tahu untuk coba lagi.
            users_coll.delete_one({"email": email}) # Rollback
            flash('Registrasi berhasil tetapi gagal mengirim OTP. Silakan coba registrasi lagi atau hubungi support.', 'danger')
            return redirect(url_for('web.web_register_page_route'))

    except Exception as e:
        current_app.logger.error(f"Kesalahan registrasi web: {e}")
        flash('Terjadi kesalahan saat registrasi. Silakan coba lagi nanti.', 'danger')
        return redirect(url_for('web.web_register_page_route'))

@web_bp.route('/login-email', methods=['POST'])
def web_login_email_password_route():
    # Login WEB: Memeriksa is_active (yang seharusnya True setelah OTP web diverifikasi)
    if 'user_id' in session and session.get('is_web_user'):
        return redirect(url_for('web.web_profile_route'))

    email = request.form.get('email', '').lower()
    password = request.form.get('password')

    if not email or not password:
        flash('Email dan password wajib diisi.', 'warning')
        return redirect(url_for('web.web_login_page_route'))

    user = get_user_by_email(email)
    if not user:
        flash('Email tidak terdaftar.', 'danger')
        return redirect(url_for('web.web_login_page_route'))

    if not user.get('is_active', False):
        flash('Akun Anda belum aktif. Silakan verifikasi email Anda melalui OTP yang telah dikirim.', 'warning')
        # Arahkan ke halaman verifikasi OTP jika email ada di session (misal, dari percobaan registrasi sebelumnya)
        if session.get('email_for_verification') == email and session.get('otp_for_verification'):
             return redirect(url_for('web.web_verify_otp_page_route'))
        return redirect(url_for('web.web_login_page_route'))


    if user.get("auth_provider") == "google":
        flash('Akun ini terdaftar via Google. Silakan login dengan Google.', 'info')
        return redirect(url_for('web.web_login_page_route'))

    if not user.get("password") or not current_app.bcrypt.check_password_hash(user['password'], password):
        flash('Password salah.', 'danger')
        return redirect(url_for('web.web_login_page_route'))

    users_coll = get_users_collection()
    users_coll.update_one({"_id": user["_id"]}, {"$set": {"last_login": datetime.now(timezone.utc)}})

    session['user_id'] = str(user['_id'])
    session['username'] = user['username']
    session['email'] = user['email']
    session['profile_picture'] = user.get('profile_picture')
    session['is_web_user'] = True
    session.modified = True

    flash('Login berhasil!', 'success')
    return redirect(url_for('web.web_profile_route'))


# --- WEB OTP Routes (digunakan oleh registrasi web sekarang) ---

@web_bp.route('/verify-otp', methods=['GET']) # Halaman OTP WEB
def web_verify_otp_page_route():
    if 'user_id' in session and session.get('is_web_user'): # Jika sudah login
        return redirect(url_for('web.web_profile_route'))

    email_for_verification = session.get('email_for_verification')
    if not email_for_verification or not session.get('otp_for_verification'):
        flash('Sesi OTP tidak valid atau OTP belum diminta. Silakan coba proses registrasi lagi.', 'warning')
        return redirect(url_for('web.web_register_page_route')) # Arahkan ke registrasi jika sesi OTP tidak ada
    return render_template('auth/verify_otp.html', email_for_verification=email_for_verification)


@web_bp.route('/verify-otp/submit', methods=['POST']) # Submit OTP WEB
def web_verify_otp_submit_route():
    # MODIFIKASI: Setelah verifikasi OTP web berhasil, aktifkan akun dan loginkan pengguna.
    entered_otp = request.form.get('otp')
    user_email_for_otp = session.get('email_for_verification')

    if not entered_otp or not user_email_for_otp:
        flash('Permintaan tidak valid. Silakan minta OTP lagi.', 'danger')
        return redirect(url_for('web.web_login_page_route')) # Atau ke registrasi

    stored_otp = session.get('otp_for_verification')
    stored_otp_time_iso = session.get('otp_timestamp')
    otp_expiry_minutes = current_app.config.get('OTP_EXPIRY_MINUTES', 10)

    if not stored_otp or not stored_otp_time_iso:
        flash('Sesi OTP tidak valid atau kedaluwarsa. Silakan minta OTP baru.', 'danger')
        return redirect(url_for('web.web_register_page_route')) # Atau ke resend OTP

    try:
        otp_generation_time = datetime.fromisoformat(stored_otp_time_iso)
        if not otp_generation_time.tzinfo:
            otp_generation_time = otp_generation_time.replace(tzinfo=timezone.utc)
        current_time_utc = datetime.now(timezone.utc)
        otp_expiry_time_check = otp_generation_time + timedelta(minutes=otp_expiry_minutes)

        if current_time_utc > otp_expiry_time_check:
            flash('OTP sudah kedaluwarsa. Silakan minta yang baru.', 'danger')
            # Hapus session OTP yang kedaluwarsa
            session.pop('otp_for_verification', None)
            session.pop('otp_timestamp', None)
            # session.pop('email_for_verification', None) # Biarkan email untuk resend mungkin
            session.modified = True
            return redirect(url_for('web.web_resend_otp_route')) # Arahkan ke resend OTP

        if entered_otp != stored_otp:
            flash('OTP salah.', 'danger')
            return redirect(url_for('web.web_verify_otp_page_route')) # Kembali ke halaman OTP

        # OTP Benar untuk alur web
        user = get_user_by_email(user_email_for_otp)
        if not user:
            flash('Pengguna tidak ditemukan saat verifikasi OTP. Silakan registrasi ulang.', 'danger')
            session.pop('otp_for_verification', None)
            session.pop('otp_timestamp', None)
            session.pop('email_for_verification', None)
            session.modified = True
            return redirect(url_for('web.web_register_page_route'))

        # Aktifkan akun pengguna
        users_coll = get_users_collection()
        users_coll.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "is_active": True,
                "email_verified": True,
                "last_login": datetime.now(timezone.utc) # Set last_login saat aktivasi & login
                }
            # Jika Anda menyimpan otp_code/expiry di DB untuk API, Anda bisa unset di sini juga
            # "$unset": {"otp_code": "", "otp_expiry": ""}
            }
        )

        # Hapus data OTP dari session setelah berhasil
        session.pop('otp_for_verification', None)
        session.pop('otp_timestamp', None)
        session.pop('email_for_verification', None) # Bisa dihapus atau dibiarkan jika tidak masalah

        # Langsung login pengguna setelah verifikasi OTP web
        session['user_id'] = str(user['_id'])
        session['username'] = user['username']
        session['email'] = user['email']
        session['profile_picture'] = user.get('profile_picture')
        session['is_web_user'] = True
        session.modified = True

        flash('Verifikasi OTP berhasil! Akun Anda telah diaktifkan dan Anda sudah login.', 'success')
        return redirect(url_for('web.web_profile_route')) # Arahkan ke profil atau dashboard

    except ValueError as e:
        current_app.logger.error(f"Kesalahan parsing timestamp OTP (web): {e}")
        flash('Terjadi kesalahan internal saat verifikasi OTP. Coba lagi.', 'danger')
        return redirect(url_for('web.web_login_page_route'))
    except Exception as e:
        current_app.logger.error(f"Kesalahan verifikasi OTP tak terduga (web): {e}", exc_info=True)
        flash('Terjadi kesalahan tak terduga saat verifikasi OTP.', 'danger')
        return redirect(url_for('web.web_login_page_route'))

@web_bp.route('/resend-otp', methods=['GET']) # Kirim Ulang OTP WEB
def web_resend_otp_route():
    if 'user_id' in session and session.get('is_web_user'):
        return redirect(url_for('web.web_profile_route'))

    email_to_verify = session.get('email_for_verification')
    if not email_to_verify: # Jika tidak ada email di session (misal, sesi habis atau langsung ke URL ini)
        flash('Sesi tidak ditemukan atau email untuk OTP hilang. Silakan mulai proses registrasi lagi.', 'warning')
        return redirect(url_for('web.web_register_page_route'))

    user = get_user_by_email(email_to_verify)
    if not user: # Seharusnya tidak terjadi jika email_for_verification valid
        flash(f"Pengguna dengan email {email_to_verify} tidak ditemukan. Silakan registrasi.", "danger")
        session.pop('email_for_verification', None) # Hapus email salah dari session
        session.modified = True
        return redirect(url_for('web.web_register_page_route'))

    if user.get("email_verified"): # Jika email sudah terverifikasi, tidak perlu kirim OTP registrasi lagi
        flash("Email ini sudah terverifikasi. Anda bisa langsung login.", "info")
        # Hapus session OTP yang mungkin tersisa
        session.pop('otp_for_verification', None)
        session.pop('otp_timestamp', None)
        session.pop('email_for_verification', None)
        session.modified = True
        return redirect(url_for('web.web_login_page_route'))

    # Generate OTP baru untuk session web
    otp_code_session = generate_otp_service()
    session['otp_for_verification'] = otp_code_session # Perbarui OTP di session
    session['otp_timestamp'] = datetime.now(timezone.utc).isoformat() # Perbarui timestamp
    session.modified = True

    if send_otp_email_service(email_to_verify, otp_code_session):
        flash(f'OTP baru telah dikirim ke {email_to_verify}.', 'info')
    else:
        flash('Gagal mengirim ulang OTP. Coba lagi atau hubungi support.', 'danger')
    return redirect(url_for('web.web_verify_otp_page_route')) # Kembali ke halaman verifikasi OTP


# --- API AUTHENTICATION (Untuk Aplikasi Flutter - TIDAK BERUBAH DARI SEBELUMNYA) ---
@web_bp.route('/api/auth/register', methods=['POST'])
def api_auth_register_route():
    # ... (kode dari jawaban sebelumnya, sudah benar untuk alur API dengan OTP) ...
    data = request.get_json()
    if not data: return jsonify({'status': 'error', 'message': 'Request body harus JSON.'}), 400
    username = data.get('username')
    email = data.get('email', '').lower()
    password = data.get('password')
    gender = data.get('gender', "Not specified")
    occupation = data.get('occupation', "Not specified")
    if not all([username, email, password]): return jsonify({'status': 'error', 'message': 'Username, email, dan password wajib diisi.'}), 400
    if len(password) < 6: return jsonify({'status': 'error', 'message': 'Password minimal 6 karakter.'}), 400
    users_coll = get_users_collection()
    existing_user = users_coll.find_one({"email": email})
    if existing_user:
        if not existing_user.get("email_verified"):
            otp_code = generate_otp_service()
            otp_expiry_duration = current_app.config.get('OTP_EXPIRY_MINUTES', 10)
            otp_expiry_time = datetime.now(timezone.utc) + timedelta(minutes=otp_expiry_duration)
            update_data = {"username": username,"password": current_app.bcrypt.generate_password_hash(password).decode('utf-8'),"gender": gender,"occupation": occupation,"otp_code": otp_code,"otp_expiry": otp_expiry_time, "is_active": False, "email_verified": False}
            users_coll.update_one({"_id": existing_user["_id"]}, {"$set": update_data})
            if send_otp_email_service(email, otp_code):
                return jsonify({'status': 'success','message': 'Email sudah terdaftar namun belum diverifikasi. OTP baru telah dikirim ulang.','email': email}), 200
            else: return jsonify({'status': 'error', 'message': 'Gagal mengirim ulang OTP. Coba lagi nanti.'}), 500
        else: return jsonify({'status': 'error', 'message': 'Email sudah terdaftar dan terverifikasi.'}), 409
    hashed_password = current_app.bcrypt.generate_password_hash(password).decode('utf-8')
    otp_code = generate_otp_service()
    otp_expiry_duration = current_app.config.get('OTP_EXPIRY_MINUTES', 10)
    otp_expiry_time = datetime.now(timezone.utc) + timedelta(minutes=otp_expiry_duration)
    user_data = {"email": email, "username": username, "password": hashed_password,"gender": gender, "occupation": occupation,"is_active": False,"email_verified": False,"otp_code": otp_code,"otp_expiry": otp_expiry_time,"last_login": None, "created_at": datetime.now(timezone.utc),"is_admin": False, "auth_provider": "local"}
    try:
        users_coll.insert_one(user_data)
        if send_otp_email_service(email, otp_code):
            return jsonify({'status': 'success','message': 'Registrasi berhasil. Kode OTP telah dikirim ke email Anda.','email': email}), 201
        else:
            users_coll.delete_one({"email": email})
            return jsonify({'status': 'error', 'message': 'Registrasi berhasil tetapi gagal mengirim OTP. Hubungi support.'}), 500
    except Exception as e:
        current_app.logger.error(f"Kesalahan registrasi API: {e}")
        return jsonify({'status': 'error', 'message': 'Terjadi kesalahan saat registrasi.'}), 500


@web_bp.route('/api/auth/verify-otp', methods=['POST'])
def api_auth_verify_otp_route():
    # ... (kode dari jawaban sebelumnya, sudah benar untuk alur API) ...
    data = request.get_json()
    if not data: return jsonify({'status': 'error', 'message': 'Request body harus JSON.'}), 400
    email = data.get('email', '').lower()
    entered_otp = data.get('otp')
    if not all([email, entered_otp]): return jsonify({'status': 'error', 'message': 'Email dan OTP wajib diisi.'}), 400
    users_coll = get_users_collection()
    user = users_coll.find_one({"email": email})

    if not user:
        return jsonify({'status': 'error', 'message': 'Pengguna tidak ditemukan.'}), 404

    if user.get("email_verified"):
        users_coll.update_one({"_id": user["_id"]}, {"$unset": {"otp_code": "", "otp_expiry": ""}})
        return jsonify({'status': 'success', 'message': 'Akun sudah terverifikasi. Silakan login.'}), 200

    stored_otp = user.get('otp_code')
    otp_expiry_time = user.get('otp_expiry') # Ini objek datetime dari MongoDB

    if not stored_otp or not otp_expiry_time:
        return jsonify({'status': 'error', 'message': 'OTP tidak ditemukan atau sudah kedaluwarsa. Silakan registrasi ulang untuk mendapatkan OTP baru.'}), 400

    # --- TAMBAHKAN BLOK INI UNTUK MEMASTIKAN otp_expiry_time ADALAH AWARE DATETIME ---
    if not isinstance(otp_expiry_time, datetime):
        # Jika bukan datetime (misal, salah simpan sebagai string, meskipun seharusnya tidak)
        current_app.logger.error(f"Format otp_expiry salah (bukan datetime) untuk user {email}: {type(otp_expiry_time)}")
        return jsonify({'status': 'error', 'message': 'Kesalahan server internal (format OTP expiry tidak valid).'}), 500

    if otp_expiry_time.tzinfo is None or otp_expiry_time.tzinfo.utcoffset(otp_expiry_time) is None:
        # Jika naive, asumsikan itu UTC dan buat menjadi aware
        otp_expiry_time = otp_expiry_time.replace(tzinfo=timezone.utc)
    # --- AKHIR BLOK TAMBAHAN ---

    # Baris yang menyebabkan error sebelumnya:
    if datetime.now(timezone.utc) > otp_expiry_time:
        users_coll.update_one(
            {"_id": user["_id"]},
            {"$unset": {"otp_code": "", "otp_expiry": ""}}
        )
        return jsonify({'status': 'error', 'message': 'OTP sudah kedaluwarsa. Silakan registrasi ulang untuk mendapatkan OTP baru.'}), 400

    if entered_otp != stored_otp:
        return jsonify({'status': 'error', 'message': 'OTP salah.'}), 400

    # OTP Valid
    users_coll.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"is_active": True, "email_verified": True},
            "$unset": {"otp_code": "", "otp_expiry": ""}
        }
    )
    return jsonify({'status': 'success', 'message': 'Email berhasil diverifikasi. Anda sekarang bisa login.'}), 200

@web_bp.route('/api/auth/login', methods=['POST'])
def api_auth_login_route():
    data = request.get_json()
    if not data: return jsonify({"status": "error", "message": "Request body harus JSON"}), 400
    email = data.get('email', '').lower()
    password = data.get('password')
    if not email or not password: return jsonify({"status": "error", "message": "Email dan password wajib diisi"}), 400
    
    user = get_user_by_email(email)
    if not user: return jsonify({"status": "error", "message": "Kredensial salah"}), 401
    if not user.get('is_active', False) or not user.get('email_verified', False): return jsonify({"status": "error", "message": "Akun belum aktif atau email belum diverifikasi. Selesaikan verifikasi OTP atau hubungi support."}), 403
    if user.get("auth_provider") == "google": return jsonify({"status": "error", "message": "Silakan gunakan Google Sign-In untuk akun ini."}), 400
    if not user.get("password") or not current_app.bcrypt.check_password_hash(user['password'], password): return jsonify({"status": "error", "message": "Kredensial salah"}), 401

    # --- AWAL TAMBAHAN: MANAJEMEN SESI & LOG AKTIVITAS ---
    now = datetime.now(timezone.utc)
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)

    user_agent_string = request.headers.get('User-Agent', 'Unknown')
    parsed_ua = user_agent_parser.Parse(user_agent_string)
    device_info = f"{parsed_ua['os']['family']} on {parsed_ua['user_agent']['family']}"
    
    session_id = str(uuid.uuid4())
    
    new_session = {
        "session_id": session_id,
        "ip_address": ip_address,
        "device_info": device_info,
        "login_time": now,
        "last_seen": now
    }
    
    new_activity = {
        "activity": "User Logged In",
        "timestamp": now,
        "ip_address": ip_address,
        "device_info": device_info
    }

    users_coll = get_users_collection()
    users_coll.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"last_login": now},
            "$push": {
                "active_sessions": {"$each": [new_session], "$slice": -10}, # Simpan 10 sesi terakhir
                "activity_log": {"$each": [new_activity], "$slice": -50} # Simpan 50 log terakhir
            }
        }
    )
    # --- AKHIR TAMBAHAN ---

    identity_data = {"id": str(user["_id"]), "username": user["username"], "email": user["email"]}
    access_token = create_access_token(identity_data)
    refresh_token = create_refresh_token(str(user["_id"]))
    
    user_data_for_client = {
        "id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"],
        "gender": user.get("gender"),
        "occupation": user.get("occupation"),
        "profile_picture": user.get("profile_picture"),
        "is_admin": user.get("is_admin", False),
        "auth_provider": user.get("auth_provider"),
        "created_at": user.get("created_at").isoformat() if user.get("created_at") else None,
        "last_login": now.isoformat() # Kirim waktu login terbaru
    }
    
    return jsonify({
        "status": "success",
        "message": "Login berhasil",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "session_id": session_id,  # <-- KIRIM SESSION ID KE FLUTTER
        "user": user_data_for_client
    }), 200


@web_bp.route('/api/auth/request-otp', methods=['POST'])
def api_auth_request_otp_route():
    # ... (kode dari jawaban sebelumnya, sudah benar untuk alur API) ...
    data = request.get_json()
    if not data: return jsonify({'status': 'error', 'message': 'Request body harus JSON.'}), 400
    email = data.get('email', '').lower()
    if not email: return jsonify({'status': 'error', 'message': 'Email wajib diisi.'}), 400
    users_coll = get_users_collection()
    user = users_coll.find_one({"email": email})
    if not user: return jsonify({'status': 'error', 'message': 'Email tidak terdaftar.'}), 404
    if user.get('email_verified'): return jsonify({'status': 'info', 'message': 'Email ini sudah terverifikasi.'}), 200
    otp_code = generate_otp_service()
    otp_expiry_duration = current_app.config.get('OTP_EXPIRY_MINUTES', 10)
    otp_expiry_time = datetime.now(timezone.utc) + timedelta(minutes=otp_expiry_duration)
    users_coll.update_one({"_id": user["_id"]},{"$set": {"otp_code": otp_code,"otp_expiry": otp_expiry_time, "is_active": False, "email_verified": False}})
    if send_otp_email_service(email, otp_code):
        return jsonify({'status': 'success', 'message': 'OTP baru telah dikirim ke email Anda.'}), 200
    else: return jsonify({'status': 'error', 'message': 'Gagal mengirim OTP. Coba lagi nanti.'}), 500

# --- ROUTE LAINNYA (Google, Forgot Password, Profile, Logout, dll. tetap sama seperti jawaban sebelumnya) ---
# (Salin sisa route dari jawaban sebelumnya ke sini)
@web_bp.route('/google/login/web')
def google_login_web_start():
    current_app.logger.info(f"Mencoba login Google web. URL Berikutnya: {request.args.get('next')}")
    try:
        client_id = current_app.config.get('GOOGLE_CLIENT_ID')
        client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET')
        if not client_id or not client_secret:
            current_app.logger.error("GOOGLE_CLIENT_ID atau GOOGLE_CLIENT_SECRET hilang dari config.")
            flash("Layanan Login Google tidak dikonfigurasi dengan benar. Hubungi support.", "danger")
            return redirect(url_for('web.web_login_page_route'))
        google = get_google_client()
        redirect_uri = url_for('web.google_authorize_web_callback', _external=True)
        next_url_after_login = request.args.get('next') or url_for('web.web_profile_route')
        session['oauth_web_next_url'] = next_url_after_login
        session['oauth_flow_type'] = 'web'
        session.modified = True
        return google.authorize_redirect(redirect_uri)
    except Exception as e:
        current_app.logger.error(f"Kesalahan tak terduga saat memulai login Google web: {e}", exc_info=True)
        flash("Terjadi kesalahan tak terduga dengan Login Google. Coba lagi nanti.", "danger")
        return redirect(url_for('web.web_login_page_route'))

@web_bp.route('/google/callback/web')
def google_authorize_web_callback():
    next_url_target = session.pop('oauth_web_next_url', url_for('web.web_profile_route'))
    token_data, user_obj, error_message = process_google_oauth_callback_service() # Hapus is_api_request=False
    if error_message or not user_obj:
        flash(error_message or "Kesalahan OAuth Google tidak diketahui saat login web.", "danger")
        return redirect(url_for('web.web_login_page_route'))
    users_coll = get_users_collection()
    users_coll.update_one(
        {"_id": user_obj["_id"]},
        {"$set": {"is_active": True, "email_verified": True, "last_login": datetime.now(timezone.utc)}}
    )
    session['user_id'] = str(user_obj['_id'])
    session['username'] = user_obj['username']
    session['email'] = user_obj['email']
    session['profile_picture'] = user_obj.get('profile_picture')
    session['is_web_user'] = True
    session.modified = True
    flash(f"Selamat datang kembali, {user_obj['username']}! Anda login via Google.", "success")
    return redirect(next_url_target)

@web_bp.route('/api/auth/google/app-signin', methods=['POST']) # Atau di blueprint API Anda
def api_google_app_signin_route():
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'Request body harus JSON.'}), 400

    id_token = data.get('id_token')
    if not id_token:
        return jsonify({'status': 'error', 'message': 'id_token wajib diisi.'}), 400

    try:
        # Anda perlu mengimplementasikan logika ini di backend.auth.services
        # Ini akan melibatkan:
        # 1. Memverifikasi id_token dengan server Google (menggunakan google-auth library).
        #    Saat verifikasi, Anda akan menggunakan Client ID Aplikasi WEB Anda sebagai salah satu audiens yang diharapkan.
        # 2. Setelah token valid dan info pengguna didapatkan (email, nama, dll.):
        #    a. Cek apakah pengguna dengan email tersebut sudah ada di database Anda.
        #    b. Jika belum ada: Buat pengguna baru (tandai sebagai terverifikasi dan aktif, auth_provider='google').
        #    c. Jika sudah ada: Update last_login atau info lainnya jika perlu.
        #    d. Ambil data pengguna dari database Anda.
        # 3. Buat token JWT aplikasi Anda (access token & refresh token).
        # 4. Kembalikan respons JSON sukses dengan token JWT dan data pengguna.

        # Contoh pemanggilan service (ANDA HARUS MEMBUAT FUNGSI INI):
        # user_app_tokens, user_data_from_db, error_message = process_google_id_token_for_app_login(id_token, current_app.config['GOOGLE_WEB_CLIENT_ID'])

        # --- AWAL BLOK CONTOH LOGIKA (HARUS DIIMPLEMENTASIKAN DI SERVICES ANDA) ---
        # Ini hanya ilustrasi kasar, gunakan google-auth library untuk verifikasi yang benar
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests

        # GANTI DENGAN CLIENT ID APLIKASI WEB ANDA YANG DIGUNAKAN DI FLUTTER (serverClientId)
        GOOGLE_WEB_CLIENT_ID = current_app.config.get('GOOGLE_CLIENT_ID_WEB_FOR_TOKEN_VERIFY') # <--- BARIS BARU, SESUAIKAN DENGAN config.py
        if not GOOGLE_WEB_CLIENT_ID:
            # Pesan error ini sekarang seharusnya tidak muncul jika variabel environment sudah di-set dengan benar
            current_app.logger.error("GOOGLE_CLIENT_ID_WEB_FOR_TOKEN_VERIFY tidak dikonfigurasi di server Flask (via environment variable atau config).")
            return jsonify({'status': 'error', 'message': 'Konfigurasi server error untuk Google Sign-In.'}), 500

        idinfo = None
        try:
            idinfo = google_id_token.verify_oauth2_token(id_token, google_requests.Request(), GOOGLE_WEB_CLIENT_ID)
            # Jika ingin mendukung multiple client ID (misal, iOS juga), GOOGLE_WEB_CLIENT_ID bisa berupa list
            # idinfo = google_id_token.verify_oauth2_token(id_token, google_requests.Request(), [GOOGLE_WEB_CLIENT_ID_ANDROID, GOOGLE_WEB_CLIENT_ID_IOS, GOOGLE_WEB_CLIENT_ID_WEB])
        except ValueError as e:
            # Invalid token
            current_app.logger.error(f"Google ID token verification failed: {e}")
            return jsonify({'status': 'error', 'message': 'Token Google tidak valid atau kedaluwarsa.'}), 401

        user_email = idinfo.get('email')
        user_name = idinfo.get('name')
        user_picture = idinfo.get('picture')
        # Anda bisa ambil info lain seperti given_name, family_name

        if not user_email:
             return jsonify({'status': 'error', 'message': 'Tidak dapat mengambil email dari token Google.'}), 400

        users_coll = get_users_collection()
        user = users_coll.find_one({"email": user_email})

        if not user: # Pengguna baru
            username_suggestion = user_email.split('@')[0] # Contoh pembuatan username
            # Pastikan username unik jika perlu
            counter = 0
            temp_username = username_suggestion
            while users_coll.find_one({"username": temp_username}):
                counter += 1
                temp_username = f"{username_suggestion}{counter}"
            final_username = temp_username

            new_user_data = {
                "email": user_email,
                "username": final_username,
                "password": None, # Tidak ada password untuk Google Sign-In
                "auth_provider": "google",
                "profile_picture": user_picture,
                "full_name": user_name, # Simpan nama lengkap jika ada
                "is_active": True,
                "email_verified": True,
                "created_at": datetime.now(timezone.utc),
                "last_login": datetime.now(timezone.utc),
                "gender": "Not specified", # Bisa coba ambil dari token jika ada, atau default
                "occupation": "Not specified",
                "is_admin": False
            }
            insert_result = users_coll.insert_one(new_user_data)
            user_id = insert_result.inserted_id
            user = users_coll.find_one({"_id": user_id}) # Ambil data user yang baru dibuat
        else: # Pengguna sudah ada
            users_coll.update_one(
                {"_id": user["_id"]},
                {"$set": {
                    "last_login": datetime.now(timezone.utc),
                    "auth_provider": "google", # Pastikan provider diupdate jika sebelumnya local
                    "profile_picture": user_picture if user_picture else user.get("profile_picture"),
                    "is_active": True, # Pastikan aktif
                    "email_verified": True # Pastikan terverifikasi
                    }
                }
            )
            user = get_user_by_email(user_email) # Ambil data user yang terupdate

        if not user: # Double check setelah create/update
            return jsonify({'status': 'error', 'message': 'Gagal memproses data pengguna.'}), 500

        # Buat token JWT aplikasi Anda
        identity_data = {"id": str(user["_id"]), "username": user["username"], "email": user["email"]}
        access_token = create_access_token(identity_data) # Ganti dengan implementasi JWT Anda
        refresh_token = create_refresh_token(str(user["_id"])) # Ganti dengan implementasi JWT Anda

        user_data_for_client = {
            "id": str(user["_id"]),
            "username": user["username"],
            "email": user["email"],
            "gender": user.get("gender"),
            "occupation": user.get("occupation"),
            "profile_picture": user.get("profile_picture"),
            "auth_provider": user.get("auth_provider"),
        }
        # --- AKHIR BLOK CONTOH LOGIKA ---

        return jsonify({
            'status': 'success',
            'message': 'Login dengan Google berhasil.',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user_data_for_client
        }), 200

    except ValueError as e: # Error dari verify_oauth2_token
        current_app.logger.error(f"Error verifikasi token Google: {e}")
        return jsonify({'status': 'error', 'message': 'Token Google tidak valid.'}), 401
    except Exception as e:
        current_app.logger.error(f"Kesalahan internal saat login Google: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Terjadi kesalahan internal server.'}), 500

@web_bp.route('/forgot-password', methods=['GET', 'POST'])
def web_forgot_password_request_route():
    if request.method == 'POST':
        email = request.form.get('email', '').lower()
        if not email:
            flash('Alamat email wajib diisi.', 'danger')
            return render_template('auth/forgot_password_web.html')
        user = get_user_by_email(email)
        users_coll = get_users_collection()
        if user and user.get("auth_provider") == "local" and user.get("password"):
            reset_token = generate_reset_token_service()
            expiry_time = datetime.now(timezone.utc) + timedelta(minutes=current_app.config.get('RESET_TOKEN_EXPIRY_MINUTES', 60))
            users_coll.update_one(
                {"_id": user["_id"]},
                {"$set": {"reset_password_token": reset_token, "reset_token_expiry": expiry_time}}
            )
            send_reset_password_email_service(user['email'], reset_token)
        flash('Jika akun dengan email tersebut ada dan memenuhi syarat, link reset password telah dikirim. Periksa email Anda (termasuk folder spam).', 'info')
        return redirect(url_for('web.web_login_page_route'))
    return render_template('auth/forgot_password_web.html')

@web_bp.route('/api/auth/forgot-password', methods=['POST']) # Atau di blueprint API Anda
def api_auth_forgot_password_route():
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'Request body harus JSON.'}), 400

    email = data.get('email', '').lower()
    if not email:
        return jsonify({'status': 'error', 'message': 'Email wajib diisi.'}), 400

    user = get_user_by_email(email)
    users_coll = get_users_collection()

    # Logika ini mirip dengan web_forgot_password_request_route,
    # tapi mengembalikan JSON.
    if user and user.get("auth_provider") == "local" and user.get("password"):
        reset_token = generate_reset_token_service()
        expiry_time = datetime.now(timezone.utc) + timedelta(minutes=current_app.config.get('RESET_TOKEN_EXPIRY_MINUTES', 60))

        users_coll.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "reset_password_token": reset_token,
                "reset_token_expiry": expiry_time
            }}
        )
        # Untuk API, Anda bisa memilih untuk mengirim email seperti web,
        # atau jika flow API berbeda (misal pakai OTP untuk reset), sesuaikan di sini.
        # Kita asumsikan API juga mengirim link reset password via email untuk saat ini.
        if send_reset_password_email_service(user['email'], reset_token):
            current_app.logger.info(f"API: Password reset email sent to {user['email']}")
            return jsonify({'status': 'success', 'message': 'Jika akun dengan email tersebut ada dan memenuhi syarat, link reset password telah dikirim.'}), 200
        else:
            current_app.logger.error(f"API: Failed to send password reset email to {user['email']}")
            # Jangan beritahu penyerang apakah email ada atau tidak, tapi log errornya.
            return jsonify({'status': 'error', 'message': 'Gagal memproses permintaan reset password. Coba lagi nanti.'}), 500
    else:
        # Tetap kembalikan pesan generik untuk API demi keamanan,
        # meskipun user tidak ditemukan atau bukan local auth.
        current_app.logger.info(f"API: Password reset attempt for non-eligible or non-existent email: {email}")
        return jsonify({'status': 'success', 'message': 'Jika akun dengan email tersebut ada dan memenuhi syarat, link reset password telah dikirim.'}), 200
    
# Di routes.py
@web_bp.route('/api/auth/reset-password', methods=['POST']) # atau di blueprint API
def api_auth_reset_password_submit_route():
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'Request body harus JSON.'}), 400

    token = data.get('token')
    new_password = data.get('new_password') # Sesuaikan dengan key dari Flutter
    confirm_password = data.get('confirm_password') # Sesuaikan

    if not all([token, new_password, confirm_password]):
        return jsonify({'status': 'error', 'message': 'Token, password baru, dan konfirmasi password wajib diisi.'}), 400

    if new_password != confirm_password:
        return jsonify({'status': 'error', 'message': 'Password tidak cocok.'}), 400

    if len(new_password) < 6:
        return jsonify({'status': 'error', 'message': 'Password minimal 6 karakter.'}), 400

    users_coll = get_users_collection()
    user = users_coll.find_one({
        "reset_password_token": token,
        "reset_token_expiry": {"$gt": datetime.now(timezone.utc)}
    })

    if not user:
        return jsonify({'status': 'error', 'message': 'Token reset password tidak valid atau kedaluwarsa.'}), 400 # atau 401

    if user.get("auth_provider") == "google":
        users_coll.update_one({"_id": user["_id"]}, {"$unset": {"reset_password_token": "", "reset_token_expiry": ""}})
        return jsonify({'status': 'error', 'message': 'Password tidak bisa direset untuk akun yang terhubung dengan Google.'}), 400

    hashed_password = current_app.bcrypt.generate_password_hash(new_password).decode('utf-8')
    users_coll.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"password": hashed_password, "auth_provider": "local"},
            "$unset": {"reset_password_token": "", "reset_token_expiry": ""}
        }
    )
    return jsonify({'status': 'success', 'message': 'Password Anda berhasil direset. Silakan login.'}), 200

@web_bp.route('/reset-password/<token>', methods=['GET'])
def web_reset_password_form_route(token):
    if 'user_id' in session and session.get('is_web_user'):
        return redirect(url_for('web.web_profile_route'))
    users_coll = get_users_collection()
    user = users_coll.find_one({
        "reset_password_token": token,
        "reset_token_expiry": {"$gt": datetime.now(timezone.utc)}
    })
    if not user:
        flash('Token reset password tidak valid atau kedaluwarsa. Minta link baru.', 'danger')
        return redirect(url_for('web.web_forgot_password_request_route'))
    if user.get("auth_provider") == "google":
        flash('Password tidak bisa direset untuk akun yang terhubung dengan Google.', 'warning')
        users_coll.update_one({"_id": user["_id"]}, {"$unset": {"reset_password_token": "", "reset_token_expiry": ""}})
        return redirect(url_for('web.web_login_page_route'))
    return render_template('auth/reset_password_form_web.html', token=token)

@web_bp.route('/reset-password/<token>', methods=['POST'])
def web_reset_password_submit_route(token):
    if 'user_id' in session and session.get('is_web_user'):
        return redirect(url_for('web.web_profile_route'))

    password = request.form.get('new_password')  # <--- UBAH INI
    confirm_password = request.form.get('confirm_password')

    if not password or not confirm_password:
        flash('Kedua field password wajib diisi.', 'danger')
        return redirect(url_for('web.web_reset_password_form_route', token=token))
    if password != confirm_password:
        flash('Password tidak cocok.', 'danger')
        return redirect(url_for('web.web_reset_password_form_route', token=token))
    if len(password) < 6:
        flash('Password minimal 6 karakter.', 'danger')
        return redirect(url_for('web.web_reset_password_form_route', token=token))
    users_coll = get_users_collection()
    user = users_coll.find_one({
        "reset_password_token": token,
        "reset_token_expiry": {"$gt": datetime.now(timezone.utc)}
    })
    if not user:
        flash('Token reset password tidak valid atau kedaluwarsa. Minta link baru.', 'danger')
        return redirect(url_for('web.web_forgot_password_request_route'))
    if user.get("auth_provider") == "google":
        flash('Password tidak bisa direset untuk akun yang terhubung dengan Google.', 'warning')
        users_coll.update_one({"_id": user["_id"]}, {"$unset": {"reset_password_token": "", "reset_token_expiry": ""}})
        return redirect(url_for('web.web_login_page_route'))
    hashed_password = current_app.bcrypt.generate_password_hash(password).decode('utf-8')
    users_coll.update_one(
        {"_id": user["_id"]},
        {"$set": {"password": hashed_password, "auth_provider": "local"},
         "$unset": {"reset_password_token": "", "reset_token_expiry": ""}}
    )
    flash('Password Anda berhasil direset. Silakan login dengan password baru Anda.', 'success')
    return redirect(url_for('web.web_login_page_route'))

@web_bp.route('/profile')
@web_login_required
def web_profile_route():
    user_id_str = session.get('user_id')
    user_data = get_user_by_id(user_id_str)
    if not user_data:
        flash("Data pengguna tidak ditemukan. Silakan login lagi.", "danger")
        session.clear()
        session.modified = True
        return redirect(url_for('web.web_login_page_route'))
    session['profile_picture'] = user_data.get('profile_picture')
    session['username'] = user_data.get('username')
    return render_template('web/profile_web.html', user=user_data)

@web_bp.route('/logout')
@web_login_required
def web_logout_route():
    keys_to_pop = ['user_id', 'username', 'email', 'profile_picture', 'is_web_user','otp_for_verification', 'email_for_verification', 'otp_timestamp','oauth_web_next_url', 'oauth_token', 'oauth_flow_type']
    for key in keys_to_pop: session.pop(key, None)
    session.modified = True
    flash('Anda berhasil logout.', 'success')
    return redirect(url_for('web.web_login_page_route'))

@web_bp.route('/interview-simulation')
@web_login_required
def interview_simulation_page():
    user_info = {"username": session.get("username", "Pengguna")}
    current_app.logger.info(f"Pengguna {session.get('user_id')} mengakses simulasi interview.")
    return render_template('web/gimmick.html', user=user_info, app_name=current_app.config.get("APP_NAME", "FLUENT"))

@web_bp.route("/predict_page")
def predict_page():
    """Menyajikan halaman deteksi ekspresi TFLite."""
    return render_template('predict.html')

@web_bp.route('/static/<path:filename>')
def web_serve_static(filename):
    static_folder = os.path.join(current_app.root_path, 'static')
    return send_from_directory(static_folder, filename)