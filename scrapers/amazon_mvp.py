import os
import sys
import argparse
import pandas as pd
import requests
import time
import random

from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logger import logger
from query_config import get_amazon_queries
from country_config import COUNTRIES

# Load environment variables from scrapers/.env
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Load SerpAPI keys from env
serp_keys_str = os.getenv("SERP_API_KEYS", "")
SERP_API_KEYS = [k.strip() for k in serp_keys_str.split(",") if k.strip()]

if not SERP_API_KEYS:
    logger.warning("No SERP_API_KEYS found in .env, scraper may fail.")

OUTPUT_CSV = "outputs/amazon_trending.csv"
OUTPUT_JSON = "outputs/amazon_trending.json"

def fetch_serpapi_results(query, domain="amazon.com"):
    """Fetch Amazon search results using SerpApi with key rotation."""
    base_params = {
        "engine": "amazon",
        "k": query,
        "amazon_domain": domain
    }
    
    for api_key in SERP_API_KEYS:
        params = base_params.copy()
        params["api_key"] = api_key
        
        try:
            logger.info(f"Fetching '{query}' on {domain} via SerpApi (Key: ...{api_key[-4:]})")
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

def run_amazon_scraper(queries=None):
    logger.info("Amazon scraper started (Multi-Country via SerpApi)")
    
    user_queries = get_amazon_queries(queries)
    if not user_queries:
        logger.warning("No queries provided.")
        return

    rows = []
    
    # Focus only on Iceland as the main market
    iceland_config = COUNTRIES.get("Iceland")
    if not iceland_config:
        logger.error("Iceland configuration not found!")
        return
    
    domain = iceland_config.get("amazon_domain", "amazon.co.uk")
    market_type = iceland_config.get("market_type", "regional")
    
    logger.info(f"--- Processing Iceland ({domain}) ---")
    
    for q in user_queries:
            results = fetch_serpapi_results(q, domain=domain)
            
            if not results:
                 logger.warning(f"No results found for '{q}' in Iceland")
                 continue
            
            # Limit to max 10 products per query
            results = results[:10]
                 
            for i, item in enumerate(results):
                title = item.get("title", "N/A")
                link = item.get("link", "")
                
                # Ensure absolute URL
                if link.startswith("/"):
                    url = f"https://www.{domain}{link}"
                else:
                    url = link

                price_data = item.get("price")
                price = None
                if isinstance(price_data, dict):
                    price = price_data.get("value") # Extract numeric value if available
                elif isinstance(price_data, (str, float, int)):
                    price = price_data
                
                rating = item.get("rating")
                
                # Simple trend score based on rank
                trend_score = max(1, 100 - i * 5)
                
                rows.append({
                    "product_title": title,
                    "product_url": url,
                    "price": price,
                    "rating": rating,
                    "trend_score": trend_score,
                    "country": "Iceland",
                    "amazon_market_type": market_type,
                    "category": "Inferred from Query"
                })
                
            time.sleep(1) # Polite delay between queries per country

    def process_regional_countries(rows):
        # Optional: For regional countries, mapped to a local domain, we could duplicate
        # the local data or just let the dashboard handle it.
        # For now, we only save the scraped "local" data.
        pass

    df = pd.DataFrame(rows)
    if not df.empty:
        df.to_csv(OUTPUT_CSV, index=False)
        df.to_json(OUTPUT_JSON, orient="records")
        logger.info(f"Amazon scraper completed | records: {len(df)}")
    else:
        logger.warning("Amazon scraper completed but found NO records.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Amazon product scraper via SerpApi")
    parser.add_argument("--queries", type=str, help="Comma separated queries")
    args = parser.parse_args()
    
    q_list = [x.strip() for x in args.queries.split(",")] if args.queries else None
    run_amazon_scraper(queries=q_list)