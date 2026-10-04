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
LENGTH_SCALE = 1.08

# Natural pause after each sentence.
SENTENCE_SILENCE = 0.45


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

filter_inputs = []
concat_labels = []

input_index = 0

for i, part in enumerate(parts):

    filter_inputs.append(
        f"[{input_index}:a]"
        f"asetpts=PTS-STARTPTS"
        f"[s{i}]"
    )

    concat_labels.append(
        f"[s{i}]"
    )

    input_index += 1

    if i < len(parts) - 1:

        silence_index = input_index

        # silence input is added later

        filter_inputs.append(
            f"[{silence_index}:a]"
            f"asetpts=PTS-STARTPTS"
            f"[sil{i}]"
        )

        concat_labels.append(
            f"[sil{i}]"
        )

        input_index += 1


# Rebuild input arguments with silence sources.
ffmpeg_inputs = []

for i, part in enumerate(parts):

    ffmpeg_inputs.extend(
        [
            "-i",
            part["path"]
        ]
    )

    if i < len(parts) - 1:

        ffmpeg_inputs.extend(
            [
                "-f",
                "lavfi",
                "-t",
                str(SENTENCE_SILENCE),
                "-i",
                "anullsrc=r=22050:cl=mono"
            ]
        )


concat_filter = (
    "".join(filter_inputs)
    + ""
    + "".join(concat_labels)
    + f"concat=n={len(concat_labels)}:v=0:a=1"
    + "[outa]"
)

final_filter = (
    "".join(filter_inputs)
    + f"{''.join(concat_labels)}"
    + f"concat=n={len(concat_labels)}:v=0:a=1"
    + "[outa]"
)


# Correct the filter because each label needs to be joined.
filter_complex = "".join(filter_inputs)

# Build final concat input labels explicitly.
labels = []

for i in range(len(parts)):

    labels.append(f"[s{i}]")

    if i < len(parts) - 1:
        labels.append(f"[sil{i}]")


filter_complex += (
    "".join(labels)
    + f"concat=n={len(labels)}:v=0:a=1[outa]"
)


print("")
print("Rendering final voice with sentence pauses...")

final_voice_process = subprocess.run(
    [
        "ffmpeg",
        "-y",
        *ffmpeg_inputs,
        "-filter_complex",
        filter_complex,
        "-map",
        "[outa]",
        "-c:a",
        "pcm_s16le",
        VOICE_PATH
    ],
    capture_output=True,
    text=True
)

if final_voice_process.returncode != 0:

    print(final_voice_process.stderr)

    raise RuntimeError(
        "Gagal membuat final voice."
    )


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
# DURATION SAFETY CHECK
# ============================================================

if final_duration < MIN_DURATION:

    raise RuntimeError(
        f"Voice terlalu pendek: "
        f"{final_duration:.2f}s. "
        f"Target minimal {MIN_DURATION}s."
    )

if final_duration > MAX_DURATION:

    raise RuntimeError(
        f"Voice terlalu panjang: "
        f"{final_duration:.2f}s. "
        f"Target maksimal {MAX_DURATION}s."
    )

print("")
print("VOICE V7 SUCCESS")
