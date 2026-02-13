import requests
import os
from datetime import datetime, timedelta, timezone

NB_USERNAME = os.getenv("NB_USERNAME")
NB_PASSWORD = os.getenv("NB_PASSWORD")

session = requests.Session()

# ---- LOGIN ----
login_resp = session.post(
    "https://newsblur.com/api/login",
    data={
        "username": NB_USERNAME,
        "password": NB_PASSWORD
    }
)

if login_resp.status_code != 200:
    print("Login failed:", login_resp.text)
    exit(1)

print("Logged in")

# ---- FETCH UNREAD STORIES ----
url = "https://newsblur.com/reader/river_stories"
params = {
    "read_filter": "unread",
    "order": "newest",
    "page": 1
}

response = session.get(url, params=params)

# ---- DEBUG GUARD ----
if not response.headers.get("Content-Type", "").startswith("application/json"):
    print("ERROR: API did not return JSON")
    print("Status:", response.status_code)
    print("Content-Type:", response.headers.get("Content-Type"))
    print("Body preview:", response.text[:500])
    exit(1)

data = response.json()

stories = data.get("stories", [])

now = datetime.now(timezone.utc)
cutoff = now - timedelta(hours=24)

selected = []

for s in stories:
    ts = datetime.fromtimestamp(s["story_timestamp"], tz=timezone.utc)
    if ts >= cutoff:
        selected.append(s)

print(f"Collected {len(selected)} stories from last 24h")

# ---- SAVE TEXT FILE ----
with open("newsblur_24h_unread.txt", "w", encoding="utf-8") as f:
    for s in selected:
        f.write(s.get("story_title", "") + "\n")
        f.write(s.get("story_permalink", "") + "\n\n")
        content = s.get("story_content", "")
        f.write(content + "\n")
        f.write("\n" + "="*80 + "\n\n")

print("Saved to newsblur_24h_unread.txt")
