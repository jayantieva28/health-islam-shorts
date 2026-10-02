import os
import requests

os.makedirs("output", exist_ok=True)

API_KEY = os.environ.get("OPENROUTER_API_KEY")

if not API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY belum tersedia.")

MODEL = "openrouter/free"

topic = "Benefits of eating oats"

# Simpan topic untuk digunakan oleh video search
with open("output/topic.txt", "w", encoding="utf-8") as f:
    f.write(topic)

prompt = f"""
Create a 45-60 second YouTube Shorts script in English.

Topic:
{topic}

Requirements:
- Strong opening hook.
- Evidence-based nutrition information.
- Use cautious and accurate wording.
- Do not claim that food cures or treats diseases.
- Do not exaggerate health benefits.
- Do not invent scientific facts.
- Do not give dangerous medical advice.
- Do not tell viewers to stop prescribed treatment.
- Give one practical takeaway.
- End with a simple call to action.
- Output ONLY the script.
"""

url = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": MODEL,
    "messages": [
        {
            "role": "user",
            "content": prompt
        }
    ]
}

response = requests.post(
    url,
    headers=headers,
    json=payload,
    timeout=120
)

response.raise_for_status()

data = response.json()

script = data["choices"][0]["message"]["content"].strip()

if not script:
    raise RuntimeError("AI menghasilkan script kosong.")

with open("output/script.txt", "w", encoding="utf-8") as f:
    f.write(script)

print("======================================")
print("SCRIPT BERHASIL DIBUAT")
print(f"Topic: {topic}")
print("Saved: output/script.txt")
print("Saved: output/topic.txt")
print("======================================")
