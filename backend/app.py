import os
import uuid
import threading
from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp

app = Flask(__name__)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ✅ cookies path in Render Secret Files
COOKIES_PATH = "/etc/secrets/cookies.txt"

# In local system (Windows) this path won't exist, so keep fallback
if not os.path.exists(COOKIES_PATH):
    COOKIES_PATH = None

# ✅ store progress
progress_data = {}


def download_video_task(url, filetype, task_id):
    try:
        progress_data[task_id] = {"status": "downloading", "progress": 0, "filename": None, "error": None}

        def hook(d):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)

                if total and total > 0:
                    percent = int((downloaded / total) * 100)
                    progress_data[task_id]["progress"] = percent

            if d["status"] == "finished":
                progress_data[task_id]["progress"] = 100

        # ✅ headers for Render (YouTube blocks sometimes)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.youtube.com/"
        }

        ydl_opts = {
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [hook],
            "headers": headers,
            "outtmpl": os.path.join(DOWNLOAD_DIR, f"{task_id}.%(ext)s"),
        }

        # ✅ Add cookies if available
        if COOKIES_PATH:
            ydl_opts["cookiefile"] = COOKIES_PATH

        # ✅ MP4 (Video + Audio merged)
        if filetype == "mp4":
            ydl_opts["format"] = "bestvideo+bestaudio/best"
            ydl_opts["merge_output_format"] = "mp4"

        # ✅ MP3 (Audio Extract)
        elif filetype == "mp3":
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]

        else:
            progress_data[task_id]["status"] = "error"
            progress_data[task_id]["error"] = "Invalid format selected!"
            return

        # ✅ Download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            # ✅ Guess final filename correctly
            if filetype == "mp4":
                final_path = os.path.join(DOWNLOAD_DIR, f"{task_id}.mp4")
            else:
                final_path = os.path.join(DOWNLOAD_DIR, f"{task_id}.mp3")

        # ✅ Fix: Empty file problem check
        if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
            progress_data[task_id]["status"] = "error"
            progress_data[task_id]["error"] = "ERROR: The downloaded file is empty (blocked by YouTube / cookies issue)."
            return

        progress_data[task_id]["status"] = "completed"
        progress_data[task_id]["filename"] = os.path.basename(final_path)

    except Exception as e:
        progress_data[task_id]["status"] = "error"
        progress_data[task_id]["error"] = str(e)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/download", methods=["POST"])
def download():
    data = request.json
    url = data.get("url")
    filetype = data.get("filetype")

    if not url or not filetype:
        return jsonify({"error": "URL and file type required"}), 400

    task_id = str(uuid.uuid4())
    progress_data[task_id] = {"status": "starting", "progress": 0, "filename": None, "error": None}

    t = threading.Thread(target=download_video_task, args=(url, filetype, task_id))
    t.start()

    return jsonify({"task_id": task_id})


@app.route("/progress/<task_id>")
def progress(task_id):
    return jsonify(progress_data.get(task_id, {"status": "not_found", "progress": 0}))


@app.route("/file/<task_id>")
def get_file(task_id):
    task = progress_data.get(task_id)
    if not task or task.get("status") != "completed":
        return jsonify({"error": "File not ready"}), 400

    filename = task.get("filename")
    if not filename:
        return jsonify({"error": "File not found"}), 404

    filepath = os.path.join(DOWNLOAD_DIR, filename)

    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return jsonify({"error": "Downloaded file is missing or empty"}), 500

    # ✅ send file
    return send_file(filepath, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
