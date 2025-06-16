from flask import Blueprint, request, jsonify, current_app
from backend.utils.decorators import token_required
from backend.database import get_users_collection
from bson.objectid import ObjectId
from datetime import datetime, timezone # <-- TAMBAHKAN
# Jika pakai Pydantic: from backend.models import UserUpdate, UserResponse

users_api_bp = Blueprint('users_api', __name__) # url_prefix di backend/__init__.py

@users_api_bp.route('/update', methods=['PUT'])
@token_required
def update_user_profile_route(current_user): # current_user dari @token_required
    data = request.get_json()
    users_coll = get_users_collection()
    update_fields = {}

    # Validasi data (misal pakai Pydantic: UserUpdate(**data).model_dump(exclude_unset=True))
    if "username" in data and data["username"] != current_user.get("username"):
        # Cek username unik jika diubah
        if users_coll.find_one({"username": data["username"], "_id": {"$ne": current_user["_id"]}}):
            return jsonify({"status": "fail", "message": "Username already taken"}), 400
        update_fields["username"] = data["username"]
    if "occupation" in data:
        update_fields["occupation"] = data["occupation"]
    if "gender" in data:
        update_fields["gender"] = data["gender"]
    # Tambah field lain yang bisa diupdate, misal profile_picture

    if not update_fields:
        return jsonify({"status": "fail", "message": "No valid fields to update"}), 400

    try:
        users_coll.update_one({"_id": current_user["_id"]}, {"$set": update_fields})
        updated_user_from_db = users_coll.find_one({"_id": current_user["_id"]})
        # Jika pakai Pydantic: user_resp = UserResponse.model_validate(updated_user_from_db).model_dump_json(by_alias=True)
        user_response_data = {
            "id": str(updated_user_from_db["_id"]),
            "username": updated_user_from_db["username"],
            "email": updated_user_from_db["email"], # Email tidak boleh diubah di sini
            "gender": updated_user_from_db.get("gender"),
            "occupation": updated_user_from_db.get("occupation"),
            "profile_picture": updated_user_from_db.get("profile_picture")
        }
        return jsonify({
            "status": "success", "message": "User data updated successfully",
            "user": user_response_data
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error updating user {current_user['_id']}: {e}")
        return jsonify({"status": "error", "message": "Failed to update user data"}), 500


@users_api_bp.route('/profile', methods=['GET'])
@token_required
def get_user_profile_route(current_user):
    # current_user sudah berisi data user dari token
    # Jika pakai Pydantic: UserResponse.model_validate(current_user).model_dump_json(by_alias=True)
    user_response_data = {
        "id": str(current_user["_id"]),
        "username": current_user["username"],
        "email": current_user["email"],
        "gender": current_user.get("gender"),
        "occupation": current_user.get("occupation"),
        "is_active": current_user.get("is_active", True),
        "auth_provider": current_user.get("auth_provider"),
        "created_at": current_user.get("created_at").isoformat() if current_user.get("created_at") else None,
        "last_login": current_user.get("last_login").isoformat() if current_user.get("last_login") else None,
        "profile_picture": current_user.get("profile_picture")
    }
    return jsonify({
        "status": "success",
        "user": user_response_data
    }), 200
    
@users_api_bp.route('/sessions', methods=['GET'])
@token_required
def get_active_sessions_route(current_user):
    """Mengambil semua sesi aktif untuk pengguna saat ini."""
    # Ambil session ID dari header untuk menandai sesi saat ini
    current_session_id = request.headers.get('X-Session-ID')

    active_sessions = current_user.get('active_sessions', [])
    
    # Tambahkan flag 'is_current' untuk UI di Flutter
    for session in active_sessions:
        if isinstance(session.get('login_time'), datetime):
            session['login_time'] = session['login_time'].isoformat()
        if isinstance(session.get('last_seen'), datetime):
            session['last_seen'] = session['last_seen'].isoformat()
        session['is_current'] = (session['session_id'] == current_session_id)

    return jsonify({
        "status": "success",
        "sessions": sorted(active_sessions, key=lambda s: s['last_seen'], reverse=True) # Urutkan dari yg terbaru
    }), 200

@users_api_bp.route('/sessions/<session_id_to_delete>', methods=['DELETE'])
@token_required
def terminate_session_route(current_user, session_id_to_delete):
    """Menghapus/mengakhiri sesi dari perangkat lain."""
    users_coll = get_users_collection()
    
    # Log aktivitas penghapusan sesi
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)

    user_agent_string = request.headers.get('User-Agent', 'Unknown')
    new_activity = {
        "activity": f"Session '{session_id_to_delete[:8]}...' Terminated",
        "timestamp": datetime.now(timezone.utc),
        "ip_address": ip_address,
        "device_info": user_agent_string
    }

    result = users_coll.update_one(
        {"_id": current_user["_id"]},
        {
            "$pull": {"active_sessions": {"session_id": session_id_to_delete}},
            "$push": {"activity_log": {"$each": [new_activity], "$slice": -50}}
        }
    )

    if result.modified_count > 0:
        return jsonify({"status": "success", "message": "Sesi berhasil dihapus."}), 200
    else:
        return jsonify({"status": "fail", "message": "Sesi tidak ditemukan atau sudah dihapus."}), 404

@users_api_bp.route('/activity-log', methods=['GET'])
@token_required
def get_activity_log_route(current_user):
    """Mengambil log aktivitas untuk pengguna saat ini."""
    activity_log = current_user.get('activity_log', [])

    # Konversi datetime ke string ISO untuk JSON
    for log in activity_log:
        if isinstance(log.get('timestamp'), datetime):
            log['timestamp'] = log['timestamp'].isoformat()

    return jsonify({
        "status": "success",
        "log": sorted(activity_log, key=lambda x: x['timestamp'], reverse=True) # Urutkan dari yang terbaru
    }), 200

@users_api_bp.route('/sessions/ping', methods=['POST'])
@token_required
def update_session_last_seen(current_user):
    """API internal untuk update 'last_seen' sebuah sesi. Dipanggil secara periodik oleh app."""
    session_id = request.headers.get('X-Session-ID')
    if not session_id:
        return jsonify({"status": "fail", "message": "X-Session-ID header is required."}), 400

    users_coll = get_users_collection()
    users_coll.update_one(
        {"_id": current_user["_id"], "active_sessions.session_id": session_id},
        {"$set": {"active_sessions.$.last_seen": datetime.now(timezone.utc)}}
    )
    return jsonify({"status": "success", "message": "Session updated."}), 200