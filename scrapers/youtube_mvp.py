import os
import sys
import argparse
import requests
import pandas as pd
from datetime import datetime

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logger import logger
from country_config import COUNTRIES
from query_config import get_youtube_queries

# Load environment variables from scrapers/.env
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

if not YOUTUBE_API_KEY:
    logger.warning("No YOUTUBE_API_KEY found in .env, scraper may fail.")

OUTPUT_CSV = "outputs/youtube_trending.csv"
OUTPUT_JSON = "outputs/youtube_trending.json"

MAX_RESULTS = 15

TRENDING_SUPPORTED = {
    "IN", "JP", "AU", "CA", "BR", "MX"
}

# Keywords to filter out non-product content (trailers, music, etc.)
EXCLUDED_KEYWORDS = [
    "trailer", "official video", "music video", "song", "lyrics", 
    "clip", "full movie", "episode", "teaser", "movie", "official audio",
    "lyric video", "soundtrack", "ost", "ending", "scene"
]

PROXY_MAP = {
    "India": "IN",
    "Bangladesh": "IN",
    "Sri Lanka": "IN",

    "UK": "GB",
    "Europe": "GB",
    "Iceland": "GB",

    "Germany": "DE",
    "France": "DE",
    "Italy": "DE",
    "Spain": "DE",
    "Netherlands": "DE",
    "Sweden": "DE",
    "Poland": "DE",

    "UAE": "AE",
    "Saudi": "AE",
    "Qatar": "AE",
    "Kuwait Abroad": "AE",
    "Oman": "AE",
    "Jordan": "AE",

    "Singapore": "SG",
    "Indonesia": "SG",
    "Malaysia": "SG",
    "Thailand": "SG",
    "Vietnam": "SG",

    "South Africa": "ZA",
    "Nigeria": "ZA",
    "Ghana": "ZA",
    "Kenya": "ZA",

    "Japan": "JP",
    "Australia": "AU",
    "Canada": "CA",
    "Brazil": "BR",
    "Mexico": "MX",
}

def fetch_trending_videos(region_code):
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": MAX_RESULTS,
        "key": YOUTUBE_API_KEY
    }
    res = requests.get(url, params=params, timeout=10)
    res.raise_for_status()
    return res.json().get("items", [])

def fetch_search_videos(query):
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": MAX_RESULTS,
        "key": YOUTUBE_API_KEY
    }
    res = requests.get(url, params=params, timeout=10)
    res.raise_for_status()
    return res.json().get("items", [])

def run_youtube_scraper(queries=None):
    logger.info("YouTube scraper started | proxy-based regional model")

    search_queries = get_youtube_queries(queries)
    rows = []
    proxy_cache = {}

    for country in COUNTRIES.keys():
        proxy = PROXY_MAP.get(country)
        if not proxy:
            continue

        if proxy not in proxy_cache:
            try:
                if proxy in TRENDING_SUPPORTED:
                    logger.info(f"{proxy} | using TRENDING feed")
                    items = fetch_trending_videos(proxy)
                    confidence = "high"
                else:
                    logger.info(f"{proxy} | SEARCH proxy feed (queries: {search_queries})")
                    items = []
                    for q in search_queries:
                        items.extend(fetch_search_videos(q))
                    confidence = "medium"

                proxy_cache[proxy] = (items, confidence)

            except Exception as e:
                logger.warning(f"YouTube failed | proxy={proxy} | {e}")
                proxy_cache[proxy] = ([], "low")

        items, confidence = proxy_cache[proxy]

        count = 0 
        for item in items:
            if count >= 5: # Keep target of 5 valid items per country
                break
                
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            video_id = item.get("id")
            if isinstance(video_id, dict):
                video_id = video_id.get("videoId")
            
            title = snippet.get("title", "")
            title_lower = title.lower()
            
            # Filter Logic
            if any(kw in title_lower for kw in EXCLUDED_KEYWORDS):
                continue
                
            view_count = int(stats.get("viewCount", 0) or 0)
            trend_score = view_count if view_count else max(1, 100 - count * 10) # Use 'count' for rank fallback

            rows.append({
                "video_title": title,
                "channel": snippet.get("channelTitle"),
                "published_at": snippet.get("publishedAt"),
                "video_url": f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
                "trend_score": trend_score,
                "country": country,
                "proxy_region": proxy,
                "signal_source": "youtube",
                "confidence": confidence,
                "collected_at": datetime.utcnow().isoformat()
            })
            count += 1

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_CSV, index=False)
    df.to_json(OUTPUT_JSON, orient="records")

    logger.info(f"YouTube scraper completed | total records: {len(df)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube trend scraper")
    parser.add_argument(
        "--queries",
        type=str,
        default=None,
        help='Comma-separated search queries, e.g. "gadgets,skincare,fitness"',
    )
    args = parser.parse_args()
    q_list = [x.strip() for x in args.queries.split(",")] if args.queries else None
    run_youtube_scraper(queries=q_list)
