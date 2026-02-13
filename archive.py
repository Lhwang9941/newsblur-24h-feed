import os
import requests
from datetime import datetime, timedelta, timezone
from trafilatura import fetch_url, extract

# ===== CONFIG =====
NB_USERNAME = os.getenv("NB_USERNAME")
NB_PASSWORD = os.getenv("NB_PASSWORD")
OUTPUT_FILE = "last_24h_news.txt"
WINDOW_HOURS = 24
# ==================

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
})

# ---------- LOGIN ----------
login = session.post("https://www.newsblur.com/api/login", data={
    "username": NB_USERNAME,
    "password": NB_PASSWORD
}, allow_redirects=True)

if login.status_code != 200:
    print("Login failed:", login.status_code)
    print(login.text[:500])
    exit(1)

print("Logged in")

# ---------- FETCH FEED ----------
feed_url = "https://www.newsblur.com/api/reader/river_stories"
response = session.get(feed_url, allow_redirects=True)

# ---- DEBUG SAFETY CHECK ----
content_type = response.headers.get("Content-Type", "")
if "application/json" not in content_type:
    print("ERROR: API did not return JSON")
    print("Status:", response.status_code)
    print("Content-Type:", content_type)
    print("Body preview:", response.text[:500])
    exit(1)

data = response.json()
stories = data.get("stories", [])

print(f"Fetched {len(stories)} stories")

now = datetime.now(timezone.utc)
window_start = now - timedelta(hours=WINDOW_HOURS)

blocks = []

for story in stories:
    ts = story.get("story_timestamp")
    if not ts:
        continue

    story_time = datetime.fromtimestamp(ts, tz=timezone.utc)

    if not (window_start <= story_time <= now):
        continue

    url = story.get("story_permalink")
    if not url:
        continue

    downloaded = fetch_url(url)
    text = extract(downloaded) or ""

    block = f"""
==============================
SOURCE: {story.get('story_authors','')}
DATE: {story.get('story_date','')}
TITLE: {story.get('story_title','')}
URL: {url}
------------------------------
{text.strip() if text else '[NO TEXT EXTRACTED]'}
==============================
"""
    blocks.append(block)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(blocks))

print(f"Saved {len(blocks)} stories to {OUTPUT_FILE}")
