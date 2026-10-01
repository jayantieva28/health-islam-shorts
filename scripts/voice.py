import os
import subprocess
import urllib.request

script_path = "output/script.txt"
voice_path = "output/voice.wav"

with open(script_path, "r", encoding="utf-8") as f:
    text = f.read().strip()

if not text:
    raise RuntimeError("Script is empty")

os.makedirs("models", exist_ok=True)

model_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
config_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"

model_path = "models/en_US-lessac-medium.onnx"
config_path = "models/en_US-lessac-medium.onnx.json"

if not os.path.exists(model_path):
    print("Downloading Piper voice model...")
    urllib.request.urlretrieve(model_url, model_path)

if not os.path.exists(config_path):
    print("Downloading voice configuration...")
    urllib.request.urlretrieve(config_url, config_path)

print("Generating voice...")

process = subprocess.run(
    [
        "piper",
        "--model", model_path,
        "--output_file", voice_path
    ],
    input=text,
    text=True,
    capture_output=True
)

if process.returncode != 0:
    print(process.stderr)
    raise RuntimeError("Piper TTS failed")

print("VOICE GENERATED SUCCESSFULLY")
print(voice_path)
