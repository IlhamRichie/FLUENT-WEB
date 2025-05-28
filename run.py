import os
from backend import create_app # create_app dari backend/__init__.py
from dotenv import load_dotenv

load_dotenv() # Ini akan memuat variabel dari .env ke environment

# Dapatkan konfigurasi environment (development, production, dll.)
# Ini bisa juga di-set di dalam create_app atau config.py jika lebih disukai
FLASK_ENV = os.environ.get("FLASK_ENV", "development")

app = create_app() # config_class default akan digunakan (Config dari config.py)

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        # Debug mode biasanya dikontrol oleh FLASK_DEBUG atau app.config['DEBUG']
        # app.config['DEBUG'] sudah di-set di config.py berdasarkan FLASK_DEBUG
        # Jadi, tidak perlu set debug=True secara eksplisit di sini jika sudah di config
    )