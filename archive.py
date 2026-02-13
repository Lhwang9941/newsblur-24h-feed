import requests
import os
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup

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

# ---- SETTINGS ----
CUTOFF = datetime.now(timezone.utc) - timedelta(hours=24)
PAGE = 1
ALL_SELECTED = []

print("Fetching unread stories...")

while True:
    url = "https://newsblur.com/reader/river_stories"
    params = {
        "read_filter": "unread",
        "order": "newest",
        "page": PAGE
    }

    response = session.get(url, params=params)

    if not response.headers.get("Content-Type", "").startswith("application/json"):
        print("Non-JSON response, stopping pagination.")
        break

    data = response.json()
    stories = data.get("stories", [])

    if not stories:
        break

    print(f"Page {PAGE}: {len(stories)} stories")

    for s in stories:
        try:
            ts = datetime.fromtimestamp(int(s["story_timestamp"]), tz=timezone.utc)
        except:
            continue

        if ts >= CUTOFF:
            ALL_SELECTED.append(s)
        else:
            # since ordered newest → oldest, we can stop early
            break

    PAGE += 1

print(f"Total collected from last 24h: {len(ALL_SELECTED)}")

# ---- TEXT CLEANING FUNCTION ----
def clean_html(html):
    soup = BeautifulSoup(html, "html.parser")

    # remove images, figures, videos, embeds
    for tag in soup(["img", "figure", "video", "iframe", "picture", "source", "svg"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    # normalize whitespace
    lines = [l.strip() for l in text.splitlines()]
    lines = [l for l in lines if l]
    return "\n".join(lines)

# ---- SAVE TXT ----
with open("last_24h_news.txt", "w", encoding="utf-8") as f:
    for s in ALL_SELECTED:
        title = s.get("story_title", "").strip()
        permalink = s.get("story_permalink", "")
        raw_content = s.get("story_content", "")

        ts = datetime.fromtimestamp(int(s["story_timestamp"]), tz=timezone.utc)
        time_str = ts.strftime("%Y-%m-%d %H:%M:%S GMT")

        body = clean_html(raw_content)

        f.write(title + "\n")
        f.write(time_str + "\n")
        f.write(permalink + "\n\n")
        f.write(body + "\n")
        f.write("\n" + "="*100 + "\n\n")

print("Saved to last_24h_news.txt")
