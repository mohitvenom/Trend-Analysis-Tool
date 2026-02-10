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

OUTPUT_CSV = "outputs/aliexpress_trending.csv"
OUTPUT_JSON = "outputs/aliexpress_trending.json"

def fetch_serpapi_aliexpress_results(query):
    """Fetch AliExpress search results using SerpApi with key rotation."""
    base_params = {
        "engine": "aliexpress",
        "query": query,  # AliExpress uses 'query' parameter
    }
    
    for api_key in SERP_API_KEYS:
        params = base_params.copy()
        params["api_key"] = api_key
        
        try:
            logger.info(f"Fetching '{query}' on AliExpress via SerpApi (Key: ...{api_key[-4:]})")
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

def run_aliexpress_scraper(queries=None):
    logger.info("AliExpress scraper started (Global marketplace via SerpApi)")
    
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
    
    market_type = iceland_config.get("market_type", "regional")
    
    logger.info(f"--- Processing AliExpress (Global marketplace) ---")
    
    for q in user_queries:
        results = fetch_serpapi_aliexpress_results(q)
        
        if not results:
             logger.warning(f"No results found for '{q}' on AliExpress")
             continue
        
        # Limit to max 10 products per query
        results = results[:10]
             
        for i, item in enumerate(results):
            title = item.get("title", "N/A")
            link = item.get("link", "")
            
            # AliExpress pricing
            price_data = item.get("price")
            price = None
            if isinstance(price_data, dict):
                price = price_data.get("current") or price_data.get("value")
            elif isinstance(price_data, (str, float, int)):
                price = price_data
            
            # Rating information
            rating = item.get("rating")
            reviews = item.get("reviews")
            
            # Orders (popularity indicator)
            orders = item.get("orders", 0)
            
            # Simple trend score based on rank and orders
            trend_score = max(1, 100 - i * 5)
            if orders:
                # Boost score based on order volume
                try:
                    order_count = int(str(orders).replace("+", "").replace("k", "000").replace("K", "000"))
                    trend_score += min(order_count // 100, 50)
                except:
                    pass
            
            rows.append({
                "product_title": title,
                "product_url": link,
                "price": price,
                "rating": rating,
                "reviews": reviews,
                "orders": orders,
                "trend_score": trend_score,
                "country": "Iceland",
                "marketplace": "AliExpress",
                "market_type": market_type,
                "category": "Inferred from Query"
            })
            
        time.sleep(1)  # Polite delay between queries

    df = pd.DataFrame(rows)
    if not df.empty:
        df.to_csv(OUTPUT_CSV, index=False)
        df.to_json(OUTPUT_JSON, orient="records")
        logger.info(f"AliExpress scraper completed | records: {len(df)}")
    else:
        logger.warning("AliExpress scraper completed but found NO records.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape AliExpress trending products")
    parser.add_argument("--queries", nargs="+", help="Custom search queries")
    args = parser.parse_args()
    
    run_aliexpress_scraper(queries=args.queries)
