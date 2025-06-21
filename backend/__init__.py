import os
from datetime import datetime, timezone, timedelta

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_swagger_ui import get_swaggerui_blueprint

from backend.utils.template_filters import format_to_wib, format_to_wib_timesince

from .config import Config
from .database import init_db, get_questions_collection

def create_app(config_class=Config):
    """
    Application Factory untuk membuat dan mengonfigurasi aplikasi Flask.
    """
    app = Flask(__name__, instance_relative_config=True)
    
    # 1. Muat Konfigurasi
    app.config.from_object(config_class)
    Config.init_app(app) # Jika ada logika inisialisasi tambahan di Config

    # Pastikan instance folder ada
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # 2. Inisialisasi Ekstensi
    app.bcrypt = Bcrypt(app)
    app.mail = Mail(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}, r"/*": {"origins": "*"}})
    
    # Inisialisasi OAuth dari service
    from .auth.services import init_app_oauth
    init_app_oauth(app)
    
    # 3. Inisialisasi Database
    init_db(app)

    # 4. Daftarkan Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        # Jika request ke path API, kembalikan JSON
        if request.path.startswith('/api/'):
            return jsonify({'status': 'error', 'message': 'Endpoint tidak ditemukan.'}), 404
        # Jika tidak, kembalikan halaman HTML
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        app.logger.error(f"Internal server error: {e}", exc_info=True)
        if request.path.startswith('/api/'):
            return jsonify({'status': 'error', 'message': 'Terjadi kesalahan internal pada server.'}), 500
        return render_template('errors/500.html'), 500
    
    # 5. Daftarkan Jinja Filters & Context Processors
    def format_datetime_to_wib(utc_dt):
        """Custom filter untuk mengubah datetime UTC menjadi format string WIB."""
        if not utc_dt:
            return ""
        wib_tz = timezone(timedelta(hours=7))
        wib_dt = utc_dt.astimezone(wib_tz)
        return wib_dt.strftime('%d %b %Y, %H:%M:%S WIB')

    app.jinja_env.filters['to_wib'] = format_to_wib
    app.jinja_env.filters['to_wib_timesince'] = format_to_wib_timesince

    @app.context_processor
    def inject_now():
        return {'now': datetime.now(timezone.utc)}

    # 6. Daftarkan Blueprints
    from .auth.routes import auth_bp, debug_bp
    from .users.routes import users_api_bp
    from .interview.routes import interview_api_bp
    from .analysis.routes import analysis_api_bp
    from .admin.routes import admin_bp
    from .web.routes import web_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth') # Diubah ke /api/auth untuk konsistensi
    app.register_blueprint(users_api_bp, url_prefix='/api/users') # Diubah ke /api/users
    app.register_blueprint(interview_api_bp, url_prefix='/api/interview')
    app.register_blueprint(analysis_api_bp, url_prefix='/api/analysis')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(web_bp) # Untuk halaman web
    app.register_blueprint(debug_bp) # Untuk debugging

    # 7. Daftarkan Swagger UI
    SWAGGER_URL = '/api/docs' # URL yang lebih umum
    API_URL = '/static/swagger.json'
    swaggerui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL, API_URL,
        config={'app_name': "FLUENT Interview API"}
    )
    app.register_blueprint(swaggerui_blueprint)

    # 8. (Opsional) Seeding Data Awal
    with app.app_context():
        questions_coll = get_questions_collection()
        if questions_coll is not None and questions_coll.count_documents({}) == 0:
            app.logger.info("Database pertanyaan kosong, melakukan seeding data awal...")
            default_questions = [
                {"question": "Ceritakan tentang diri Anda", "category": "general", "ideal_answer_keywords": ["pengalaman", "pendidikan", "kemampuan", "tujuan"]},
                {"question": "Apa kelebihan dan kelemahan Anda?", "category": "general", "ideal_answer_keywords": ["kelebihan", "kelemahan", "perbaikan", "pengembangan"]},
                {"question": "Mengapa Anda tertarik dengan posisi ini?", "category": "specific", "ideal_answer_keywords": ["motivasi", "kesesuaian", "kontribusi", "perusahaan"]},
            ]
            questions_coll.insert_many(default_questions)
            app.logger.info(f"{len(default_questions)} pertanyaan default berhasil ditambahkan.")
        elif questions_coll is None:
            app.logger.error("Koleksi 'questions' tidak ditemukan. Seeding data dibatalkan.")

    return app