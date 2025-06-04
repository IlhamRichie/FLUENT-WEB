from flask import current_app
import base64
import numpy as np
import cv2 # Untuk decode base64 ke frame
import tempfile
import os
from speech_recognition import Recognizer, AudioFile

# Impor fungsi detektor yang sebenarnya
from .detectors.emotion_detector import detect_emotion_from_frame # atau detect_emotion_from_image_path
from .detectors.mouth_detector import detect_mouth_status_from_frame
from .detectors.pose_detector import detect_pose_status_from_frame

def analyze_realtime_frame_service(base64_frame_data: str):
    try:
        img_data = base64.b64decode(base64_frame_data)
        np_arr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return {"status": "fail", "message": "Invalid image data in frame"}, 400

        # Panggil fungsi detektor yang sebenarnya
        # Untuk detektor yang bekerja dengan path, Anda mungkin perlu menyimpan frame sementara
        # with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
        #     image_path = tmp_file.name
        #     cv2.imwrite(image_path, frame)
        # emotion_result = detect_emotion_from_image_path(image_path)
        # mouth_result = detect_mouth_status_from_image_path(image_path)
        # pose_result = detect_pose_status_from_image_path(image_path)
        # os.unlink(image_path)

        # Jika detektor bekerja langsung dengan frame:
        emotion_result = detect_emotion_from_frame(frame)
        mouth_result = detect_mouth_status_from_frame(frame)
        pose_result = detect_pose_status_from_frame(frame)


        return {
            "status": "success",
            "results": {
                "emotion": emotion_result,
                "mouth": mouth_result,
                "pose": pose_result
            }
        }, 200

    except base64.binascii.Error:
        return {"status": "fail", "message": "Invalid base64 string for frame"}, 400
    except Exception as e:
        current_app.logger.error(f"Error in analyze_realtime_frame_service: {e}", exc_info=True)
        return {"status": "error", "message": f"Analysis error: {str(e)}"}, 500

def analyze_speech_audio_service(audio_file_storage): # Menerima FileStorage object
    # Buat file temporer untuk menyimpan audio
    # Gunakan fd untuk memastikan file descriptor ditutup sebelum AudioFile membacanya
    fd, temp_path = tempfile.mkstemp(suffix=".wav") # Asumsi audio adalah wav atau bisa dikonversi
    os.close(fd) # Tutup file descriptor yang dibuka oleh mkstemp
    
    try:
        audio_file_storage.save(temp_path) # Simpan audio yang diupload ke path temporer

        recognizer_instance = Recognizer()
        with AudioFile(temp_path) as source:
            audio_data = recognizer_instance.record(source) # Baca seluruh file audio

        # Lakukan pengenalan
        # Anda bisa mencoba beberapa service jika satu gagal, atau menambahkan error handling lebih baik
        text = recognizer_instance.recognize_google(audio_data, language="id-ID")
        words = text.split()
        word_count = len(words)
        # WPM biasanya dihitung berdasarkan durasi audio, yang tidak kita dapatkan langsung di sini
        # Untuk WPM yang lebih akurat, Anda perlu durasi audio.
        # AudioFile(temp_path).duration bisa memberikan durasi
        duration_seconds = 0
        try:
            with AudioFile(temp_path) as source_for_duration:
                 duration_seconds = source_for_duration.duration
        except Exception:
            pass # Gagal mendapatkan durasi, WPM mungkin tidak akurat

        wpm = 0
        if duration_seconds > 0:
            duration_minutes = duration_seconds / 60
            wpm = round(word_count / duration_minutes) if duration_minutes > 0 else 0


        return {
            "status": "success",
            "transcript": text,
            "word_count": word_count,
            "words_per_minute": wpm, # Ini masih perkiraan
            "language": "id-ID",
            "duration_seconds": round(duration_seconds, 2) if duration_seconds else None
        }, 200

    except Exception as e:
        current_app.logger.error(f"Error in analyze_speech_audio_service: {e}", exc_info=True)
        # Pesan error spesifik dari speech_recognition bisa lebih informatif
        return {"status": "error", "message": f"Speech recognition error: {str(e)}"}, 500
    finally:
        # Selalu hapus file temporer
        if os.path.exists(temp_path):
            os.unlink(temp_path)