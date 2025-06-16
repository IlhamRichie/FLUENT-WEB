from flask import Blueprint, request, jsonify, current_app
from backend.utils.decorators import token_required
from .services import (
    start_interview_session_service,
    submit_interview_answer_service,
    get_interview_results_service
)
from flask import Blueprint, request, jsonify
from backend.interview import services as interview_service

interview_api_bp = Blueprint('interview_api', __name__)

@interview_api_bp.route("/generate_question", methods=["POST"])
def handle_generate_question():
    if not request.is_json:
        return jsonify({"error": "Request harus JSON"}), 400
    topic = request.get_json().get("topic")
    if not topic:
        return jsonify({"error": "Request harus mengandung 'topic'"}), 400
    
    try:
        result = interview_service.generate_interview_question(topic)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "Gagal membuat pertanyaan", "details": str(e)}), 500

@interview_api_bp.route("/analyze_realtime_chunk", methods=["POST"])
def handle_analyze_chunk():
    if not request.is_json:
        return jsonify({"error": "Request harus JSON"}), 400
    data = request.get_json()
    audio_base64, video_base64 = data.get("audio"), data.get("video")
    if not audio_base64 or not video_base64:
        return jsonify({"error": "Request harus mengandung 'audio' dan 'video'"}), 400
        
    try:
        result = interview_service.analyze_realtime_chunk(audio_base64, video_base64)
        return jsonify(result)
    except Exception as e:
        print(f"Error pada analisis real-time: {e}")
        return jsonify({"error": "Analisis AI gagal", "details": str(e)}), 500

@interview_api_bp.route("/save_report", methods=["POST"])
def handle_save_report():
    # NOTE: Bagian penyimpanan ke Firestore diabaikan sesuai permintaan.
    # Jika ingin diaktifkan, Anda bisa memanggil service dari sini.
    # Contoh: db_service.save_report(uid, report_data, analysis_result)
    
    if not request.is_json: return jsonify({"error": "Request harus JSON"}), 400
    report_data = request.get_json()
    full_transcript = report_data.get("transcript")
    if not full_transcript: return jsonify({"error": "Request harus mengandung 'transcript'"}), 400

    try:
        # Panggil service untuk menghasilkan analisis akhir
        analysis_result = interview_service.generate_final_report(full_transcript)
        
        # Di sini seharusnya ada logika penyimpanan ke database
        print("Analisis berhasil dibuat. Penyimpanan ke DB dilewati.")
        
        return jsonify(analysis_result)
    except Exception as e:
        return jsonify({"error": "Gagal menghasilkan analisis akhir", "details": str(e)}), 500

@interview_api_bp.route('/start', methods=['POST'])
@token_required
def start_interview_route(current_user):
    data = request.get_json() or {}
    category = data.get('category', 'general')
    num_questions = int(data.get('num_questions', 5))

    response, session_data, status_code = start_interview_session_service(
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

@interview_api_bp.route('/submit', methods=['POST'])
@token_required
def submit_answer_route(current_user):
    data = request.get_json()
    session_id_str = data.get("session_id")
    answer_text = data.get("answer_text")

    if not all([session_id_str, answer_text is not None]): # answer_text bisa string kosong
        return jsonify({"status": "fail", "message": "Missing session_id or answer_text"}), 400

    response_msg, updated_session, eval_result, completed, overall_score, status_code = \
        submit_interview_answer_service(session_id_str, current_user["_id"], answer_text)

    if status_code == 200:
        resp_payload = {"status": "success", "evaluation": eval_result, "interview_completed": completed}
        if completed:
            resp_payload["overall_score"] = overall_score
            # Untuk debugging atau info tambahan, bisa kirim detail sesi
            # resp_payload["session_details"] = updated_session # Hati-hati dengan data sensitif
        else:
            current_idx = updated_session.get("current_question_index", 0)
            resp_payload["next_question"] = updated_session["questions"][current_idx]["question_text"]
            resp_payload["next_question_id"] = updated_session["questions"][current_idx]["question_id"]
            resp_payload["current_question_index"] = current_idx
        return jsonify(resp_payload), 200
    return jsonify(response_msg), status_code


@interview_api_bp.route('/results/<session_id_str>', methods=['GET'])
@token_required
def get_results_route(current_user, session_id_str):
    response, session_doc, status_code = get_interview_results_service(session_id_str, current_user["_id"])

    if status_code == 200 and session_doc:
        # Format datetime untuk JSON response
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