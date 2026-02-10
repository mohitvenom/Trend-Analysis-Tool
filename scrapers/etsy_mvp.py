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

# Etsy API credentials from environment
ETSY_API_KEY = os.getenv("ETSY_API_KEY")
ETSY_SHARED_SECRET = os.getenv("ETSY_SHARED_SECRET")

OUTPUT_CSV = "outputs/etsy_trending.csv"
OUTPUT_JSON = "outputs/etsy_trending.json"

def fetch_etsy_listings(query, limit=10):
    """Fetch Etsy listings using official Etsy API v3."""
    
    if not ETSY_API_KEY:
        logger.error("ETSY_API_KEY not found in environment variables!")
        return []
    
    # Etsy API v3 endpoint for searching listings
    url = "https://openapi.etsy.com/v3/public/listings/active"
    
    headers = {
        "x-api-key": ETSY_API_KEY,
    }
    
    params = {
        "keywords": query,
        "limit": limit,
        "sort_on": "score",  # Sort by relevance
        "sort_order": "desc"
    }
    
    try:
        logger.info(f"Fetching '{query}' from Etsy API v3")
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            logger.info(f"Found {len(results)} results for '{query}'")
            return results
        elif response.status_code == 401:
            logger.error(f"Etsy API authentication failed. Check your API key.")
            return []
        elif response.status_code == 403:
            logger.error(f"Etsy API access forbidden. You may need commercial access.")
            return []
        elif response.status_code == 429:
            logger.warning(f"Etsy API rate limit exceeded. Waiting...")
            time.sleep(5)
            return []
        else:
            logger.error(f"Etsy API HTTP Error: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        logger.error(f"Etsy API Request Exception: {e}")
        return []

def run_etsy_scraper(queries=None):
    logger.info("Etsy scraper started (Official API v3)")
    
    if not ETSY_API_KEY:
        logger.error("Etsy API credentials not configured. Please set ETSY_API_KEY in .env file")
        return
    
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
    
    logger.info(f"--- Processing Etsy (Global marketplace) ---")
    
    for q in user_queries:
        results = fetch_etsy_listings(q, limit=10)
        
        if not results:
             logger.warning(f"No results found for '{q}' on Etsy")
             continue
             
        for i, item in enumerate(results):
            # Extract listing details
            listing_id = item.get("listing_id")
            title = item.get("title", "N/A")
            
            # Build product URL
            url = f"https://www.etsy.com/listing/{listing_id}"
            
            # Price information
            price_data = item.get("price")
            price = None
            if price_data:
                # Price is in format like {"amount": 2500, "divisor": 100, "currency_code": "USD"}
                amount = price_data.get("amount", 0)
                divisor = price_data.get("divisor", 100)
                currency = price_data.get("currency_code", "USD")
                price = f"{currency} {amount / divisor:.2f}"
            
            # Shop information
            shop_id = item.get("shop_id")
            
            # Number of favorers (popularity indicator)
            num_favorers = item.get("num_favorers", 0)
            
            # Simple trend score based on rank and popularity
            trend_score = max(1, 100 - i * 5) + min(num_favorers // 10, 50)
            
            rows.append({
                "product_title": title,
                "product_url": url,
                "price": price,
                "shop_id": shop_id,
                "num_favorers": num_favorers,
                "trend_score": trend_score,
                "country": "Iceland",
                "marketplace": "Etsy",
                "market_type": market_type,
                "category": "Inferred from Query"
            })
            
        time.sleep(1)  # Polite delay between queries

    df = pd.DataFrame(rows)
    if not df.empty:
        df.to_csv(OUTPUT_CSV, index=False)
        df.to_json(OUTPUT_JSON, orient="records")
        logger.info(f"Etsy scraper completed | records: {len(df)}")
    else:
        logger.warning("Etsy scraper completed but found NO records.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Etsy trending products")
    parser.add_argument("--queries", nargs="+", help="Custom search queries")
    args = parser.parse_args()
    
    run_etsy_scraper(queries=args.queries)
