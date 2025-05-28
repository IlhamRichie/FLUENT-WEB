from flask import Blueprint, request, jsonify, current_app
from backend.utils.decorators import token_required
from .services import analyze_realtime_frame_service, analyze_speech_audio_service

analysis_api_bp = Blueprint('analysis_api', __name__)

@analysis_api_bp.route('/realtime', methods=['POST'])
@token_required
def analyze_realtime_route(current_user):
    data = request.get_json()
    if not data or "frame" not in data:
        return jsonify({"status": "fail", "message": "Frame data not provided in base64 format"}), 400

    base64_frame = data["frame"]
    response, status_code = analyze_realtime_frame_service(base64_frame)
    return jsonify(response), status_code

@analysis_api_bp.route('/speech', methods=['POST'])
@token_required
def analyze_speech_route(current_user):
    if 'audio' not in request.files:
        return jsonify({"status": "fail", "message": "No audio file provided in the 'audio' field"}), 400

    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({"status": "fail", "message": "No selected audio file"}), 400

    # Anda bisa menambahkan validasi tipe file di sini jika perlu
    # allowed_extensions = {'wav', 'mp3', 'ogg', 'flac'}
    # if not ('.' in audio_file.filename and audio_file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
    #     return jsonify({"status": "fail", "message": "Invalid audio file type"}), 400

    response, status_code = analyze_speech_audio_service(audio_file)
    return jsonify(response), status_code