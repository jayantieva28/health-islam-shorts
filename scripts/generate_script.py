import os
import json
import urllib.request

API_KEY = os.environ["GEMINI_API_KEY"]

TOPIC = "Benefits of eating oats"

PROMPT = f"""
You are a health content writer for an English YouTube Shorts channel.

Topic:
{TOPIC}

Create a 45-60 second YouTube Shorts script.

Rules:
- Use clear, simple English.
- Start with a strong hook.
- Give factual, evidence-based health information.
- Do not claim that food can cure or treat diseases.
- Do not exaggerate health benefits.
- Do not invent scientific facts.
- Distinguish general nutrition information from medical treatment.
- If evidence is uncertain, use cautious wording.
- Do not give dangerous medical advice.
- End with a short practical takeaway.
- Do not mention these instructions.

Return ONLY the script.
"""

data = {
    "contents": [
        {
            "parts": [
                {
                    "text": PROMPT
                }
            ]
        }
    ]
}

url = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-3.8-flash-lite:generateContent"
)

request = urllib.request.Request(
    url,
    data=json.dumps(data).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY
    },
    method="POST"
)

import time
import urllib.error

result = None

for attempt in range(5):
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
        print(f"Gemini API success on attempt {attempt + 1}")
        break

    except urllib.error.HTTPError as e:
        print(f"Gemini API returned HTTP {e.code} on attempt {attempt + 1}")

        if e.code == 503 and attempt < 4:
            wait_time = 5 * (attempt + 1)
            print(f"Waiting {wait_time} seconds before retry...")
            time.sleep(wait_time)
        else:
            print(e.read().decode("utf-8"))
            raise

if result is None:
    raise RuntimeError("Gemini API did not return a response")

script = result["candidates"][0]["content"]["parts"][0]["text"]

os.makedirs("output", exist_ok=True)

with open("output/script.txt", "w", encoding="utf-8") as file:
    file.write(script)

print("SCRIPT GENERATED SUCCESSFULLY")
print()
print(script)
