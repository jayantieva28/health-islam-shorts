import os
import re
import glob
import subprocess
import math


# ============================================================
# CONFIGURATION
# ============================================================

VOICE_FILE = "output/voice.wav"
CLIPS_DIR = "output/clips"
OUTPUT_DIR = "output"

FINAL_VIDEO = "output/short.mp4"
BASE_VIDEO = "output/video_base.mp4"
CONCAT_FILE = "output/segments.txt"
SUBTITLE_FILE = "output/subtitles.srt"

MIN_CLIPS = 5

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30


# ============================================================
# HELPERS
# ============================================================

def run_command(command):
    print("\nRunning:")
    print(" ".join(command))

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    print(result.stdout)

    if result.returncode != 0:
        raise RuntimeError(
            "Command failed:\n" + " ".join(command)
        )


def get_duration(filename):
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        filename
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Unable to read duration: {filename}"
        )

    return float(result.stdout.strip())


def format_srt_time(seconds):
    milliseconds = int(round((seconds - int(seconds)) * 1000))

    total_seconds = int(seconds)

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    if milliseconds >= 1000:
        milliseconds = 0
        secs += 1

        if secs >= 60:
            secs = 0
            minutes += 1

        if minutes >= 60:
            minutes = 0
            hours += 1

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


# ============================================================
# CLEAN SCRIPT FOR SUBTITLES
# ============================================================

def clean_script_for_subtitles(text):

    # Remove markdown bold/italic markers
    text = text.replace("**", "")
    text = text.replace("__", "")
    text = text.replace("*", "")
    text = text.replace("_", "")

    # Remove common production notes
    lines = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        # Remove lines like:
        # [Scene: ...]
        # [Cut to ...]
        # [Music ...]
        if line.startswith("[") and line.endswith("]"):
            continue

        # Remove common headings
        lower = line.lower()

        if lower in [
            "hook:",
            "intro:",
            "introduction:",
            "body:",
            "main:",
            "cta:",
            "call to action:",
            "islamic teaching:",
            "conclusion:",
            "outro:"
        ]:
            continue

        # Remove lines beginning with production labels
        if lower.startswith("[scene"):
            continue

        if lower.startswith("[cut"):
            continue

        if lower.startswith("[music"):
            continue

        if lower.startswith("[camera"):
            continue

        if lower.startswith("[text overlay"):
            continue

        lines.append(line)

    text = " ".join(lines)

    # Remove remaining bracketed notes
    text = re.sub(r"\[[^\]]*\]", "", text)

    # Remove repeated whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ============================================================
# CREATE SUBTITLES
# ============================================================

def create_subtitles(script, voice_duration):

    print("\n======================================")
    print("CREATING SUBTITLES")
    print("======================================")

    clean_text = clean_script_for_subtitles(script)

    if not clean_text:
        raise RuntimeError(
            "No usable narration text found for subtitles."
        )

    words = clean_text.split()

    # Maximum 5 words per subtitle
    chunks = []

    for i in range(0, len(words), 5):
        chunk = " ".join(words[i:i + 5]).strip()

        if chunk:
            chunks.append(chunk)

    if not chunks:
        raise RuntimeError(
            "Unable to create subtitle chunks."
        )

    # Estimate subtitle timing based on character length.
    # This keeps longer sentences visible slightly longer.
    weights = [
        max(len(chunk), 1)
        for chunk in chunks
    ]

    total_weight = sum(weights)

    current_time = 0.0

    subtitle_entries = []

    for index, (chunk, weight) in enumerate(zip(chunks, weights)):

        duration = voice_duration * (weight / total_weight)

        start = current_time
        end = current_time + duration

        # Keep the last subtitle exactly aligned with voice duration.
        if index == len(chunks) - 1:
            end = voice_duration

        subtitle_entries.append(
            (
                index + 1,
                start,
                end,
                chunk
            )
        )

        current_time = end

    with open(
        SUBTITLE_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        for number, start, end, text in subtitle_entries:

            f.write(
                f"{number}\n"
                f"{format_srt_time(start)} --> "
                f"{format_srt_time(end)}\n"
                f"{text}\n\n"
            )

    print(f"Created {len(subtitle_entries)} subtitle entries.")
    print(f"Saved: {SUBTITLE_FILE}")


# ============================================================
# FIND VIDEO CLIPS
# ============================================================

def get_video_clips():

    clips = sorted(
        glob.glob(
            os.path.join(CLIPS_DIR, "*.mp4")
        )
    )

    if len(clips) < MIN_CLIPS:

        raise RuntimeError(
            f"Minimal {MIN_CLIPS} footage diperlukan, "
            f"tetapi hanya ditemukan {len(clips)} footage."
        )

    print("\n======================================")
    print("VIDEO CLIPS")
    print("======================================")

    for index, clip in enumerate(clips, start=1):
        print(f"{index}. {clip}")

    selected = clips[:MIN_CLIPS]

    print("\nFootage yang akan digunakan:")

    for index, clip in enumerate(selected, start=1):
        print(f"{index}. {os.path.basename(clip)}")

    return selected


# ============================================================
# CREATE 5 VIDEO SEGMENTS
# ============================================================

def create_segments(clips, voice_duration):

    print("\n======================================")
    print("CREATING 5 VIDEO SEGMENTS")
    print("======================================")

    segment_duration = voice_duration / len(clips)

    print(
        f"Voice duration: {voice_duration:.2f} seconds"
    )

    print(
        f"Each footage duration: {segment_duration:.2f} seconds"
    )

    segment_files = []

    for index, clip in enumerate(clips, start=1):

        output_file = os.path.join(
            OUTPUT_DIR,
            f"segment_{index:02d}.mp4"
        )

        print("\n--------------------------------------")
        print(f"FOOTAGE {index}/{len(clips)}")
        print(f"Source: {clip}")
        print(f"Output: {output_file}")

        # Loop source if it is shorter than required.
        # Trim source if it is longer than required.
        command = [
            "ffmpeg",
            "-y",

            "-stream_loop", "-1",
            "-i", clip,

            "-t", str(segment_duration),

            "-vf",
            (
                "scale="
                f"{VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
                "force_original_aspect_ratio=increase,"
                f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
                f"fps={FPS},"
                "setsar=1"
            ),

            "-an",

            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",

            "-pix_fmt", "yuv420p",

            output_file
        ]

        run_command(command)

        segment_files.append(output_file)

    return segment_files


# ============================================================
# CONCATENATE SEGMENTS
# ============================================================

def concatenate_segments(segment_files):

    print("\n======================================")
    print("CONCATENATING SEGMENTS")
    print("======================================")

    with open(
        CONCAT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        for segment in segment_files:

            absolute_path = os.path.abspath(segment)

            # Escape single quotes for concat file
            absolute_path = absolute_path.replace("'", "'\\''")

            f.write(
                f"file '{absolute_path}'\n"
            )

    command = [
        "ffmpeg",
        "-y",

        "-f", "concat",
        "-safe", "0",

        "-i", CONCAT_FILE,

        "-c", "copy",

        BASE_VIDEO
    ]

    run_command(command)


# ============================================================
# CREATE FINAL VIDEO
# ============================================================

def create_final_video():

    print("\n======================================")
    print("CREATING FINAL SHORT")
    print("======================================")

    # Subtitle style:
    # - small
    # - bold
    # - white
    # - black outline
    # - lower-middle position
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
        "MarginL=60,"
        "MarginR=60,"
        "MarginV=70"
        "'"
    )

    # Watermark
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

    video_filter = (
        f"{subtitle_filter},"
        f"{watermark_filter}"
    )

    command = [
        "ffmpeg",
        "-y",

        "-i", BASE_VIDEO,
        "-i", VOICE_FILE,

        "-vf", video_filter,

        "-map", "0:v:0",
        "-map", "1:a:0",

        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",

        "-c:a", "aac",
        "-b:a", "128k",

        "-shortest",

        "-movflags", "+faststart",

        FINAL_VIDEO
    ]

    run_command(command)


# ============================================================
# MAIN
# ============================================================

def main():

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(VOICE_FILE):
        raise RuntimeError(
            f"Voice file not found: {VOICE_FILE}"
        )

    if not os.path.isdir(CLIPS_DIR):
        raise RuntimeError(
            f"Clips directory not found: {CLIPS_DIR}"
        )

    # --------------------------------------------------------
    # 1. Read voice duration
    # --------------------------------------------------------

    voice_duration = get_duration(VOICE_FILE)

    if voice_duration <= 0:
        raise RuntimeError(
            "Voice duration is invalid."
        )

    print("\n======================================")
    print("VOICE")
    print("======================================")

    print(
        f"Voice duration: {voice_duration:.2f} seconds"
    )

    # --------------------------------------------------------
    # 2. Read script
    # --------------------------------------------------------

    script_file = "output/script.txt"

    if not os.path.exists(script_file):
        raise RuntimeError(
            f"Script not found: {script_file}"
        )

    with open(
        script_file,
        "r",
        encoding="utf-8"
    ) as f:

        script = f.read().strip()

    if not script:
        raise RuntimeError(
            "Script is empty."
        )

    # --------------------------------------------------------
    # 3. Create subtitles
    # --------------------------------------------------------

    create_subtitles(
        script,
        voice_duration
    )

    # --------------------------------------------------------
    # 4. Get at least 5 clips
    # --------------------------------------------------------

    clips = get_video_clips()

    # --------------------------------------------------------
    # 5. Create exactly 5 required segments
    # --------------------------------------------------------

    segment_files = create_segments(
        clips,
        voice_duration
    )

    # --------------------------------------------------------
    # 6. Concatenate all 5 segments
    # --------------------------------------------------------

    concatenate_segments(
        segment_files
    )

    # --------------------------------------------------------
    # 7. Add voice + subtitles + watermark
    # --------------------------------------------------------

    create_final_video()

    # --------------------------------------------------------
    # 8. Verify final output
    # --------------------------------------------------------

    if not os.path.exists(FINAL_VIDEO):
        raise RuntimeError(
            "Final video was not created."
        )

    final_duration = get_duration(
        FINAL_VIDEO
    )

    print("\n======================================")
    print("VIDEO COMPLETE")
    print("======================================")

    print(f"Final video: {FINAL_VIDEO}")
    print(
        f"Final duration: {final_duration:.2f} seconds"
    )

    print(
        f"Footage used: {len(clips)}"
    )

    print("\nSUCCESS")


if __name__ == "__main__":
    main()
