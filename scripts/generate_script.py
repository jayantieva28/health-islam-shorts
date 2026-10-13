
import os
import csv
import json
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
MIN_WORDS = 100
MAX_WORDS = 125
NEW_TOPICS_BATCH = 12

CATEGORIES = [
    "Healthy Food",
    "Natural Foods",
    "Islamic Lifestyle",
]

API_URL = "https://openrouter.ai/api/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def normalize_topic(topic):
    return re.sub(r"[^a-z0-9]+", " ", topic.lower()).strip()


def read_topics():
    if not os.path.exists(TOPICS_FILE):
        raise RuntimeError("topics.csv tidak ditemukan.")

    with open(TOPICS_FILE, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"id", "category", "topic", "status"}

        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise RuntimeError(
                "Header topics.csv harus memiliki kolom: "
                "id, category, topic, status."
            )

        rows = []
        for row in reader:
            if not row.get("id") or not row.get("topic"):
                continue
            rows.append({
                "id": row["id"].strip(),
                "category": row["category"].strip(),
                "topic": row["topic"].strip(),
                "status": row["status"].strip().upper(),
            })

    return rows


def save_topics(rows):
    temp_file = TOPICS_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["id", "category", "topic", "status"],
        )
        writer.writeheader()
        writer.writerows(rows)

    os.replace(temp_file, TOPICS_FILE)


def request_ai(prompt, max_tokens=1800):
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You create original, responsible health education "
                    "topics and scripts. Follow the requested output format."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": max_tokens,
    }

    response = requests.post(
        API_URL,
        headers=HEADERS,
        json=payload,
        timeout=120,
    )
    response.raise_for_status()

    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError("AI tidak mengembalikan choices.")

    content = choices[0].get("message", {}).get("content", "")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("AI mengembalikan respons kosong.")

    return content.strip()


def extract_json(text):
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.I)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])

        start = text.find("[")
        end = text.rfind("]")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])

        raise ValueError("Respons AI bukan JSON yang valid.")


def generate_new_topics(existing_rows):
    print("Tidak ada topik READY. Membuat topik baru...")

    existing = {
        normalize_topic(row["topic"])
        for row in existing_rows
    }

    existing_list = "\n".join(
        f"- {row['topic']}" for row in existing_rows
    )

    prompt = f"""
Create exactly {NEW_TOPICS_BATCH} new topics for an English-language
YouTube Shorts channel called Tayyib Health Notes.

Use ONLY these categories:
- Healthy Food
- Natural Foods
- Islamic Lifestyle

Existing topics that must not be repeated:
{existing_list}

Requirements:
- Every topic must be meaningfully different from existing topics.
- Use specific, useful educational topics suitable for 45-60 second videos.
- Keep topics concise and natural in English.
- Health and nutrition topics must allow cautious, evidence-based discussion.
- Do not promise cures or unsupported medical benefits.
- Islamic Lifestyle topics must respect Islamic teachings and avoid
  inventing religious quotations or attributions.
- Distribute topics across the three categories where practical.
- Return ONLY a JSON array of objects in this exact shape:
[
  {{"category": "Healthy Food", "topic": "Example topic"}}
]
"""

    raw = request_ai(prompt, max_tokens=1800)
    result = extract_json(raw)

    if isinstance(result, dict):
        result = result.get("topics", [])

    if not isinstance(result, list):
        raise RuntimeError("AI tidak mengembalikan daftar topik.")

    new_rows = []
    seen = set(existing)

    max_id = max(
        (int(row["id"]) for row in existing_rows if row["id"].isdigit()),
        default=0,
    )

    for item in result:
        if not isinstance(item, dict):
            continue

        category = str(item.get("category", "")).strip()
        topic = str(item.get("topic", "")).strip()
        key = normalize_topic(topic)

        if category not in CATEGORIES or not topic:
            continue
        if len(topic) > 120 or len(topic.split()) < 3:
            continue
        if key in seen:
            continue

        seen.add(key)
        max_id += 1
        new_rows.append({
            "id": str(max_id),
            "category": category,
            "topic": topic,
            "status": "READY",
        })

        if len(new_rows) >= NEW_TOPICS_BATCH:
            break

    if not new_rows:
        raise RuntimeError(
            "AI tidak menghasilkan topik baru yang valid dan unik. "
            "topics.csv tidak diubah."
        )

    # Baca ulang sebelum menyimpan untuk mengurangi risiko menimpa
    # perubahan daftar topik yang terjadi selama permintaan AI.
    latest_rows = read_topics()
    latest_keys = {
        normalize_topic(row["topic"]) for row in latest_rows
    }

    final_rows = []
    for row in new_rows:
        if normalize_topic(row["topic"]) not in latest_keys:
            final_rows.append(row)
            latest_keys.add(normalize_topic(row["topic"]))

    if not final_rows:
        raise RuntimeError(
            "Topik yang dibuat ternyata sudah ada. "
            "Silakan jalankan workflow lagi."
        )

    save_topics(latest_rows + final_rows)

    print(f"Berhasil menambahkan {len(final_rows)} topik baru:")
    for row in final_rows:
        print(f"  {row['category']}: {row['topic']}")

    return read_topics()


def select_topic():
    rows = read_topics()
    ready = [row for row in rows if row["status"] == "READY"]

    if not ready:
        rows = generate_new_topics(rows)
        ready = [row for row in rows if row["status"] == "READY"]

    if not ready:
        raise RuntimeError(
            "Tidak ada topik READY setelah pembuatan topik baru."
        )

    selected = ready[0]

    print("======================================")
    print("TOPIC TERPILIH")
    print("======================================")
    print(f"ID       : {selected['id']}")
    print(f"Category : {selected['category']}")
    print(f"Topic    : {selected['topic']}")
    print("======================================")

    return selected


selected = select_topic()
selected_id = selected["id"]
selected_category = selected["category"]
selected_topic = selected["topic"]

with open("output/topic.txt", "w", encoding="utf-8") as f:
    f.write(selected_topic)


prompt = f"""
Create a 45-60 second YouTube Shorts script in English.

Category:
{selected_category}

Topic:
{selected_topic}

Write a complete spoken narration of approximately 105-120 words.

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
- Output ONLY the words the narrator should speak.
- Do NOT include scene, camera, music, or production directions.
- Do NOT include headings, Markdown, bullet points, or speaker labels.
- Do NOT include quotation marks around the narration.
- Do NOT output safety classifications or metadata.
- Do NOT output "User Safety", "safe", "unsafe", "pass", or "fail".
- Do NOT explain these instructions.
"""


def clean_script(text):
    text = text.strip()
    text = re.sub(
        r"^```[a-zA-Z]*\s*",
        "",
        text,
    )
    text = re.sub(r"\s*```$", "", text)

    if len(text) >= 2:
        if (
            (text.startswith('"') and text.endswith('"'))
            or (text.startswith("'") and text.endswith("'"))
        ):
            text = text[1:-1].strip()

    return text.strip()


def validate_script(script):
    if not script:
        return False, "Script kosong."

    lower = script.lower()

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
        "fail.",
    ]

    for phrase in forbidden_exact:
        if phrase in lower:
            return False, f"Output mengandung respons safety/meta: {phrase}"

    word_count = len(script.split())

    if word_count < MIN_WORDS:
        return False, f"Terlalu pendek: {word_count} kata."

    if word_count > MAX_WORDS:
        return False, f"Terlalu panjang: {word_count} kata."

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

    topic_words = [
        word.lower()
        for word in re.findall(r"[A-Za-z]+", selected_topic)
        if len(word) >= 4
    ]

    topic_matches = sum(
        1 for word in topic_words if word in lower
    )

    if topic_words and topic_matches == 0:
        return False, "Script tidak terlihat membahas topik yang dipilih."

    return True, f"Valid ({word_count} kata)."


script = None

for attempt in range(1, MAX_ATTEMPTS + 1):
    print("")
    print("======================================")
    print(f"SCRIPT GENERATION ATTEMPT {attempt}/{MAX_ATTEMPTS}")
    print("======================================")

    current_prompt = prompt

    if attempt > 1:
        current_prompt += f"""

IMPORTANT RETRY INSTRUCTION:
Your previous response was invalid.

Write a complete spoken narration about:
{selected_topic}

- Write approximately 100-125 spoken words.
- Do not answer with a safety classification.
- Do not discuss these instructions.
- Do not provide metadata or a refusal.
- Output only the actual narration.
"""

    try:
        raw_script = request_ai(current_prompt, max_tokens=1200)
        candidate = clean_script(raw_script)

        print("Raw output:")
        print(candidate[:500])

        valid, reason = validate_script(candidate)

        print("")
        print("VALIDATION RESULT")
        print(f"Valid : {valid}")
        print(f"Reason: {reason}")

        if valid:
            script = candidate
            print("SCRIPT VALID.")
            break

        print("SCRIPT DITOLAK. Mencoba generate ulang...")
        time.sleep(2)

    except Exception as exc:
        print(f"Generation error: {type(exc).__name__}: {exc}")

        if attempt == MAX_ATTEMPTS:
            raise RuntimeError(
                f"Gagal membuat script setelah {MAX_ATTEMPTS} percobaan."
            )

        time.sleep(3)

if not script:
    raise RuntimeError(
        f"AI gagal menghasilkan script valid setelah "
        f"{MAX_ATTEMPTS} percobaan."
    )

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
