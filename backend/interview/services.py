# FLUENTSERVICE/backend/interview/services.py
from flask import current_app
from datetime import datetime, timezone
from bson.objectid import ObjectId
# --- UBAH IMPOR INI ---
from backend.database import get_questions_collection, get_sessions_collection

def start_interview_session_service(user_id: ObjectId, category: str = 'general', num_questions: int = 5):
    questions_coll = get_questions_collection() # Gunakan fungsi getter
    sessions_coll = get_sessions_collection()   # Gunakan fungsi getter

    pipeline = [{"$match": {"category": category}}]
    if num_questions > 0:
        pipeline.append({"$sample": {"size": num_questions}})
    
    questions = list(questions_coll.aggregate(pipeline))

    if not questions:
        return {"status": "fail", "message": f"No questions available for category '{category}'"}, None, 404

    session_data = {
        "user_id": user_id,
        "start_time": datetime.now(timezone.utc),
        "status": "ongoing",
        "questions": [{
            "question_id": str(q["_id"]),
            "question_text": q["question"],
            "ideal_keywords": q.get("ideal_answer_keywords", []),
            "user_answer": None,
            "evaluation": None
        } for q in questions],
        "current_question_index": 0,
        "category": category
    }
    try:
        session_id_obj = sessions_coll.insert_one(session_data).inserted_id
        session_data["_id"] = session_id_obj # Tambahkan _id ke data yang dikembalikan
        return {"status": "success"}, session_data, 201
    except Exception as e:
        current_app.logger.error(f"Error starting interview session for user {user_id}: {e}")
        return {"status": "error", "message": "Failed to start interview session"}, None, 500

def submit_interview_answer_service(session_id_str: str, user_id: ObjectId, answer_text: str):
    sessions_coll = get_sessions_collection()   # Gunakan fungsi getter
    try:
        session_obj_id = ObjectId(session_id_str)
    except Exception:
        return {"status": "fail", "message": "Invalid session_id format"}, None, 400

    session_doc = sessions_coll.find_one({"_id": session_obj_id, "user_id": user_id})

    if not session_doc:
        return {"status": "fail", "message": "Session not found or access denied"}, None, 404
    if session_doc.get("status") == "completed":
        return {"status": "fail", "message": "Interview already completed"}, None, 400

    current_idx = session_doc.get("current_question_index", 0)
    if current_idx >= len(session_doc["questions"]):
        # Seharusnya tidak terjadi jika status belum completed, tapi sebagai failsafe
        return {"status": "fail", "message": "All questions answered, interview might be completed."}, None, 400

    question_data = session_doc["questions"][current_idx]
    ideal_keywords = [kw.lower() for kw in question_data.get("ideal_keywords", [])]
    answer_words = set(answer_text.lower().split())
    matched_keywords = [kw for kw in ideal_keywords if kw in answer_words]
    score = (len(matched_keywords) / len(ideal_keywords)) * 100 if ideal_keywords else 0.0

    evaluation = {
        "matched_keywords": matched_keywords,
        "score": round(score, 2),
        "feedback": "Good answer" if score > 70 else ("Adequate answer" if score > 40 else "Needs improvement")
    }

    update_query = {
        f"questions.{current_idx}.user_answer": answer_text,
        f"questions.{current_idx}.evaluation": evaluation,
        "$inc": {"current_question_index": 1}
    }
    sessions_coll.update_one({"_id": session_obj_id}, update_query)

    # Re-fetch untuk mendapatkan data terbaru
    updated_session_doc = sessions_coll.find_one({"_id": session_obj_id})
    next_idx = updated_session_doc.get("current_question_index", 0)
    is_completed = False
    overall_score = None

    if next_idx >= len(updated_session_doc["questions"]):
        sessions_coll.update_one(
            {"_id": session_obj_id},
            {"$set": {"status": "completed", "end_time": datetime.now(timezone.utc)}}
        )
        is_completed = True
        final_session_doc = sessions_coll.find_one({"_id": session_obj_id}) # Fetch lagi setelah update status
        total_score = sum(q.get("evaluation", {}).get("score", 0) for q in final_session_doc.get("questions", []))
        num_q = len(final_session_doc.get("questions", []))
        overall_score = round(total_score / num_q, 2) if num_q > 0 else 0.0
        updated_session_doc = final_session_doc # Gunakan yang paling baru

    return {"status": "success"}, updated_session_doc, evaluation, is_completed, overall_score, 200

def get_interview_results_service(session_id_str: str, user_id: ObjectId):
    sessions_coll = get_sessions_collection()   # Gunakan fungsi getter
    try:
        session_obj_id = ObjectId(session_id_str)
    except Exception:
        return {"status": "fail", "message": "Invalid session_id format"}, None, 400

    session_doc = sessions_coll.find_one({"_id": session_obj_id, "user_id": user_id})
    if not session_doc:
        return {"status": "fail", "message": "Session not found or access denied"}, None, 404
    if session_doc.get("status") != "completed":
        return {"status": "fail", "message": "Results not available, interview not completed yet"}, None, 400

    questions_data = session_doc.get("questions", [])
    total_score = sum(q.get("evaluation", {}).get("score", 0) for q in questions_data)
    num_q = len(questions_data)
    overall_score_val = round(total_score / num_q, 2) if num_q > 0 else 0.0
    session_doc["overall_score"] = overall_score_val # Tambahkan ke dokumen untuk konsistensi

    return {"status": "success"}, session_doc, 200