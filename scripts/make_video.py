import subprocess
import os

voice = "output/voice.wav"
visual = "output/visual.jpg"
video = "output/short.mp4"

if not os.path.exists(voice):
    raise RuntimeError("voice.wav not found")

if not os.path.exists(visual):
    raise RuntimeError("visual.jpg not found")

cmd = [
    "ffmpeg",
    "-y",
    "-loop", "1",
    "-i", visual,
    "-i", voice,
    "-vf",
    "scale=1080:1920:force_original_aspect_ratio=increase,"
    "crop=1080:1920",
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-b:a", "128k",
    "-shortest",
    video
]

print("Creating Shorts video with visual...")

result = subprocess.run(cmd)

if result.returncode != 0:
    raise RuntimeError("FFmpeg failed")

print("VIDEO WITH VISUAL GENERATED SUCCESSFULLY")
print(video)
