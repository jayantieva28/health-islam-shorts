import os
import csv
import requests
import re
import time

os.makedirs("output", exist_ok=True)

API_KEY = os.environ.get("OPENROUTER_API_KEY")

if not API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY belum tersedia.")

MODEL = "openrouter/free"
TOPICS_FILE = "topics.csv"
MAX_ATTEMPTS = 5
MIN_WORDS = 80
MAX_WORDS = 150


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
# 3. PROMPT UTAMA
# ============================================================

prompt = f"""
Create a 45-60 second YouTube Shorts script in English.

Category:
{selected_category}

Topic:
{selected_topic}

Write a complete spoken narration of approximately 90-120 words.

The narration must directly explain the topic above.

Requirements:
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
- Do NOT output safety classifications.
- Do NOT output "User Safety".
- Do NOT output "safe", "unsafe", "pass", or "fail".
- Do NOT output explanations about these instructions.
- Do NOT output metadata.
"""


# ============================================================
# 4. VALIDASI SCRIPT
# ============================================================

def clean_script(text):
    text = text.strip()

    # Hapus code fence jika AI menggunakannya
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    # Hapus quotation luar jika seluruh output dibungkus quotation
    if len(text) >= 2:
        if (text.startswith('"') and text.endswith('"')) or \
           (text.startswith("'") and text.endswith("'")):
            text = text[1:-1].strip()

    return text.strip()


def validate_script(script):
    if not script:
        return False, "Script kosong."

    lower = script.lower()

    # --------------------------------------------------------
    # Deteksi respons safety/moderation yang salah
    # --------------------------------------------------------

    forbidden_exact = [
        "user safety",
        "assistant safety",
        "safety: safe",
        "safety: unsafe",
        "content safety",
        "safety classification",
        "safe.",
        "unsafe.",
        "pass.",
        "fail."
    ]

    for phrase in forbidden_exact:
        if phrase in lower:
            return False, f"Output mengandung respons safety/meta: {phrase}"

    # --------------------------------------------------------
    # Jumlah kata
    # --------------------------------------------------------

    words = script.split()
    word_count = len(words)

    if word_count < MIN_WORDS:
        return False, f"Terlalu pendek: {word_count} kata."

    if word_count > MAX_WORDS:
        return False, f"Terlalu panjang: {word_count} kata."

    # --------------------------------------------------------
    # Deteksi production notes / heading
    # --------------------------------------------------------

    forbidden_patterns = [
        r"\[scene:",
        r"\[cut to",
        r"\[music",
        r"\[text overlay",
        r"\[camera",
        r"\[visual",
        r"^hook:",
        r"^intro:",
        r"^cta:",
        r"^conclusion:",
        r"^islamic teaching:",
        r"^narrator:",
        r"^speaker:",
    ]

    for pattern in forbidden_patterns:
        if re.search(pattern, lower, re.MULTILINE):
            return False, f"Production note/heading terdeteksi: {pattern}"

    # --------------------------------------------------------
    # Pastikan topik muncul secara bermakna
    # --------------------------------------------------------

    topic_words = [
        word.lower()
        for word in re.findall(r"[A-Za-z]+", selected_topic)
        if len(word) >= 4
    ]

    topic_matches = sum(
        1 for word in topic_words
        if word in lower
    )

    if topic_words and topic_matches == 0:
        return False, "Script tidak terlihat membahas topic yang dipilih."

    return True, f"Valid ({word_count} kata)."


# ============================================================
# 5. GENERATE + RETRY
# ============================================================

url = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

script = None

for attempt in range(1, MAX_ATTEMPTS + 1):

    print("")
    print("======================================")
    print(f"SCRIPT GENERATION ATTEMPT {attempt}/{MAX_ATTEMPTS}")
    print("======================================")

    current_prompt = prompt

    # Pada retry, berikan instruksi tambahan
    if attempt > 1:
        current_prompt += f"""

IMPORTANT RETRY INSTRUCTION:

Your previous response was invalid.

You MUST produce a complete spoken narration about:
{selected_topic}

The previous response failed validation.

This time:
- Write approximately 90-120 spoken words.
- Do not answer with a safety classification.
- Do not say "User Safety".
- Do not discuss these instructions.
- Do not provide metadata.
- Do not provide a refusal.
- Output only the actual narration.
"""

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": current_prompt
            }
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=120
        )

        response.raise_for_status()

        data = response.json()

        choices = data.get("choices", [])

        if not choices:
            raise RuntimeError("AI tidak mengembalikan choices.")

        message = choices[0].get("message", {})
        raw_script = message.get("content", "")

        script = clean_script(raw_script)

        print("Raw output:")
        print(script[:500])

        valid, reason = validate_script(script)

        print("")
        print("VALIDATION RESULT")
        print(f"Valid : {valid}")
        print(f"Reason: {reason}")

        if valid:
            print("")
            print("SCRIPT VALID.")
            break

        print("")
        print("SCRIPT DITOLAK.")
        print("Mencoba generate ulang...")

        script = None

        time.sleep(2)

    except Exception as e:
        print("")
        print(f"Generation error: {e}")

        if attempt == MAX_ATTEMPTS:
            raise RuntimeError(
                f"Gagal membuat script setelah {MAX_ATTEMPTS} percobaan."
            )

        time.sleep(3)


# ============================================================
# 6. JIKA SEMUA RETRY GAGAL
# ============================================================

if not script:
    raise RuntimeError(
        f"AI gagal menghasilkan script valid setelah "
        f"{MAX_ATTEMPTS} percobaan."
    )


# ============================================================
# 7. SIMPAN SCRIPT
# ============================================================

with open("output/script.txt", "w", encoding="utf-8") as f:
    f.write(script)

print("")
print("======================================")
print("SCRIPT BERHASIL DIBUAT")
print("======================================")
print(f"Topic: {selected_topic}")
print(f"Words: {len(script.split())}")
print("Saved: output/script.txt")
print("Saved: output/topic.txt")
