import os
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv() # Ini akan memuat variabel dari .env ke environment

class Config:
    # ... (semua atribut config Anda yang sudah ada) ...
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev-flask-secret-key')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dev-jwt-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    INACTIVITY_DAYS = int(os.environ.get('INACTIVITY_DAYS', 30))
    OTP_EXPIRY_MINUTES = int(os.environ.get('OTP_EXPIRY_MINUTES', 5))
    RESET_TOKEN_EXPIRY_MINUTES = int(os.environ.get('RESET_TOKEN_EXPIRY_MINUTES', 15))

    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

    FLUTTER_APP_SCHEME = os.environ.get('FLUTTER_APP_SCHEME', 'fluentai')
    FLUTTER_OAUTH_CALLBACK_HOST = os.environ.get('FLUTTER_OAUTH_CALLBACK_HOST', 'oauthcallback')

    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', '1', 't']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', '1', 't']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    # MAIL_DEFAULT_SENDER akan di-set di init_app

    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
    MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "fluent_db")

    DEBUG = os.environ.get("FLASK_DEBUG", "true").lower() in ['true', '1', 't']
    FLASK_ENV = os.environ.get("FLASK_ENV", "development")

    # Tambahkan metode static init_app
    @staticmethod
    def init_app(app):
        """Melakukan inisialisasi konfigurasi yang bergantung pada instance app."""
        # Set MAIL_DEFAULT_SENDER setelah app.config dimuat dan MAIL_USERNAME ada
        # app.config akan berisi atribut dari kelas Config setelah app.config.from_object(Config)
        if app.config.get('MAIL_USERNAME'):
            app.config['MAIL_DEFAULT_SENDER'] = ('FLUENT App', app.config['MAIL_USERNAME'])
        else:
            # Fallback jika MAIL_USERNAME tidak di-set di environment
            app.config['MAIL_DEFAULT_SENDER'] = ('FLUENT App', 'noreply@example.com')
            if app.debug: # Beri peringatan jika dalam mode debug
                app.logger.warning(
                    "MAIL_USERNAME is not set. MAIL_DEFAULT_SENDER defaulted to 'noreply@example.com'."
                )
        # Anda bisa menambahkan logika setup config dinamis lainnya di sini jika perlu