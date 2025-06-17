from flask import Blueprint, request, jsonify, session, redirect, url_for, current_app, flash, render_template
from datetime import datetime, timezone
import urllib.parse
import json

from backend.utils.decorators import token_required
from .services import (
    create_user_service,
    authenticate_user_service,
    generate_jwt_tokens,
    refresh_access_token_service,
    get_google_client, # Untuk mendapatkan instance Google dari OAuth
    process_google_oauth_callback_service,
    generate_otp_service,
    send_otp_email_service,
    get_user_by_email, # Untuk lookup user by email
    generate_reset_token_service,
    send_reset_password_email_service,
    get_user_by_id
)
from backend.database import get_users_collection

# url_prefix akan di-set saat registrasi Blueprint di backend/__init__.py
auth_bp = Blueprint('auth_api', __name__) # Nama blueprint untuk API, misal 'auth_api'

@auth_bp.route("/register", methods=["POST"])
def register_route():
    data = request.get_json()
    response, status_code = create_user_service(data)
    return jsonify(response), status_code

@auth_bp.route("/login", methods=["POST"])
def login_route():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"status": "fail", "message": "Missing email or password"}), 400

    auth_response, user_obj, status_code = authenticate_user_service(data['email'], data['password'])

    if status_code == 200 and user_obj:
        # Generate token seperti biasa
        access_token, refresh_token = generate_jwt_tokens(str(user_obj["_id"]))
        
        # [FIX] TAMBAHKAN BLOK INI UNTUK MEMBUAT SESSION COOKIE
        session.clear() # Hapus session lama jika ada
        session['is_web_user'] = True
        session['user_id'] = str(user_obj["_id"])
        session['username'] = user_obj.get("username")
        session.modified = True
        # --- AKHIR DARI BLOK TAMBAHAN ---

        # Siapkan data untuk respons JSON
        user_data_for_response = {
            "id": str(user_obj["_id"]),
            "username": user_obj.get("username"),
            "email": user_obj.get("email"),
            "gender": user_obj.get("gender"),
            "occupation": user_obj.get("occupation"),
            "is_active": user_obj.get("is_active", True),
            "profile_picture": user_obj.get("profile_picture")
        }
        
        return jsonify({
            "status": "success",
            "message": "Login successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user_data_for_response
        }), 200
        
    return jsonify(auth_response), status_code

@auth_bp.route("/refresh", methods=["POST"])
def refresh_route():
    refresh_token_str = request.json.get('refresh_token')
    response, status_code = refresh_access_token_service(refresh_token_str)
    return jsonify(response), status_code

# --- Google OAuth Routes untuk API (misalnya dipanggil oleh Flutter via webview) ---
# Ini adalah callback yang akan dipanggil oleh Google setelah user login di webview
# dan kemudian akan redirect ke Flutter app.
@auth_bp.route('/google/login/api') # Endpoint yang dipanggil oleh Flutter untuk memulai
def google_login_api_start():
    google = get_google_client()
    # Simpan info bahwa ini adalah request dari API/Flutter untuk callback
    session['oauth_api_request'] = True
    session['oauth_next_url'] = f"{current_app.config['FLUTTER_APP_SCHEME']}://{current_app.config['FLUTTER_OAUTH_CALLBACK_HOST']}" # Target Flutter
    session.modified = True
    redirect_uri = url_for('auth_api.google_authorize_api_callback', _external=True) # Callback server
    if not current_app.config['GOOGLE_CLIENT_ID'] or current_app.config['GOOGLE_CLIENT_ID'] == '801295038520-90b851hknplg0rpq77n8vr4bs1g5h7mm.apps.googleusercontent.com':
         # Handle error jika client ID tidak ada, mungkin redirect ke Flutter dengan pesan error
        error_message = urllib.parse.quote("Google OAuth Client ID not configured.")
        flutter_redirect_url = f"{session['oauth_next_url']}?status=error&message={error_message}"
        return redirect(flutter_redirect_url)
    return google.authorize_redirect(redirect_uri)

@auth_bp.route('/google/callback/api') # Callback dari Google, server-side
def google_authorize_api_callback():
    is_api_request = session.pop('oauth_api_request', False) # Cek apakah ini dari API
    flutter_target_url_base = session.pop('oauth_next_url', f"{current_app.config['FLUTTER_APP_SCHEME']}://{current_app.config['FLUTTER_OAUTH_CALLBACK_HOST']}")

    token_data, user_obj, error_message = process_google_oauth_callback_service()

    if error_message or not user_obj:
        error_msg_encoded = urllib.parse.quote(error_message or "Unknown Google OAuth error.")
        flutter_redirect_url = f"{flutter_target_url_base}?status=error&message={error_msg_encoded}"
        return redirect(flutter_redirect_url)

    # Sukses, generate JWT token untuk Flutter
    access_token, refresh_token = generate_jwt_tokens(str(user_obj["_id"]))
    user_data_for_flutter = {
        "id": str(user_obj["_id"]), "username": user_obj["username"], "email": user_obj["email"],
        "gender": user_obj.get("gender"), "occupation": user_obj.get("occupation"),
        "profile_picture": user_obj.get("profile_picture"), "is_active": user_obj.get("is_active", True)
    }
    user_data_encoded = urllib.parse.quote(json.dumps(user_data_for_flutter))

    flutter_redirect_url = (f"{flutter_target_url_base}"
                            f"?status=success&access_token={access_token}&refresh_token={refresh_token}&user={user_data_encoded}")
    return redirect(flutter_redirect_url)

debug_bp = Blueprint('debug', __name__)

@debug_bp.route("/debug-time")
def debug_time():
    """Endpoint ini hanya untuk debugging, untuk melihat waktu server."""
    server_utc_time = datetime.now(timezone.utc)
    server_local_time = datetime.now() # Waktu lokal naive server
    
    # Dapatkan waktu sekarang dari sisi client (browser) menggunakan sedikit JavaScript
    client_side_script = """
        <script>
            document.getElementById('clientTime').innerText = new Date().toString();
            document.getElementById('clientTimeUTC').innerText = new Date().toUTCString();
        </script>
    """
    
    return f"""
        <html>
            <head><title>Debug Waktu</title></head>
            <body>
                <h1>Analisis Waktu Server vs Client</h1>
                <p>Ini adalah alat untuk membandingkan jam di server (tempat Flask berjalan) dengan jam di browser Anda.</p>
                <hr>
                <h2>Waktu Menurut Server (Python/Flask)</h2>
                <p>Waktu UTC Server: <strong>{server_utc_time.isoformat()}</strong></p>
                <p>Waktu Lokal Server (Naive): <strong>{server_local_time.isoformat()}</strong></p>
                <hr>
                <h2>Waktu Menurut Browser Anda (JavaScript)</h2>
                <p>Waktu Lokal Browser: <strong id="clientTime"></strong></p>
                <p>Waktu UTC Browser: <strong id="clientTimeUTC"></strong></p>
                {client_side_script}
            </body>
        </html>
    """