import os
import subprocess
from pathlib import Path

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

output_file = OUTPUT_DIR / "test_short.mp4"

title = "3 Healthy Habits\nFor a Better Life"

subtitle = "Health • Lifestyle • Wellbeing"

command = [
    "ffmpeg",
    "-y",
    "-f", "lavfi",
    "-i", "color=c=black:s=1080x1920:r=30",
    "-t", "10",
    "-vf",
    (
        "drawtext="
        "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        "text='3 HEALTHY HABITS':"
        "fontcolor=white:"
        "fontsize=82:"
        "x=(w-text_w)/2:"
        "y=760,"
        "drawtext="
        "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        "text='For a Better Life':"
        "fontcolor=white:"
        "fontsize=58:"
        "x=(w-text_w)/2:"
        "y=900,"
        "drawtext="
        "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        "text='Health • Lifestyle • Wellbeing':"
        "fontcolor=white:"
        "fontsize=40:"
        "x=(w-text_w)/2:"
        "y=1100"
    ),
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-movflags", "+faststart",
    str(output_file)
]

print("Starting video generation...")

result = subprocess.run(
    command,
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print("VIDEO GENERATION FAILED")
    print(result.stderr)
    raise SystemExit(1)

print("VIDEO GENERATED SUCCESSFULLY")
print(f"File: {output_file}")
print(f"Size: {output_file.stat().st_size} bytes")
