import json

import random
import requests
import argparse
from datetime import datetime, timedelta, timezone
from country_config import COUNTRIES

import os
from dotenv import load_dotenv

# Load environment variables from scrapers/.env
load_dotenv(os.path.join(os.path.dirname(__file__), 'scrapers', '.env'))

# Map seasonal_config country names to COUNTRIES keys when they differ
COUNTRY_ALIASES = {"Saudi Arabia": "Saudi", "United Kingdom": "UK", "United Arab Emirates": "UAE"}

# Load SerpAPI keys from env
serp_keys_str = os.getenv("SERP_API_KEYS", "")
SERP_API_KEYS = [k.strip() for k in serp_keys_str.split(",") if k.strip()]
SERP_ENDPOINT = "https://serpapi.com/search.json"

# URGENT: skip date filter so all festivals are considered (seasonal_config uses 2026; SerpAPI may fail on some domains)
SKIP_DATE_FILTER = True
MAX_PRODUCTS_PER_COUNTRY = 5  # fast mode: fewer per country
# Safety cap: allow some misses per country (e.g. empty results) without hanging forever.
MAX_FETCH_ATTEMPTS_PER_COUNTRY = 10  # fast mode: fewer attempts
MAX_EMPTY_RESULTS_PER_DOMAIN = 2  # move to next domain quickly if nothing comes back
USE_MOCK_IF_NO_RESULTS = True  # if SerpAPI returns nothing, add sample rows so JSON has structure
DEBUG_SERP = False
TARGET_COUNTRIES = None  # set by CLI args (None = allow all countries)

DATE_WINDOW_PAST_DAYS = 7
DATE_WINDOW_FUTURE_DAYS = 180


def _is_quota_or_rate_limit_error(status_code, data):
    if status_code in (401, 403, 429):
        return True
    msg = (data.get("error") or data.get("message") or "")
    msg_l = str(msg).lower()
    # Typical SerpAPI limit/quota wording
    return any(
        token in msg_l
        for token in (
            "exhausted",
            "monthly searches",
            "plan",
            "quota",
            "rate limit",
            "too many requests",
            "limit",
        )
    )


def load_seasonal_data(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def is_festival_near(start, end):
    if SKIP_DATE_FILTER:
        return True
    today = datetime.now(timezone.utc).date()
    window_start = today - timedelta(days=DATE_WINDOW_PAST_DAYS)
    window_end = today + timedelta(days=DATE_WINDOW_FUTURE_DAYS)
    return not (end < window_start or start > window_end)

def resolve_amazon_domain(country):
    c = COUNTRY_ALIASES.get(country, country)
    config = COUNTRIES.get(c)
    if not config:
        return None
    return config["amazon_domain"]

def _parse_product(top):
    if not top or not isinstance(top, dict):
        return None
    price = top.get("price")
    if not price and top.get("prices") and isinstance(top["prices"], list) and top["prices"]:
        price = (top["prices"][0].get("raw") or top["prices"][0].get("value")) if top["prices"] else None
    return {
        "product_title": top.get("title") or top.get("product_title"),
        "product_url": top.get("link") or top.get("url") or top.get("product_link"),
        "price": price,
        "rating": top.get("rating"),
        "is_prime": top.get("is_prime", False),
    }

def fetch_top_amazon_product(keyword, amazon_domain):
    products = fetch_amazon_products(keyword, amazon_domain, limit=1)
    return products[0] if products else None


def fetch_amazon_products(keyword, amazon_domain, limit=8, sort_by_bestsellers=False):
    """Fetch up to `limit` products from Amazon search (SerpAPI).
    If sort_by_bestsellers=True, uses Best Sellers sort (s=exact-aware-popularity-rank).
    """
    for domain in (amazon_domain, "amazon.com"):
        base_params = {"engine": "amazon", "amazon_domain": domain, "k": keyword}
        if sort_by_bestsellers:
            base_params["s"] = "exact-aware-popularity-rank"

        keys = SERP_API_KEYS or []
        if not keys:
            return []
        empty_results = 0
        for key_idx, api_key in enumerate(keys):
            params = dict(base_params)
            params["api_key"] = api_key
            try:
                response = requests.get(SERP_ENDPOINT, params=params, timeout=8)
                status = response.status_code
                data = response.json()
            except (requests.RequestException, ValueError):
                if DEBUG_SERP:
                    print(f"[SerpAPI exception] domain={domain} keyword={keyword!r} key_idx={key_idx}")
                continue

            if data.get("error") and _is_quota_or_rate_limit_error(status, data):
                if DEBUG_SERP:
                    print(f"[SerpAPI rotate key] domain={domain} keyword={keyword!r} key_idx={key_idx} -> {data.get('error')}")
                continue
            if status >= 400 or data.get("error"):
                if DEBUG_SERP:
                    print(f"[SerpAPI error] domain={domain} keyword={keyword!r} key_idx={key_idx} status={status} -> {data.get('error')}")
                break

            results = (
                data.get("organic_results")
                or data.get("product_results")
                or data.get("shopping_results")
                or (data.get("products") if isinstance(data.get("products"), list) else None)
                or []
            )
            if not results:
                empty_results += 1
                if empty_results >= MAX_EMPTY_RESULTS_PER_DOMAIN:
                    break
                continue

            # Parse all results, then prioritize Prime products (more likely to ship internationally)
            parsed_products = []
            seen_urls = set()
            for item in results[:limit * 3]:
                if not isinstance(item, dict):
                    continue
                parsed = _parse_product(item)
                if not parsed or (not parsed.get("product_title") and not parsed.get("product_url")):
                    continue
                url = parsed.get("product_url")
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)
                parsed_products.append(parsed)

            # Sort: Prime products first (more likely to ship to various locations)
            parsed_products.sort(key=lambda p: (not p.get("is_prime", False)))
            output = parsed_products[:limit]
            if output:
                return output
            break
    return []

def _parse_festival_filter(value):
    """
    Parse a string like:
      "Iceland:Festival A,Festival B;Poland:Easter,Christmas"
    into:
      {"Iceland": {"Festival A", "Festival B"}, "Poland": {"Easter", "Christmas"}}
    """
    if not value:
        return {}
    country_map = {}
    parts = [p.strip() for p in value.split(";") if p.strip()]
    for part in parts:
        if ":" not in part:
            continue
        country, festivals = part.split(":", 1)
        country = country.strip()
        fest_list = [f.strip() for f in festivals.split(",") if f.strip()]
        if country and fest_list:
            country_map[country] = set(fest_list)
    return country_map


def run_pipeline(target_countries=None, festival_filter=None):
    seasonal_data = load_seasonal_data("seasonal_config.json")
    output = []

    for country, country_data in seasonal_data.items():
        if target_countries and country not in target_countries:
            continue
        festivals = (country_data.get("festivals") or []) if isinstance(country_data, dict) else []

        amazon_domain = resolve_amazon_domain(country)
        if not amazon_domain or amazon_domain == "EU_AGGREGATED":
            continue

        # Pre-filter eligible festivals for this country.
        eligible = []
        for festival in festivals:
            if not isinstance(festival, dict):
                continue
            try:
                start = datetime.strptime(
                    festival.get("expected_start_date") or "", "%Y-%m-%d"
                ).date()
                end = datetime.strptime(
                    festival.get("expected_end_date") or "", "%Y-%m-%d"
                ).date()
            except (ValueError, TypeError):
                continue
            if not is_festival_near(start, end):
                continue
            # If a festival filter is provided, enforce it.
            if festival_filter:
                allowed = festival_filter.get(country)
                if allowed and festival.get("festival_name") not in allowed:
                    continue
            keywords = festival.get("related_keywords") or []
            if not keywords:
                continue
            eligible.append(festival)

        if not eligible:
            continue

        country_products = 0
        attempts = 0
        seen_urls = set()
        while country_products < MAX_PRODUCTS_PER_COUNTRY and attempts < MAX_FETCH_ATTEMPTS_PER_COUNTRY:
            attempts += 1
            festival = random.choice(eligible)
            keywords = festival.get("related_keywords") or []
            keyword = random.choice(keywords)
            product = fetch_top_amazon_product(keyword, amazon_domain)
            if not product:
                continue

            url = product.get("product_url")
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)

            output.append({
                "country": country,
                "festival_name": festival.get("festival_name", "?"),
                "keyword_used": keyword,
                "amazon_domain": amazon_domain,
                "product_title": product.get("product_title"),
                "price": product.get("price"),
                "rating": product.get("rating"),
                "product_url": url,
                "fetch_timestamp": datetime.now(timezone.utc).isoformat()
            })
            country_products += 1

    return output


def _mock_products(seasonal_data):
    """Return a few sample rows when SerpAPI gives no results (e.g. Amazon not on plan)."""
    out = []
    for country, country_data in list(seasonal_data.items())[:3]:
        festivals = (country_data.get("festivals") or []) if isinstance(country_data, dict) else []
        domain = resolve_amazon_domain(country)
        if not domain or domain == "EU_AGGREGATED":
            continue
        for f in festivals[:2]:
            if not isinstance(f, dict):
                continue
            kw = (f.get("related_keywords") or [f.get("festival_name", "")])[0]
            out.append({
                "country": country,
                "festival_name": f.get("festival_name", "?"),
                "keyword_used": kw,
                "amazon_domain": domain,
                "product_title": f"[MOCK] Top result for '{kw}' on {domain}",
                "price": None,
                "rating": None,
                "product_url": f"https://www.{domain}/s?k={kw.replace(' ', '+')}",
                "fetch_timestamp": datetime.now(timezone.utc).isoformat(),
                "_mock": True
            })
            if len(out) >= 5:
                return out
    return out


def _load_existing_results(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        return []
    return []


def _dedupe_results(items):
    """Deduplicate by (country, product_url) to avoid repeats across runs."""
    seen = set()
    deduped = []
    for item in items:
        if not isinstance(item, dict):
            continue
        key = (item.get("country"), item.get("product_url"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _parse_countries_arg(value):
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    return {c.strip() for c in value.split(",") if c.strip()}


def run_custom_festival_search(keyword, festival_name, country):
    """
    User-driven festival search: keyword + festival name + Amazon country/domain.
    Runs SerpAPI Amazon search and appends results to festival_trending_products.json.
    """
    amazon_domain = None
    country_label = country

    # Resolve country name to amazon domain
    c = COUNTRY_ALIASES.get(country, country)
    if c in COUNTRIES:
        amazon_domain = COUNTRIES[c]["amazon_domain"]
        country_label = c
    else:
        # User might have passed raw domain like "amazon.in"
        domain_clean = str(country).strip().lower()
        if domain_clean.startswith("amazon.") or domain_clean == "amazon.com":
            amazon_domain = domain_clean if "." in domain_clean else "amazon.com"
            # Infer country label from domain
            for cnt, meta in COUNTRIES.items():
                if meta.get("amazon_domain") == amazon_domain:
                    country_label = cnt
                    break

    if not amazon_domain or amazon_domain == "EU_AGGREGATED":
        return []

    products = fetch_amazon_products(keyword, amazon_domain, limit=8, sort_by_bestsellers=True)
    if not products:
        return []

    output = []
    for product in products:
        output.append({
            "country": country_label,
            "festival_name": festival_name or "Custom",
            "keyword_used": keyword,
            "amazon_domain": amazon_domain,
            "product_title": product.get("product_title"),
            "price": product.get("price"),
            "rating": product.get("rating"),
            "product_url": product.get("product_url"),
            "is_prime": product.get("is_prime", False),
            "fetch_timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # Append to existing file and dedupe
    existing = _load_existing_results("festival_trending_products.json")
    combined = _dedupe_results(existing + output)
    with open("festival_trending_products.json", "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2)

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch festival-related products via SerpAPI.")
    parser.add_argument("--country", type=str, default=None, help="Single country name (e.g. 'Iceland').")
    parser.add_argument("--countries", type=str, default=None, help="Comma-separated list (e.g. 'Iceland,India').")
    parser.add_argument(
        "--festival-filter",
        type=str,
        default=None,
        help="Filter festivals per country, e.g. \"Iceland:Reykjavik Culture Night,Winter Lights Festival;Poland:Easter Sunday\"",
    )
    args = parser.parse_args()

    target = _parse_countries_arg(args.countries) or (_parse_countries_arg(args.country))
    festival_filter = _parse_festival_filter(args.festival_filter)

    results = run_pipeline(target_countries=target, festival_filter=festival_filter)
    if USE_MOCK_IF_NO_RESULTS and len(results) == 0:
        seasonal_data = load_seasonal_data("seasonal_config.json")
        results = _mock_products(seasonal_data)
        print("SerpAPI returned no products; added MOCK samples. Check API key / Amazon plan.")

    # Append to existing file instead of overwriting, then dedupe.
    existing = _load_existing_results("festival_trending_products.json")
    combined = _dedupe_results(existing + results)
    with open("festival_trending_products.json", "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2)
    print(f"Fetched {len(results)} new festival products; total stored: {len(combined)} -> festival_trending_products.json")
