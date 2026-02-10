COUNTRIES = {
    # --------------------
    # Local marketplaces
    # --------------------
    "India": {"amazon_domain": "amazon.in", "market_type": "local"},
    "UAE": {"amazon_domain": "amazon.ae", "market_type": "local"},
    "UK": {"amazon_domain": "amazon.co.uk", "market_type": "local"},
    "Germany": {"amazon_domain": "amazon.de", "market_type": "local"},
    "France": {"amazon_domain": "amazon.fr", "market_type": "local"},
    "Italy": {"amazon_domain": "amazon.it", "market_type": "local"},
    "Spain": {"amazon_domain": "amazon.es", "market_type": "local"},
    "Netherlands": {"amazon_domain": "amazon.nl", "market_type": "local"},
    "Sweden": {"amazon_domain": "amazon.se", "market_type": "local"},
    "Poland": {"amazon_domain": "amazon.pl", "market_type": "local"},
    "Japan": {"amazon_domain": "amazon.co.jp", "market_type": "local"},
    "Australia": {"amazon_domain": "amazon.com.au", "market_type": "local"},
    "USA": {"amazon_domain": "amazon.com", "market_type": "local"},
    "Canada": {"amazon_domain": "amazon.ca", "market_type": "local"},
    "Brazil": {"amazon_domain": "amazon.com.br", "market_type": "local"},
    "Mexico": {"amazon_domain": "amazon.com.mx", "market_type": "local"},
    "Singapore": {"amazon_domain": "amazon.sg", "market_type": "local"},
    "Saudi": {"amazon_domain": "amazon.sa", "market_type": "local"},
    "Turkey": {"amazon_domain": "amazon.com.tr", "market_type": "local"},

    # --------------------
    # Aggregated local market
    # --------------------
    "Europe": {
        "amazon_domain": "EU_AGGREGATED",
        "market_type": "local"
    },

    # --------------------
    # Regional / inferred
    # --------------------
    "Iceland": {"amazon_domain": "amazon.co.uk", "market_type": "regional"},
    "Nigeria": {"amazon_domain": "amazon.com", "market_type": "regional"},
    "Ghana": {"amazon_domain": "amazon.com", "market_type": "regional"},
    "Kenya": {"amazon_domain": "amazon.com", "market_type": "regional"},
    "South Africa": {"amazon_domain": "amazon.com", "market_type": "regional"},
    "Bangladesh": {"amazon_domain": "amazon.in", "market_type": "regional"},
    "Sri Lanka": {"amazon_domain": "amazon.in", "market_type": "regional"},
    "Egypt": {"amazon_domain": "amazon.ae", "market_type": "regional"},
    "Qatar": {"amazon_domain": "amazon.ae", "market_type": "regional"},
    "Kuwait Abroad": {"amazon_domain": "amazon.ae", "market_type": "regional"},
    "Oman": {"amazon_domain": "amazon.ae", "market_type": "regional"},
    "Jordan": {"amazon_domain": "amazon.ae", "market_type": "regional"},
    "Indonesia": {"amazon_domain": "amazon.sg", "market_type": "regional"},
    "Malaysia": {"amazon_domain": "amazon.sg", "market_type": "regional"},
    "Thailand": {"amazon_domain": "amazon.sg", "market_type": "regional"},
    "Vietnam": {"amazon_domain": "amazon.sg", "market_type": "regional"},
}

# --------------------
# SERP Target Domains (Competitor Sites)
# --------------------
# These are used to filter SERP results for "trending" products on other platforms.
TARGET_DOMAINS = {
    "India": ["amazon.in", "flipkart.com", "myntra.com", "ajio.com", "meesho.com"],
    "UAE": ["amazon.ae", "noon.com", "sharafdg.com", "carrefouruae.com"],
    "USA": ["amazon.com", "walmart.com", "ebay.com", "bestbuy.com", "target.com"],
    "UK": ["amazon.co.uk", "ebay.co.uk", "argos.co.uk", "johnlewis.com"],
    "Iceland": ["asos.com", "amazon.co.uk", "boozt.com", "elko.is"],

    # Defaults for others
    "Global": ["amazon.com", "ebay.com", "aliexpress.com", "etsy.com"]
}

def get_target_domains(country_name):
    """Return specific domains for a country or fall back to Global/Amazon."""
    return TARGET_DOMAINS.get(country_name, TARGET_DOMAINS["Global"] + [COUNTRIES.get(country_name, {}).get("amazon_domain", "amazon.com")])

