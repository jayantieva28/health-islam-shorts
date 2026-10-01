import os
import json
import urllib.request

API_KEY = os.environ["OPENROUTER_API_KEY"]

url = "https://openrouter.ai/api/v1/chat/completions"

data = {
    "model": "openrouter/free",
    "messages": [
        {
            "role": "user",
            "content": "Reply with exactly: OPENROUTER CONNECTION SUCCESS"
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

try:
    with urllib.request.urlopen(request, timeout=60) as response:
        print("HTTP STATUS:", response.status)

        result = json.loads(
            response.read().decode("utf-8")
        )

        print(json.dumps(result, indent=2))

except Exception as e:
    print("ERROR:", repr(e))
    raise
