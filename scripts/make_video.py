import os
import subprocess
import glob

CLIPS_DIR = "output/clips"
VOICE_FILE = "output/voice.wav"
OUTPUT_FILE = "output/short.mp4"

os.makedirs("output", exist_ok=True)

clips = sorted(glob.glob(f"{CLIPS_DIR}/clip_*.mp4"))

if not clips:
    raise RuntimeError("Tidak ada video clip ditemukan di output/clips/")

print(f"Ditemukan {len(clips)} video clips.")

# Buat file daftar untuk FFmpeg
list_file = "output/clips.txt"

with open(list_file, "w") as f:
    for clip in clips:
        absolute_path = os.path.abspath(clip)
        f.write(f"file '{absolute_path}'\n")

# Gabungkan semua video
temp_video = "output/combined.mp4"

subprocess.run([
    "ffmpeg",
    "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", list_file,
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-pix_fmt", "yuv420p",
    temp_video
], check=True)

# Gabungkan video dengan voice-over
subprocess.run([
    "ffmpeg",
    "-y",
    "-i", temp_video,
    "-i", VOICE_FILE,
    "-map", "0:v:0",
    "-map", "1:a:0",
    "-c:v", "copy",
    "-c:a", "aac",
    "-shortest",
    OUTPUT_FILE
], check=True)

print("====================================")
print("VIDEO BERHASIL DIBUAT")
print(f"Output: {OUTPUT_FILE}")
print("====================================")
