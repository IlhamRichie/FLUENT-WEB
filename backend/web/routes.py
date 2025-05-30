# FLUENTSERVICE/backend/web/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app # TAMBAHKAN current_app
from datetime import datetime, timedelta, timezone
from bson.objectid import ObjectId
from flask import send_from_directory, current_app
import os


from backend.auth.services import (
    get_google_client,
    process_google_oauth_callback_service,
    generate_otp_service,
    send_otp_email_service,
    get_user_by_email, # Ini yang kita panggil
    get_user_by_id,
    generate_reset_token_service,
    send_reset_password_email_service
)
from backend.database import get_users_collection
from backend.utils.decorators import web_login_required
# from backend import bcrypt # HAPUS IMPOR INI

web_bp = Blueprint('web', __name__, template_folder='../templates')

# ... (route-route lain seperti index_route, features_route, api_docs_page_route tetap sama) ...
@web_bp.route('/')
def index_route():
    return render_template('web/index.html')

@web_bp.route('/features')
def features_route():
    return render_template('web/features.html')

@web_bp.route('/api-docs-page')
def api_docs_page_route():
    return render_template('web/api_docs.html')


@web_bp.route('/login', methods=['GET'])
def web_login_route():
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
    if 'user_id' in session and session.get('is_web_user'):
        return redirect(url_for('web.web_profile_route'))

    form = request.form
    username = form.get('username')
    email = form.get('email', '').lower()
    password = form.get('password')
    confirm_password = form.get('confirm_password')
    gender = form.get('gender') or "Not specified"
    occupation = form.get('occupation') or "Not specified"

    if not all([username, email, password, confirm_password]):
        flash('All fields (except gender and occupation) are required.', 'danger')
        return redirect(url_for('web.web_register_page_route'))
    if password != confirm_password:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('web.web_register_page_route'))
    if len(password) < 6:
        flash('Password must be at least 6 characters long.', 'danger')
        return redirect(url_for('web.web_register_page_route'))
    
    users_coll = get_users_collection()
    if users_coll.find_one({"$or": [{"username": username}, {"email": email}]}):
        flash('Username or email already registered.', 'danger')
        return redirect(url_for('web.web_register_page_route'))

    # Gunakan current_app.bcrypt
    hashed_password = current_app.bcrypt.generate_password_hash(password).decode('utf-8')
    user_data = {
        "email": email, "username": username, "password": hashed_password,
        "gender": gender, "occupation": occupation, "is_active": True,
        "last_login": None, "created_at": datetime.now(timezone.utc),
        "is_admin": False, "auth_provider": "local"
    }
    try:
        users_coll.insert_one(user_data)
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('web.web_login_route'))
    except Exception as e:
        current_app.logger.error(f"Web registration error: {e}")
        flash('An error occurred during registration. Please try again later.', 'danger')
        return redirect(url_for('web.web_register_page_route'))

@web_bp.route('/login-email', methods=['POST']) # Login dengan email & password, lalu kirim OTP
def web_login_email_password_route():
    if 'user_id' in session and session.get('is_web_user'):
        return redirect(url_for('web.web_profile_route'))

    # --- PASTIKAN BARIS INI ADA DAN BENAR ---
    email = request.form.get('email', '').lower()
    password = request.form.get('password')

    if not email or not password: # Sekarang 'email' sudah terdefinisi
        flash('Email and password are required.', 'warning')
        return redirect(url_for('web.web_login_route'))

    user = get_user_by_email(email) # Sekarang 'email' bisa digunakan
    if not user:
        flash('Email not registered.', 'danger')
        return redirect(url_for('web.web_login_route'))
    if not user.get('is_active', True):
        flash('Your account is inactive. Please contact support.', 'warning')
        return redirect(url_for('web.web_login_route'))
    if user.get("auth_provider") == "google":
        flash('This account is registered via Google. Please log in with Google.', 'info')
        return redirect(url_for('web.web_login_route'))
    if not user.get("password") or not current_app.bcrypt.check_password_hash(user['password'], password):
        flash('Incorrect password.', 'danger')
        return redirect(url_for('web.web_login_route'))

    # Hapus OTP lama jika ada
    session.pop('otp_for_verification', None)
    session.pop('otp_timestamp', None)
    session.pop('email_for_verification', None)

    otp = generate_otp_service()
    session['otp_for_verification'] = otp
    session['email_for_verification'] = email # Simpan email untuk verifikasi OTP
    session['otp_timestamp'] = datetime.now(timezone.utc).isoformat()
    session.modified = True
    
    if send_otp_email_service(email, otp):
        flash(f'An OTP has been sent to {email}.', 'info')
        return redirect(url_for('web.web_verify_otp_page_route'))
    else:
        flash('Failed to send OTP. Please try again or contact support.', 'danger')
        return redirect(url_for('web.web_login_route'))


# ... (route /verify-otp, /resend-otp, /google/login/web, /google/callback/web tetap sama karena tidak menggunakan bcrypt secara langsung) ...
@web_bp.route('/verify-otp', methods=['GET'])
def web_verify_otp_page_route():
    if 'user_id' in session and session.get('is_web_user'):
        return redirect(url_for('web.web_profile_route'))

    email_for_verification = session.get('email_for_verification')
    if not email_for_verification or not session.get('otp_for_verification'):
        flash('Invalid OTP session or OTP not requested. Please try logging in again.', 'warning')
        return redirect(url_for('web.web_login_route'))
    return render_template('auth/verify_otp.html', email_for_verification=email_for_verification)

@web_bp.route('/verify-otp/submit', methods=['POST'])
def web_verify_otp_submit_route():
    entered_otp = request.form.get('otp')
    user_email_for_otp = session.get('email_for_verification')

    if not entered_otp or not user_email_for_otp:
        flash('Invalid request. Please try requesting OTP again.', 'danger')
        return redirect(url_for('web.web_login_route'))

    stored_otp = session.get('otp_for_verification')
    stored_otp_time_iso = session.get('otp_timestamp')
    otp_expiry_minutes = current_app.config['OTP_EXPIRY_MINUTES']

    if not stored_otp or not stored_otp_time_iso:
        flash('OTP session invalid or expired. Please request a new OTP.', 'danger')
        return redirect(url_for('web.web_login_route'))

    try:
        otp_generation_time = datetime.fromisoformat(stored_otp_time_iso)
        if not otp_generation_time.tzinfo:
             otp_generation_time = otp_generation_time.replace(tzinfo=timezone.utc)
        current_time_utc = datetime.now(timezone.utc)
        otp_expiry_time = otp_generation_time + timedelta(minutes=otp_expiry_minutes)

        if current_time_utc > otp_expiry_time:
            flash('OTP has expired. Please request a new one.', 'danger')
            session.pop('otp_for_verification', None)
            session.pop('otp_timestamp', None)
            session.pop('email_for_verification', None)
            session.modified = True
            return redirect(url_for('web.web_login_route'))

        if entered_otp != stored_otp:
            flash('Invalid OTP.', 'danger')
            return redirect(url_for('web.web_verify_otp_page_route'))

        user = get_user_by_email(user_email_for_otp)
        if not user:
            flash('User not found during OTP verification. Please login again.', 'danger')
            session.pop('otp_for_verification', None)
            session.pop('otp_timestamp', None)
            session.pop('email_for_verification', None)
            session.modified = True
            return redirect(url_for('web.web_login_route'))

        session.pop('otp_for_verification', None)
        session.pop('otp_timestamp', None)
        session.pop('email_for_verification', None)
        session.modified = True

        users_coll = get_users_collection()
        users_coll.update_one({"_id": user["_id"]}, {"$set": {"last_login": datetime.now(timezone.utc), "is_active": True}})

        session['user_id'] = str(user['_id'])
        session['username'] = user['username']
        session['email'] = user['email']
        session['profile_picture'] = user.get('profile_picture')
        session['is_web_user'] = True
        session.modified = True

        flash('OTP verified successfully! You are now logged in.', 'success')
        return redirect(url_for('web.web_profile_route'))

    except ValueError as e:
        current_app.logger.error(f"OTP timestamp parsing error: {e}")
        flash('An internal error occurred during OTP verification. Please try again.', 'danger')
        return redirect(url_for('web.web_login_route'))
    except Exception as e:
        current_app.logger.error(f"Unexpected OTP verification error: {e}", exc_info=True)
        flash('An unexpected error occurred during OTP verification.', 'danger')
        return redirect(url_for('web.web_login_route'))

@web_bp.route('/resend-otp', methods=['GET'])
def web_resend_otp_route():
    if 'user_id' in session and session.get('is_web_user'):
        return redirect(url_for('web.web_profile_route'))

    email_to_verify = session.get('email_for_verification')
    if not email_to_verify:
        flash('Session not found or email for OTP is missing. Please try logging in again.', 'warning')
        return redirect(url_for('web.web_login_route'))

    session.pop('otp_for_verification', None)
    session.pop('otp_timestamp', None)

    otp = generate_otp_service()
    session['otp_for_verification'] = otp
    session['otp_timestamp'] = datetime.now(timezone.utc).isoformat()
    session.modified = True

    if send_otp_email_service(email_to_verify, otp):
        flash(f'A new OTP has been sent to {email_to_verify}.', 'info')
    else:
        flash('Failed to resend OTP.', 'danger')
    return redirect(url_for('web.web_verify_otp_page_route'))

@web_bp.route('/google/login/web')
def google_login_web_start():
    google = get_google_client()
    session['oauth_web_request'] = True
    session['oauth_next_url'] = request.args.get('next') or url_for('web.web_profile_route', _external=True)
    session.modified = True
    redirect_uri = url_for('web.google_authorize_web_callback', _external=True)
    if not current_app.config['GOOGLE_CLIENT_ID'] or current_app.config['GOOGLE_CLIENT_ID'] == '801295038520-90b851hknplg0rpq77n8vr4bs1g5h7mm.apps.googleusercontent.com':
        flash("Google Login service is currently unavailable. Please try again later.", "danger")
        return redirect(url_for('web.web_login_route'))
    return google.authorize_redirect(redirect_uri)

@web_bp.route('/google/callback/web')
def google_authorize_web_callback():
    is_web_request = session.pop('oauth_web_request', False)
    next_url_target = session.pop('oauth_next_url', url_for('web.web_profile_route'))

    token_data, user_obj, error_message = process_google_oauth_callback_service()

    if error_message or not user_obj:
        flash(error_message or "Unknown Google OAuth error during web login.", "danger")
        return redirect(url_for('web.web_login_route'))

    session['user_id'] = str(user_obj['_id'])
    session['username'] = user_obj['username']
    session['email'] = user_obj['email']
    session['profile_picture'] = user_obj.get('profile_picture')
    session['is_web_user'] = True
    session.modified = True
    flash(f"Welcome back, {user_obj['username']}! You are logged in via Google.", "success")
    return redirect(next_url_target)


@web_bp.route('/forgot-password', methods=['GET', 'POST'])
def web_forgot_password_request_route():
    # ... (logika lainnya sama)
    if request.method == 'POST':
        email = request.form.get('email', '').lower()
        if not email:
            flash('Email address is required.', 'danger')
            return render_template('auth/forgot_password_web.html')

        user = get_user_by_email(email)
        users_coll = get_users_collection()

        if user and user.get("auth_provider") == "local" and user.get("password"):
            reset_token = generate_reset_token_service()
            expiry_time = datetime.now(timezone.utc) + timedelta(minutes=current_app.config['RESET_TOKEN_EXPIRY_MINUTES'])

            users_coll.update_one(
                {"_id": user["_id"]},
                {"$set": {
                    "reset_password_token": reset_token,
                    "reset_token_expiry": expiry_time
                }}
            )
            send_reset_password_email_service(user['email'], reset_token)

        flash('If an account with that email exists and is eligible, a password reset link has been sent. Please check your email (including spam folder).', 'info')
        return redirect(url_for('web.web_login_route'))

    return render_template('auth/forgot_password_web.html')

@web_bp.route('/reset-password/<token>', methods=['GET'])
def web_reset_password_form_route(token):
    # ... (logika lainnya sama)
    if 'user_id' in session and session.get('is_web_user'):
        return redirect(url_for('web.web_profile_route'))

    users_coll = get_users_collection()
    user = users_coll.find_one({
        "reset_password_token": token,
        "reset_token_expiry": {"$gt": datetime.now(timezone.utc)}
    })

    if not user:
        flash('Invalid or expired password reset token. Please request a new link.', 'danger')
        return redirect(url_for('web.web_forgot_password_request_route'))

    if user.get("auth_provider") == "google":
        flash('Password cannot be reset for accounts linked with Google.', 'warning')
        users_coll.update_one(
            {"_id": user["_id"]},
            {"$unset": {"reset_password_token": "", "reset_token_expiry": ""}}
        )
        return redirect(url_for('web.web_login_route'))

    return render_template('auth/reset_password_form_web.html', token=token)


@web_bp.route('/reset-password/<token>', methods=['POST'])
def web_reset_password_submit_route(token):
    # ... (logika validasi password sama)
    if 'user_id' in session and session.get('is_web_user'):
        return redirect(url_for('web.web_profile_route'))

    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if not password or not confirm_password:
        flash('Both password fields are required.', 'danger')
        return redirect(url_for('web.web_reset_password_form_route', token=token))
    if password != confirm_password:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('web.web_reset_password_form_route', token=token))
    if len(password) < 6:
        flash('Password must be at least 6 characters long.', 'danger')
        return redirect(url_for('web.web_reset_password_form_route', token=token))

    users_coll = get_users_collection()
    user = users_coll.find_one({
        "reset_password_token": token,
        "reset_token_expiry": {"$gt": datetime.now(timezone.utc)}
    })

    if not user:
        flash('Invalid or expired password reset token. Please request a new link.', 'danger')
        return redirect(url_for('web.web_forgot_password_request_route'))

    if user.get("auth_provider") == "google":
        flash('Password cannot be reset for accounts linked with Google.', 'warning')
        users_coll.update_one(
            {"_id": user["_id"]},
            {"$unset": {"reset_password_token": "", "reset_token_expiry": ""}}
        )
        return redirect(url_for('web.web_login_route'))

    # Gunakan current_app.bcrypt
    hashed_password = current_app.bcrypt.generate_password_hash(password).decode('utf-8')
    users_coll.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"password": hashed_password, "auth_provider": "local"},
            "$unset": {"reset_password_token": "", "reset_token_expiry": ""}
        }
    )
    flash('Your password has been successfully reset. Please log in with your new password.', 'success')
    return redirect(url_for('web.web_login_route'))


# ... (route /profile dan /logout tetap sama) ...
@web_bp.route('/profile')
@web_login_required
def web_profile_route():
    user_id_str = session.get('user_id')
    user_data = get_user_by_id(user_id_str)

    if not user_data:
        flash("User data not found. Please log in again.", "danger")
        session.clear()
        session.modified = True
        return redirect(url_for('web.web_login_route'))

    session['profile_picture'] = user_data.get('profile_picture')
    session['username'] = user_data.get('username')
    session.modified = True
    return render_template('web/profile_web.html', user=user_data)

@web_bp.route('/logout')
@web_login_required
def web_logout_route():
    keys_to_pop = [
        'user_id', 'username', 'email', 'profile_picture', 'is_web_user',
        'otp_for_verification', 'email_for_verification', 'otp_timestamp',
        'oauth_next_url', 'oauth_token', 'oauth_web_request', 'oauth_api_request'
    ]
    for key in keys_to_pop:
        session.pop(key, None)
    session.modified = True
    flash('You have been successfully logged out.', 'success')
    return redirect(url_for('web.web_login_route'))

@web_bp.route('/interview-simulation')
@web_login_required# Hanya user yang sudah login bisa akses
def interview_simulation_page():
    # Anda bisa mengirim data user ke template jika diperlukan
    user_info = {
        "username": session.get("username", "Pengguna"),
        # Tambahkan data lain jika perlu
    }
    current_app.logger.info(f"User {session.get('user_id')} accessing interview simulation.")
    return render_template('web/gimmick.html', user=user_info, app_name=current_app.config.get("APP_NAME", "FLUENT"))


# Route untuk serve static files (jika tidak dihandle oleh Nginx/Apache di production)
from flask import send_from_directory
import os
@web_bp.route('/static/<path:filename>')
def web_serve_static(filename):
    static_folder = os.path.join(current_app.root_path, 'static')
    return send_from_directory(static_folder, filename)