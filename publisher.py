import json
import os
import requests
from datetime import datetime
from pathlib import Path

ARTICLES_FILE = Path(__file__).parent / "new_articles.json"
SITE_DIR = Path(__file__).parent
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

CATEGORY_COLORS = {
    "eat": "#C4442A", "hoods": "#B7791F", "events": "#D53F8C",
    "gems": "#276749", "outdoors": "#285E61", "nightlife": "#553C9A",
    "gossip": "#9B2C2C", "parties": "#C05621", "dating": "#D53F8C",
    "crime": "#742A2A",
}

CATEGORY_LABELS = {
    "eat": "Eat and Drink", "hoods": "Neighbourhoods", "events": "What is On",
    "gems": "Local Gems", "outdoors": "Outdoors", "nightlife": "Nightlife",
    "gossip": "Gossip", "parties": "Parties", "dating": "Dating", "crime": "Crime",
}


def get_pexels_image(query):
    if not PEXELS_API_KEY:
        return ""
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "per_page": 1, "size": "medium"},
            timeout=10,
        )
        if resp.status_code == 200:
            photos = resp.json().get("photos", [])
            if photos:
                return photos[0]["src"]["medium"]
    except Exception:
        pass
    return ""


def build_post_html(article):
    cat = article.get("category", "gossip")
    color = CATEGORY_COLORS.get(cat, "#333")
    label = CATEGORY_LABELS.get(cat, cat.title())
    img_url = article.get("image_url", "")
    source_url = article.get("source_url", "#")
    tag = article.get("tag", "")
    headline = article.get("headline", "Untitled")
    desc = article.get("description", "")

    if img_url:
        bg = f"background-image:url('{img_url}')"
    else:
        bg = f"background:{color}"

    return (
        f'<a href="{source_url}" target="_blank" class="post">'
        f'<div class="post__img"><div class="post__bg" style="{bg}"></div></div>'
        f'<div class="post__body">'
        f'<div class="post__meta"><span class="post__cat" style="color:{color}">{label}</span>'
        f'<span class="post__dot">-</span><span class="post__time">{tag}</span></div>'
        f'<h3 class="post__h">{headline}</h3>'
        f'<p class="post__p">{desc}</p>'
        f'</div></a>\n'
    )


def update_homepage(articles):
    index_path = SITE_DIR / "index.html"
    if not index_path.exists():
        print("  WARN: index.html not found")
        return

    html = index_path.read_text()

    start_marker = "<!-- AUTO-FEED-START -->"
    end_marker = "<!-- AUTO-FEED-END -->"

    if start_marker not in html:
        grid_marker = "<!-- CATEGORY GRID -->"
        if grid_marker in html:
            feed_block = f"\n{start_marker}\n{end_marker}\n{grid_marker}"
            html = html.replace(grid_marker, feed_block)
            print("  Added feed markers to index.html")
        else:
            print("  WARN: No injection point in index.html")
            return

    feed_html = f"\n{start_marker}\n"
    feed_html += '<div class="day"><span class="day__label">Just In</span><div class="day__line"></div>'
    feed_html += f'<span class="day__count">Auto-updated {datetime.now().strftime("%b %d, %I:%M %p")}</span></div>\n'

    for article in articles[:8]:
        feed_html += build_post_html(article)

    feed_html += f"{end_marker}\n"

    before = html[:html.index(start_marker)]
    after = html[html.index(end_marker) + len(end_marker):]
    html = before + feed_html + after

    index_path.write_text(html)
    print(f"  OK: Homepage updated with {min(len(articles), 8)} stories")


def run_publisher():
    print("=" * 50)
    print("PUBLISHER v3")
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 50)

    if not ARTICLES_FILE.exists():
        print("No articles. Run ai_editor first.")
        return

    articles = json.loads(ARTICLES_FILE.read_text())
    unpublished = [a for a in articles if not a.get("published")]

    if not unpublished:
        print("No new articles to publish.")
        return

    print(f"Publishing {len(unpublished)} new articles...")

    for article in unpublished:
        if PEXELS_API_KEY and article.get("image_query"):
            img = get_pexels_image(article["image_query"])
            if img:
                article["image_url"] = img

    update_homepage(unpublished)

    for a in unpublished:
        a["published"] = True
        a["published_at"] = datetime.now().isoformat()

    ARTICLES_FILE.write_text(json.dumps(articles, indent=2))
    print(f"OK: Published {len(unpublished)} articles")


if __name__ == "__main__":
    run_publisher()
