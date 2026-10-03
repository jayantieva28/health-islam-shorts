import os
import re
import subprocess
import urllib.request


# ============================================================
# CONFIG
# ============================================================

SCRIPT_PATH = "output/script.txt"
VOICE_PATH = "output/voice.wav"

MODEL_DIR = "models"

MODEL_URL = (
    "https://huggingface.co/rhasspy/"
    "piper-voices/resolve/main/"
    "en/en_US/lessac/medium/"
    "en_US-lessac-medium.onnx"
)

CONFIG_URL = (
    "https://huggingface.co/rhasspy/"
    "piper-voices/resolve/main/"
    "en/en_US/lessac/medium/"
    "en_US-lessac-medium.onnx.json"
)

MODEL_PATH = (
    "models/en_US-lessac-medium.onnx"
)

CONFIG_PATH = (
    "models/en_US-lessac-medium.onnx.json"
)

PARTS_DIR = "output/voice_parts"


# ============================================================
# READ SCRIPT
# ============================================================

if not os.path.exists(SCRIPT_PATH):
    raise RuntimeError(
        f"Script tidak ditemukan: {SCRIPT_PATH}"
    )


with open(
    SCRIPT_PATH,
    "r",
    encoding="utf-8"
) as f:
    text = f.read().strip()


if not text:
    raise RuntimeError(
        "Script kosong."
    )


# Remove accidental production notes
text = re.sub(
    r"\[[^\]]*\]",
    "",
    text
)

text = re.sub(
    r"\*\*",
    "",
    text
)

text = re.sub(
    r"\s+",
    " ",
    text
).strip()


# ============================================================
# SCRIPT INFORMATION
# ============================================================

word_count = len(
    text.split()
)

character_count = len(text)


print(
    "\n======================================"
)

print(
    "PIPER VOICE GENERATOR"
)

print(
    "======================================"
)

print(
    f"Words: {word_count}"
)

print(
    f"Characters: {character_count}"
)

print(
    "\nFull script:"
)

print(text)


# ============================================================
# SPLIT INTO SENTENCES
# ============================================================

# Split after ., ! or ?
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
    raise RuntimeError(
        "Tidak ada kalimat yang berhasil "
        "ditemukan dalam script."
    )


print(
    f"\nSentences detected: {len(sentences)}"
)

for i, sentence in enumerate(
    sentences,
    start=1
):
    print(
        f"{i}. {sentence}"
    )


# ============================================================
# PREPARE DIRECTORIES
# ============================================================

os.makedirs(
    MODEL_DIR,
    exist_ok=True
)

os.makedirs(
    PARTS_DIR,
    exist_ok=True
)


# Remove old voice parts
for filename in os.listdir(PARTS_DIR):

    path = os.path.join(
        PARTS_DIR,
        filename
    )

    if os.path.isfile(path):
        os.remove(path)


# Remove old voice
if os.path.exists(VOICE_PATH):
    os.remove(VOICE_PATH)


# ============================================================
# DOWNLOAD PIPER MODEL
# ============================================================

if not os.path.exists(MODEL_PATH):

    print(
        "\nDownloading Piper voice model..."
    )

    urllib.request.urlretrieve(
        MODEL_URL,
        MODEL_PATH
    )


# ============================================================
# DOWNLOAD CONFIG
# ============================================================

if not os.path.exists(CONFIG_PATH):

    print(
        "Downloading voice configuration..."
    )

    urllib.request.urlretrieve(
        CONFIG_URL,
        CONFIG_PATH
    )


# ============================================================
# GENERATE EACH SENTENCE
# ============================================================

print(
    "\nGenerating voice..."
)

part_files = []


for index, sentence in enumerate(
    sentences,
    start=1
):

    part_path = os.path.join(
        PARTS_DIR,
        f"part_{index:03d}.wav"
    )

    print(
        f"\nGenerating sentence "
        f"{index}/{len(sentences)}"
    )

    print(
        sentence
    )

    process = subprocess.run(
        [
            "piper",
            "--model",
            MODEL_PATH,
            "--output_file",
            part_path
        ],
        input=sentence,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    if process.returncode != 0:

        print(
            process.stderr
        )

        raise RuntimeError(
            f"Piper gagal pada sentence "
            f"{index}."
        )

    if not os.path.exists(
        part_path
    ):
        raise RuntimeError(
            f"Audio part tidak dibuat: "
            f"{part_path}"
        )

    part_files.append(
        part_path
    )


# ============================================================
# CREATE FFMPEG CONCAT LIST
# ============================================================

concat_file = (
    "output/voice_concat.txt"
)

with open(
    concat_file,
    "w",
    encoding="utf-8"
) as f:

    for part in part_files:

        absolute_path = os.path.abspath(
            part
        )

        f.write(
            f"file '{absolute_path}'\n"
        )


# ============================================================
# CONCATENATE ALL VOICE PARTS
# ============================================================

print(
    "\nCombining all voice parts..."
)

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
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)


if concat_process.returncode != 0:

    print(
        concat_process.stdout
    )

    raise RuntimeError(
        "FFmpeg gagal menggabungkan "
        "voice parts."
    )


# ============================================================
# CHECK FINAL VOICE
# ============================================================

if not os.path.exists(
    VOICE_PATH
):

    raise RuntimeError(
        "voice.wav tidak berhasil dibuat."
    )


# Get final duration using ffprobe
probe = subprocess.run(
    [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        VOICE_PATH
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)


if probe.returncode != 0:

    raise RuntimeError(
        "Gagal membaca durasi voice.wav."
    )


try:
    duration = float(
        probe.stdout.strip()
    )
except:
    raise RuntimeError(
        "Durasi voice.wav tidak valid."
    )


# ============================================================
# FINAL VALIDATION
# ============================================================

print(
    "\n======================================"
)

print(
    "VOICE GENERATED SUCCESSFULLY"
)

print(
    f"Words: {word_count}"
)

print(
    f"Sentences: {len(sentences)}"
)

print(
    f"Duration: {duration:.2f} seconds"
)

print(
    f"Output: {VOICE_PATH}"
)

print(
    "======================================"
)


# A Shorts script should not produce an
# extremely short voice file.
if duration < 20:

    raise RuntimeError(
        f"Voice terlalu pendek: "
        f"{duration:.2f} seconds. "
        f"Expected at least 20 seconds."
    )
