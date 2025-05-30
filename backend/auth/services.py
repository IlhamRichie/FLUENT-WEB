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

# backend/auth/services.py
def init_app_oauth(app):
    global _google_oauth_client
    oauth.init_app(app)
    client_id_to_register = app.config.get('GOOGLE_CLIENT_ID')
    client_secret_to_register = app.config.get('GOOGLE_CLIENT_SECRET')

    app.logger.info(f"Attempting to register Google OAuth. Client ID: {client_id_to_register}") # Log Client ID yang digunakan

    if not client_id_to_register or not client_secret_to_register:
        app.logger.error("CRITICAL: GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET is missing in app.config. Google OAuth client will NOT be registered.")
        _google_oauth_client = None
        return

    try:
        registered_google_client = oauth.register(
            name='google',
            client_id=client_id_to_register,
            client_secret=client_secret_to_register,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'}
        )
        # Verifikasi bahwa klien 'google' benar-benar terdaftar di objek oauth
        if hasattr(oauth, 'google') and oauth.google:
             _google_oauth_client = oauth.google
             app.logger.info("Google OAuth client registered successfully via server metadata.")
             # Anda bisa coba log beberapa properti klien untuk memastikan metadata diambil
             # app.logger.info(f"   Authorize URL from client: {oauth.google.authorize_url}")
             # app.logger.info(f"   Token URL from client: {oauth.google.access_token_url}")
             # app.logger.info(f"   Userinfo endpoint from client: {oauth.google.userinfo_endpoint}")
        else:
            app.logger.error("Authlib registered the client, but 'oauth.google' is not available as expected.")
            _google_oauth_client = None

    except Exception as e:
        app.logger.error(f"Failed to register Google OAuth client with Authlib: {e}", exc_info=True)
        _google_oauth_client = None

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
# backend/auth/services.py
def get_google_client():
    global _google_oauth_client # Jika Anda menggunakan ini
    if _google_oauth_client is None:
        current_app.logger.error("Google OAuth client (_google_oauth_client) is None. Was init_app_oauth called successfully at startup?")
        # Pertimbangkan untuk memanggil init_app_oauth lagi sebagai fallback, tapi ini menunjukkan masalah startup
        # init_app_oauth(current_app._get_current_object())
        # if _google_oauth_client is None:
        raise RuntimeError("Google OAuth client not available. Check app config and startup logs.")
    return _google_oauth_client

def process_google_oauth_callback_service():
    try:
        google = get_google_client()
    except RuntimeError as e:
        current_app.logger.critical(f"Google client not available in callback: {e}")
        return None, None, "Google Login service is critically misconfigured. Please contact support."

    users_coll = get_users_collection()
    if users_coll is None:
        current_app.logger.error("Users collection is None in process_google_oauth_callback_service.")
        return None, None, "Database service unavailable. Please try again later."

    token_response = None
    userinfo = None

    try:
        current_app.logger.info("Attempting to authorize access token from Google...")
        token_response = google.authorize_access_token()
        if not token_response or 'access_token' not in token_response:
            current_app.logger.error(f"Google OAuth: Failed to authorize access token. Response: {token_response}")
            return None, None, "Google OAuth: Failed to obtain access token from Google."
        current_app.logger.info("Successfully authorized access token from Google.")

        current_app.logger.info("Fetching userinfo from Google...")
        
        # Method 1: Use built-in userinfo() if available
        if hasattr(google, 'userinfo') and callable(google.userinfo):
            userinfo = google.userinfo(token=token_response)
            if isinstance(userinfo, dict):
                # Direct dictionary response
                pass
            else:
                # Handle case where it might be a response object
                try:
                    userinfo = userinfo.json()
                except Exception as e:
                    current_app.logger.error(f"Failed to parse userinfo response: {e}")
                    return token_response, None, "Failed to process Google user information"
        
        # Method 2: Fallback to manual userinfo endpoint request
        elif hasattr(google, 'userinfo_endpoint') and google.userinfo_endpoint:
            current_app.logger.info(f"Using google.get() with discovered userinfo_endpoint: {google.userinfo_endpoint}")
            userinfo_resp = google.get(google.userinfo_endpoint, token=token_response)
            if userinfo_resp.status_code != 200:
                error_msg = f"Google userinfo request failed with status {userinfo_resp.status_code}"
                current_app.logger.error(f"{error_msg}: {userinfo_resp.text}")
                return token_response, None, f"{error_msg}. Please try again."
            try:
                userinfo = userinfo_resp.json()
            except ValueError as e:
                current_app.logger.error(f"Failed to decode userinfo JSON: {e}")
                return token_response, None, "Failed to process Google user information"
        
        else:
            current_app.logger.error("Google OAuth: No valid method to fetch userinfo available")
            return token_response, None, "Google OAuth client configuration error (cannot fetch userinfo)."

        # Check for errors in userinfo response
        if not userinfo or 'error' in userinfo:
            error_msg = userinfo.get('error', 'No userinfo received')
            current_app.logger.error(f"Google OAuth Error in userinfo: {error_msg}")
            return token_response, None, f"Google authentication error: {error_msg}"

        current_app.logger.info(f"Successfully fetched userinfo: email='{userinfo.get('email')}', name='{userinfo.get('name')}'")

    except Exception as e:
        current_app.logger.error(f"Google OAuth Error during token exchange or userinfo fetch: {str(e)}", exc_info=True)
        authlib_error_description = session.pop("google_authlib_error_description", None)
        response_text = getattr(e, 'response', None)

        if authlib_error_description:
            error_msg = f"Google login failed: {authlib_error_description}"
        elif response_text is not None and hasattr(response_text, 'text') and response_text.text:
            error_msg = f"Google authentication process failed: {str(e)} - Server Response: {response_text.text[:200]}"
        else:
            error_msg = f"Google authentication process failed: {str(e)}"
        return token_response, None, error_msg

    # Process user information
    email_from_google = userinfo.get('email', '').lower()
    if not email_from_google:
        current_app.logger.error("Google OAuth: Email not found in userinfo response.")
        return token_response, None, "Email not received from Google. Please ensure your Google account has an email."

    if not userinfo.get('email_verified', False):
        current_app.logger.warning(f"Google OAuth: Email {email_from_google} is not verified by Google. Proceeding anyway.")

    # Find or create user
    user = users_coll.find_one({'email': email_from_google})
    now_utc = datetime.now(timezone.utc)

    if user:
        current_app.logger.info(f"Google OAuth: User found with email {email_from_google}. Updating user data.")
        if not user.get('is_active', False):
            current_app.logger.warning(f"Google OAuth: Account for {email_from_google} is inactive.")
            return token_response, None, "Your account is currently inactive. Please contact support."

        update_fields = {
            'last_login': now_utc,
            'is_active': True,
            'auth_provider': "google",
            'username': userinfo.get('name', user.get('username')),
            'profile_picture': userinfo.get('picture', user.get('profile_picture')),
            'updated_at': now_utc
        }
        
        try:
            users_coll.update_one({'_id': user['_id']}, {'$set': update_fields})
            user = users_coll.find_one({'_id': user['_id']})
        except Exception as e:
            current_app.logger.error(f"Error updating existing user {email_from_google}: {e}", exc_info=True)
            return token_response, None, "Failed to update your account information. Please try again."
    else:
        current_app.logger.info(f"Google OAuth: Creating new user for email {email_from_google}")
        new_user_data = {
            'email': email_from_google,
            'username': userinfo.get('name', email_from_google.split('@')[0]),
            'password': None,
            'gender': userinfo.get('gender', 'Not specified'),
            'occupation': 'Not specified',
            'is_active': True,
            'is_verified': True,
            'last_login': now_utc,
            'created_at': now_utc,
            'updated_at': now_utc,
            'is_admin': False,
            'auth_provider': 'google',
            'profile_picture': userinfo.get('picture')
        }
        
        try:
            result = users_coll.insert_one(new_user_data)
            user = users_coll.find_one({'_id': result.inserted_id})
            current_app.logger.info(f"Successfully created new user {email_from_google}")
        except Exception as e:
            current_app.logger.error(f"Error creating new user: {e}", exc_info=True)
            return None, None, "Failed to create your account. Please try again."

    if not user:
        current_app.logger.critical(f"CRITICAL: User object is None after processing for email: {email_from_google}")
        return token_response, None, "An unexpected error occurred during login."

    current_app.logger.info(f"Google OAuth process successful for user: {user.get('email')}")
    return token_response, user, None

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