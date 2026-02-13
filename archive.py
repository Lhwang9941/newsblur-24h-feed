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

# Login
login = session.post("https://www.newsblur.com/api/login", data={
    "username": NB_USERNAME,
    "password": NB_PASSWORD
})

if login.status_code != 200:
    print("Login failed")
    exit(1)

print("Logged in")

# Fetch feed
response = session.get("https://www.newsblur.com/api/reader/river_stories")
stories = response.json().get("stories", [])

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
