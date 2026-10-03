import os
import re
import subprocess
from pathlib import Path

OUTPUT_DIR = Path("output")
CLIPS_DIR = OUTPUT_DIR / "clips"

VOICE = OUTPUT_DIR / "voice.wav"
SCRIPT = OUTPUT_DIR / "script.txt"
SRT = OUTPUT_DIR / "subtitles.srt"
CONCAT = OUTPUT_DIR / "combined.mp4"
FINAL = OUTPUT_DIR / "short.mp4"

WATERMARK = "Tayyib Health Notes"


def run(cmd):
    print("RUN:", " ".join(str(x) for x in cmd))
    subprocess.run(cmd, check=True)


def get_duration(file):
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file)
        ],
        capture_output=True,
        text=True,
        check=True
    )
    return float(result.stdout.strip())


def timestamp(seconds):
    ms = int(round((seconds - int(seconds)) * 1000))
    total = int(seconds)

    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60

    if ms >= 1000:
        secs += 1
        ms -= 1000

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def create_subtitles(script_text, duration):
    # Bersihkan script
    text = re.sub(r"\s+", " ", script_text).strip()

    # Pecah berdasarkan kalimat
    sentences = re.split(r"(?<=[.!?])\s+", text)

    chunks = []

    for sentence in sentences:
        words = sentence.split()

        # Maksimum sekitar 5 kata per subtitle
        for i in range(0, len(words), 5):
            chunk = " ".join(words[i:i + 5]).strip()
            if chunk:
                chunks.append(chunk)

    if not chunks:
        raise RuntimeError("Tidak ada teks untuk subtitle.")

    # Durasi tiap subtitle berdasarkan panjang teks
    weights = [max(len(x), 1) for x in chunks]
    total_weight = sum(weights)

    current = 0.0
    entries = []

    for index, (chunk, weight) in enumerate(zip(chunks, weights), start=1):
        if index == len(chunks):
            end = duration
        else:
            end = current + duration * weight / total_weight

        entries.append(
            f"{index}\n"
            f"{timestamp(current)} --> {timestamp(end)}\n"
            f"{chunk}\n"
        )

        current = end

    SRT.write_text("\n".join(entries), encoding="utf-8")

    print(f"Subtitle dibuat: {SRT}")
    print(f"Jumlah subtitle: {len(chunks)}")


# ============================================================
# 1. CHECK FILE
# ============================================================

if not VOICE.exists():
    raise RuntimeError("voice.wav tidak ditemukan.")

if not SCRIPT.exists():
    raise RuntimeError("script.txt tidak ditemukan.")

clips = sorted(CLIPS_DIR.glob("clip_*.mp4"))

if not clips:
    raise RuntimeError("Tidak ada video clips ditemukan.")

print(f"Ditemukan {len(clips)} video clips.")


# ============================================================
# 2. VOICE DURATION
# ============================================================

voice_duration = get_duration(VOICE)

print(f"Durasi voice: {voice_duration:.2f} detik")


# ============================================================
# 3. NORMALIZE VIDEO CLIPS
# ============================================================

normalized_dir = OUTPUT_DIR / "normalized"
normalized_dir.mkdir(exist_ok=True)

normalized = []

total_duration = 0
index = 1

while total_duration < voice_duration + 1:
    for clip in clips:

        output = normalized_dir / f"clip_{index:03d}.mp4"

        run([
            "ffmpeg",
            "-y",
            "-i", str(clip),
            "-vf",
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "setsar=1",
            "-r", "30",
            "-an",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            str(output)
        ])

        normalized.append(output)

        duration = get_duration(output)
        total_duration += duration

        print(f"Normalized clip {index}: {duration:.2f}s")

        index += 1

        if total_duration >= voice_duration + 1:
            break


# ============================================================
# 4. CREATE CONCAT LIST
# ============================================================

concat_file = OUTPUT_DIR / "concat.txt"

with open(concat_file, "w", encoding="utf-8") as f:
    for clip in normalized:
        absolute_path = clip.resolve()
        f.write(f"file '{absolute_path}'\n")


# ============================================================
# 5. CONCAT VIDEO
# ============================================================

run([
    "ffmpeg",
    "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", str(concat_file),
    "-c", "copy",
    str(CONCAT)
])


# ============================================================
# 6. CREATE SUBTITLE FILE
# ============================================================

script_text = SCRIPT.read_text(encoding="utf-8")

create_subtitles(
    script_text,
    voice_duration
)


# ============================================================
# 7. ADD VOICE + SUBTITLE + WATERMARK
# ============================================================

subtitle_filter = (
    "subtitles=output/subtitles.srt:"
    "force_style='"
    "FontName=DejaVu Sans,"
    "FontSize=12,"
    "Bold=1,"
    "PrimaryColour=&H00FFFFFF,"
    "OutlineColour=&H00000000,"
    "BorderStyle=1,"
    "Outline=2,"
    "Shadow=1,"
    "Alignment=2,"
    "MarginL=80,"
    "MarginR=80,"
    "MarginV=500"
    "'"
)

watermark_filter = (
    "drawtext="
    "text='Tayyib Health Notes':"
    "fontcolor=white@0.65:"
    "fontsize=32:"
    "x=w-tw-45:"
    "y=55:"
    "shadowcolor=black@0.5:"
    "shadowx=2:"
    "shadowy=2"
)

video_filter = f"{subtitle_filter},{watermark_filter}"


run([
    "ffmpeg",
    "-y",
    "-i", str(CONCAT),
    "-i", str(VOICE),
    "-vf", video_filter,
    "-map", "0:v:0",
    "-map", "1:a:0",
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-crf", "23",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-b:a", "128k",
    "-shortest",
    "-movflags", "+faststart",
    str(FINAL)
])


print("")
print("======================================")
print("VIDEO BERHASIL DIBUAT")
print("======================================")
print(f"Video    : {FINAL}")
print(f"Subtitle : {SRT}")
print(f"Watermark: {WATERMARK}")
print("======================================")
