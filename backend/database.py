# FLUENTSERVICE/backend/database.py
from pymongo import MongoClient
from flask import current_app # current_app lebih aman daripada mengoper app jika modul ini diimpor sebelum app dibuat

# Variabel global untuk menyimpan instance koneksi dan koleksi
# Sebaiknya diakses melalui fungsi getter untuk enkapsulasi dan fleksibilitas
_mongo_client = None
_db = None
_users_collection = None
_questions_collection = None
_sessions_collection = None

def init_db(app_context): # Terima app_context (app)
    global _mongo_client, _db, _users_collection, _questions_collection, _sessions_collection
    try:
        mongo_uri = app_context.config['MONGO_URI']
        db_name = app_context.config['MONGO_DB_NAME']
        _mongo_client = MongoClient(mongo_uri)
        _db = _mongo_client[db_name]

        _users_collection = _db["users"]
        _questions_collection = _db["questions"]
        _sessions_collection = _db["interview_sessions"]

        _mongo_client.admin.command('ping') # Verifikasi koneksi
        app_context.logger.info("MongoDB connection successful and collections initialized.")
    except Exception as e:
        app_context.logger.error(f"Error connecting to MongoDB or initializing collections: {e}")
        raise ConnectionError(f"Failed to connect to MongoDB: {e}")

def get_db():
    if _db is None:
        # Ini seharusnya tidak terjadi jika init_db dipanggil dengan benar saat app start
        # dan request diproses dalam app context.
        if current_app:
            init_db(current_app) # Coba inisialisasi jika dalam app context
        else:
            raise RuntimeError("Database not initialized and no application context available.")
    return _db

def get_users_collection():
    if _users_collection is None:
        if current_app: init_db(current_app)
        else: raise RuntimeError("Users collection not initialized and no application context.")
    return _users_collection

# --- TAMBAHKAN FUNGSI GETTER INI ---
def get_questions_collection():
    if _questions_collection is None:
        if current_app: init_db(current_app) # Pastikan DB diinisialisasi
        else: raise RuntimeError("Questions collection not initialized and no application context.")
    return _questions_collection

def get_sessions_collection():
    if _sessions_collection is None:
        if current_app: init_db(current_app) # Pastikan DB diinisialisasi
        else: raise RuntimeError("Sessions collection not initialized and no application context.")
    return _sessions_collection

# --- Ekspor variabel global lama (jika masih ada kode yang menggunakannya, tapi sebaiknya dihindari) ---
# Ini hanya untuk transisi, idealnya semua akses melalui fungsi getter
db = _db
users_collection = _users_collection
questions_collection = _questions_collection # Ini yang menyebabkan error sebelumnya jika diimpor langsung
sessions_collection = _sessions_collection