
import os
import json
import re
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

VIDEO_PATH = Path("output/short.mp4")
TOPIC_PATH = Path("output/topic.txt")
SCRIPT_PATH = Path("output/script.txt")

def read_text(path):
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return ""

def get_topic(topic_text):
    for line in topic_text.splitlines():
        if line.lower().startswith("topic:"):
            return line.split(":", 1)[1].strip()
    return topic_text.strip() or "Healthy Living"

def fallback_metadata(topic):
    clean_topic = topic.strip().rstrip(".")
    title = f"{clean_topic}: What You Should Know"
    title = title[:100]

    description = (
        f"Discover what you should know about {clean_topic} "
        "in this short educational video.\n\n"
        "This video shares general health information, not a "
        "personal diagnosis or a substitute for professional "
        "medical advice. Evidence and individual needs can vary.\n\n"
        "#Shorts #Health #HealthyLiving"
    )

    words = re.findall(r"[a-zA-Z0-9]+", clean_topic.lower())
    tags = list(dict.fromkeys([
        clean_topic.lower(),
        *words,
        "health education",
        "healthy living",
        "nutrition",
        "wellness",
        "health tips",
        "YouTube Shorts",
    ]))

    return {
        "title": title,
        "description": description,
        "tags": tags[:15],
    }

def generate_metadata(topic, script):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("OpenRouter key missing; using fallback metadata.")
        return fallback_metadata(topic)

    prompt = f"""
Create YouTube Shorts metadata for an English-language
health education channel called Tayyib Health Notes.

VIDEO TOPIC:
{topic}

ACTUAL VIDEO SCRIPT:
{script[:10000]}

Requirements:
- Target a broad international English-speaking audience.
- Write natural, clear English.
- Make the title engaging, accurate, and specific to this video.
- Do not use clickbait or promise a cure.
- Base the description on the actual topic and script.
- Do not invent scientific facts, sources, or medical benefits.
- Include a concise educational disclaimer in the description.
- Include 2 or 3 relevant hashtags at the end of the description.
- Return 5 to 15 relevant YouTube tags, including specific topic
  terms and a few relevant health/nutrition terms.
- Avoid unrelated tags and keyword stuffing.
- Return ONLY valid JSON in this exact shape:
{{
  "title": "English title",
  "description": "English description with hashtags",
  "tags": ["tag one", "tag two"]
}}
"""

    payload = {
        "model": "openrouter/free",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You write accurate, responsible YouTube metadata. "
                    "Never exaggerate health claims."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 800,
    }

    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))

        content = result["choices"][0]["message"]["content"]
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise ValueError("Metadata response was not valid JSON.")

        metadata = json.loads(match.group(0))
        title = str(metadata.get("title", "")).strip()
        description = str(metadata.get("description", "")).strip()
        tags = metadata.get("tags", [])

        if not title or not description or not isinstance(tags, list):
            raise ValueError("Metadata fields are incomplete.")

        clean_tags = []
        for tag in tags:
            if isinstance(tag, str) and tag.strip():
                clean_tags.append(tag.strip()[:100])

        if not clean_tags:
            clean_tags = fallback_metadata(topic)["tags"]

        metadata = {
            "title": title[:100],
            "description": description[:5000],
            "tags": clean_tags,
        }

        # YouTube limits the combined tag text to about 500 characters.
        final_tags = []
        total_chars = 0
        for tag in metadata["tags"]:
            cost = len(tag) + (1 if final_tags else 0)
            if total_chars + cost > 480:
                continue
            final_tags.append(tag)
            total_chars += cost

        metadata["tags"] = final_tags
        return metadata

    except Exception as exc:
        print(
            "Metadata generation failed; using fallback metadata. "
            f"Reason: {type(exc).__name__}"
        )
        return fallback_metadata(topic)

def main():
    required = [
        "YOUTUBE_CLIENT_ID",
        "YOUTUBE_CLIENT_SECRET",
        "YOUTUBE_REFRESH_TOKEN",
    ]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            "Missing GitHub Actions secrets: " + ", ".join(missing)
        )

    if not VIDEO_PATH.is_file():
        raise FileNotFoundError(f"Video not found: {VIDEO_PATH}")

    topic = get_topic(read_text(TOPIC_PATH))
    script = read_text(SCRIPT_PATH)

    metadata = generate_metadata(topic, script)

    print("Prepared English metadata.")
    print("Title:", metadata["title"])
    print("Tags:", ", ".join(metadata["tags"]))

    credentials = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )

    youtube = build(
        "youtube",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": metadata["title"],
                "description": metadata["description"],
                "tags": metadata["tags"],
                "categoryId": "27",
                "defaultLanguage": "en",
            },
            "status": {
                "privacyStatus": "private",
            },
        },
        media_body=MediaFileUpload(
            str(VIDEO_PATH),
            mimetype="video/mp4",
            chunksize=8 * 1024 * 1024,
            resumable=True,
        ),
    )

    response = request.execute()
    print("YouTube upload succeeded.")
    print("Video ID:", response["id"])
    print("Privacy status: private")
    print("Uploaded at:", datetime.now(timezone.utc).isoformat())

if __name__ == "__main__":
    main()
