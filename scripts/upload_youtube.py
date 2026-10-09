
import os
from pathlib import Path
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

VIDEO_PATH = Path("output/short.mp4")
TOPIC_PATH = Path("output/topic.txt")

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

    topic_text = TOPIC_PATH.read_text(
        encoding="utf-8"
    ) if TOPIC_PATH.is_file() else ""

    topic = "Healthy Living"
    for line in topic_text.splitlines():
        if line.lower().startswith("topic:"):
            topic = line.split(":", 1)[1].strip()
            break

    credentials = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )

    youtube = build(
        "youtube", "v3", credentials=credentials,
        cache_discovery=False
    )

    title = f"{topic} | Tayyib Health Notes"
    description = (
        f"Learn about {topic} in this health Short.\n\n"
        "Educational content only; not a substitute for professional "
        "medical advice.\n\n"
        "#Shorts #Health #TayyibHealthNotes"
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title[:100],
                "description": description,
                "categoryId": "27",
                "defaultLanguage": "en",
            },
            "status": {
                "privacyStatus": "private",
                "selfDeclaredMadeForKids": False,
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
