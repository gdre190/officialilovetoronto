import json
import os
import requests
from datetime import datetime
from pathlib import Path

RAW_FILE = Path(__file__).parent / "raw_items.json"
ARTICLES_FILE = Path(__file__).parent / "new_articles.json"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = """You are the AI editor for "I Love Toronto" - a raw, unfiltered, edgy city media brand. NOT a blog. NOT BlogTO. Think 6ixBuzz meets Barstool meets the wildest Toronto group chat.

Your audience: 20-35 year olds in downtown Toronto who go out, date, drink, and care about what is actually happening.

CONTENT PRIORITIES:
1. DATING AND HOOKUP CULTURE - Toronto dating horror stories, Hinge/Tinder drama, toxic patterns, hot takes about Toronto men/women
2. CRIME AND DARK NEWS - Home invasions, carjackings, stabbings, robberies, missing persons, anything scary or shocking
3. INFLUENCER AND CELEBRITY - Drake, Weeknd, anyone spotted at a Toronto club/restaurant, influencer drama, TikTokers getting called out
4. NIGHTLIFE AND PARTY DRAMA - Club closings, liquor license pulls, King West drama, bouncer incidents, bottle service culture
5. RESTAURANT/BAR DRAMA - Closings, health inspection failures, viral reviews, chef walkouts, owner meltdowns
6. VIRAL/WEIRD - Anything bizarre happening in Toronto, weird Reddit posts, TikToks blowing up
7. REAL ESTATE GOSSIP - Insane listings, condo battles vs beloved venues, renovictions

NEVER PICK: Weather, traffic, government press releases, corporate events, webinars, generic listicles, family-friendly events, anything boring.

CATEGORIES - assign exactly one:
gossip, dating, crime, eat, nightlife, hoods, events, gems, outdoors

For each story write:
- category: one of the above
- headline: Punchy, provocative, max 14 words. Like a text to your most unhinged friend.
- tag: 1-3 words (e.g. "CAUGHT", "RIP", "Messy", "Viral", "Dark", "Spotted", "Toxic", "Unhinged", "Down Bad", "Wild", "Yikes")
- description: 2-3 sentences MAX. Conversational, opinionated, slightly unhinged.
- source_url: original link
- image_query: Pexels search query for a dark/moody thumbnail

VOICE: You are the most plugged-in, slightly chaotic friend in the group chat. STRONG opinions always. Dark humor is fine. Short punchy sentences.

Return ONLY a JSON array. No markdown, no backticks, no preamble."""


def load_raw_items():
    if not RAW_FILE.exists():
        print("WARN: No raw items. Run scraper first.")
        return []
    return json.loads(RAW_FILE.read_text())


def call_claude(items):
    if not ANTHROPIC_API_KEY:
        print("WARN: ANTHROPIC_API_KEY not set.")
        return []

    items_text = "\n\n".join([
        f"[{i+1}] SOURCE: {item['source']}\n"
        f"SCORE: {item.get('interest_score', 0)}\n"
        f"TITLE: {item['title']}\n"
        f"LINK: {item['link']}\n"
        f"SUMMARY: {item['summary'][:500]}"
        for i, item in enumerate(items[:40])
    ])

    user_message = f"Here are {min(len(items), 40)} items scraped from Toronto media and Reddit right now ({datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}). Pick the 5-8 JUICIEST stories.\n\n{items_text}"

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": MODEL,
                "max_tokens": 3500,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_message}],
            },
            timeout=120,
        )

        if resp.status_code != 200:
            print(f"WARN: Claude API error {resp.status_code}: {resp.text[:300]}")
            return []

        data = resp.json()
        text = "".join(b.get("text", "") for b in data.get("content", []))
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]

        articles = json.loads(text)
        return articles

    except json.JSONDecodeError as e:
        print(f"WARN: JSON parse error: {e}")
        return []
    except Exception as e:
        print(f"WARN: Error calling Claude: {e}")
        return []


def run_editor():
    print("=" * 50)
    print("AI EDITOR v3 - UNFILTERED")
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 50)

    items = load_raw_items()
    if not items:
        print("No items to process.")
        return []

    print(f"Sending {min(len(items), 40)} items to Claude...")
    articles = call_claude(items)

    if articles:
        print(f"OK: Claude picked {len(articles)} stories:")
        for a in articles:
            print(f"  [{a['category']:10s}] [{a.get('tag',''):12s}] {a['headline']}")

        existing = []
        if ARTICLES_FILE.exists():
            try:
                existing = json.loads(ARTICLES_FILE.read_text())
            except json.JSONDecodeError:
                existing = []

        for a in articles:
            a["created_at"] = datetime.now().isoformat()

        existing.extend(articles)
        existing = existing[-200:]
        ARTICLES_FILE.write_text(json.dumps(existing, indent=2))
        print(f"Saved to {ARTICLES_FILE}")
    else:
        print("WARN: No articles generated.")

    return articles


if __name__ == "__main__":
    run_editor()
