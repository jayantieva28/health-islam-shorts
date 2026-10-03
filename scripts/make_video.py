import os
import re
import subprocess
import math


# ============================================================
# CONFIG
# ============================================================

OUTPUT_DIR = "output"
CLIPS_DIR = "output/clips"

VOICE_FILE = "output/voice.wav"
THUMBNAIL_FILE = "output/thumbnail.jpg"
SCRIPT_FILE = "output/script.txt"

FINAL_VIDEO = "output/short.mp4"

WIDTH = 1080
HEIGHT = 1920
FPS = 30

# Opening photo duration
PHOTO_DURATION = 2.0

# Transition duration
TRANSITION = 0.35

# Minimum number of clips required
MIN_CLIPS = 7

# Subtitle settings
SUBTITLE_FONT = "DejaVu Sans"
SUBTITLE_SIZE = 12
SUBTITLE_MARGIN_V = 70


# ============================================================
# RUN COMMAND
# ============================================================

def run(cmd):

    print("\nRUNNING:")
    print(" ".join(str(x) for x in cmd))

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    print(result.stdout)

    if result.returncode != 0:
        raise RuntimeError(
            "Command gagal:\n" +
            " ".join(str(x) for x in cmd)
        )


# ============================================================
# GET MEDIA DURATION
# ============================================================

def get_duration(filename):

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        filename
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Gagal membaca durasi: {filename}"
        )

    try:
        return float(result.stdout.strip())
    except:
        raise RuntimeError(
            f"Durasi tidak valid: {filename}"
        )


# ============================================================
# GET VOICE DURATION
# ============================================================

def get_voice_duration():

    duration = get_duration(
        VOICE_FILE
    )

    print(
        f"\nVoice duration: {duration:.2f} seconds"
    )

    return duration


# ============================================================
# FIND ALL VIDEO CLIPS
# ============================================================

def get_clips():

    if not os.path.isdir(CLIPS_DIR):
        raise RuntimeError(
            f"Folder tidak ditemukan: {CLIPS_DIR}"
        )

    clips = []

    for filename in os.listdir(CLIPS_DIR):

        if filename.lower().endswith(".mp4"):

            clips.append(
                os.path.join(
                    CLIPS_DIR,
                    filename
                )
            )

    # Natural sorting: clip_01, clip_02, ...
    def sort_key(path):

        name = os.path.basename(path)

        numbers = re.findall(
            r"\d+",
            name
        )

        if numbers:
            return int(numbers[-1])

        return 999999

    clips.sort(
        key=sort_key
    )

    print(
        f"\nVideo clips found: {len(clips)}"
    )

    for clip in clips:
        print(
            " -",
            clip
        )

    if len(clips) < MIN_CLIPS:

        raise RuntimeError(
            f"Minimal {MIN_CLIPS} video diperlukan. "
            f"Hanya ditemukan {len(clips)}."
        )

    return clips


# ============================================================
# CREATE SUBTITLE FILE
# ============================================================

def format_srt_time(seconds):

    milliseconds = int(
        round(
            (seconds - int(seconds)) * 1000
        )
    )

    total_seconds = int(seconds)

    hours = total_seconds // 3600

    minutes = (
        total_seconds % 3600
    ) // 60

    secs = total_seconds % 60

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d},"
        f"{milliseconds:03d}"
    )


def create_subtitles(
    voice_duration
):

    if not os.path.exists(
        SCRIPT_FILE
    ):
        raise RuntimeError(
            "script.txt tidak ditemukan."
        )

    with open(
        SCRIPT_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        script = f.read().strip()

    # Remove accidental production notes
    script = re.sub(
        r"\[[^\]]*\]",
        "",
        script
    )

    script = re.sub(
        r"\*\*",
        "",
        script
    )

    script = re.sub(
        r"\s+",
        " ",
        script
    ).strip()

    words = script.split()

    # EXACTLY 5 WORDS PER SUBTITLE CHUNK
    chunks = []

    for i in range(
        0,
        len(words),
        5
    ):

        chunk = " ".join(
            words[i:i + 5]
        ).strip()

        if chunk:
            chunks.append(chunk)

    if not chunks:
        raise RuntimeError(
            "Tidak ada teks untuk subtitle."
        )

    subtitle_file = (
        "output/subtitles.srt"
    )

    # Divide subtitle timing across voice.
    chunk_duration = (
        voice_duration /
        len(chunks)
    )

    with open(
        subtitle_file,
        "w",
        encoding="utf-8"
    ) as f:

        for index, chunk in enumerate(
            chunks,
            start=1
        ):

            start = (
                (index - 1)
                * chunk_duration
            )

            end = (
                index
                * chunk_duration
            )

            # Prevent final subtitle
            # from exceeding voice duration.
            end = min(
                end,
                voice_duration
            )

            f.write(
                f"{index}\n"
            )

            f.write(
                f"{format_srt_time(start)} --> "
                f"{format_srt_time(end)}\n"
            )

            f.write(
                f"{chunk}\n\n"
            )

    print(
        f"\nSubtitles created: "
        f"{subtitle_file}"
    )

    print(
        f"Subtitle chunks: {len(chunks)}"
    )

    return subtitle_file


# ============================================================
# DETECT FINAL CTA
# ============================================================

def detect_cta():

    if not os.path.exists(
        SCRIPT_FILE
    ):
        return []

    with open(
        SCRIPT_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        script = f.read().lower()

    # Focus on the ending of the script.
    words = script[-500:]

    cta_items = []

    if "subscribe" in words:
        cta_items.append(
            "SUBSCRIBE"
        )

    if "like" in words:
        cta_items.append(
            "LIKE"
        )

    if "share" in words:
        cta_items.append(
            "SHARE"
        )

    if "follow" in words:
        cta_items.append(
            "FOLLOW"
        )

    # Avoid showing unrelated CTA.
    if not cta_items:
        cta_items = [
            "SUBSCRIBE"
        ]

    print(
        "\nDetected CTA:",
        " • ".join(cta_items)
    )

    return cta_items


# ============================================================
# PREPARE WORKING DIRECTORIES
# ============================================================

def prepare_directories():

    os.makedirs(
        "output/segments",
        exist_ok=True
    )

    # Remove old generated segments.
    for filename in os.listdir(
        "output/segments"
    ):

        path = os.path.join(
            "output/segments",
            filename
        )

        if os.path.isfile(path):
            os.remove(path)


# ============================================================
# CREATE OPENING PHOTO
# ============================================================

def create_photo_segment():

    output = (
        "output/segments/segment_00.mp4"
    )

    print(
        "\nCreating opening photo..."
    )

    # Slight zoom effect.
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "zoompan="
        "z='min(zoom+0.0008,1.08)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        "d=1:"
        "s=1080x1920:"
        "fps=30,"
        "fade=t=out:st=1.65:d=0.35"
    )

    run([
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        THUMBNAIL_FILE,
        "-t",
        str(PHOTO_DURATION),
        "-vf",
        vf,
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        output
    ])

    return output


# ============================================================
# CREATE VIDEO SEGMENTS
# ============================================================

def create_video_segments(
    clips,
    voice_duration
):

    # Time available after opening photo.
    available_duration = (
        voice_duration -
        PHOTO_DURATION
    )

    if available_duration <= 5:
        raise RuntimeError(
            "Voice terlalu pendek."
        )

    # Get original durations.
    durations = []

    for clip in clips:

        duration = get_duration(
            clip
        )

        durations.append(
            duration
        )

        print(
            f"\n{os.path.basename(clip)} "
            f"duration = {duration:.2f}s"
        )

    total_source_duration = sum(
        durations
    )

    print(
        "\nTotal original video duration:",
        f"{total_source_duration:.2f}s"
    )

    print(
        "Required video duration:",
        f"{available_duration:.2f}s"
    )

    # --------------------------------------------------------
    # Allocate duration proportionally.
    #
    # This ensures ALL downloaded videos are used.
    # --------------------------------------------------------

    target_durations = []

    for duration in durations:

        target = (
            available_duration
            * duration
            / total_source_duration
        )

        target_durations.append(
            target
        )

    segment_files = []

    for index, (
        clip,
        source_duration,
        target_duration
    ) in enumerate(
        zip(
            clips,
            durations,
            target_durations
        ),
        start=1
    ):

        output = (
            f"output/segments/"
            f"segment_{index:02d}.mp4"
        )

        print("\n--------------------------------")
        print(
            f"Preparing clip {index}"
        )

        print(
            f"Source: {source_duration:.2f}s"
        )

        print(
            f"Target: {target_duration:.2f}s"
        )

        # Speed factor:
        #
        # If target is longer:
        # video is slowed down.
        #
        # If target is shorter:
        # video is trimmed.
        speed_factor = (
            target_duration /
            source_duration
        )

        print(
            f"Speed factor: "
            f"{speed_factor:.3f}"
        )

        # Slight slowdown / speed adjustment.
        setpts = (
            f"setpts={speed_factor:.8f}*PTS"
        )

        # Crop/fill vertical 1080x1920.
        scale_crop = (
            "scale=1080:1920:"
            "force_original_aspect_ratio=increase,"
            "crop=1080:1920"
        )

        # Fade first video in.
        if index == 1:

            fade = (
                "fade=t=in:"
                f"st=0:"
                f"d={TRANSITION}"
            )

        else:

            fade = "null"

        vf = (
            f"{setpts},"
            f"{scale_crop},"
            f"{fade},"
            "fps=30,"
            "format=yuv420p"
        )

        run([
            "ffmpeg",
            "-y",
            "-i",
            clip,
            "-vf",
            vf,
            "-t",
            f"{target_duration:.3f}",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            output
        ])

        segment_files.append(
            output
        )

    return segment_files


# ============================================================
# CONCATENATE VISUAL SEGMENTS
# ============================================================

def concatenate_segments(
    photo_segment,
    video_segments
):

    all_segments = [
        photo_segment
    ] + video_segments

    concat_file = (
        "output/segments/concat.txt"
    )

    with open(
        concat_file,
        "w",
        encoding="utf-8"
    ) as f:

        for segment in all_segments:

            absolute_path = os.path.abspath(
                segment
            )

            f.write(
                f"file '{absolute_path}'\n"
            )

    visual_video = (
        "output/visual.mp4"
    )

    print(
        "\nConcatenating all visual segments..."
    )

    run([
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        concat_file,
        "-c",
        "copy",
        visual_video
    ])

    return visual_video


# ============================================================
# FINAL VIDEO
# ============================================================

def create_final_video(
    visual_video,
    subtitle_file,
    voice_duration,
    cta_items
):

    print(
        "\nCreating final Shorts video..."
    )

    # --------------------------------------------------------
    # CTA TEXT
    # --------------------------------------------------------

    cta_text = " • ".join(
        cta_items
    )

    # Escape characters for drawtext.
    cta_text = (
        cta_text
        .replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
    )

    # CTA appears during final 2.8 seconds.
    cta_start = max(
        0,
        voice_duration - 2.8
    )

    # Fade in/out.
    cta_duration = 2.8

    cta_filter = (
        "drawtext="
        "fontfile=/usr/share/fonts/truetype/dejavu/"
        "DejaVuSans-Bold.ttf:"
        f"text='{cta_text}':"
        "fontcolor=white:"
        "fontsize=58:"
        "borderw=4:"
        "bordercolor=black:"
        "x=(w-text_w)/2:"
        "y=h*0.82:"
        f"enable='between(t,{cta_start:.3f},{voice_duration:.3f})':"
        "alpha="
        f"if(lt(t,{cta_start:.3f}),0,"
        f"if(lt(t,{cta_start + 0.5:.3f}),"
        f"(t-{cta_start:.3f})/0.5,"
        f"if(gt(t,{voice_duration - 0.5:.3f}),"
        f"({voice_duration:.3f}-t)/0.5,1)))"
    )

    # --------------------------------------------------------
    # WATERMARK
    # --------------------------------------------------------

    watermark_filter = (
        "drawtext="
        "fontfile=/usr/share/fonts/truetype/dejavu/"
        "DejaVuSans.ttf:"
        "text='Tayyib Health Notes':"
        "fontcolor=white@0.75:"
        "fontsize=27:"
        "borderw=2:"
        "bordercolor=black@0.5:"
        "x=45:"
        "y=55"
    )

    # --------------------------------------------------------
    # SUBTITLE
    #
    # DO NOT CHANGE:
    # FontSize 12
    # MarginV 70
    # 5 words per chunk
    # --------------------------------------------------------

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

    vf = (
        f"{watermark_filter},"
        f"{cta_filter},"
        f"{subtitle_filter}"
    )

    run([
        "ffmpeg",
        "-y",
        "-i",
        visual_video,
        "-i",
        VOICE_FILE,
        "-t",
        f"{voice_duration:.3f}",
        "-vf",
        vf,
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "22",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ar",
        "44100",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        FINAL_VIDEO
    ])

    print(
        "\n======================================"
    )

    print(
        "FINAL VIDEO CREATED"
    )

    print(
        f"Output: {FINAL_VIDEO}"
    )

    print(
        f"Duration: {voice_duration:.2f}s"
    )

    print(
        "======================================"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n======================================"
    )

    print(
        "TAYYIB HEALTH NOTES"
    )

    print(
        "V6-B VIDEO ASSEMBLER"
    )

    print(
        "======================================"
    )

    # --------------------------------------------------------
    # CHECK FILES
    # --------------------------------------------------------

    required_files = [
        VOICE_FILE,
        THUMBNAIL_FILE,
        SCRIPT_FILE
    ]

    for filename in required_files:

        if not os.path.exists(filename):

            raise RuntimeError(
                f"File tidak ditemukan: {filename}"
            )

    # --------------------------------------------------------
    # PREPARE
    # --------------------------------------------------------

    prepare_directories()

    # --------------------------------------------------------
    # VOICE
    # --------------------------------------------------------

    voice_duration = (
        get_voice_duration()
    )

    # --------------------------------------------------------
    # CLIPS
    # --------------------------------------------------------

    clips = get_clips()

    # --------------------------------------------------------
    # SUBTITLES
    # --------------------------------------------------------

    subtitle_file = create_subtitles(
        voice_duration
    )

    # --------------------------------------------------------
    # CTA
    # --------------------------------------------------------

    cta_items = detect_cta()

    # --------------------------------------------------------
    # PHOTO
    # --------------------------------------------------------

    photo_segment = (
        create_photo_segment()
    )

    # --------------------------------------------------------
    # VIDEOS
    # --------------------------------------------------------

    video_segments = (
        create_video_segments(
            clips,
            voice_duration
        )
    )

    # --------------------------------------------------------
    # CONCAT
    # --------------------------------------------------------

    visual_video = (
        concatenate_segments(
            photo_segment,
            video_segments
        )
    )

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    create_final_video(
        visual_video,
        subtitle_file,
        voice_duration,
        cta_items
    )


if __name__ == "__main__":
    main()
