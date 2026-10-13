
import os
import re
import json
import requests

API_KEY = os.environ.get("PIXABAY_API_KEY")
if not API_KEY:
    raise RuntimeError("PIXABAY_API_KEY belum tersedia.")

TOPIC_FILE = "output/topic.txt"
SCRIPT_FILE = "output/script.txt"
OUTPUT_DIR = "output"
CLIPS_DIR = "output/clips"
THUMBNAIL_FILE = "output/thumbnail.jpg"

# Riwayat permanen di root repository.
HISTORY_FILE = "used_footage.json"
CURRENT_FILE = "output/current_footage.json"

MIN_VIDEOS = 7
VIDEO_API = "https://pixabay.com/api/videos/"
IMAGE_API = "https://pixabay.com/api/"


def clean_text(text):
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def read_text(path):
    if not os.path.exists(path):
        raise RuntimeError(f"File tidak ditemukan: {path}")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().strip()
    if not text:
        raise RuntimeError(f"File kosong: {path}")
    return text


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return set()

    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    ids = data.get("used_ids", [])
    return {str(value) for value in ids}


def save_history(used_ids):
    data = {
        "used_ids": sorted(used_ids),
    }
    temp = HISTORY_FILE + ".tmp"
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(temp, HISTORY_FILE)


def download_file(url, filename):
    print(f"Downloading: {url}")
    response = requests.get(url, timeout=120)
    response.raise_for_status()

    with open(filename, "wb") as f:
        f.write(response.content)

    if os.path.getsize(filename) < 1000:
        os.remove(filename)
        raise RuntimeError(f"File unduhan terlalu kecil: {filename}")

    print(f"Saved: {filename}")


def search_thumbnail(topic):
    queries = [topic, clean_text(topic).replace("benefits of ", "")]

    for query in queries:
        params = {
            "key": API_KEY,
            "q": query,
            "image_type": "photo",
            "orientation": "vertical",
            "safesearch": "true",
            "per_page": 10,
        }

        response = requests.get(IMAGE_API, params=params, timeout=120)
        response.raise_for_status()
        hits = response.json().get("hits", [])

        hits.sort(
            key=lambda item: (
                item.get("imageWidth", 0) * item.get("imageHeight", 0)
            ),
            reverse=True,
        )

        for hit in hits:
            url = hit.get("largeImageURL")
            if not url:
                continue
            try:
                download_file(url, THUMBNAIL_FILE)
                print("Thumbnail ID:", hit.get("id"))
                return True
            except Exception as exc:
                print("Thumbnail dilewati:", exc)

    return False


def get_keywords(topic, script):
    stopwords = {
        "the", "and", "are", "can", "for", "with", "this", "that",
        "your", "from", "into", "about", "have", "their", "they",
        "you", "when", "what", "how", "why", "also", "more", "than",
        "some", "very", "just", "like", "healthy", "health",
        "benefits", "benefit", "food", "eating", "eat", "helps",
        "help", "may", "could", "should", "people",
    }

    words = clean_text(f"{topic} {script}").lower().split()
    result = []
    for word in words:
        if len(word) >= 4 and word not in stopwords and word not in result:
            result.append(word)
    return result[:12]


def search_videos(topic, script, history):
    keywords = get_keywords(topic, script)
    subject = clean_text(topic)
    subject = re.sub(
        r"\b(benefits?|of|eating)\b",
        "",
        subject,
        flags=re.IGNORECASE,
    )
    subject = clean_text(subject)

    queries = [clean_text(topic), subject]
    if len(keywords) >= 2:
        queries.append(" ".join(keywords[:2]))
    if len(keywords) >= 3:
        queries.append(" ".join(keywords[:3]))

    queries = list(dict.fromkeys(q for q in queries if q))
    downloaded = []
    current_ids = set()
    selected_records = []

    for query in queries:
        if len(downloaded) >= MIN_VIDEOS:
            break

        print(f"\nPencarian footage: {query}")
        params = {
            "key": API_KEY,
            "q": query,
            "video_type": "film",
            "orientation": "vertical",
            "safesearch": "true",
            "per_page": 50,
        }

        response = requests.get(VIDEO_API, params=params, timeout=120)
        response.raise_for_status()
        hits = response.json().get("hits", [])
        print("Hasil ditemukan:", len(hits))

        for hit in hits:
            if len(downloaded) >= MIN_VIDEOS:
                break

            video_id = str(hit.get("id", ""))
            if not video_id or video_id in history or video_id in current_ids:
                if video_id in history:
                    print("Lewati footage lama:", video_id)
                continue

            variants = hit.get("videos", {})
            selected = (
                variants.get("medium")
                or variants.get("large")
                or variants.get("small")
            )
            if not selected or not selected.get("url"):
                continue

            index = len(downloaded) + 1
            filename = os.path.join(CLIPS_DIR, f"clip_{index:02d}.mp4")

            try:
                download_file(selected["url"], filename)
                downloaded.append(filename)
                current_ids.add(video_id)
                selected_records.append({
                    "id": video_id,
                    "url": selected["url"],
                    "query": query,
                })
                print("ID footage baru:", video_id)
            except Exception as exc:
                print(f"Footage {video_id} dilewati:", exc)
                if os.path.exists(filename):
                    os.remove(filename)

    # Simpan pilihan untuk proses video saat ini.
    with open(CURRENT_FILE, "w", encoding="utf-8") as f:
        json.dump(selected_records, f, indent=2)

    # Catat ID baru segera setelah berhasil diunduh agar tidak terpilih
    # lagi pada run berikutnya. Pastikan file ini di-commit ke GitHub.
    history.update(current_ids)
    save_history(history)

    return downloaded


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(CLIPS_DIR, exist_ok=True)

    # Bersihkan klip lokal lama saja; jangan hapus riwayat.
    for name in os.listdir(CLIPS_DIR):
        path = os.path.join(CLIPS_DIR, name)
        if name.lower().endswith(".mp4") and os.path.isfile(path):
            os.remove(path)

    if os.path.exists(THUMBNAIL_FILE):
        os.remove(THUMBNAIL_FILE)

    topic = read_text(TOPIC_FILE)
    script = read_text(SCRIPT_FILE)

    print("\nTAYYIB HEALTH NOTES — FOOTAGE SEARCH")
    print("Topic:", topic)

    history = load_history()
    print("ID footage yang sudah tercatat:", len(history))

    if not search_thumbnail(topic):
        raise RuntimeError("Tidak berhasil mendapatkan foto thumbnail.")

    clips = search_videos(topic, script, history)

    print(f"\nFootage baru berhasil diunduh: {len(clips)}")
    for clip in clips:
        print("-", clip)

    if len(clips) < MIN_VIDEOS:
        raise RuntimeError(
            f"Hanya {len(clips)} footage baru ditemukan; "
            f"minimal {MIN_VIDEOS} diperlukan. "
            "Tidak akan menggunakan ulang ID yang tercatat."
        )

    print("\nVISUAL SEARCH SUCCESS")


if __name__ == "__main__":
    main()
