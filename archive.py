import requests
import os
import trafilatura
from datetime import datetime, timedelta, timezone
import pytz
from urllib.parse import urlparse

# ===== country inference function (STEP 2 GOES HERE) =====
def infer_country_from_url(url):
    domain = urlparse(url).netloc.lower()

    mapping = {
        ".kr": ("South Korea", "Asia/Seoul"),
        ".jp": ("Japan", "Asia/Tokyo"),
        ".cn": ("China", "Asia/Shanghai"),
        ".ru": ("Russia", "Europe/Moscow"),
        ".fr": ("France", "Europe/Paris"),
        ".de": ("Germany", "Europe/Berlin"),
        ".uk": ("United Kingdom", "Europe/London"),
        ".co.uk": ("United Kingdom", "Europe/London"),
        ".it": ("Italy", "Europe/Rome"),
        ".es": ("Spain", "Europe/Madrid"),
        ".pt": ("Portugal", "Europe/Lisbon"),
        ".ua": ("Ukraine", "Europe/Kyiv"),
        ".pl": ("Poland", "Europe/Warsaw"),
        ".se": ("Sweden", "Europe/Stockholm"),
        ".no": ("Norway", "Europe/Oslo"),
        ".fi": ("Finland", "Europe/Helsinki"),
        ".com": ("Unknown", "UTC"),
        ".org": ("Unknown", "UTC"),
        ".net": ("Unknown", "UTC")
    }

    for tld, data in mapping.items():
        if domain.endswith(tld):
            return data

    return ("Unknown", "UTC")

# ===== FULL ARTICLE SCRAPER =====
def fetch_full_article(url):
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None

        text = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=False,
            include_images=False
        )

        return text
    except Exception as e:
        print("SCRAPE ERROR:", e)
        return None

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
import re
from bs4 import BeautifulSoup

def clean_html(html):
    soup = BeautifulSoup(html, "html.parser")

    # remove non-content elements
    for tag in soup([
        "img", "figure", "video", "iframe", "picture", "source", "svg",
        "script", "style", "nav", "footer", "header", "form", "aside",
        "noscript", "button", "input"
    ]):
        tag.decompose()

    # remove comments
    for c in soup.find_all(string=lambda text: isinstance(text, type(soup.comment))):
        c.extract()

    # extract paragraphs properly
    paragraphs = []

    for p in soup.find_all(["p", "div", "article", "section"]):
        text = p.get_text(" ", strip=True)

        # clean excessive whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # skip junk blocks
        if len(text) < 40:
            continue

        # skip navigation-like lines
        if text.lower().startswith(("share", "advertisement", "related", "sponsored", "cookie")):
            continue

        paragraphs.append(text)

    # de-duplicate consecutive paragraphs
    cleaned = []
    prev = None
    for p in paragraphs:
        if p != prev:
            cleaned.append(p)
        prev = p

    return "\n\n".join(cleaned)

# ---- SAVE TXT ----
with open("last_24h_news.txt", "w", encoding="utf-8") as f:
    for s in ALL_SELECTED:
        title = s.get("story_title", "").strip()
        permalink = s.get("story_permalink", "")
        publisher = s.get("story_feed_title", "Unknown Publisher")

        # UTC timestamp
        ts_utc = datetime.fromtimestamp(int(s["story_timestamp"]), tz=timezone.utc)

        # Country + local timezone
        country, tz_name = infer_country_from_url(permalink)
        local_tz = pytz.timezone(tz_name)

        local_time = ts_utc.astimezone(local_tz)
        kst_time = ts_utc.astimezone(kst)

        date_str = local_time.strftime("%Y-%m-%d")
        local_time_str = local_time.strftime("%H:%M:%S %Z")
        kst_time_str = kst_time.strftime("%H:%M:%S KST")

        body = fetch_full_article(permalink)
        if not body:
            body = title

        # ===== FORMAT OUTPUT =====
        f.write(title + "\n")
        f.write(country + "\n")
        f.write(publisher + "\n")
        f.write(date_str + "\n")
        f.write(local_time_str + "\n")
        f.write(kst_time_str + "\n\n")

        f.write(body + "\n")
        f.write("\n" + "="*100 + "\n\n")

print("Saved to last_24h_news.txt")
