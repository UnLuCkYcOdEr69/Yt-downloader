const API = "https://yt-downloader-p7s2.onrender.com";

const fetchBtn = document.getElementById("fetchBtn");
const statusEl = document.getElementById("status");

const infoBox = document.getElementById("info");
const actionsBox = document.getElementById("actions");

const thumbEl = document.getElementById("thumb");
const titleEl = document.getElementById("title");

const progressBox = document.getElementById("progressBox");
const progressFill = document.getElementById("progressFill");
const progressText = document.getElementById("progressText");
const progressPercent = document.getElementById("progressPercent");

function setLoading(isLoading, text = "Fetch") {
  if (isLoading) fetchBtn.classList.add("loading");
  else fetchBtn.classList.remove("loading");

  fetchBtn.disabled = isLoading;
  fetchBtn.querySelector(".btn-text").innerText = text;
}

function showProgress(message, percent) {
  progressBox.classList.remove("hidden");
  progressText.innerText = message;
  progressPercent.innerText = `${percent}%`;
  progressFill.style.width = `${percent}%`;
}

function hideProgress() {
  progressBox.classList.add("hidden");
  progressFill.style.width = "0%";
  progressPercent.innerText = "0%";
}

async function fetchInfo() {
  const url = document.getElementById("url").value.trim();
  if (!url) return alert("Paste a YouTube URL!");

  statusEl.innerText = "Fetching details... ⏳";
  setLoading(true, "Fetching");

  // reset view
  infoBox.classList.add("hidden");
  actionsBox.classList.add("hidden");
  hideProgress();

  try {
    const res = await fetch(API + "/info", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Invalid video");

    // show info
    thumbEl.src = data.thumbnail;
    titleEl.innerText = data.title || "Untitled Video";

    infoBox.classList.remove("hidden");
    actionsBox.classList.remove("hidden");

    statusEl.innerText = "Ready ✅ Choose MP4 or MP3";
  } catch (err) {
    statusEl.innerText = "Error ❌ " + err.message;
  } finally {
    setLoading(false, "Fetch");
  }
}

async function downloadFile(type) {
  const url = document.getElementById("url").value.trim();
  if (!url) return alert("Paste a YouTube URL!");

  const endpoint = type === "mp4" ? "/download/video" : "/download/audio";

  try {
    statusEl.innerText = "Starting download... ⏳";
    showProgress("Queued...", 0);

    // ✅ Step 1: Start task
    const res = await fetch(API + endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to start download");

    const taskId = data.task_id;

    // ✅ Step 2: Poll progress
    const interval = setInterval(async () => {
      try {
        const pr = await fetch(API + "/progress/" + taskId);
        const pData = await pr.json();

        const percent = pData.percent || 0;

        if (pData.status === "downloading") {
          statusEl.innerText = "Downloading... ⏳";
          showProgress("Downloading...", percent);
        }

        if (pData.status === "processing") {
          statusEl.innerText = "Merging audio & video... ⚙️";
          showProgress("Merging...", percent);
        }

        if (pData.status === "done") {
          clearInterval(interval);
          showProgress("Complete ✅", 100);
          statusEl.innerText = "Preparing file... ✅";

          const downloadUrl = API + "/download/" + pData.file;

          // ✅ Step 3: Fetch file as blob (prevents empty download)
          const fileRes = await fetch(downloadUrl);

          if (!fileRes.ok) {
            throw new Error("Download failed. File not ready yet.");
          }

          const blob = await fileRes.blob();

          // ✅ Safety check
          if (!blob || blob.size < 1024) {
            throw new Error("Downloaded file is empty. Try again in 2 seconds.");
          }

          // ✅ Force save
          const a = document.createElement("a");
          const blobUrl = window.URL.createObjectURL(blob);
          a.href = blobUrl;

          // ✅ Give a nice filename
          const ext = type === "mp4" ? "mp4" : "mp3";
          a.download = `youtube_download.${ext}`;

          document.body.appendChild(a);
          a.click();
          a.remove();

          window.URL.revokeObjectURL(blobUrl);

          setTimeout(() => {
            hideProgress();
            statusEl.innerText = "Done ✅";
          }, 700);
        }

        if (pData.status === "error") {
          clearInterval(interval);
          hideProgress();
          statusEl.innerText = "Error ❌ " + (pData.error || "Download failed");
        }
      } catch (err) {
        clearInterval(interval);
        hideProgress();
        statusEl.innerText = "Error ❌ " + err.message;
      }
    }, 400);

  } catch (err) {
    hideProgress();
    statusEl.innerText = "Error ❌ " + err.message;
  }
}
