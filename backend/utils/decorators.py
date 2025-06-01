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
        if auth_header:
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'message': 'Bearer token malformed'}), 401
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            data = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            # get_user_by_id sudah handle lookup ke DB
            current_user_from_db = get_user_by_id(data['user_id'])
            if not current_user_from_db:
                return jsonify({'message': 'User not found for token'}), 401
            if not current_user_from_db.get('is_active', True):
                return jsonify({'message': 'Your account is inactive'}), 403
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 401
        except Exception as e:
            current_app.logger.error(f"Token processing error: {str(e)}")
            return jsonify({'message': f'Token processing error: {str(e)}'}), 401
        
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