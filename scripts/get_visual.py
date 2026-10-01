import os
import requests

OUTPUT = "output/visual.jpg"
os.makedirs("output", exist_ok=True)

search_term = "oats"

url = "https://commons.wikimedia.org/w/api.php"

params = {
    "action": "query",
    "generator": "search",
    "gsrsearch": search_term,
    "gsrnamespace": 6,
    "gsrlimit": 10,
    "prop": "imageinfo",
    "iiprop": "url",
    "iiurlwidth": 1080,
    "format": "json"
}

headers = {
    "User-Agent": "health-islam-shorts/1.0"
}

print("Searching Wikimedia Commons...")

response = requests.get(
    url,
    params=params,
    headers=headers,
    timeout=30
)

response.raise_for_status()

data = response.json()

pages = data.get("query", {}).get("pages", {})

image_url = None

for page in pages.values():
    info = page.get("imageinfo", [])
    if info:
        image_url = info[0].get("thumburl") or info[0].get("url")
        if image_url:
            break

if not image_url:
    raise RuntimeError("No suitable image found")

print("Downloading image...")
print(image_url)

image = requests.get(
    image_url,
    headers=headers,
    timeout=30
)

image.raise_for_status()

with open(OUTPUT, "wb") as f:
    f.write(image.content)

print("VISUAL DOWNLOADED SUCCESSFULLY")
print(OUTPUT)
