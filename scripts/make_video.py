import subprocess
import os

voice = "output/voice.wav"
video = "output/short.mp4"

if not os.path.exists(voice):
    raise RuntimeError("voice.wav not found")

cmd = [
    "ffmpeg",
    "-y",
    "-f", "lavfi",
    "-i", "color=c=black:s=1080x1920:r=30",
    "-i", voice,
    "-t", "60",
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-b:a", "128k",
    "-shortest",
    video
]

print("Creating Shorts video...")

result = subprocess.run(cmd)

if result.returncode != 0:
    raise RuntimeError("FFmpeg failed")

print("VIDEO GENERATED SUCCESSFULLY")
print(video)
