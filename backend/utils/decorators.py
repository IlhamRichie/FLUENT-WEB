from functools import wraps
from flask import request, jsonify, session, flash, redirect, url_for, current_app
import jwt

# Impor fungsi get_user_by_id dari auth.services
from backend.auth.services import get_user_by_id
from backend.database import get_users_collection # Untuk admin_required


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({'status': 'fail', 'message': 'Authorization header is missing!'}), 401

        try:
            # Pastikan formatnya "Bearer <token>"
            token_parts = auth_header.split(" ")
            if len(token_parts) != 2 or token_parts[0].lower() != 'bearer':
                raise jwt.InvalidTokenError("Token malformed, must be 'Bearer <token>'.")
            token = token_parts[1]
        except Exception:
            return jsonify({'status': 'fail', 'message': 'Token malformed!'}), 401

        try:
            # --- PERBAIKAN 1: Gunakan 'SECRET_KEY' untuk konsistensi ---
            # Pastikan 'SECRET_KEY' ada di file config.py Anda
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])

            # --- PERBAIKAN 2: Cara mengambil user_id yang benar dari payload ---
            # Akses 'identity' dulu, baru 'id'
            identity_payload = data.get('identity')
            if not isinstance(identity_payload, dict):
                 # Fallback jika identity bukan dictionary (misal dari flask-jwt-extended lama)
                 identity_payload = data.get('sub')
                 if not identity_payload:
                     return jsonify({'status': 'fail', 'message': 'Invalid token payload structure.'}), 401
                 user_id = identity_payload['id']
            else:
                 user_id = identity_payload.get('id')


            if not user_id:
                return jsonify({'status': 'fail', 'message': 'User ID not found in token identity.'}), 401

            # Panggil fungsi yang sudah ada untuk mengambil data user dari DB
            current_user_from_db = get_user_by_id(user_id)
            
            if not current_user_from_db:
                return jsonify({'status': 'fail', 'message': 'User for this token not found.'}), 401
            
            # (Opsional) Cek jika akun aktif
            if not current_user_from_db.get('is_active', True):
                return jsonify({'status': 'fail', 'message': 'Your account is inactive.'}), 403

        except jwt.ExpiredSignatureError:
            return jsonify({'status': 'fail', 'message': 'Token has expired! Please log in again.'}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({'status': 'fail', 'message': f'Token is invalid! {e}'}), 401
        except Exception as e:
            current_app.logger.error(f"An unexpected error occurred during token processing: {str(e)}")
            return jsonify({'status': 'error', 'message': 'An internal error occurred during authentication.'}), 500
        
        # Jika semua valid, teruskan ke fungsi route dengan data user
        return f(current_user_from_db, *args, **kwargs)

    return decorated

def web_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_web_user'):
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('web.web_login_page_route')) # Nama fungsi route web login
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in session or not session.get('is_admin'):
            flash('Access denied. You must be logged in as an admin.', 'danger')
            return redirect(url_for('admin.admin_login_route')) # Nama fungsi route admin login
        
        users_coll = get_users_collection()
        admin_user = users_coll.find_one({"email": session['email'], "is_admin": True})
        
        if not admin_user: # Cek ulang jika status admin dicabut saat sesi masih aktif
            flash('Admin account not valid or privileges revoked.', 'danger')
            session.clear()
            return redirect(url_for('admin.admin_login_route'))
        
        # Bisa pass admin_user ke fungsi jika dibutuhkan
        return f(*args, **kwargs) # atau f(admin_user, *args, **kwargs)
    return decorated_function