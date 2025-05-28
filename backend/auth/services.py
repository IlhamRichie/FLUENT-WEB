# FLUENTSERVICE/backend/auth/services.py
from flask import current_app, session, url_for, render_template # Tambahkan current_app
from datetime import datetime, timezone, timedelta
import jwt
import secrets
import random
import string
from authlib.integrations.flask_client import OAuth # OAuth dibuat di sini
from bson.objectid import ObjectId
import urllib.parse
import json

from backend.database import get_users_collection
# from backend.models import UserCreate, UserInDBBase, UserResponse # Jika pakai Pydantic

# Buat instance OAuth di sini
oauth = OAuth()

def init_app_oauth(app): # Fungsi untuk dipanggil dari create_app
    oauth.init_app(app)
    # Daftarkan provider Google di sini setelah oauth diinisialisasi dengan app
    # Ini penting karena membutuhkan app.config
    google = oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        access_token_url='https://accounts.google.com/o/oauth2/token',
        authorize_url='https://accounts.google.com/o/oauth2/auth',
        api_base_url='https://www.googleapis.com/oauth2/v1/',
        userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
        client_kwargs={'scope': 'openid email profile'},
        jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
    )
    # Anda mungkin ingin menyimpan 'google' ini di suatu tempat jika perlu diakses
    # atau selalu akses via oauth.google
    return google


def get_user_by_id(user_id_str: str):
    # ... (tidak berubah)
    users_coll = get_users_collection()
    try:
        return users_coll.find_one({"_id": ObjectId(user_id_str)})
    except Exception:
        return None

def get_user_by_email(email: str):
    # ... (tidak berubah)
    users_coll = get_users_collection()
    return users_coll.find_one({"email": email.lower()})

def create_user_service(data: dict):
    users_coll = get_users_collection()
    email = data.get("email", "").lower()
    username = data.get("username")
    password = data.get("password")
    gender = data.get("gender", "Not specified")
    occupation = data.get("occupation", "Not specified")

    if not all([email, username, password]):
        return {"status": "fail", "message": "Email, username, and password are required"}, 400

    if users_coll.find_one({"$or": [{"username": username}, {"email": email}]}):
        return {"status": "fail", "message": "Username or email already exists"}, 400

    # Akses bcrypt dari current_app
    hashed_password = current_app.bcrypt.generate_password_hash(password).decode('utf-8')
    user_data = {
        "email": email, "username": username, "password": hashed_password,
        "gender": gender, "occupation": occupation, "is_active": True,
        "last_login": None, "created_at": datetime.now(timezone.utc),
        "is_admin": data.get("is_admin", False), "auth_provider": "local"
    }
    try:
        user_id_obj = users_coll.insert_one(user_data).inserted_id
        return {
            "status": "success", "message": "User registered successfully",
            "user": {"id": str(user_id_obj), "username": username, "email": email}
        }, 201
    except Exception as e:
        current_app.logger.error(f"User Registration Error: {e}")
        return {"status": "error", "message": "Registration failed due to an internal error"}, 500

def authenticate_user_service(email_input: str, password_input: str):
    user = get_user_by_email(email_input)
    if not user:
        return {"status": "fail", "message": "User not found"}, None, 404
    if not user.get('is_active', True):
        return {"status": "fail", "message": "Account is inactive"}, None, 403
    if user.get("auth_provider") == "google":
        return {"status": "fail", "message": "Please login using Google OAuth for this account."}, None, 401
    # Akses bcrypt dari current_app
    if not user.get("password") or not current_app.bcrypt.check_password_hash(user['password'], password_input):
        return {"status": "fail", "message": "Invalid password"}, None, 401

    users_coll = get_users_collection()
    users_coll.update_one({"_id": user["_id"]}, {"$set": {"last_login": datetime.now(timezone.utc), "is_active": True}})
    return {"status": "success"}, user, 200

# ... (generate_jwt_tokens, refresh_access_token_service tidak berubah signifikan) ...
def generate_jwt_tokens(user_id: str):
    access_token = jwt.encode({
        'user_id': user_id,
        'exp': datetime.now(timezone.utc) + current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
    }, current_app.config['JWT_SECRET_KEY'], algorithm="HS256")
    refresh_token = jwt.encode({
        'user_id': user_id,
        'exp': datetime.now(timezone.utc) + current_app.config['JWT_REFRESH_TOKEN_EXPIRES']
    }, current_app.config['JWT_SECRET_KEY'], algorithm="HS256")
    return access_token, refresh_token

def refresh_access_token_service(refresh_token_str: str):
    if not refresh_token_str:
        return {"status": "fail", "message": "Refresh token is missing"}, 401
    try:
        data = jwt.decode(refresh_token_str, current_app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
        user = get_user_by_id(data['user_id'])
        if not user: return {"status": "fail", "message": "User not found for token"}, 404
        if not user.get('is_active', True): return {"status": "fail", "message": "Account is inactive"}, 403

        access_token, _ = generate_jwt_tokens(str(user['_id']))
        return {"status": "success", "access_token": access_token}, 200
    except jwt.ExpiredSignatureError: return {"status": "fail", "message": "Refresh token has expired"}, 401
    except jwt.InvalidTokenError: return {"status": "fail", "message": "Invalid refresh token"}, 401
    except Exception as e:
        current_app.logger.error(f"Refresh token processing error: {str(e)}")
        return {"status": "error", "message": f'Token processing error: {str(e)}'}, 500

# get_google_client sekarang hanya mengakses oauth.google
def get_google_client():
    # oauth.google seharusnya sudah ada setelah init_app_oauth dipanggil
    if not hasattr(oauth, 'google') or not oauth.google:
        # Ini seharusnya tidak terjadi jika init_app_oauth dipanggil dengan benar
        current_app.logger.error("Google OAuth client not registered/initialized properly.")
        raise RuntimeError("Google OAuth client not available.")
    return oauth.google


def process_google_oauth_callback_service():
    google = get_google_client() # Dapat client Google yang sudah terdaftar
    # ... (sisa logika sama seperti sebelumnya, menggunakan 'google' ini) ...
    users_coll = get_users_collection()
    config = current_app.config
    try:
        token = google.authorize_access_token()
        user_info_resp = google.get('userinfo', token=token)
        user_info_resp.raise_for_status()
        userinfo = user_info_resp.json()
    except Exception as e:
        current_app.logger.error(f"Google OAuth Error during token/userinfo fetch: {str(e)}")
        return None, None, f"Google OAuth authentication failed: {str(e)}"

    email = userinfo.get('email')
    if not email:
        return None, None, "Email not found from Google profile."
    email = email.lower()

    user = users_coll.find_one({'email': email})
    now_utc = datetime.now(timezone.utc)

    if user:
        if not user.get('is_active', True):
            return None, None, "Account is inactive. Please contact administrator."
        users_coll.update_one(
            {'_id': user['_id']},
            {'$set': {
                'last_login': now_utc, 'is_active': True, 'auth_provider': "google",
                'username': userinfo.get('name', user.get('username')),
                'profile_picture': userinfo.get('picture', user.get('profile_picture'))
            }}
        )
        user = users_coll.find_one({'_id': user['_id']})
    else:
        new_user_data = {
            'email': email,
            'username': userinfo.get('name', email.split('@')[0]),
            'password': None,
            'gender': userinfo.get('gender', 'Not specified'),
            'occupation': 'Not specified', 'is_active': True, 'last_login': now_utc,
            'created_at': now_utc, 'is_admin': False, 'auth_provider': 'google',
            'profile_picture': userinfo.get('picture')
        }
        user_id_obj = users_coll.insert_one(new_user_data).inserted_id
        user = users_coll.find_one({'_id': user_id_obj})

    if not user:
        current_app.logger.error(f"Failed to process Google OAuth user for email: {email}")
        return None, None, "Internal error processing login with Google."
    return token, user, None


def generate_otp_service(length=6):
    # ... (tidak berubah)
    return "".join(random.choices(string.digits, k=length))


def send_otp_email_service(recipient_email: str, otp_code: str):
    try:
        msg_subject = "Kode Verifikasi OTP Anda - FLUENT"
        html_body = render_template("email/email_otp_template.html",
                                    otp=otp_code,
                                    app_name="FLUENT",
                                    config=current_app.config,
                                    current_year_fallback=datetime.now().year) # Tambahkan ini

        from flask_mail import Message # Impor Message di sini
        # Akses mail dari current_app
        msg = Message(subject=msg_subject, recipients=[recipient_email], html=html_body,
                      sender=current_app.config.get('MAIL_DEFAULT_SENDER'))
        current_app.mail.send(msg) # Gunakan current_app.mail
        current_app.logger.info(f"OTP email sent to {recipient_email}")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send OTP email to {recipient_email}: {e}")
        return False

# ... (generate_reset_token_service dan send_reset_password_email_service serupa, gunakan current_app.mail) ...
def generate_reset_token_service():
    return secrets.token_urlsafe(32)

def send_reset_password_email_service(recipient_email: str, reset_token: str):
    try:
        reset_url = url_for('web.web_reset_password_form_route', token=reset_token, _external=True)
        msg_subject = "Link Reset Password Anda - FLUENT"
        html_body = render_template("email/email_reset_password_template.html",
                                 reset_url=reset_url,
                                 app_name="FLUENT",
                                 config=current_app.config)
        from flask_mail import Message
        msg = Message(subject=msg_subject, recipients=[recipient_email], html=html_body,
                      sender=current_app.config.get('MAIL_DEFAULT_SENDER'))
        current_app.mail.send(msg)
        current_app.logger.info(f"Password reset email sent to {recipient_email}")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send password reset email to {recipient_email}: {e}")
        return False