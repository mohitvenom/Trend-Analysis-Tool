import os
import sys
import argparse
import pandas as pd
import requests
import time

from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logger import logger
from query_config import get_amazon_queries  # Reuse same query config
from country_config import COUNTRIES

# Load environment variables from scrapers/.env
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Load SerpAPI keys from env
serp_keys_str = os.getenv("SERP_API_KEYS", "")
SERP_API_KEYS = [k.strip() for k in serp_keys_str.split(",") if k.strip()]

if not SERP_API_KEYS:
    logger.warning("No SERP_API_KEYS found in .env, scraper may fail.")

OUTPUT_CSV = "outputs/ebay_trending.csv"
OUTPUT_JSON = "outputs/ebay_trending.json"

def fetch_serpapi_ebay_results(query, ebay_domain="ebay.co.uk"):
    """Fetch eBay search results using SerpApi with key rotation."""
    base_params = {
        "engine": "ebay",
        "_nkw": query,  # eBay uses _nkw for search query
        "ebay_domain": ebay_domain
    }
    
    for api_key in SERP_API_KEYS:
        params = base_params.copy()
        params["api_key"] = api_key
        
        try:
            logger.info(f"Fetching '{query}' on {ebay_domain} via SerpApi (Key: ...{api_key[-4:]})")
            response = requests.get("https://serpapi.com/search.json", params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if "error" in data:
                    logger.warning(f"SerpApi Error: {data['error']}")
                    continue
                return data.get("organic_results", [])
            elif response.status_code in (401, 403, 429):
                 logger.warning(f"SerpApi Key Exhausted/Invalid ({response.status_code}). Rotating...")
                 continue
            else:
                 logger.error(f"SerpApi HTTP Error: {response.status_code}")
                 
        except Exception as e:
            logger.error(f"Request Exception: {e}")
            
    logger.error("All SerpApi keys failed or exhausted.")
    return []

def run_ebay_scraper(queries=None):
    logger.info("eBay scraper started (Iceland via SerpApi)")
    
    user_queries = get_amazon_queries(queries)  # Reuse same queries
    if not user_queries:
        logger.warning("No queries provided.")
        return

    rows = []
    
    # Focus only on Iceland as the main market
    iceland_config = COUNTRIES.get("Iceland")
    if not iceland_config:
        logger.error("Iceland configuration not found!")
        return
    
    ebay_domain = "ebay.co.uk"  # UK eBay ships to Iceland
    market_type = iceland_config.get("market_type", "regional")
    
    logger.info(f"--- Processing Iceland ({ebay_domain}) ---")
    
    for q in user_queries:
        results = fetch_serpapi_ebay_results(q, ebay_domain=ebay_domain)
        
        if not results:
             logger.warning(f"No results found for '{q}' on eBay Iceland")
             continue
        
        # Limit to max 10 products per query
        results = results[:10]
             
        for i, item in enumerate(results):
            title = item.get("title", "N/A")
            link = item.get("link", "")
            
            # eBay pricing can be in different formats
            price_data = item.get("price")
            price = None
            if isinstance(price_data, dict):
                price = price_data.get("raw") or price_data.get("value")
            elif isinstance(price_data, (str, float, int)):
                price = price_data
            
            # eBay may have condition (new, used, etc.)
            condition = item.get("condition", "")
            
            # Simple trend score based on rank
            trend_score = max(1, 100 - i * 5)
            
            rows.append({
                "product_title": title,
                "product_url": link,
                "price": price,
                "condition": condition,
                "trend_score": trend_score,
                "country": "Iceland",
                "marketplace": "eBay",
                "market_type": market_type,
                "category": "Inferred from Query"
            })
            
        time.sleep(1)  # Polite delay between queries

    df = pd.DataFrame(rows)
    if not df.empty:
        df.to_csv(OUTPUT_CSV, index=False)
        df.to_json(OUTPUT_JSON, orient="records")
        logger.info(f"eBay scraper completed | records: {len(df)}")
    else:
        logger.warning("eBay scraper completed but found NO records.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape eBay trending products")
    parser.add_argument("--queries", nargs="+", help="Custom search queries")
    args = parser.parse_args()
    
    run_ebay_scraper(queries=args.queries)
