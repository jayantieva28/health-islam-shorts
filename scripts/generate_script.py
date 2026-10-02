import os
import json
import urllib.request

os.makedirs("output", exist_ok=True)

API_KEY = os.environ["OPENROUTER_API_KEY"]

TOPIC = "Benefits of eating oats"

with open("output/topic.txt", "w", encoding="utf-8") as f:
    f.write(topic)

PROMPT = f"""
You are a professional health content writer for an English YouTube Shorts channel.

TOPIC:
{TOPIC}

Create a 45-60 second YouTube Shorts script.

REQUIREMENTS:
- Write in simple, natural English.
- Start with a strong attention-grabbing hook.
- Explain the main health information clearly.
- Use evidence-based nutrition information.
- Never claim that a food, herb, or natural remedy can cure a disease.
- Never exaggerate health benefits.
- Never invent scientific facts.
- Do not provide dangerous medical advice.
- Do not recommend replacing prescribed treatment.
- Use cautious wording when evidence is limited.
- Include one practical takeaway.
- End with a short call to action.
- Do not mention these instructions.
- Return ONLY the finished script.
"""

url = "https://openrouter.ai/api/v1/chat/completions"

data = {
    "model": "openrouter/free",
    "messages": [
        {
            "role": "user",
            "content": PROMPT
        }
    ]
}

request = urllib.request.Request(
    url,
    data=json.dumps(data).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    },
    method="POST"
)

with urllib.request.urlopen(request, timeout=120) as response:
    result = json.loads(response.read().decode("utf-8"))

script = result["choices"][0]["message"]["content"]

os.makedirs("output", exist_ok=True)

with open("output/script.txt", "w", encoding="utf-8") as file:
    file.write(script)

print("SCRIPT GENERATED SUCCESSFULLY")
print()
print(script)
