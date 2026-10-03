import os
import re
import requests
from urllib.parse import quote


# ============================================================
# CONFIG
# ============================================================

API_KEY = os.environ.get("PIXABAY_API_KEY")

if not API_KEY:
    raise RuntimeError("PIXABAY_API_KEY belum tersedia.")

TOPIC_FILE = "output/topic.txt"
SCRIPT_FILE = "output/script.txt"

OUTPUT_DIR = "output"
CLIPS_DIR = "output/clips"

THUMBNAIL_FILE = "output/thumbnail.jpg"

MIN_VIDEOS = 7

VIDEO_API = "https://pixabay.com/api/videos/"
IMAGE_API = "https://pixabay.com/api/"


# ============================================================
# HELPERS
# ============================================================

def clean_text(text):
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_topic():
    if not os.path.exists(TOPIC_FILE):
        raise RuntimeError(
            f"Topic file tidak ditemukan: {TOPIC_FILE}"
        )

    with open(
        TOPIC_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        topic = f.read().strip()

    if not topic:
        raise RuntimeError("Topic kosong.")

    return topic


def get_script():
    if not os.path.exists(SCRIPT_FILE):
        raise RuntimeError(
            f"Script file tidak ditemukan: {SCRIPT_FILE}"
        )

    with open(
        SCRIPT_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        script = f.read().strip()

    if not script:
        raise RuntimeError("Script kosong.")

    return script


def get_keywords(topic, script):
    """
    Membuat kata kunci sederhana dari topic + script.
    Kata umum dibuang agar pencarian Pixabay lebih spesifik.
    """

    stopwords = {
        "the", "and", "are", "can", "for", "with",
        "this", "that", "your", "from", "into",
        "about", "have", "has", "their", "they",
        "you", "when", "what", "how", "why",
        "its", "it's", "also", "more", "than",
        "with", "some", "very", "just", "like",
        "healthy", "health", "benefits", "benefit",
        "food", "eating", "eat", "helps", "help",
        "may", "could", "should", "people"
    }

    text = clean_text(
        f"{topic} {script}"
    ).lower()

    words = text.split()

    keywords = []

    for word in words:

        if len(word) < 4:
            continue

        if word in stopwords:
            continue

        if word not in keywords:
            keywords.append(word)

    return keywords[:12]


def download_file(url, filename):
    print(f"Downloading: {url}")

    response = requests.get(
        url,
        timeout=120
    )

    response.raise_for_status()

    with open(filename, "wb") as f:
        f.write(response.content)

    size = os.path.getsize(filename)

    if size < 1000:
        raise RuntimeError(
            f"Downloaded file terlalu kecil: {filename}"
        )

    print(
        f"Saved: {filename} "
        f"({size / 1024:.1f} KB)"
    )


# ============================================================
# SEARCH PHOTO
# ============================================================

def search_thumbnail(topic):

    print("\n======================================")
    print("SEARCHING THUMBNAIL PHOTO")
    print("======================================")

    queries = [
        topic,
        clean_text(topic).replace(
            "benefits of ",
            ""
        ),
    ]

    for query in queries:

        print(f"Photo query: {query}")

        params = {
            "key": API_KEY,
            "q": query,
            "image_type": "photo",
            "orientation": "vertical",
            "safesearch": "true",
            "per_page": 10
        }

        response = requests.get(
            IMAGE_API,
            params=params,
            timeout=120
        )

        response.raise_for_status()

        data = response.json()

        hits = data.get("hits", [])

        if not hits:
            continue

        # Prefer a high-resolution image.
        hits = sorted(
            hits,
            key=lambda x: (
                x.get("imageWidth", 0)
                * x.get("imageHeight", 0)
            ),
            reverse=True
        )

        selected = hits[0]

        image_url = selected.get(
            "largeImageURL"
        )

        if not image_url:
            continue

        download_file(
            image_url,
            THUMBNAIL_FILE
        )

        print(
            f"Thumbnail selected: "
            f"{selected.get('id')}"
        )

        print(
            f"Thumbnail query: {query}"
        )

        return True

    return False


# ============================================================
# SEARCH VIDEOS
# ============================================================

def search_videos(topic, script):

    print("\n======================================")
    print("SEARCHING VIDEO FOOTAGE")
    print("======================================")

    keywords = get_keywords(
        topic,
        script
    )

    print(
        "Keywords:",
        ", ".join(keywords)
    )

    # We use several targeted searches instead of
    # one extremely broad search.
    queries = []

    # 1. Exact topic
    queries.append(
        clean_text(topic)
    )

    # 2. Main subject from topic
    subject = clean_text(topic)

    subject = re.sub(
        r"\bbenefits?\b",
        "",
        subject,
        flags=re.IGNORECASE
    )

    subject = re.sub(
        r"\bof\b",
        "",
        subject,
        flags=re.IGNORECASE
    )

    subject = re.sub(
        r"\beating\b",
        "",
        subject,
        flags=re.IGNORECASE
    )

    subject = clean_text(subject)

    if subject:
        queries.append(subject)

    # 3. Selected keyword combinations
    if len(keywords) >= 2:

        queries.append(
            " ".join(keywords[:2])
        )

    if len(keywords) >= 3:

        queries.append(
            " ".join(keywords[:3])
        )

    unique_queries = []

    for query in queries:

        query = query.strip()

        if query and query not in unique_queries:
            unique_queries.append(query)

    downloaded = []
    used_ids = set()

    for query in unique_queries:

        if len(downloaded) >= MIN_VIDEOS:
            break

        print("\n--------------------------------------")
        print(f"Video query: {query}")

        params = {
            "key": API_KEY,
            "q": query,
            "video_type": "film",
            "orientation": "vertical",
            "safesearch": "true",
            "per_page": 20
        }

        response = requests.get(
            VIDEO_API,
            params=params,
            timeout=120
        )

        response.raise_for_status()

        data = response.json()

        hits = data.get("hits", [])

        print(
            f"Results returned: {len(hits)}"
        )

        for hit in hits:

            if len(downloaded) >= MIN_VIDEOS:
                break

            video_id = hit.get("id")

            if video_id in used_ids:
                continue

            videos = hit.get(
                "videos",
                {}
            )

            # Prefer medium or large.
            selected_video = (
                videos.get("medium")
                or videos.get("large")
                or videos.get("small")
            )

            if not selected_video:
                continue

            video_url = selected_video.get(
                "url"
            )

            if not video_url:
                continue

            clip_number = len(downloaded) + 1

            filename = os.path.join(
                CLIPS_DIR,
                f"clip_{clip_number:02d}.mp4"
            )

            try:

                download_file(
                    video_url,
                    filename
                )

                downloaded.append(
                    filename
                )

                used_ids.add(
                    video_id
                )

                print(
                    f"Selected video ID: {video_id}"
                )

            except Exception as e:

                print(
                    f"Skipping video {video_id}: "
                    f"{e}"
                )

    return downloaded


# ============================================================
# MAIN
# ============================================================

def main():

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    os.makedirs(
        CLIPS_DIR,
        exist_ok=True
    )

    # Remove old clips.
    for filename in os.listdir(CLIPS_DIR):

        if filename.endswith(".mp4"):

            path = os.path.join(
                CLIPS_DIR,
                filename
            )

            os.remove(path)

    # Remove old thumbnail.
    if os.path.exists(THUMBNAIL_FILE):
        os.remove(THUMBNAIL_FILE)

    # --------------------------------------------------------
    # READ TOPIC + SCRIPT
    # --------------------------------------------------------

    topic = get_topic()
    script = get_script()

    print("\n======================================")
    print("V6-A VISUAL SEARCH")
    print("======================================")

    print(f"Topic: {topic}")

    print("\nScript:")
    print(script)

    # --------------------------------------------------------
    # THUMBNAIL
    # --------------------------------------------------------

    thumbnail_ok = search_thumbnail(
        topic
    )

    if not thumbnail_ok:

        raise RuntimeError(
            "Tidak berhasil mendapatkan "
            "foto thumbnail yang relevan."
        )

    # --------------------------------------------------------
    # VIDEO FOOTAGE
    # --------------------------------------------------------

    clips = search_videos(
        topic,
        script
    )

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    print("\n======================================")
    print("VISUAL SEARCH RESULT")
    print("======================================")

    print(
        f"Thumbnail: {THUMBNAIL_FILE}"
    )

    print(
        f"Videos downloaded: {len(clips)}"
    )

    for index, clip in enumerate(
        clips,
        start=1
    ):
        print(
            f"{index}. {clip}"
        )

    if len(clips) < MIN_VIDEOS:

        raise RuntimeError(
            f"GAGAL: minimal {MIN_VIDEOS} "
            f"video diperlukan, tetapi hanya "
            f"{len(clips)} berhasil diunduh."
        )

    print("\nV6-A SUCCESS")
    print(
        f"Minimal {MIN_VIDEOS} video tersedia."
    )


if __name__ == "__main__":
    main()
