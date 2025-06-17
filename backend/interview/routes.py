from flask import Blueprint, request, jsonify, current_app
from backend.utils.decorators import token_required
from backend.interview import services as interview_service

# --- Blueprint Definition ---
# Nama Blueprint disatukan menjadi satu.
# URL prefix '/interview' akan berlaku untuk semua route di file ini.
interview_api_bp = Blueprint('interview_api', __name__, url_prefix='/interview')

# ===================================================================
# == ENDPOINTS UNTUK SIMULASI AI REAL-TIME (DENGAN GEMINI) ==
# ===================================================================

@interview_api_bp.route("/generate_question", methods=["POST"])
def handle_generate_question():
    """Endpoint untuk menghasilkan satu pertanyaan wawancara berdasarkan topik."""
    if not request.is_json:
        return jsonify({"error": "Request harus JSON"}), 400
    
    topic = request.json.get("topic")
    if not topic:
        return jsonify({"error": "Request harus mengandung 'topic'"}), 400
    
    try:
        result = interview_service.generate_interview_question(topic)
        return jsonify(result)
    except Exception as e:
        # Menambahkan log di server untuk memudahkan debugging
        current_app.logger.error(f"Error generating question: {e}")
        return jsonify({"error": "Gagal membuat pertanyaan", "details": str(e)}), 500

@interview_api_bp.route("/analyze_realtime_chunk", methods=["POST"])
def handle_analyze_chunk():
    """Endpoint untuk menganalisis potongan audio & video secara real-time."""
    if not request.is_json:
        return jsonify({"error": "Request harus JSON"}), 400
        
    data = request.json
    audio_base64 = data.get("audio")
    video_base64 = data.get("video")

    if not audio_base64 or not video_base64:
        return jsonify({"error": "Request harus mengandung 'audio' dan 'video'"}), 400
        
    try:
        result = interview_service.analyze_realtime_chunk(audio_base64, video_base64)
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"Error on real-time analysis: {e}")
        return jsonify({"error": "Analisis AI gagal", "details": str(e)}), 500

@interview_api_bp.route("/save_report", methods=["POST"])
@token_required # Sebaiknya endpoint ini dilindungi
def handle_save_report(current_user):
    """Endpoint untuk menghasilkan dan menyimpan laporan akhir dari transkrip."""
    if not request.is_json: 
        return jsonify({"error": "Request harus JSON"}), 400
        
    report_data = request.json
    full_transcript = report_data.get("transcript")

    if not full_transcript: 
        return jsonify({"error": "Request harus mengandung 'transcript'"}), 400

    try:
        analysis_result = interview_service.generate_final_report(full_transcript)
        
        # Di sini Anda bisa menambahkan logika untuk menyimpan `analysis_result`
        # ke database (MongoDB) yang terhubung dengan `current_user['_id']`.
        # Contoh: db_service.save_final_report(current_user['_id'], report_data, analysis_result)
        
        print(f"Analisis berhasil dibuat untuk user {current_user['username']}. Penyimpanan ke DB dilewati.")
        
        return jsonify(analysis_result)
    except Exception as e:
        current_app.logger.error(f"Error saving final report: {e}")
        return jsonify({"error": "Gagal menghasilkan atau menyimpan analisis akhir", "details": str(e)}), 500


# ===================================================================
# == ENDPOINTS UNTUK ALUR WAWANCARA BERBASIS SESI (TERSTRUKTUR) ==
# ===================================================================
# Catatan: Service functions seperti `start_interview_session_service`
# belum Anda berikan, jadi saya asumsikan mereka ada di services.py

@interview_api_bp.route('/start', methods=['POST'])
@token_required
def start_interview_route(current_user):
    """Memulai sesi wawancara baru dan mengembalikan pertanyaan pertama."""
    data = request.get_json() or {}
    category = data.get('category', 'general')
    num_questions = int(data.get('num_questions', 5))

    try:
        response, session_data, status_code = interview_service.start_interview_session_service(
            current_user["_id"], category, num_questions
        )
        if status_code == 201 and session_data:
            return jsonify({
                "status": "success",
                "session_id": str(session_data["_id"]),
                "current_question": session_data["questions"][0]["question_text"],
                "current_question_id": session_data["questions"][0]["question_id"],
                "total_questions": len(session_data["questions"])
            }), 201
        return jsonify(response), status_code
    except Exception as e:
        current_app.logger.error(f"Error starting interview session: {e}")
        return jsonify({"status": "fail", "message": str(e)}), 500


@interview_api_bp.route('/submit', methods=['POST'])
@token_required
def submit_answer_route(current_user):
    """Mengirim jawaban, mendapatkan evaluasi, dan pertanyaan berikutnya."""
    data = request.get_json()
    session_id_str = data.get("session_id")
    answer_text = data.get("answer_text")

    if not all([session_id_str, answer_text is not None]):
        return jsonify({"status": "fail", "message": "session_id dan answer_text diperlukan"}), 400

    try:
        response_msg, updated_session, eval_result, completed, overall_score, status_code = \
            interview_service.submit_interview_answer_service(session_id_str, current_user["_id"], answer_text)

        if status_code == 200:
            resp_payload = {"status": "success", "evaluation": eval_result, "interview_completed": completed}
            if completed:
                resp_payload["overall_score"] = overall_score
            else:
                current_idx = updated_session.get("current_question_index", 0)
                resp_payload["next_question"] = updated_session["questions"][current_idx]["question_text"]
                resp_payload["next_question_id"] = updated_session["questions"][current_idx]["question_id"]
                resp_payload["current_question_index"] = current_idx
            return jsonify(resp_payload), 200
        return jsonify(response_msg), status_code
    except Exception as e:
        current_app.logger.error(f"Error submitting answer: {e}")
        return jsonify({"status": "fail", "message": str(e)}), 500


@interview_api_bp.route('/results/<session_id_str>', methods=['GET'])
@token_required
def get_results_route(current_user, session_id_str):
    """Mengambil hasil akhir dari sebuah sesi wawancara."""
    try:
        response, session_doc, status_code = interview_service.get_interview_results_service(session_id_str, current_user["_id"])

        if status_code == 200 and session_doc:
            start_time_iso = session_doc.get("start_time").isoformat() if session_doc.get("start_time") else None
            end_time_iso = session_doc.get("end_time").isoformat() if session_doc.get("end_time") else None

            return jsonify({
                "status": "success",
                "results": {
                    "session_id": str(session_doc["_id"]),
                    "user_id": str(session_doc["user_id"]),
                    "start_time": start_time_iso,
                    "end_time": end_time_iso,
                    "questions": session_doc.get("questions", []),
                    "overall_score": session_doc.get("overall_score", 0.0),
                    "category": session_doc.get("category", "general")
                }
            }), 200
        return jsonify(response), status_code
    except Exception as e:
        current_app.logger.error(f"Error getting results: {e}")
        return jsonify({"status": "fail", "message": str(e)}), 500