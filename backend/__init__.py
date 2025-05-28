# FLUENTSERVICE/backend/__init__.py
import os
from flask import Flask
# ... (impor lainnya) ...
from .config import Config
from .database import init_db, get_questions_collection # Impor fungsi getter

def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    Config.init_app(app)

    from flask_bcrypt import Bcrypt
    from flask_cors import CORS
    from flask_mail import Mail
    from .auth.services import init_app_oauth

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
    from .web.routes import web_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(users_api_bp, url_prefix='/api/users')
    app.register_blueprint(interview_api_bp, url_prefix='/api/interview')
    app.register_blueprint(analysis_api_bp, url_prefix='/api/analysis')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(web_bp)

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
        current_questions_collection = get_questions_collection() # Panggil fungsi getter
        # --- UBAH KONDISI DI SINI ---
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