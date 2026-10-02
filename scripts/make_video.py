import os
import glob
import subprocess
import math

CLIPS_DIR = "output/clips"
VOICE_FILE = "output/voice.wav"
OUTPUT_FILE = "output/short.mp4"
TEMP_DIR = "output/normalized"

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs("output", exist_ok=True)

clips = sorted(glob.glob(f"{CLIPS_DIR}/clip_*.mp4"))

if not clips:
    raise RuntimeError("Tidak ada video clip ditemukan.")

print(f"Ditemukan {len(clips)} video clips.")

# --------------------------------------------------
# 1. Cek durasi voice-over
# --------------------------------------------------

voice_duration = float(subprocess.check_output([
    "ffprobe",
    "-v", "error",
    "-show_entries", "format=duration",
    "-of", "default=noprint_wrappers=1:nokey=1",
    VOICE_FILE
]).decode().strip())

print(f"Durasi voice-over: {voice_duration:.2f} detik")

# --------------------------------------------------
# 2. Normalisasi semua video
# --------------------------------------------------

normalized = []

for i, clip in enumerate(clips, start=1):

    output = f"{TEMP_DIR}/clip_{i:02d}.mp4"

    print(f"Memproses clip {i}: {clip}")

    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", clip,
        "-t", "8",
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "fps=30,"
        "setsar=1",
        "-an",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output
    ], check=True)

    normalized.append(output)

# --------------------------------------------------
# 3. Ulangi clip sampai cukup untuk voice-over
# --------------------------------------------------

selected = []
duration_total = 0

while duration_total < voice_duration + 1:
    for clip in normalized:
        selected.append(clip)

        duration = float(subprocess.check_output([
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            clip
        ]).decode().strip())

        duration_total += duration

        if duration_total >= voice_duration + 1:
            break

print(f"Total durasi video sebelum voice: {duration_total:.2f} detik")

# --------------------------------------------------
# 4. Buat daftar concat
# --------------------------------------------------

list_file = "output/video_list.txt"

with open(list_file, "w") as f:
    for clip in selected:
        f.write(f"file '{os.path.abspath(clip)}'\n")

# --------------------------------------------------
# 5. Gabungkan video
# --------------------------------------------------

combined = "output/combined.mp4"

subprocess.run([
    "ffmpeg",
    "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", list_file,
    "-c", "copy",
    "-an",
    combined
], check=True)

# --------------------------------------------------
# 6. Gabungkan video + voice-over
# --------------------------------------------------

subprocess.run([
    "ffmpeg",
    "-y",
    "-i", combined,
    "-i", VOICE_FILE,
    "-map", "0:v:0",
    "-map", "1:a:0",
    "-c:v", "copy",
    "-c:a", "aac",
    "-b:a", "128k",
    "-shortest",
    "-movflags", "+faststart",
    OUTPUT_FILE
], check=True)

print("======================================")
print("SHORTS BERHASIL DIBUAT")
print(f"Output: {OUTPUT_FILE}")
print(f"Durasi voice: {voice_duration:.2f} detik")
print("Format: 1080x1920 / 9:16 / 30 FPS")
print("======================================")
