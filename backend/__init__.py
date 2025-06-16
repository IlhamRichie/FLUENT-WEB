# FLUENTSERVICE/backend/__init__.py
import os
from flask import Flask, render_template # Hapus 'app' dari impor ini
# ... (impor lainnya) ...
from .config import Config
from .database import init_db, get_questions_collection # Impor fungsi getter
# Hapus impor 'Flask, render_template' yang duplikat jika ada
from flask import request, jsonify # Pastikan ini diimpor di atas
from flask_cors import CORS

# HAPUS DEFINISI ERROR HANDLER DARI SINI


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True) # Instance app dibuat di sini
    app.config.from_object(config_class)
    Config.init_app(app)

    # --- PINDAHKAN DEFINISI ERROR HANDLER KE SINI ---
    @app.errorhandler(404)
    def page_not_found(e):
        # Untuk mengakses request, impor `request` dari flask jika belum
        # from flask import request, current_app
        # current_app.logger.warning(f"Page not found: {request.url} - {e}")
        # Jika request ke path API, kembalikan JSON
        if request.path.startswith('/api/'):
            return jsonify({'status': 'error', 'message': 'Endpoint tidak ditemukan.'}), 404
        # Jika tidak, baru kembalikan halaman HTML
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        # from flask import request, current_app
        # current_app.logger.error(f"Internal server error: {request.url} - {e}")
        return render_template('errors/500.html'), 500
    # --- BATAS PEMINDAHAN ERROR HANDLER ---

    from flask_bcrypt import Bcrypt
    from flask_cors import CORS
    from flask_mail import Mail
    from .auth.services import init_app_oauth
    from datetime import timezone, timedelta
    
    def format_datetime_to_wib(utc_dt):
        """Custom filter untuk mengubah datetime UTC ke format string WIB."""
        if not utc_dt:
            return "N/A"
        
        # Buat timezone untuk WIB (UTC+7)
        wib_tz = timezone(timedelta(hours=7))
        
        # Ubah datetime ke zona waktu WIB
        wib_dt = utc_dt.astimezone(wib_tz)
        
        # Format ke string yang mudah dibaca
        return wib_dt.strftime('%d %b %Y, %H:%M:%S WIB')

    # Daftarkan fungsi sebagai filter Jinja2
    app.jinja_env.filters['to_wib'] = format_datetime_to_wib

    app.bcrypt = Bcrypt(app)
    CORS(app, resources={
        r"/api/*": {"origins": "*"},
        r"/*": {"origins": "*"}
    })
    app.mail = Mail(app)
    init_app_oauth(app)

    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    init_db(app) # Inisialisasi koneksi database

    # ... (Register Blueprints seperti sebelumnya) ...
    from .auth.routes import auth_bp
    from .users.routes import users_api_bp
    from .interview.routes import interview_api_bp
    from .analysis.routes import analysis_api_bp
    from .admin.routes import admin_bp
    from .web.routes import web_bp # Pastikan web_bp diimpor

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(users_api_bp, url_prefix='/api/user')
    app.register_blueprint(interview_api_bp, url_prefix='/api/interview')
    app.register_blueprint(analysis_api_bp, url_prefix='/api/analysis')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(web_bp) # Daftarkan web_bp

    # ... (Swagger UI seperti sebelumnya) ...
    from flask_swagger_ui import get_swaggerui_blueprint
    SWAGGER_URL = '/api/docs/swagger'
    API_URL = '/static/swagger.json'
    swaggerui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL, API_URL,
        config={'app_name': "Fluent Interview API"}
    )
    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)


    from datetime import datetime, timezone
    @app.context_processor
    def inject_now():
        return {'now': datetime.now(timezone.utc)}

    # Seeding data
    with app.app_context():
        current_questions_collection = get_questions_collection()
        if current_questions_collection is not None and current_questions_collection.count_documents({}) == 0:
            current_questions_collection.insert_many([
                {"question": "Ceritakan tentang diri Anda", "category": "general", "ideal_answer_keywords": ["pengalaman", "pendidikan", "kemampuan", "tujuan"]},
                {"question": "Apa kelebihan dan kelemahan Anda?", "category": "general", "ideal_answer_keywords": ["kelebihan", "kelemahan", "perbaikan", "pengembangan"]},
                {"question": "Mengapa Anda tertarik dengan posisi ini?", "category": "specific", "ideal_answer_keywords": ["motivasi", "kesesuaian", "kontribusi", "perusahaan"]},
            ])
            app.logger.info("Default questions seeded.")
        elif current_questions_collection is None:
            app.logger.error("Questions collection is None. Cannot seed data. Check MongoDB connection and initialization.")

    return app