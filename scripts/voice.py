import os
import re
import json
import subprocess
import urllib.request
import wave


# ============================================================
# CONFIG
# ============================================================

SCRIPT_PATH = "output/script.txt"
VOICE_PATH = "output/voice.wav"
TIMING_PATH = "output/voice_timing.json"

MODEL_DIR = "models"

MODEL_URL = (
    "https://huggingface.co/rhasspy/piper-voices/"
    "resolve/main/en/en_US/lessac/medium/"
    "en_US-lessac-medium.onnx"
)

CONFIG_URL = (
    "https://huggingface.co/rhasspy/piper-voices/"
    "resolve/main/en/en_US/lessac/medium/"
    "en_US-lessac-medium.onnx.json"
)

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "en_US-lessac-medium.onnx"
)

CONFIG_PATH = os.path.join(
    MODEL_DIR,
    "en_US-lessac-medium.onnx.json"
)


# ============================================================
# TARGET
# ============================================================

MIN_DURATION = 50.0
MAX_DURATION = 55.0

# Piper:
# > 1.0 = slower
# < 1.0 = faster
#
# 1.08 gives a slightly more relaxed delivery.
LENGTH_SCALE = 1.20

# Natural pause after each sentence.
SENTENCE_SILENCE = 1.0


# ============================================================
# READ SCRIPT
# ============================================================

if not os.path.exists(SCRIPT_PATH):
    raise RuntimeError("output/script.txt tidak ditemukan.")

with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
    text = f.read().strip()

if not text:
    raise RuntimeError("Script kosong.")


# ============================================================
# CLEAN TEXT
# ============================================================

text = re.sub(r"\s+", " ", text).strip()

# Remove accidental markdown
text = text.replace("**", "")
text = text.replace("__", "")

if not text:
    raise RuntimeError("Script kosong setelah cleaning.")


# ============================================================
# SPLIT INTO SENTENCES
# ============================================================

sentences = re.split(
    r"(?<=[.!?])\s+",
    text
)

sentences = [
    s.strip()
    for s in sentences
    if s.strip()
]

if not sentences:
    raise RuntimeError("Tidak dapat menemukan kalimat dalam script.")


print("======================================")
print("VOICE GENERATION V7")
print("======================================")
print(f"Sentences: {len(sentences)}")
print(f"Length scale: {LENGTH_SCALE}")
print(f"Sentence silence: {SENTENCE_SILENCE}")
print("======================================")


# ============================================================
# CREATE MODEL DIRECTORY
# ============================================================

os.makedirs(MODEL_DIR, exist_ok=True)

if not os.path.exists(MODEL_PATH):
    print("Downloading Piper voice model...")
    urllib.request.urlretrieve(
        MODEL_URL,
        MODEL_PATH
    )

if not os.path.exists(CONFIG_PATH):
    print("Downloading Piper voice configuration...")
    urllib.request.urlretrieve(
        CONFIG_URL,
        CONFIG_PATH
    )


# ============================================================
# HELPER: WAV DURATION
# ============================================================

def wav_duration(path):
    with wave.open(path, "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()

    return frames / float(rate)


# ============================================================
# GENERATE EACH SENTENCE
# ============================================================

os.makedirs("output/voice_parts", exist_ok=True)

parts = []

for index, sentence in enumerate(sentences, start=1):

    part_path = (
        f"output/voice_parts/part_{index:03d}.wav"
    )

    print("")
    print(f"Generating sentence {index}/{len(sentences)}")
    print(sentence)

    process = subprocess.run(
        [
            "piper",
            "--model",
            MODEL_PATH,
            "--config",
            CONFIG_PATH,
            "--output_file",
            part_path,
            "--length_scale",
            str(LENGTH_SCALE),
            "--noise_scale",
            "0.667",
            "--noise_w",
            "0.8"
        ],
        input=sentence,
        text=True,
        capture_output=True
    )

    if process.returncode != 0:

        print(process.stderr)

        raise RuntimeError(
            f"Piper gagal pada sentence {index}."
        )

    if not os.path.exists(part_path):
        raise RuntimeError(
            f"Audio sentence {index} tidak dibuat."
        )

    duration = wav_duration(part_path)

    print(
        f"Duration sentence {index}: "
        f"{duration:.3f}s"
    )

    parts.append(
        {
            "index": index,
            "text": sentence,
            "path": part_path,
            "duration": duration
        }
    )


# ============================================================
# CREATE CONCAT LIST
# ============================================================

concat_file = "output/voice_concat.txt"

with open(concat_file, "w", encoding="utf-8") as f:

    for part in parts:

        absolute_path = os.path.abspath(
            part["path"]
        )

        # Escape single quotes for ffmpeg concat file
        escaped = absolute_path.replace(
            "'",
            "'\\''"
        )

        f.write(
            f"file '{escaped}'\n"
        )


# ============================================================
# CONCAT AUDIO
# ============================================================

print("")
print("Combining voice parts...")

concat_process = subprocess.run(
    [
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
        VOICE_PATH
    ],
    capture_output=True,
    text=True
)

if concat_process.returncode != 0:

    print(concat_process.stderr)

    raise RuntimeError(
        "Gagal menggabungkan voice parts."
    )


# ============================================================
# CREATE EXACT SENTENCE TIMING
# ============================================================

current_time = 0.0

timing = []

for i, part in enumerate(parts):

    start = current_time

    end = (
        current_time
        + part["duration"]
    )

    timing.append(
        {
            "index": part["index"],
            "text": part["text"],
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(
                part["duration"],
                3
            )
        }
    )

    current_time = end

    # Add silence between sentences.
    if i < len(parts) - 1:
        current_time += SENTENCE_SILENCE


# ============================================================
# IMPORTANT:
# The actual concatenated WAV currently does not contain
# our artificial sentence silence.
#
# Therefore create final audio using FFmpeg with explicit
# silence between each sentence.
# ============================================================

filter_parts = []

input_args = []

for i, part in enumerate(parts):

    input_args.extend(
        [
            "-i",
            part["path"]
        ]
    )

    filter_parts.append(
        f"[{i}:a]"
        f"apad=pad_dur=0"
        f"[a{i}]"
    )


# Build concat with silence through FFmpeg.
#
# Easier and more reliable approach:
# use individual inputs + anullsrc between them.

# ============================================================
# BUILD FINAL VOICE WITH SENTENCE PAUSES
# ============================================================

ffmpeg_inputs = []
filter_parts = []
concat_labels = []

input_index = 0

for i, part in enumerate(parts):

    # --------------------------------------------------------
    # Add generated sentence audio
    # --------------------------------------------------------

    ffmpeg_inputs.extend([
        "-i",
        part["path"]
    ])

    filter_parts.append(
        f"[{input_index}:a]"
        f"asetpts=PTS-STARTPTS"
        f"[s{i}]"
    )

    concat_labels.append(f"[s{i}]")

    input_index += 1

    # --------------------------------------------------------
    # Add silence AFTER each sentence except the last one
    # --------------------------------------------------------

    if i < len(parts) - 1:

        silence_index = input_index

        ffmpeg_inputs.extend([
            "-f",
            "lavfi",
            "-t",
            str(SENTENCE_SILENCE),
            "-i",
            "anullsrc=r=22050:cl=mono"
        ])

        filter_parts.append(
            f"[{silence_index}:a]"
            f"asetpts=PTS-STARTPTS"
            f"[sil{i}]"
        )

        concat_labels.append(f"[sil{i}]")

        input_index += 1


# ------------------------------------------------------------
# Build concat filter
# ------------------------------------------------------------

filter_complex = (
    ";".join(filter_parts)
    + ";"
    + "".join(concat_labels)
    + f"concat=n={len(concat_labels)}:v=0:a=1"
    + "[outa]"
)


print("")
print("Rendering final voice with sentence pauses...")
print("Sentences:", len(parts))
print("Silence between sentences:", SENTENCE_SILENCE, "seconds")


# ------------------------------------------------------------
# Run FFmpeg
# ------------------------------------------------------------

final_voice_command = [
    "ffmpeg",
    "-y",
    *ffmpeg_inputs,
    "-filter_complex",
    filter_complex,
    "-map",
    "[outa]",
    "-ar",
    "22050",
    "-ac",
    "1",
    "-c:a",
    "pcm_s16le",
    VOICE_PATH
]


print("")
print("FFmpeg command:")
print(" ".join(final_voice_command))
print("")


final_voice_process = subprocess.run(
    final_voice_command,
    capture_output=True,
    text=True
)


if final_voice_process.returncode != 0:

    print("===== FFMPEG ERROR =====")
    print(final_voice_process.stderr)

    raise RuntimeError(
        "Gagal membuat final voice."
    )


print("")
print("FINAL VOICE GENERATED SUCCESSFULLY")
print("Output:", VOICE_PATH)
# ============================================================
# ACTUAL FINAL DURATION
# ============================================================

final_duration = wav_duration(
    VOICE_PATH
)

print("")
print("======================================")
print("VOICE GENERATED")
print("======================================")
print(
    f"Words: {len(text.split())}"
)
print(
    f"Sentences: {len(sentences)}"
)
print(
    f"Duration: {final_duration:.3f} seconds"
)
print(
    f"Output: {VOICE_PATH}"
)


# ============================================================
# SAVE TIMING
# ============================================================

# Recalculate timing using actual final sentence audio
# durations + inserted silences.

current = 0.0

final_timing = []

for i, part in enumerate(parts):

    start = current

    end = (
        start
        + part["duration"]
    )

    final_timing.append(
        {
            "index": part["index"],
            "text": part["text"],
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(
                part["duration"],
                3
            )
        }
    )

    current = end

    if i < len(parts) - 1:
        current += SENTENCE_SILENCE


with open(
    TIMING_PATH,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        {
            "voice_duration": round(
                final_duration,
                3
            ),
            "sentences": final_timing
        },
        f,
        ensure_ascii=False,
        indent=2
    )


print(
    f"Timing: {TIMING_PATH}"
)


# ============================================================
# PAD SILENCE AT END IF VOICE IS TOO SHORT
# ============================================================

if duration < MIN_DURATION:
    silence_needed = MIN_DURATION - duration

    print(
        f"Voice is short by {silence_needed:.2f} seconds."
    )
    print("Adding silence at the end of the voice...")

    padded_voice = VOICE_PATH + ".padded.wav"

    pad_process = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i", VOICE_PATH,
            "-af",
            f"apad=pad_dur={silence_needed:.3f}",
            "-t",
            f"{MIN_DURATION:.3f}",
            "-ar", "22050",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            padded_voice
        ],
        capture_output=True,
        text=True
    )

    if pad_process.returncode != 0:
        print(pad_process.stderr)
        raise RuntimeError("Gagal menambahkan silence di akhir voice.")

    import os
    os.replace(padded_voice, VOICE_PATH)

    duration = MIN_DURATION

    print(
        f"Silence added successfully. Final duration: {duration:.2f}s"
    )


if duration > MAX_DURATION:
    raise RuntimeError(
        f"Voice terlalu panjang: {duration:.2f}s. "
        f"Target maksimal {MAX_DURATION}s."
    )

print("")
print("VOICE V7 SUCCESS")
