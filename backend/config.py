# backend/config.py
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'a-very-secret-key-for-flask-sessions-dev')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'a-very-secret-jwt-key-dev')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES_HOURS', 1)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.environ.get('JWT_REFRESH_TOKEN_EXPIRES_DAYS', 30)))

    INACTIVITY_DAYS = int(os.environ.get('INACTIVITY_DAYS', 3)) # Dari file Anda
    OTP_EXPIRY_MINUTES = int(os.environ.get('OTP_EXPIRY_MINUTES', 5))
    RESET_TOKEN_EXPIRY_MINUTES = int(os.environ.get('RESET_TOKEN_EXPIRY_MINUTES', 30)) # Dari file Anda

    # Kredensial Google OAuth untuk Authlib (Alur Web/Redirect)
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID') # Client ID untuk alur web OAuth
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

    # Client ID Web yang digunakan untuk memverifikasi ID Token dari aplikasi native (Flutter)
    # Ini bisa sama atau berbeda dari GOOGLE_CLIENT_ID di atas, tergantung setup Anda di Google Cloud Console
    GOOGLE_CLIENT_ID_WEB_FOR_TOKEN_VERIFY = os.environ.get('GOOGLE_CLIENT_ID_WEB_FOR_TOKEN_VERIFY', GOOGLE_CLIENT_ID)

    FLUTTER_APP_SCHEME = os.environ.get('FLUTTER_APP_SCHEME', 'fluentai')
    FLUTTER_OAUTH_CALLBACK_HOST = os.environ.get('FLUTTER_OAUTH_CALLBACK_HOST', 'oauthcallback')

    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', '1', 't']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() in ['true', '1', 't']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'edigitaldompet@gmail.com') # Ganti dengan default yang aman
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'jyag nujw fwki njdl') # Ganti dengan default yang aman
    
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
    MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "flutterauth") # Sesuai file Anda

    DEBUG = os.environ.get("FLASK_DEBUG", "True").lower() in ['true', '1', 't']
    FLASK_ENV = os.environ.get("FLASK_ENV", "development")
    API_SECRET_KEY = os.environ.get('API_KEY', 'fluentendpoint') # Dari file Anda

    APP_NAME = "Fluent" # Nama Aplikasi

    @staticmethod
    def init_app(app):
        if app.config.get('MAIL_USERNAME') and app.config['MAIL_USERNAME'] != 'edigitaldompet@gmail.com':
            app.config['MAIL_DEFAULT_SENDER'] = (Config.APP_NAME, app.config['MAIL_USERNAME'])
        else:
            app.config['MAIL_DEFAULT_SENDER'] = (Config.APP_NAME, 'fluent@fluent.com')
            if app.debug:
                app.logger.warning(
                    f"MAIL_USERNAME is not set or is placeholder. MAIL_DEFAULT_SENDER defaulted to '{app.config['MAIL_DEFAULT_SENDER']}'."
                )