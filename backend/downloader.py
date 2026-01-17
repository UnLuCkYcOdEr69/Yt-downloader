import yt_dlp
import os
import uuid
import time

COOKIES_PATH = os.path.join(os.path.dirname(__file__), "cookies.txt")

def ensure_cookies_file():
    cookies_data = os.getenv("YT_COOKIES", "").strip()
    if cookies_data:
        with open(COOKIES_PATH, "w", encoding="utf-8") as f:
            f.write(cookies_data)
        return COOKIES_PATH
    return None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def get_video_info(url):
    cookies_file = ensure_cookies_file()
    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        info = ydl.extract_info(url, download=False)

    return {
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
    }


def _build_progress_hook(progress_store, task_id):
    def hook(d):
        status = d.get("status")

        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0

            percent = 0
            if total > 0:
                percent = int((downloaded / total) * 100)

            progress_store[task_id] = {
                "status": "downloading",
                "percent": percent,
                "speed": d.get("speed"),
                "eta": d.get("eta")
            }

        elif status == "finished":
            # yt-dlp finished downloading streams, merging may start
            progress_store[task_id] = {
                "status": "processing",
                "percent": 99
            }

    return hook


# 🎥 MP4 — VIDEO + AUDIO merged
def download_video(url, task_id, progress_store):
    cookies_file = ensure_cookies_file()
    uid = str(uuid.uuid4())
    outtmpl = os.path.join(DOWNLOAD_DIR, f"{uid}.%(ext)s")

    progress_store[task_id] = {"status": "starting", "percent": 1}

    ydl_opts = {
        "format": "bv*[ext=mp4][vcodec^=avc1]+ba[ext=m4a]/bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]",
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "prefer_ffmpeg": True,
        "noplaylist": True,
        "quiet": True,
        "progress_hooks": [_build_progress_hook(progress_store, task_id)],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    final_file = os.path.join(DOWNLOAD_DIR, f"{uid}.mp4")

    timeout = time.time() + 30
    while not os.path.exists(final_file):
        if time.time() > timeout:
            progress_store[task_id] = {"status": "error", "percent": 0, "error": "Final MP4 not created"}
            raise RuntimeError("Final MP4 not created")
        time.sleep(0.2)

    progress_store[task_id] = {"status": "done", "percent": 100, "file": f"{uid}.mp4"}
    return f"{uid}.mp4"


# 🎧 MP3 — AUDIO only
def download_audio(url, task_id, progress_store):
    cookies_file = ensure_cookies_file()
    uid = str(uuid.uuid4())
    outtmpl = os.path.join(DOWNLOAD_DIR, f"{uid}.%(ext)s")

    progress_store[task_id] = {"status": "starting", "percent": 1}

    ydl_opts = {
        if cookies_file:
    ydl_opts["cookiefile"] = cookies_file
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "progress_hooks": [_build_progress_hook(progress_store, task_id)],
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320",
        }],
        
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    final_file = os.path.join(DOWNLOAD_DIR, f"{uid}.mp3")

    timeout = time.time() + 30
    while not os.path.exists(final_file):
        if time.time() > timeout:
            progress_store[task_id] = {"status": "error", "percent": 0, "error": "Final MP3 not created"}
            raise RuntimeError("Final MP3 not created")
        time.sleep(0.2)

    progress_store[task_id] = {"status": "done", "percent": 100, "file": f"{uid}.mp3"}
    return f"{uid}.mp3"
