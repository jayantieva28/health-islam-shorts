import os
import re
import json
import subprocess


OUTPUT_DIR = "output"
CLIPS_DIR = "output/clips"

VOICE_FILE = "output/voice.wav"
VOICE_TIMING_FILE = "output/voice_timing.json"
THUMBNAIL_FILE = "output/thumbnail.jpg"
SCRIPT_FILE = "output/script.txt"

FINAL_VIDEO = "output/short.mp4"

WIDTH = 1080
HEIGHT = 1920
FPS = 30

PHOTO_DURATION = 2.0
TRANSITION = 0.35
MIN_CLIPS = 7

SUBTITLE_FONT = "DejaVu Sans"
SUBTITLE_SIZE = 12
SUBTITLE_MARGIN_V = 70

MIN_SUBTITLE_DURATION = 0.25


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
    except Exception:
        raise RuntimeError(
            f"Durasi tidak valid: {filename}"
        )


def get_voice_duration():
    duration = get_duration(VOICE_FILE)

    print(
        f"\nVoice duration: {duration:.2f} seconds"
    )

    if duration < 50:
        print(
            "WARNING: voice di bawah 50 detik. "
            "Pastikan voice.py sudah memakai V7 timing."
        )

    if duration > 55:
        raise RuntimeError(
            f"Voice terlalu panjang: {duration:.2f}s. "
            "Target V7 adalah 50-55 detik."
        )

    return duration


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

    def sort_key(path):
        name = os.path.basename(path)
        numbers = re.findall(r"\d+", name)

        if numbers:
            return int(numbers[-1])

        return 999999

    clips.sort(key=sort_key)

    print(
        f"\nVideo clips found: {len(clips)}"
    )

    for clip in clips:
        print(" -", clip)

    if len(clips) < MIN_CLIPS:
        raise RuntimeError(
            f"Minimal {MIN_CLIPS} video diperlukan. "
            f"Hanya ditemukan {len(clips)}."
        )

    return clips


def format_srt_time(seconds):
    milliseconds = int(
        round(
            (seconds - int(seconds)) * 1000
        )
    )

    if milliseconds >= 1000:
        seconds = float(int(seconds) + 1)
        milliseconds = 0

    total_seconds = int(seconds)

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d},"
        f"{milliseconds:03d}"
    )


def load_voice_timing():

    if not os.path.exists(VOICE_TIMING_FILE):
        print(
            "\nvoice_timing.json not found."
        )
        print(
            "Using fallback proportional subtitle timing."
        )
        return None

    try:
        with open(
            VOICE_TIMING_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

    except Exception as e:
        print(
            f"\nWARNING: gagal membaca "
            f"{VOICE_TIMING_FILE}: {e}"
        )
        return None

    if isinstance(data, list):
        entries = data

    elif isinstance(data, dict):
        entries = (
            data.get("sentences")
            or data.get("timings")
            or data.get("segments")
        )

    else:
        entries = None

    if not isinstance(entries, list):
        print(
            "\nWARNING: format voice_timing.json "
            "tidak dikenali."
        )
        return None

    clean = []

    for item in entries:

        if not isinstance(item, dict):
            continue

        text = (
            item.get("text")
            or item.get("sentence")
            or item.get("content")
            or ""
        )

        start = item.get(
            "start",
            item.get("start_time")
        )

        end = item.get(
            "end",
            item.get("end_time")
        )

        duration = item.get("duration")

        try:
            start = float(start)
        except Exception:
            continue

        if end is None and duration is not None:
            try:
                end = start + float(duration)
            except Exception:
                continue

        try:
            end = float(end)
        except Exception:
            continue

        text = str(text).strip()

        if not text or end <= start:
            continue

        clean.append({
            "text": text,
            "start": start,
            "end": end
        })

    if not clean:
        print(
            "\nWARNING: tidak ada timing valid."
        )
        return None

    print(
        f"\nVoice timing loaded: "
        f"{len(clean)} sentence segments"
    )

    return clean


def create_subtitles(voice_duration):

    if not os.path.exists(SCRIPT_FILE):
        raise RuntimeError(
            "script.txt tidak ditemukan."
        )

    with open(
        SCRIPT_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        script = f.read().strip()

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

    if not script:
        raise RuntimeError(
            "Script kosong."
        )

    timing = load_voice_timing()

    subtitle_file = "output/subtitles.srt"

    if timing:

        entries = []

        for segment in timing:

            sentence = segment["text"].strip()

            sentence = re.sub(
                r"\*\*",
                "",
                sentence
            )

            words = sentence.split()

            if not words:
                continue

            sentence_start = max(
                0.0,
                segment["start"]
            )

            sentence_end = min(
                voice_duration,
                segment["end"]
            )

            if sentence_end <= sentence_start:
                continue

            sentence_duration = (
                sentence_end -
                sentence_start
            )

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

            total_words = len(words)
            word_cursor = 0

            for chunk in chunks:

                chunk_words = len(
                    chunk.split()
                )

                start_ratio = (
                    word_cursor /
                    total_words
                )

                end_ratio = (
                    (word_cursor + chunk_words) /
                    total_words
                )

                start = (
                    sentence_start +
                    sentence_duration *
                    start_ratio
                )

                end = (
                    sentence_start +
                    sentence_duration *
                    end_ratio
                )

                if (
                    end - start
                    < MIN_SUBTITLE_DURATION
                ):
                    end = min(
                        sentence_end,
                        start +
                        MIN_SUBTITLE_DURATION
                    )

                entries.append({
                    "text": chunk,
                    "start": start,
                    "end": end
                })

                word_cursor += chunk_words

        if not entries:
            raise RuntimeError(
                "Voice timing tersedia tetapi "
                "subtitle tidak dapat dibuat."
            )

        print(
            "\nSubtitle mode: VOICE TIMING"
        )

    else:

        words = script.split()

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

        total_words = len(words)

        entries = []

        word_cursor = 0

        for chunk in chunks:

            chunk_words = len(
                chunk.split()
            )

            start = (
                voice_duration *
                word_cursor /
                total_words
            )

            end = (
                voice_duration *
                (word_cursor + chunk_words) /
                total_words
            )

            entries.append({
                "text": chunk,
                "start": start,
                "end": end
            })

            word_cursor += chunk_words

        print(
            "\nSubtitle mode: FALLBACK"
        )

    cleaned_entries = []

    previous_end = 0.0

    for entry in entries:

        start = max(
            previous_end,
            min(
                voice_duration,
                entry["start"]
            )
        )

        end = max(
            start,
            min(
                voice_duration,
                entry["end"]
            )
        )

        if end > start:

            cleaned_entries.append({
                "text": entry["text"],
                "start": start,
                "end": end
            })

            previous_end = end

    if not cleaned_entries:
        raise RuntimeError(
            "Tidak ada subtitle timing yang valid."
        )

    with open(
        subtitle_file,
        "w",
        encoding="utf-8"
    ) as f:

        for index, entry in enumerate(
            cleaned_entries,
            start=1
        ):

            f.write(
                f"{index}\n"
            )

            f.write(
                f"{format_srt_time(entry['start'])} --> "
                f"{format_srt_time(entry['end'])}\n"
            )

            f.write(
                f"{entry['text']}\n\n"
            )

    print(
        f"\nSubtitles created: "
        f"{subtitle_file}"
    )

    print(
        f"Subtitle chunks: "
        f"{len(cleaned_entries)}"
    )

    return subtitle_file


def detect_cta():

    if not os.path.exists(SCRIPT_FILE):
        return []

    with open(
        SCRIPT_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        script = f.read().lower()

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

    if not cta_items:
        cta_items = [
            "SUBSCRIBE"
        ]

    print(
        "\nDetected CTA:",
        " • ".join(cta_items)
    )

    return cta_items


def prepare_directories():

    os.makedirs(
        "output/segments",
        exist_ok=True
    )

    for filename in os.listdir(
        "output/segments"
    ):

        path = os.path.join(
            "output/segments",
            filename
        )

        if os.path.isfile(path):
            os.remove(path)


def create_photo_segment():

    output = (
        "output/segments/segment_00.mp4"
    )

    print(
        "\nCreating opening photo..."
    )

    vf = (
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
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


def create_video_segments(
    clips,
    voice_duration
):

    available_duration = (
        voice_duration -
        PHOTO_DURATION
    )

    if available_duration <= 5:
        raise RuntimeError(
            "Voice terlalu pendek."
        )

    durations = []

    for clip in clips:

        duration = get_duration(
            clip
        )

        if duration <= 0.05:
            raise RuntimeError(
                f"Clip tidak valid atau "
                f"terlalu pendek: {clip}"
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

    if total_source_duration < available_duration:

        raise RuntimeError(
            "\nFOOTAGE TIDAK CUKUP.\n"
            f"Original footage: "
            f"{total_source_duration:.2f}s\n"
            f"Required: "
            f"{available_duration:.2f}s\n\n"
            "V7 tidak akan mempercepat, "
            "memperlambat, atau mengulang video.\n"
            "Download additional clips "
            "and run again."
        )

    target_durations = []

    for duration in durations:

        target = (
            available_duration *
            duration /
            total_source_duration
        )

        target_durations.append(
            target
        )

    difference = (
        available_duration -
        sum(target_durations)
    )

    target_durations[-1] += difference

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

        print(
            "\n--------------------------------"
        )

        print(
            f"Preparing clip {index}"
        )

        print(
            f"Source: "
            f"{source_duration:.2f}s"
        )

        print(
            f"Target: "
            f"{target_duration:.2f}s"
        )

        print(
            "Playback speed: 1.000x"
        )

        print(
            "Action: TRIM ONLY"
        )

        scale_crop = (
            "scale=1080:1920:"
            "force_original_aspect_ratio=increase,"
            "crop=1080:1920"
        )

        if index == 1:

            fade = (
                "fade=t=in:"
                f"st=0:"
                f"d={TRANSITION}"
            )

        else:

            fade = "null"

        vf = (
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

    visual_duration = get_duration(
        visual_video
    )

    print(
        f"\nVisual duration: "
        f"{visual_duration:.3f}s"
    )

    return visual_video


def create_final_video(
    visual_video,
    subtitle_file,
    voice_duration,
    cta_items
):

    print(
        "\nCreating final Shorts video..."
    )

    cta_text = " • ".join(
        cta_items
    )

    cta_text = (
        cta_text
        .replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
    )

    cta_start = max(
        0,
        voice_duration - 2.8
    )

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
        f"enable='between(t\\,"
        f"{cta_start:.3f}\\,"
        f"{voice_duration:.3f})':"
        f"alpha='if(lt(t\\,"
        f"{cta_start:.3f})\\,0\\,"
        f"if(lt(t\\,"
        f"{cta_start + 0.5:.3f})\\,"
        f"(t-{cta_start:.3f})/0.5\\,"
        f"if(gt(t\\,"
        f"{voice_duration - 0.5:.3f})\\,"
        f"({voice_duration:.3f}-t)/0.5\\,1)))'"
    )

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
        f"Duration: "
        f"{voice_duration:.2f}s"
    )

    print(
        "======================================"
    )


def main():

    print(
        "\n======================================"
    )

    print(
        "TAYYIB HEALTH NOTES"
    )

    print(
        "V7 VIDEO ASSEMBLER"
    )

    print(
        "======================================"
    )

    required_files = [
        VOICE_FILE,
        THUMBNAIL_FILE,
        SCRIPT_FILE
    ]

    for filename in required_files:

        if not os.path.exists(filename):

            raise RuntimeError(
                f"File tidak ditemukan: "
                f"{filename}"
            )

    prepare_directories()

    voice_duration = (
        get_voice_duration()
    )

    clips = get_clips()

    subtitle_file = create_subtitles(
        voice_duration
    )

    cta_items = detect_cta()

    photo_segment = (
        create_photo_segment()
    )

    video_segments = (
        create_video_segments(
            clips,
            voice_duration
        )
    )

    visual_video = (
        concatenate_segments(
            photo_segment,
            video_segments
        )
    )

    create_final_video(
        visual_video,
        subtitle_file,
        voice_duration,
        cta_items
    )


if __name__ == "__main__":
    main()
