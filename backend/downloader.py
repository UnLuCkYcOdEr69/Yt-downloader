import yt_dlp
import os
import uuid
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

COOKIES_FILE = os.path.join(BASE_DIR, "cookies.txt")


def _get_cookiefile_if_exists():
    if os.path.exists(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0:
        return COOKIES_FILE
    return None


def get_video_info(url):
    cookiefile = _get_cookiefile_if_exists()

    ydl_opts = {
        "quiet": True,
        "noplaylist": True,
        "skip_download": True,
    }

    if cookiefile:
        ydl_opts["cookiefile"] = cookiefile

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        return {
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
        }

    except Exception:
        # ✅ fallback so frontend still shows something
        return {
            "title": "Video Found ✅ (Info limited on server)",
            "thumbnail": ""
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
            # download finished, merging/postprocessing can still happen
            progress_store[task_id] = {
                "status": "processing",
                "percent": 99
            }

    return hook


def _wait_for_file_ready(filepath, timeout_sec=60):
    """
    Wait until file exists and size becomes > 0 and stable.
    Prevents 'empty file' downloads on Render.
    """
    timeout = time.time() + timeout_sec
    last_size = -1

    while time.time() < timeout:
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            # Must be non-zero
            if size > 0:
                # Ensure it's stable (not still being written)
                if size == last_size:
                    return True
                last_size = size
        time.sleep(0.3)

    return False


# 🎥 MP4 — VIDEO + AUDIO merged
def download_video(url, task_id, progress_store):
    uid = str(uuid.uuid4())
    outtmpl = os.path.join(DOWNLOAD_DIR, f"{uid}.%(ext)s")

    progress_store[task_id] = {"status": "starting", "percent": 1}

    cookiefile = _get_cookiefile_if_exists()

    ydl_opts = {
        "format": "bv*[ext=mp4][vcodec^=avc1]+ba[ext=m4a]/bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]",
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "prefer_ffmpeg": True,
        "noplaylist": True,
        "quiet": True,
        "progress_hooks": [_build_progress_hook(progress_store, task_id)],
    }

    if cookiefile:
        ydl_opts["cookiefile"] = cookiefile

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    final_file = os.path.join(DOWNLOAD_DIR, f"{uid}.mp4")

    ready = _wait_for_file_ready(final_file, timeout_sec=90)
    if not ready:
        progress_store[task_id] = {
            "status": "error",
            "percent": 0,
            "error": "Final MP4 not created or empty"
        }
        raise RuntimeError("Final MP4 not created or empty")

    progress_store[task_id] = {
        "status": "done",
        "percent": 100,
        "file": f"{uid}.mp4"
    }
    return f"{uid}.mp4"


# 🎧 MP3 — AUDIO only
def download_audio(url, task_id, progress_store):
    uid = str(uuid.uuid4())
    outtmpl = os.path.join(DOWNLOAD_DIR, f"{uid}.%(ext)s")

    progress_store[task_id] = {"status": "starting", "percent": 1}

    cookiefile = _get_cookiefile_if_exists()

    ydl_opts = {
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

    if cookiefile:
        ydl_opts["cookiefile"] = cookiefile

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    final_file = os.path.join(DOWNLOAD_DIR, f"{uid}.mp3")

    ready = _wait_for_file_ready(final_file, timeout_sec=90)
    if not ready:
        progress_store[task_id] = {
            "status": "error",
            "percent": 0,
            "error": "Final MP3 not created or empty"
        }
        raise RuntimeError("Final MP3 not created or empty")

    progress_store[task_id] = {
        "status": "done",
        "percent": 100,
        "file": f"{uid}.mp3"
    }
    return f"{uid}.mp3"
