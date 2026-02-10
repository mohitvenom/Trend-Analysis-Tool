import sys
import os
import argparse
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logger import logger
from country_config import COUNTRIES
from query_config import get_reddit_subreddits

# -----------------------------
# CONFIG
# -----------------------------

CUTOFF_DAYS = 24
MAX_RESULTS_PER_COUNTRY = 5
REQUEST_SLEEP = 2  # seconds (rate-limit safe)

HEADERS = {
    "User-Agent": "trend-intelligence/1.0"
}

OUTPUT_CSV = "outputs/reddit_trending.csv"
OUTPUT_JSON = "outputs/reddit_trending.json"

# -----------------------------
# COUNTRY RELEVANCE KEYWORDS
# (derived ONLY from country_config.py names)
# -----------------------------

def build_country_keywords():
    keywords = {}
    for country in COUNTRIES.keys():
        base = country.lower().replace(" ", "")
        keywords[country] = [
            country.lower(),
            base,
            base[:4]  # soft match
        ]
    return keywords

COUNTRY_KEYWORDS = build_country_keywords()

cutoff_date = datetime.utcnow() - timedelta(days=CUTOFF_DAYS)

# -----------------------------
# MAIN SCRAPER
# -----------------------------

def run_reddit_scraper(subreddits=None):
    subreddits_config = get_reddit_subreddits(subreddits)
    logger.info("Reddit scraper started (global scrape + country relevance layer)")

    global_posts = []
    seen_posts = set()

    # -------- STEP 1: Global scrape (ONCE per subreddit) --------
    for vertical, subs in subreddits_config.items():
        for sub in subs:
            try:
                logger.info(f"Reddit | Global scrape | {sub}")
                url = f"https://old.reddit.com/r/{sub}/top/?t=month"
                res = requests.get(url, headers=HEADERS, timeout=15)
                res.raise_for_status()

                soup = BeautifulSoup(res.text, "html.parser")

                for post in soup.select("div.thing"):
                    post_id = post.get("data-fullname")
                    if not post_id or post_id in seen_posts:
                        continue

                    title_tag = post.select_one("a.title")
                    if not title_tag:
                        continue

                    created_ts = post.get("data-timestamp")
                    if not created_ts:
                        continue

                    created = datetime.utcfromtimestamp(int(created_ts) / 1000)
                    if created < cutoff_date:
                        continue

                    upvotes = int(post.get("data-score", 0))
                    comments = int(post.get("data-comments-count", 0))
                    permalink = post.get("data-permalink", "")

                    trend_score = upvotes + (comments * 2)

                    global_posts.append({
                        "title": title_tag.text.strip(),
                        "vertical": vertical,
                        "subreddit": sub,
                        "upvotes": upvotes,
                        "comments": comments,
                        "post_url": "https://reddit.com" + permalink,
                        "base_score": trend_score
                    })

                    seen_posts.add(post_id)

                time.sleep(REQUEST_SLEEP)

            except Exception as e:
                logger.warning(f"Reddit failed | {sub} | {e}")

    logger.info(f"Global Reddit posts collected: {len(global_posts)}")

    # -------- STEP 2: Country relevance scoring --------
    country_buckets = defaultdict(list)

    for post in global_posts:
        title_lower = post["title"].lower()

        for country in COUNTRIES.keys():
            relevance_boost = 0
            for kw in COUNTRY_KEYWORDS[country]:
                if kw in title_lower:
                    relevance_boost += 5

            adjusted_score = post["base_score"] + relevance_boost

            country_buckets[country].append({
                "title": post["title"],
                "vertical": post["vertical"],
                "subreddit": post["subreddit"],
                "upvotes": post["upvotes"],
                "comments": post["comments"],
                "post_url": post["post_url"],
                "trend_score": adjusted_score,
                "country": country
            })

    # -------- STEP 3: Top-N selection per country --------
    final_rows = []

    for country, posts in country_buckets.items():
        grouped = defaultdict(list)

        for p in posts:
            grouped[p["vertical"]].append(p)

        for vertical, items in grouped.items():
            top_items = sorted(
                items,
                key=lambda x: x["trend_score"],
                reverse=True
            )[:MAX_RESULTS_PER_COUNTRY]

            final_rows.extend(top_items)

    # -------- OUTPUT --------
    df = pd.DataFrame(final_rows)

    df.to_csv(OUTPUT_CSV, index=False)
    df.to_json(OUTPUT_JSON, orient="records")

    logger.info(f"Reddit scraper completed | records saved: {len(df)}")

# -----------------------------
# ENTRY POINT
# -----------------------------

if __name__ == "__main__":
    run_reddit_scraper()
