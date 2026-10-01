import os
import json
import urllib.request

API_KEY = os.environ["OPENROUTER_API_KEY"]

with open("output/script.txt", "r", encoding="utf-8") as file:
    script = file.read()

PROMPT = f"""
You are a strict health-content safety reviewer.

Review the following YouTube Shorts script:

--- SCRIPT ---
{script}
--- END SCRIPT ---

Analyze every health-related claim.

Use these rules:

1. Do not approve claims that say a food, herb, supplement, or natural remedy
   can cure, prevent, or treat a disease unless strong human clinical evidence
   clearly supports the exact claim.

2. Do not accept exaggerated claims such as:
   "miracle food", "detoxes the body", "guaranteed", or "cures".

3. Do not assume that "natural" means safe.

4. Identify claims that require medical evidence.

5. If evidence is uncertain or the claim is too broad, mark it REVIEW.

6. Identify potentially dangerous medical advice.

7. Do not use religious texts as medical evidence.

8. If the script contains an Islamic/religious statement, keep the religious
   claim separate from the medical claim.

Return exactly this format:

VERDICT: PASS, REVIEW, or REJECT

RISK_LEVEL: LOW, MEDIUM, or HIGH

CLAIMS:
- Claim 1: ...
  Assessment: ...
- Claim 2: ...
  Assessment: ...

PROBLEMS:
- ...

RECOMMENDATIONS:
- ...

Do not invent scientific sources.
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

review = result["choices"][0]["message"]["content"]

with open("output/fact_check.txt", "w", encoding="utf-8") as file:
    file.write(review)

print("FACT CHECK COMPLETED")
print()
print(review)
