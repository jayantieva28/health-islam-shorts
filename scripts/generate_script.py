
import os
import csv
import re
import time
import requests

os.makedirs("output", exist_ok=True)

API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY belum tersedia.")

MODEL = "openrouter/free"
TOPICS_FILE = "topics.csv"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_ATTEMPTS = 5
MIN_WORDS = 100
MAX_WORDS = 125
NEW_TOPICS_BATCH = 4

CATEGORIES = [
    "Healthy Food",
    "Natural Foods",
    "Islamic Lifestyle",
]

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def ai_request(prompt, max_tokens=1200):
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Follow the user's instructions exactly. "
                    "Produce complete, useful English content."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.5,
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
        raise RuntimeError("OpenRouter tidak mengembalikan choices.")

    content = choices[0].get("message", {}).get("content", "")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("OpenRouter mengembalikan respons kosong.")

    return content.strip()


def normalize(text):
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def read_topics():
    if not os.path.isfile(TOPICS_FILE):
        raise RuntimeError("topics.csv tidak ditemukan.")

    with open(TOPICS_FILE, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"id", "category", "topic", "status"}

        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise RuntimeError(
                "Header topics.csv harus: id,category,topic,status"
            )

        rows = []
        for row in reader:
            if not row.get("topic", "").strip():
                continue
            rows.append({
                "id": row["id"].strip(),
                "category": row["category"].strip(),
                "topic": row["topic"].strip(),
                "status": row["status"].strip().upper(),
            })

    return rows


def save_topics(rows):
    temp_path = TOPICS_FILE + ".tmp"

    with open(temp_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["id", "category", "topic", "status"],
        )
        writer.writeheader()
        writer.writerows(rows)

    os.replace(temp_path, TOPICS_FILE)


def generate_new_topics():
    existing_rows = read_topics()
    existing = {normalize(r["topic"]) for r in existing_rows}
    existing_text = "\n".join(
        "- " + r["topic"] for r in existing_rows
    )

    prompt = f"""
Generate exactly {NEW_TOPICS_BATCH} NEW topics for an English
health education YouTube Shorts channel.

Allowed categories:
Healthy Food
Natural Foods
Islamic Lifestyle

Existing topics; do not repeat them:
{existing_text}

Choose useful, specific topics suitable for a 45-60 second video.
Health topics must allow cautious, evidence-based discussion.
Do not promise cures. Do not invent Islamic quotations or attributions.

OUTPUT FORMAT:
Return only {NEW_TOPICS_BATCH} lines.
Each line must follow this exact format:
CATEGORY | TOPIC

CATEGORY must be exactly one of:
Healthy Food
Natural Foods
Islamic Lifestyle

Do not use JSON, numbering, bullets, headings, or explanations.
"""

    last_error = None

    for attempt in range(1, 4):
        try:
            raw = ai_request(prompt, max_tokens=700)
            print("Raw topic response:")
            print(raw)

            candidates = []
            seen = set(existing)

            for line in raw.splitlines():
                line = line.strip().lstrip("-*0123456789. ").strip()
                if "|" not in line:
                    continue

                category, topic = line.split("|", 1)
                category = category.strip()
                topic = topic.strip().strip('"').strip("'")
                key = normalize(topic)

                if category not in CATEGORIES:
                    continue
                if len(topic.split()) < 3 or len(topic) > 120:
                    continue
                if key in seen:
                    continue

                seen.add(key)
                candidates.append({
                    "category": category,
                    "topic": topic,
                })

            if candidates:
                # Read again to avoid overwriting newly committed topics
                latest_rows = read_topics()
                latest_seen = {
                    normalize(r["topic"]) for r in latest_rows
                }

                max_id = max(
                    (
                        int(r["id"])
                        for r in latest_rows
                        if r["id"].isdigit()
                    ),
                    default=0,
                )

                added = []
                for item in candidates:
                    key = normalize(item["topic"])
                    if key in latest_seen:
                        continue

                    max_id += 1
                    added.append({
                        "id": str(max_id),
                        "category": item["category"],
                        "topic": item["topic"],
                        "status": "READY",
                    })
                    latest_seen.add(key)

                    if len(added) >= NEW_TOPICS_BATCH:
                        break

                if added:
                    save_topics(latest_rows + added)
                    print(f"Added {len(added)} new topics.")
                    for item in added:
                        print("-", item["category"], "|", item["topic"])
                    return

            last_error = "Tidak ada topik baru yang valid dan unik."

        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            print(f"Topic generation attempt {attempt} failed: {last_error}")

        time.sleep(2)

    raise RuntimeError(
        "Gagal membuat topik baru setelah beberapa percobaan. "
        f"Alasan terakhir: {last_error}"
    )


def select_topic():
    rows = read_topics()
    ready = [r for r in rows if r["status"] == "READY"]

    if not ready:
        print("Tidak ada topik READY. Membuat topik baru...")
        generate_new_topics()
        rows = read_topics()
        ready = [r for r in rows if r["status"] == "READY"]

    if not ready:
        raise RuntimeError("Topik READY masih kosong setelah pembuatan.")

    selected = ready[0]

    print("======================================")
    print("TOPIC TERPILIH")
    print("======================================")
    print("ID       :", selected["id"])
    print("Category :", selected["category"])
    print("Topic    :", selected["topic"])
    print("======================================")

    return selected


selected = select_topic()
selected_id = selected["id"]
selected_category = selected["category"]
selected_topic = selected["topic"]

with open("output/topic.txt", "w", encoding="utf-8") as f:
    f.write(selected_topic)


SCRIPT_PROMPT = f"""
Create a 45-60 second YouTube Shorts narration in English.

Category: {selected_category}
Topic: {selected_topic}

Write 100-125 spoken words. Start with an accurate hook, provide useful
evidence-based information, use cautious scientific wording, avoid
unsupported medical claims and promises of cures, and give one practical
takeaway. Do not tell viewers to stop prescribed treatment.

If mentioning Islam, distinguish religious guidance from scientific
evidence. Do not invent religious quotations or attributions.

Output ONLY the words the narrator should speak. No headings, scene
directions, production notes, Markdown, bullet points, or metadata.
Do not output safety classifications or explanations.
"""


def clean_script(text):
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    if len(text) >= 2 and (
        (text.startswith('"') and text.endswith('"'))
        or (text.startswith("'") and text.endswith("'"))
    ):
        text = text[1:-1].strip()

    return text.strip()


def validate_script(script):
    if not script:
        return False, "Script kosong."

    lower = script.lower()
    forbidden = [
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

    for phrase in forbidden:
        if phrase in lower:
            return False, f"Output safety/meta terdeteksi: {phrase}"

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

    if topic_words and not any(word in lower for word in topic_words):
        return False, "Script tidak terlihat membahas topik yang dipilih."

    return True, f"Valid ({word_count} kata)."


script = None

for attempt in range(1, MAX_ATTEMPTS + 1):
    print("")
    print(f"SCRIPT GENERATION ATTEMPT {attempt}/{MAX_ATTEMPTS}")

    prompt = SCRIPT_PROMPT
    if attempt > 1:
        prompt += (
            f"\nRetry: write a complete 100-125 word narration "
            f"about {selected_topic}. Output narration only."
        )

    try:
        candidate = clean_script(ai_request(prompt, max_tokens=1000))
        print("Raw output:")
        print(candidate[:500])

        valid, reason = validate_script(candidate)
        print("Valid:", valid)
        print("Reason:", reason)

        if valid:
            script = candidate
            break

        time.sleep(2)

    except Exception as exc:
        print(f"Script generation error: {type(exc).__name__}: {exc}")
        if attempt < MAX_ATTEMPTS:
            time.sleep(3)

if not script:
    raise RuntimeError(
        f"Gagal membuat script valid setelah {MAX_ATTEMPTS} percobaan."
    )

with open("output/script.txt", "w", encoding="utf-8") as f:
    f.write(script)

print("")
print("======================================")
print("SCRIPT BERHASIL DIBUAT")
print("======================================")
print("Topic:", selected_topic)
print("Words:", len(script.split()))
print("Saved: output/script.txt")
print("Saved: output/topic.txt")
