import os
import json
import urllib.request

API_KEY = os.environ["GEMINI_API_KEY"]

url = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash-lite:generateContent"
)

data = {
    "contents": [
        {
            "parts": [
                {
                    "text": "Reply with exactly: OK"
                }
            ]
        }
    ]
}

request = urllib.request.Request(
    url,
    data=json.dumps(data).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY
    },
    method="POST"
)

try:
    with urllib.request.urlopen(request, timeout=60) as response:
        print("HTTP STATUS:", response.status)
        print(response.read().decode("utf-8"))

except Exception as e:
    print("ERROR:", repr(e))
    raise
