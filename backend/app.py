from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import threading
import uuid

from downloader import get_video_info, download_video, download_audio

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ✅ Store progress of each task
PROGRESS = {}


def get_url(req):
    if req.is_json:
        return req.json.get("url")
    return req.form.get("url")


@app.route("/info", methods=["POST"])
def info():
    url = get_url(request)
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        return jsonify(get_video_info(url))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ✅ Start MP4 download in background, return task_id
@app.route("/download/video", methods=["POST"])
def start_video():
    url = get_url(request)
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    task_id = str(uuid.uuid4())
    PROGRESS[task_id] = {"status": "queued", "percent": 0}

    def runner():
        try:
            download_video(url, task_id, PROGRESS)
        except Exception as e:
            PROGRESS[task_id] = {"status": "error", "percent": 0, "error": str(e)}

    threading.Thread(target=runner, daemon=True).start()
    return jsonify({"task_id": task_id})


# ✅ Start MP3 download in background, return task_id
@app.route("/download/audio", methods=["POST"])
def start_audio():
    url = get_url(request)
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    task_id = str(uuid.uuid4())
    PROGRESS[task_id] = {"status": "queued", "percent": 0}

    def runner():
        try:
            download_audio(url, task_id, PROGRESS)
        except Exception as e:
            PROGRESS[task_id] = {"status": "error", "percent": 0, "error": str(e)}

    threading.Thread(target=runner, daemon=True).start()
    return jsonify({"task_id": task_id})


# ✅ Frontend polls this endpoint to get progress %
@app.route("/progress/<task_id>", methods=["GET"])
def progress(task_id):
    return jsonify(PROGRESS.get(task_id, {"status": "unknown", "percent": 0}))


# ✅ Download final file to user's PC
@app.route("/download/<filename>", methods=["GET"])
def serve_download(filename):
    file_path = os.path.join(DOWNLOAD_DIR, filename)

    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return jsonify({"error": "File not ready or empty"}), 404

    return send_file(file_path, as_attachment=True)



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
