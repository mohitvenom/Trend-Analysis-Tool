"""
Load user-defined queries from scraper_queries_config.json.
Edit that file to customize search queries, or pass via CLI/API.
"""
import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper_queries_config.json")

DEFAULTS = {
    "amazon_queries": [
        "wireless earbuds",
        "smart watch",
        "running shoes",
        "laptop backpack",
        "portable charger",
        "bluetooth speaker"
    ],
    "youtube_queries": [
        "best gadgets",
        "tech unboxing",
        "skincare review",
        "fitness equipment",
        "home essentials",
    ],
    "reddit_subreddits": {
        "tech": ["gadgets", "technology"],
        "shopping": ["deals", "BuyItForLife"],
        "fitness": ["fitness", "homegym"],
        "lifestyle": ["skincareaddiction", "malefashionadvice"],
    },
}


def load_config():
    """Load config from JSON file, fallback to defaults."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {**DEFAULTS, **data}
        except (json.JSONDecodeError, TypeError):
            pass
    return DEFAULTS.copy()


def get_amazon_queries(override=None):
    """Get Amazon search queries. override can be a list from CLI/API."""
    if override:
        return [q.strip() for q in override if q and str(q).strip()]
    return load_config().get("amazon_queries", DEFAULTS["amazon_queries"])


def get_youtube_queries(override=None):
    """Get YouTube search queries."""
    if override:
        return [q.strip() for q in override if q and str(q).strip()]
    return load_config().get("youtube_queries", DEFAULTS["youtube_queries"])


def get_reddit_subreddits(override=None):
    """
    Get Reddit subreddits. override can be:
    - dict: {"tech": ["gadgets"], "fitness": ["fitness"]}
    - or list of "vertical:sub1,sub2" strings
    """
    if override is not None:
        if isinstance(override, dict):
            return override
        if isinstance(override, (list, tuple)):
            result = {}
            for item in override:
                s = str(item).strip()
                if ":" in s:
                    vert, subs = s.split(":", 1)
                    result[vert.strip()] = [x.strip() for x in subs.split(",") if x.strip()]
            if result:
                return result
    return load_config().get("reddit_subreddits", DEFAULTS["reddit_subreddits"])


def save_queries(amazon_queries=None, youtube_queries=None, reddit_subreddits=None):
    """Save user queries to config file (for API updates)."""
    cfg = load_config()
    if amazon_queries is not None:
        cfg["amazon_queries"] = list(amazon_queries)
    if youtube_queries is not None:
        cfg["youtube_queries"] = list(youtube_queries)
    if reddit_subreddits is not None:
        cfg["reddit_subreddits"] = dict(reddit_subreddits)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
