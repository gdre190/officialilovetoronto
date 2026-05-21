import feedparser
import requests
import json
import hashlib
from datetime import datetime
from pathlib import Path

SEEN_FILE = Path(__file__).parent / "seen_hashes.json"
OUTPUT_FILE = Path(__file__).parent / "raw_items.json"

RSS_SOURCES = [
    {"name": "blogTO", "url": "https://www.blogto.com/feed/", "priority": "high"},
    {"name": "blogTO Food", "url": "https://www.blogto.com/eat_drink/feed/", "priority": "high"},
    {"name": "NOW Magazine", "url": "https://nowtoronto.com/feed", "priority": "high"},
    {"name": "Toronto Life", "url": "https://torontolife.com/feed/", "priority": "high"},
    {"name": "Daily Hive TO", "url": "https://dailyhive.com/toronto/feed", "priority": "high"},
    {"name": "Narcity Toronto", "url": "https://www.narcity.com/toronto/feed", "priority": "high"},
    {"name": "CBC Toronto", "url": "https://www.cbc.ca/cmlink/rss-canada-toronto", "priority": "medium"},
    {"name": "CP24", "url": "https://www.cp24.com/rss/topstories", "priority": "medium"},
    {"name": "Storeys", "url": "https://storeys.com/feed/", "priority": "medium"},
    {"name": "Urban Toronto", "url": "https://urbantoronto.ca/feed", "priority": "medium"},
    {"name": "Complex Canada", "url": "https://www.complex.com/ca/feed", "priority": "medium"},
    {"name": "6ixBuzz News", "url": "https://6ixbuzztv.com/feed/", "priority": "high"},
]

REDDIT_SOURCES = [
    {"url": "https://www.reddit.com/r/toronto/hot.json?limit=30", "name": "r/toronto", "min_score": 50},
    {"url": "https://www.reddit.com/r/toronto/controversial.json?limit=20&t=week", "name": "r/toronto drama", "min_score": 15},
    {"url": "https://www.reddit.com/r/askTO/hot.json?limit=20", "name": "r/askTO", "min_score": 25},
    {"url": "https://www.reddit.com/r/FoodToronto/hot.json?limit=15", "name": "r/FoodToronto", "min_score": 15},
    {"url": "https://www.reddit.com/r/TorontoRealEstate/hot.json?limit=15", "name": "r/TorontoRealEstate", "min_score": 20},
    {"url": "https://www.reddit.com/r/Torontology/hot.json?limit=15", "name": "r/Torontology", "min_score": 10},
    {"url": "https://www.reddit.com/r/askTO/search.json?q=dating+OR+tinder+OR+hinge+OR+hookup+OR+single&sort=hot&t=week&limit=15", "name": "r/askTO dating", "min_score": 10},
    {"url": "https://www.reddit.com/r/toronto/search.json?q=crime+OR+stabbing+OR+shooting+OR+robbery+OR+home+invasion+OR+carjacking&sort=hot&t=week&limit=10", "name": "r/toronto crime", "min_score": 10},
]

REDDIT_HEADERS = {"User-Agent": "ILoveToronto-CityMedia/3.0"}

HOT_KEYWORDS_TIER1 = [
    "dating", "hookup", "tinder", "hinge", "bumble", "single", "relationship",
    "cheating", "caught", "exposed", "drama", "toxic", "red flag",
    "influencer", "spotted", "sighting", "celebrity",
    "drake", "weeknd", "ovo", "6ixbuzz",
    "stabbing", "shooting", "robbery", "home invasion", "carjacking", "murder",
    "missing", "dead", "killed", "attack", "violent",
    "sex", "affair", "scandal", "leaked", "fired", "arrested",
    "viral", "blew up", "went viral", "tiktok famous",
    "kicked out", "banned", "shut down", "raided",
    "yacht", "boat party", "rooftop", "bottle service",
]

HOT_KEYWORDS_TIER2 = [
    "opening", "closing", "closed", "shutting down", "permanently closed",
    "new restaurant", "new bar", "new spot",
    "king west", "ossington", "queen west", "dundas", "kensington",
    "patio", "party", "festival", "concert", "sold out",
    "gentrification", "eviction", "renoviction", "condo",
    "best", "worst", "overrated", "underrated", "mid",
    "fight", "beef", "called out", "cancelled",
    "secret", "hidden", "underground",
    "fifa", "world cup", "pride", "caribana",
    "health inspection", "one star", "rats", "cockroach",
]

BORING_KEYWORDS = [
    "weather forecast", "traffic update", "road closure",
    "press release", "government announces", "tax filing",
    "sponsored", "advertisement", "partner content",
    "city council voted", "budget proposal",
    "library", "community garden", "volunteer opportunity",
    "webinar", "workshop registration", "seniors",
]


def load_seen():
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def save_seen(seen):
    SEEN_FILE.write_text(json.dumps(list(seen)))


def hash_item(title, source):
    return hashlib.md5(f"{source}:{title}".encode()).hexdigest()


def score_item(item):
    score = 0
    text = f"{item['title']} {item['summary']}".lower()
    for kw in HOT_KEYWORDS_TIER1:
        if kw in text:
            score += 25
    for kw in HOT_KEYWORDS_TIER2:
        if kw in text:
            score += 10
    for kw in BORING_KEYWORDS:
        if kw in text:
            score -= 100
    if item.get("type") == "reddit":
        score += item.get("score", 0) // 8
        score += item.get("num_comments", 0) // 3
    if item.get("priority") == "high":
        score += 10
    return score


def scrape_rss():
    items = []
    for source in RSS_SOURCES:
        try:
            feed = feedparser.parse(source["url"])
            for entry in feed.entries[:25]:
                title = entry.get("title", "").strip()
                if not title:
                    continue
                items.append({
                    "title": title,
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", entry.get("description", ""))[:800],
                    "published": entry.get("published", ""),
                    "source": source["name"],
                    "priority": source["priority"],
                    "type": "article",
                })
        except Exception as e:
            print(f"  WARN: Error scraping {source['name']}: {e}")
    return items


def scrape_reddit():
    items = []
    for source in REDDIT_SOURCES:
        try:
            resp = requests.get(source["url"], headers=REDDIT_HEADERS, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for post in data.get("data", {}).get("children", []):
                    d = post["data"]
                    if d.get("score", 0) >= source["min_score"]:
                        items.append({
                            "title": d.get("title", "").strip(),
                            "link": f"https://reddit.com{d.get('permalink', '')}",
                            "summary": (d.get("selftext", "") or d.get("title", ""))[:800],
                            "published": datetime.fromtimestamp(d.get("created_utc", 0)).isoformat(),
                            "source": source["name"],
                            "type": "reddit",
                            "score": d.get("score", 0),
                            "num_comments": d.get("num_comments", 0),
                            "priority": "high" if d.get("score", 0) > 200 else "medium",
                        })
        except Exception as e:
            print(f"  WARN: Error scraping {source['name']}: {e}")
    return items


def run_scraper():
    print("=" * 50)
    print("SCRAPER v3 - DARK MODE")
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 50)

    seen = load_seen()

    print("Scraping RSS feeds...")
    rss_items = scrape_rss()
    print(f"  Found {len(rss_items)} items from {len(RSS_SOURCES)} sources")

    print("Scraping Reddit...")
    reddit_items = scrape_reddit()
    print(f"  Found {len(reddit_items)} trending posts")

    all_raw = rss_items + reddit_items
    new_items = []
    for item in all_raw:
        h = hash_item(item["title"], item["source"])
        if h not in seen:
            seen.add(h)
            item["interest_score"] = score_item(item)
            new_items.append(item)

    new_items.sort(key=lambda x: x["interest_score"], reverse=True)
    new_items = [i for i in new_items if i["interest_score"] > 0]

    print(f"OK: {len(new_items)} interesting items")
    for item in new_items[:15]:
        print(f"  [{item['interest_score']:3d}] [{item['source'][:15]:15s}] {item['title'][:70]}")

    save_seen(seen)
    OUTPUT_FILE.write_text(json.dumps(new_items, indent=2, default=str))
    return new_items


if __name__ == "__main__":
    run_scraper()
