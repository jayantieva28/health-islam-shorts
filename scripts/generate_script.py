import os
import csv
import requests

os.makedirs("output", exist_ok=True)

API_KEY = os.environ.get("OPENROUTER_API_KEY")

if not API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY belum tersedia.")

MODEL = "openrouter/free"
TOPICS_FILE = "topics.csv"

# ============================================================
# 1. AMBIL TOPIC READY PERTAMA
# ============================================================

if not os.path.exists(TOPICS_FILE):
    raise RuntimeError("topics.csv tidak ditemukan.")

selected_topic = None
selected_category = None
selected_id = None

with open(TOPICS_FILE, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    for row in reader:
        if row["status"].strip().upper() == "READY":
            selected_id = row["id"]
            selected_category = row["category"]
            selected_topic = row["topic"]
            break

if not selected_topic:
    raise RuntimeError("Tidak ada topic dengan status READY.")

print("======================================")
print("TOPIC TERPILIH")
print("======================================")
print(f"ID       : {selected_id}")
print(f"Category : {selected_category}")
print(f"Topic    : {selected_topic}")
print("======================================")


# ============================================================
# 2. SIMPAN TOPIC
# ============================================================

with open("output/topic.txt", "w", encoding="utf-8") as f:
    f.write(selected_topic)


# ============================================================
# 3. BUAT SCRIPT
# ============================================================

prompt = f"""
Create a 45-60 second YouTube Shorts script in English.

Category:
{selected_category}

Topic:
{selected_topic}

Requirements:
- Write ONLY the spoken narration.
- Start with a strong but accurate hook.
- Give useful, evidence-based information.
- Use cautious scientific wording.
- Do not claim that food cures, treats, or prevents diseases.
- Do not exaggerate health benefits.
- Do not invent scientific facts.
- Do not make unsupported medical claims.
- Do not give dangerous medical advice.
- Do not tell viewers to stop prescribed treatment.
- Distinguish religious information from medical evidence.
- If mentioning Islamic teachings, present them as religious guidance,
  not as scientific proof of a medical effect.
- Give one practical takeaway.
- End with a simple call to action.
- Keep the narration natural for spoken English.

STRICT OUTPUT RULES:
- Output ONLY the words that the narrator should speak.
- Do NOT include scene directions.
- Do NOT include camera directions.
- Do NOT include "[Scene: ...]".
- Do NOT include "[Cut to ...]".
- Do NOT include "[Music ...]".
- Do NOT include "[Text overlay ...]".
- Do NOT include production notes.
- Do NOT include headings such as "Hook", "Intro", "Islamic Teaching", or "CTA".
- Do NOT use Markdown.
- Do NOT use asterisks for emphasis.
- Do NOT use bullet points.
- Do NOT use speaker labels.
- Do NOT include quotation marks around the narration.
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
    raise RuntimeError("AI tidak menghasilkan script.")


# ============================================================
# 4. SIMPAN SCRIPT
# ============================================================

with open("output/script.txt", "w", encoding="utf-8") as f:
    f.write(script)

print("")
print("SCRIPT BERHASIL DIBUAT")
print(f"Topic: {selected_topic}")
print("Saved: output/script.txt")
print("Saved: output/topic.txt")
