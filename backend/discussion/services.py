# # backend/discussion/services.py
# from flask import current_app
# from backend.database import get_topics_collection, get_messages_collection # atau get_posts_collection
# from bson.objectid import ObjectId
# from datetime import datetime, timezone
# import pymongo # Untuk sorting direction

# # --- Layanan untuk Topik Diskusi ---
# def create_topic_service(data: dict, user_id: str, username: str):
#     topics_coll = get_topics_collection()
#     if topics_coll is None:
#         return {"status": "error", "message": "Layanan database tidak tersedia"}, 503

#     title = data.get('title', '').strip()
#     description = data.get('description', '').strip()
#     tags = data.get('tags', []) # Opsional, bisa berupa list of strings

#     if not title or not description:
#         return {"status": "fail", "message": "Judul dan deskripsi topik tidak boleh kosong"}, 400

#     try:
#         topic_doc = {
#             "title": title,
#             "description": description,
#             "tags": tags,
#             "created_by_id": ObjectId(user_id),
#             "created_by_username": username,
#             "created_at": datetime.now(timezone.utc),
#             "updated_at": datetime.now(timezone.utc),
#             "post_count": 0,
#             "last_activity_at": datetime.now(timezone.utc)
#             # Anda bisa menambahkan field lain seperti 'is_closed', 'is_pinned'
#         }
#         result = topics_coll.insert_one(topic_doc)
#         # Mengembalikan dokumen yang baru dibuat dengan ID-nya
#         created_topic = topics_coll.find_one({"_id": result.inserted_id})
#         if created_topic:
#             created_topic["_id"] = str(created_topic["_id"]) # Konversi ObjectId ke string
#             created_topic["created_by_id"] = str(created_topic["created_by_id"])
#         return {"status": "success", "message": "Topik berhasil dibuat", "topic": created_topic}, 201
#     except Exception as e:
#         current_app.logger.error(f"Error creating topic: {e}", exc_info=True)
#         return {"status": "error", "message": "Gagal membuat topik karena kesalahan internal"}, 500

# def get_all_topics_service(page=1, per_page=10):
#     topics_coll = get_topics_collection()
#     if topics_coll is None:
#         return {"status": "error", "message": "Layanan database tidak tersedia"}, 503
    
#     try:
#         skip_count = (page - 1) * per_page
#         # Urutkan berdasarkan aktivitas terakhir atau tanggal pembuatan
#         topics_cursor = topics_coll.find().sort("last_activity_at", pymongo.DESCENDING).skip(skip_count).limit(per_page)
#         topics_list = []
#         for topic in topics_cursor:
#             topic["_id"] = str(topic["_id"])
#             topic["created_by_id"] = str(topic["created_by_id"])
#             # Konversi datetime ke string jika perlu
#             topic["created_at"] = topic["created_at"].isoformat() if isinstance(topic["created_at"], datetime) else str(topic["created_at"])
#             topic["updated_at"] = topic["updated_at"].isoformat() if isinstance(topic["updated_at"], datetime) else str(topic["updated_at"])
#             topic["last_activity_at"] = topic["last_activity_at"].isoformat() if isinstance(topic["last_activity_at"], datetime) else str(topic["last_activity_at"])
#             topics_list.append(topic)
        
#         total_topics = topics_coll.count_documents({})
#         return {
#             "status": "success",
#             "topics": topics_list,
#             "page": page,
#             "per_page": per_page,
#             "total_topics": total_topics,
#             "total_pages": (total_topics + per_page - 1) // per_page
#         }, 200
#     except Exception as e:
#         current_app.logger.error(f"Error fetching all topics: {e}", exc_info=True)
#         return {"status": "error", "message": "Gagal mengambil daftar topik"}, 500

# def get_topic_by_id_service(topic_id_str: str):
#     topics_coll = get_topics_collection()
#     if topics_coll is None:
#         return {"status": "error", "message": "Layanan database tidak tersedia"}, 503

#     try:
#         topic = topics_coll.find_one({"_id": ObjectId(topic_id_str)})
#         if topic:
#             topic["_id"] = str(topic["_id"])
#             topic["created_by_id"] = str(topic["created_by_id"])
#             topic["created_at"] = topic["created_at"].isoformat() if isinstance(topic["created_at"], datetime) else str(topic["created_at"])
#             topic["updated_at"] = topic["updated_at"].isoformat() if isinstance(topic["updated_at"], datetime) else str(topic["updated_at"])
#             topic["last_activity_at"] = topic["last_activity_at"].isoformat() if isinstance(topic["last_activity_at"], datetime) else str(topic["last_activity_at"])
#             return {"status": "success", "topic": topic}, 200
#         else:
#             return {"status": "fail", "message": "Topik tidak ditemukan"}, 404
#     except Exception as e: # Termasuk bson.errors.InvalidId
#         current_app.logger.error(f"Error fetching topic by ID '{topic_id_str}': {e}", exc_info=True)
#         return {"status": "error", "message": "Gagal mengambil detail topik"}, 500


# # --- Layanan untuk Postingan/Pesan di dalam Topik ---
# # Asumsi Anda menggunakan messages_collection untuk postingan di dalam topik
# def create_post_in_topic_service(topic_id_str: str, data: dict, user_id: str, username: str):
#     messages_coll = get_messages_collection() # atau posts_collection
#     topics_coll = get_topics_collection()
#     if messages_coll is None or topics_coll is None:
#         return {"status": "error", "message": "Layanan database tidak tersedia"}, 503

#     content = data.get('content', '').strip()
#     if not content:
#         return {"status": "fail", "message": "Konten postingan tidak boleh kosong"}, 400

#     try:
#         topic_oid = ObjectId(topic_id_str)
#         # Pastikan topik ada
#         if not topics_coll.find_one({"_id": topic_oid}):
#             return {"status": "fail", "message": "Topik tidak ditemukan untuk membuat postingan"}, 404

#         post_doc = {
#             "topic_id": topic_oid,
#             "content": content,
#             "user_id": ObjectId(user_id),
#             "username": username,
#             "created_at": datetime.now(timezone.utc),
#             "updated_at": datetime.now(timezone.utc)
#             # Anda bisa menambahkan field lain seperti 'upvotes', 'replies_count'
#         }
#         result = messages_coll.insert_one(post_doc)
        
#         # Update last_activity_at dan post_count di topik
#         topics_coll.update_one(
#             {"_id": topic_oid},
#             {"$set": {"last_activity_at": datetime.now(timezone.utc)}, "$inc": {"post_count": 1}}
#         )

#         created_post = messages_coll.find_one({"_id": result.inserted_id})
#         if created_post:
#             created_post["_id"] = str(created_post["_id"])
#             created_post["topic_id"] = str(created_post["topic_id"])
#             created_post["user_id"] = str(created_post["user_id"])
#         return {"status": "success", "message": "Postingan berhasil dibuat", "post": created_post}, 201
#     except Exception as e:
#         current_app.logger.error(f"Error creating post in topic '{topic_id_str}': {e}", exc_info=True)
#         return {"status": "error", "message": "Gagal membuat postingan karena kesalahan internal"}, 500

# def get_posts_in_topic_service(topic_id_str: str, page=1, per_page=15):
#     messages_coll = get_messages_collection()
#     topics_coll = get_topics_collection()
#     if messages_coll is None or topics_coll is None:
#         return {"status": "error", "message": "Layanan database tidak tersedia"}, 503

#     try:
#         topic_oid = ObjectId(topic_id_str)
#         if not topics_coll.find_one({"_id": topic_oid}):
#             return {"status": "fail", "message": "Topik tidak ditemukan"}, 404

#         skip_count = (page - 1) * per_page
#         posts_cursor = messages_coll.find({"topic_id": topic_oid}).sort("created_at", pymongo.ASCENDING).skip(skip_count).limit(per_page)
#         posts_list = []
#         for post in posts_cursor:
#             post["_id"] = str(post["_id"])
#             post["topic_id"] = str(post["topic_id"])
#             post["user_id"] = str(post["user_id"])
#             post["created_at"] = post["created_at"].isoformat() if isinstance(post["created_at"], datetime) else str(post["created_at"])
#             post["updated_at"] = post["updated_at"].isoformat() if isinstance(post["updated_at"], datetime) else str(post["updated_at"])
#             posts_list.append(post)
        
#         total_posts = messages_coll.count_documents({"topic_id": topic_oid})
#         return {
#             "status": "success",
#             "posts": posts_list,
#             "page": page,
#             "per_page": per_page,
#             "total_posts": total_posts,
#             "total_pages": (total_posts + per_page - 1) // per_page
#         }, 200
#     except Exception as e:
#         current_app.logger.error(f"Error fetching posts for topic '{topic_id_str}': {e}", exc_info=True)
#         return {"status": "error", "message": "Gagal mengambil postingan"}, 500

# # TODO: Tambahkan fungsi service untuk:
# # - update_topic_service(topic_id, data, current_user)
# # - delete_topic_service(topic_id, current_user)
# # - update_post_service(post_id, data, current_user)
# # - delete_post_service(post_id, current_user)
# # - create_comment_service(post_id, data, current_user)
# # - get_comments_for_post_service(post_id)
# # Pastikan ada pemeriksaan hak akses (misalnya, hanya pembuat atau admin yang bisa edit/hapus)