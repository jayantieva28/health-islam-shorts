import os
import requests

API_KEY = os.environ.get("PIXABAY_API_KEY")

if not API_KEY:
    raise RuntimeError("PIXABAY_API_KEY belum tersedia.")

TOPIC_FILE = "output/topic.txt"
OUTPUT_DIR = "output/clips"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Baca topic
if not os.path.exists(TOPIC_FILE):
    raise RuntimeError("output/topic.txt tidak ditemukan.")

with open(TOPIC_FILE, "r", encoding="utf-8") as f:
    topic = f.read().strip()

if not topic:
    raise RuntimeError("topic.txt kosong.")

# Tambahkan kata yang membantu pencarian footage
query = f"{topic} healthy food"

print("======================================")
print("PIXABAY SEARCH")
print(f"Topic: {topic}")
print(f"Query: {query}")
print("======================================")

url = "https://pixabay.com/api/videos/"

params = {
    "key": API_KEY,
    "q": query,
    "video_type": "film",
    "orientation": "vertical",
    "per_page": 10,
    "safesearch": "true"
}

response = requests.get(url, params=params, timeout=30)
response.raise_for_status()

data = response.json()
hits = data.get("hits", [])

if not hits:
    print("Pencarian utama tidak menemukan video.")
    print("Mencoba pencarian berdasarkan topic saja...")

    params["q"] = topic

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    hits = data.get("hits", [])

if not hits:
    raise RuntimeError("Pixabay tidak menemukan video.")

# Hapus clip lama
for filename in os.listdir(OUTPUT_DIR):
    if filename.endswith(".mp4"):
        os.remove(os.path.join(OUTPUT_DIR, filename))

downloaded = 0

for item in hits:

    videos = item.get("videos", {})

    video_info = (
        videos.get("medium")
        or videos.get("small")
        or videos.get("tiny")
    )

    if not video_info:
        continue

    video_url = video_info.get("url")

    if not video_url:
        continue

    downloaded += 1

    output_file = os.path.join(
        OUTPUT_DIR,
        f"clip_{downloaded:02d}.mp4"
    )

    print(f"Downloading clip {downloaded}...")

    video_response = requests.get(
        video_url,
        timeout=60
    )

    video_response.raise_for_status()

    with open(output_file, "wb") as f:
        f.write(video_response.content)

    if downloaded >= 5:
        break

if downloaded == 0:
    raise RuntimeError("Tidak ada video yang berhasil didownload.")

print("======================================")
print(f"Berhasil download {downloaded} video clips.")
print(f"Topic: {topic}")
print(f"Query: {query}")
print("======================================")
