from functools import wraps
from flask import request, jsonify, session, flash, redirect, url_for, current_app, g
import jwt

# Impor fungsi get_user_by_id dari auth.services
from backend.auth.services import get_user_by_id
from backend.database import get_users_collection # Untuk admin_required


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # 1. Periksa apakah header 'Authorization' ada
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # 2. Ambil token dari header "Bearer <token>"
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'status': 'fail', 'message': 'Bearer token malformed'}), 401
        
        if not token:
            return jsonify({'status': 'fail', 'message': 'Token is missing!'}), 401

        try:
            # 3. Decode token menggunakan secret key yang sama
            # PyJWT secara otomatis akan memvalidasi 'exp' (waktu kedaluwarsa)
            data = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            
            # 4. Cari pengguna di database berdasarkan user_id dari token
            current_user = get_user_by_id(data['user_id'])
            if current_user is None:
                return jsonify({'status': 'fail', 'message': 'User not found for token'}), 404
            
            # Periksa apakah akun aktif
            if not current_user.get('is_active', True):
                return jsonify({'status': 'fail', 'message': 'Account is inactive'}), 403

        except jwt.ExpiredSignatureError:
            return jsonify({'status': 'fail', 'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'status': 'fail', 'message': 'Token is invalid!'}), 401
        except Exception as e:
            current_app.logger.error(f"Token processing error: {e}")
            return jsonify({'status': 'error', 'message': 'Internal server error during token validation'}), 500

        # 5. Lolos validasi, teruskan data pengguna ke fungsi route
        # dan simpan ke 'g' untuk akses mudah di tempat lain jika perlu
        g.current_user = current_user
        return f(current_user, *args, **kwargs)

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