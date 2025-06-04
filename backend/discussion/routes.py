# # backend/discussion/routes.py
# from flask import Blueprint, request, jsonify, current_app
# from backend.utils.decorators import token_required, require_api_key # Asumsi decorator ini ada
# from .services import (
#     create_topic_service,
#     get_all_topics_service,
#     get_topic_by_id_service,
#     create_post_in_topic_service,
#     get_posts_in_topic_service,
#     # Tambahkan impor service lain sesuai kebutuhan (misalnya, update_post, delete_post, dll.)
# )
# # Impor model Pydantic jika Anda menggunakannya untuk validasi request/response
# # from backend.models import NewTopicRequest, NewPostRequest, TopicResponse, PostResponse

# # Buat blueprint untuk diskusi
# discussion_bp = Blueprint('discussion_api', __name__)

# # --- Rute untuk Topik Diskusi ---
# @discussion_bp.route('/topics', methods=['POST'])
# @token_required # Memerlukan user yang login untuk membuat topik
# @require_api_key # Jika API key juga diperlukan
# def create_topic_route(current_user): # current_user dari @token_required
#     data = request.get_json()
#     if not data or not data.get('title') or not data.get('description'):
#         return jsonify({"status": "fail", "message": "Judul dan deskripsi topik diperlukan"}), 400
    
#     # Kirim user_id dan username dari current_user ke service
#     user_id = str(current_user['_id'])
#     username = current_user['username']
    
#     response, status_code = create_topic_service(data, user_id, username)
#     return jsonify(response), status_code

# @discussion_bp.route('/topics', methods=['GET'])
# @require_api_key # Mungkin tidak perlu token untuk hanya melihat daftar topik
# def get_all_topics_route():
#     # Tambahkan pagination jika perlu: page = request.args.get('page', 1, type=int), per_page = request.args.get('per_page', 10, type=int)
#     response, status_code = get_all_topics_service() # Tambahkan argumen pagination ke service
#     return jsonify(response), status_code

# @discussion_bp.route('/topics/<topic_id>', methods=['GET'])
# @require_api_key
# def get_topic_route(topic_id):
#     response, status_code = get_topic_by_id_service(topic_id)
#     return jsonify(response), status_code

# # --- Rute untuk Postingan di dalam Topik ---
# @discussion_bp.route('/topics/<topic_id>/posts', methods=['POST'])
# @token_required
# @require_api_key
# def create_post_route(current_user, topic_id):
#     data = request.get_json()
#     if not data or not data.get('content'):
#         return jsonify({"status": "fail", "message": "Konten postingan diperlukan"}), 400

#     user_id = str(current_user['_id'])
#     username = current_user['username']

#     response, status_code = create_post_in_topic_service(topic_id, data, user_id, username)
#     return jsonify(response), status_code

# @discussion_bp.route('/topics/<topic_id>/posts', methods=['GET'])
# @require_api_key
# def get_posts_route(topic_id):
#     # Tambahkan pagination jika perlu
#     response, status_code = get_posts_in_topic_service(topic_id) # Tambahkan argumen pagination ke service
#     return jsonify(response), status_code

# # TODO: Tambahkan rute untuk:
# # - Mengedit topik (PUT /topics/<topic_id>) - hanya oleh pembuat topik atau admin
# # - Menghapus topik (DELETE /topics/<topic_id>) - hanya oleh pembuat topik atau admin
# # - Mengedit postingan (PUT /posts/<post_id>) - hanya oleh pembuat postingan atau admin
# # - Menghapus postingan (DELETE /posts/<post_id>) - hanya oleh pembuat postingan atau admin
# # - Menambah komentar/balasan pada postingan
# # - Upvote/downvote topik atau postingan
