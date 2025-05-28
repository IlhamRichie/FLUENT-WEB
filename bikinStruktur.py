import os
from pathlib import Path

def create_project_structure(base_dir="FLUENTSERVICE"):
    """Membuat struktur direktori untuk proyek FLUENTSERVICE"""
    
    # Daftar direktori dan file yang akan dibuat
    structure = {
        "backend": {
            "__init__.py": "# Package initialization\nfrom flask import Flask\n\napp = Flask(__name__)",
            "config.py": "# Konfigurasi aplikasi",
            "database.py": "# Setup koneksi MongoDB dan koleksi",
            "models.py": "# Model data (Pydantic/dataclasses)",
            
            "auth": {
                "__init__.py": "",
                "routes.py": "# Routes untuk /register, /login, /refresh, Google OAuth",
                "services.py": "# Logika JWT, hashing, OTP, email OTP/reset"
            },
            
            "users": {
                "__init__.py": "",
                "routes.py": "# Routes untuk /user/update, /user/profile (API)"
            },
            
            "interview": {
                "__init__.py": "",
                "routes.py": "# Routes untuk /api/interview/*",
                "services.py": "# Logika sesi interview, evaluasi"
            },
            
            "analysis": {
                "__init__.py": "",
                "routes.py": "# Routes untuk /analyze_realtime, /analyze_speech",
                "services.py": "# Integrasi dengan detectors"
            },
            
            "detectors": {
                "__init__.py": "",
                "emotion_detector.py": "# Implementasi emotion detector",
                "mouth_detector.py": "# Implementasi mouth detector",
                "pose_detector.py": "# Implementasi pose detector"
            },
            
            "admin": {
                "__init__.py": "",
                "routes.py": "# Routes untuk /admin/*",
                "services.py": "# Logika untuk dashboard, manajemen pengguna/sesi admin"
            },
            
            "web": {
                "__init__.py": "",
                "routes.py": "# Routes untuk /, /features, /api/docs (halaman), OTP web, reset pass web"
            },
            
            "utils": {
                "__init__.py": "",
                "decorators.py": "# @token_required, @web_login_required, @admin_required",
                "email_utils.py": "# Fungsi send_otp_email, send_reset_password_email"
            },
            
            "static": {
                "css": {
                    "style.css": "/* CSS styles */"
                },
                "images": {},
                "swagger.json": "{}"
            },
            
            "templates": {
                "admin": {
                    "admin_dashboard.html": "<!DOCTYPE html>",
                    "admin_login.html": "<!DOCTYPE html>",
                    "admin_sessions.html": "<!DOCTYPE html>",
                    "admin_users_list.html": "<!DOCTYPE html>"
                },
                "auth": {
                    "forgot_password_web.html": "<!DOCTYPE html>",
                    "login_web.html": "<!DOCTYPE html>",
                    "register_web.html": "<!DOCTYPE html>",
                    "reset_password_form_web.html": "<!DOCTYPE html>",
                    "verify_otp.html": "<!DOCTYPE html>"
                },
                "email": {
                    "email_otp_template.html": "<!DOCTYPE html>",
                    "email_reset_password_template.html": "<!DOCTYPE html>"
                },
                "web": {
                    "api_docs.html": "<!DOCTYPE html>",
                    "features.html": "<!DOCTYPE html>",
                    "index.html": "<!DOCTYPE html>",
                    "profile_web.html": "<!DOCTYPE html>"
                },
                "base.html": "<!DOCTYPE html>"
            }
        },
        
        "instance": {},
        "create_admin.py": "# Skrip untuk membuat admin awal",
        "run.py": "from backend import app\n\nif __name__ == '__main__':\n    app.run(debug=True)"
    }
    
    # Membuat struktur
    def create_structure(root, structure):
        for name, content in structure.items():
            path = os.path.join(root, name)
            
            if isinstance(content, dict):
                os.makedirs(path, exist_ok=True)
                create_structure(path, content)
            else:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
    
    # Membuat direktori utama
    os.makedirs(base_dir, exist_ok=True)
    create_structure(base_dir, structure)
    
    print(f"Struktur proyek FLUENTSERVICE berhasil dibuat di direktori '{base_dir}'")

if __name__ == "__main__":
    create_project_structure()