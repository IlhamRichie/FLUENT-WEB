from flask import Blueprint, request, jsonify, current_app
from backend.utils.decorators import token_required
from backend.database import get_users_collection
from bson.objectid import ObjectId
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