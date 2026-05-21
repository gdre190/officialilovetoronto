import sys
from datetime import datetime

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    print(f"I LOVE TORONTO - Pipeline - Mode: {mode}")

    if mode in ("all", "scrape"):
        from scraper import run_scraper
        items = run_scraper()
        if not items and mode == "all":
            print("No new items. Stopping.")
            return

    if mode in ("all", "edit"):
        from ai_editor import run_editor
        articles = run_editor()
        if not articles and mode == "all":
            print("No articles. Stopping.")
            return

    if mode in ("all", "publish"):
        from publisher import run_publisher
        run_publisher()

    print("Done.")

if __name__ == "__main__":
    main()
