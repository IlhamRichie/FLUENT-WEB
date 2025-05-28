from flask import Blueprint, request, jsonify, current_app
from backend.utils.decorators import token_required
from .services import (
    start_interview_session_service,
    submit_interview_answer_service,
    get_interview_results_service
)

interview_api_bp = Blueprint('interview_api', __name__)

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