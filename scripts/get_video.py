import os
import requests

API_KEY = os.environ.get("PIXABAY_API_KEY")

if not API_KEY:
    raise RuntimeError("PIXABAY_API_KEY is not configured")

OUTPUT_DIR = "output/clips"
os.makedirs(OUTPUT_DIR, exist_ok=True)

query = "oats healthy food"

url = "https://pixabay.com/api/videos/"

params = {
    "key": API_KEY,
    "q": query,
    "video_type": "film",
    "orientation": "vertical",
    "per_page": 5,
    "safesearch": "true"
}

print("Searching Pixabay videos...")
print("Query:", query)

response = requests.get(url, params=params, timeout=30)
response.raise_for_status()

data = response.json()
hits = data.get("hits", [])

if not hits:
    raise RuntimeError("No suitable Pixabay videos found")

downloaded = 0

for i, item in enumerate(hits[:5], start=1):
    videos = item.get("videos", {})

    # Prefer medium quality to keep GitHub artifact size reasonable.
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

    output = os.path.join(
        OUTPUT_DIR,
        f"clip_{i:02d}.mp4"
    )

    print(f"Downloading clip {i}...")

    r = requests.get(
        video_url,
        timeout=60
    )
    r.raise_for_status()

    with open(output, "wb") as f:
        f.write(r.content)

    downloaded += 1
    print("Saved:", output)

if downloaded == 0:
    raise RuntimeError("No videos could be downloaded")

print(f"VIDEO DOWNLOAD SUCCESSFUL: {downloaded} clips")
