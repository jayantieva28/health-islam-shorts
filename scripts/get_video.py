import os
import re
import requests

API_KEY = os.environ.get("PIXABAY_API_KEY")

if not API_KEY:
    raise RuntimeError("PIXABAY_API_KEY belum tersedia.")

SCRIPT_FILE = "output/script.txt"
OUTPUT_DIR = "output/clips"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Baca script
with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
    script = f.read().strip()

if not script:
    raise RuntimeError("output/script.txt kosong.")

# Ambil beberapa kata penting dari script
stopwords = {
    "the", "and", "that", "this", "with", "from", "your",
    "have", "will", "are", "for", "you", "they", "their",
    "about", "into", "what", "when", "which", "while",
    "also", "more", "than", "can", "may", "our", "how",
    "why", "just", "like", "does", "its", "it's", "not",
    "but", "one", "two", "three", "these", "those"
}

words = re.findall(r"[a-zA-Z]+", script.lower())

important_words = []

for word in words:
    if len(word) >= 4 and word not in stopwords:
        if word not in important_words:
            important_words.append(word)

# Maksimal 4 kata utama
keywords = important_words[:4]

if not keywords:
    keywords = ["healthy food"]

query = " ".join(keywords) + " healthy food"

print("======================================")
print("PIXABAY SEARCH")
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
    print("Query utama tidak menemukan video.")
    print("Mencoba fallback search...")

    params["q"] = keywords[0] if keywords else "healthy food"

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    hits = data.get("hits", [])

if not hits:
    raise RuntimeError("Pixabay tidak menemukan video yang sesuai.")

# Bersihkan clip lama
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
print(f"Query digunakan: {query}")
print("======================================")
