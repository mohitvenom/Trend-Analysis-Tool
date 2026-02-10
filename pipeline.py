import pandas as pd
import re
import os
from difflib import SequenceMatcher
from datetime import date

# =============================
# CONFIGURATION
# =============================
SAVE_HISTORY = True

OUTPUT_DIR = "outputs"
HISTORY_DIR = "history"

FINAL_OUTPUT = os.path.join(OUTPUT_DIR, "final_trending_products.csv")
DEDUP_OUTPUT = os.path.join(OUTPUT_DIR, "final_trending_products_deduped.csv")
HISTORY_FILE = os.path.join(HISTORY_DIR, "trend_history.csv")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)

# =============================
# STEP 1: LOAD & MERGE SOURCES
# =============================
def load_and_merge():
    # Increased limit to ensure all scraped URLs are included as per user request
    LIMIT_PER_SOURCE = 10000 
    
    dfs = []
    
    # 1. Amazon Data
    if os.path.exists("outputs/amazon_trending.csv"):
        amazon = pd.read_csv("outputs/amazon_trending.csv")
        if "trend_score" in amazon.columns:
            amazon = amazon.sort_values("trend_score", ascending=False).head(LIMIT_PER_SOURCE)
        
        amazon_df = amazon.rename(columns={
            "product_title": "item",
            "product_url": "url",
            "trend_score": "raw_score"
        })[["item", "raw_score", "url", "country", "amazon_market_type"]]
        amazon_df["source"] = "Amazon"
        dfs.append(amazon_df)

    # 2. eBay Data
    if os.path.exists("outputs/ebay_trending.csv"):
        ebay = pd.read_csv("outputs/ebay_trending.csv")
        if "trend_score" in ebay.columns:
            ebay = ebay.sort_values("trend_score", ascending=False).head(LIMIT_PER_SOURCE)
            
        # Rename columns to match schema
        ebay_df = ebay.rename(columns={
            "product_title": "item",
            "product_url": "url",
            "trend_score": "raw_score",
            "market_type": "amazon_market_type" # Aligning column name for aggregation
        })
        
        # Select common columns
        cols = ["item", "raw_score", "url", "country", "amazon_market_type"]
        ebay_df = ebay_df[cols]
        ebay_df["source"] = "eBay"
        dfs.append(ebay_df)

    if not dfs:
        return pd.DataFrame(columns=["item", "raw_score", "url", "country", "amazon_market_type", "source"])

    df = pd.concat(dfs, ignore_index=True)

    # Normalize per platform
    df["platform_relative_score"] = df.groupby("source")["raw_score"].transform(
        lambda x: (x - x.min()) / (x.max() - x.min()) * 100 if x.max() != x.min() else 0
    )

    return df

# =============================
# STEP 2: AGGREGATE + CONFIDENCE
# =============================
def aggregate_and_score(df):
    agg = (
        df.groupby(["item", "country", "amazon_market_type"], as_index=False)
          .agg(
              base_strength=("platform_relative_score", "sum"),
              platform_count=("source", "nunique"),
              sources=("source", lambda x: ", ".join(sorted(set(x)))),
              urls=("url", lambda x: list(set(x)))
          )
    )

    # Adjusted confidence for single source focus
    agg["confidence_multiplier"] = 1.0 # 1 + (agg["platform_count"] - 1) * 0.5
    agg["trend_strength"] = (agg["base_strength"] * agg["confidence_multiplier"]).round(2)

    return agg.sort_values("trend_strength", ascending=False)

# =============================
# STEP 3: DEDUPLICATION (UNCHANGED LOGIC)
# =============================
BRANDS = [
    "apple", "samsung", "sony", "nike", "adidas",
    "oneplus", "xiaomi", "boat", "jbl", "philips",
    "hp", "dell", "lenovo", "asus", "acer"
]

def normalize_text(text):
    text = text.lower()
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    text = re.sub(
        r"\b(review|unboxing|best|latest|new|official|vs|comparison|2022|2023|2024|2025)\b",
        "",
        text
    )
    return re.sub(r"\s+", " ", text).strip()

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def extract_brand(text):
    for brand in BRANDS:
        if brand in text:
            return brand
    return None

def deduplicate(df):
    df["normalized_item"] = df["item"].apply(normalize_text)
    df["brand"] = df["normalized_item"].apply(extract_brand)

    groups, used = [], set()

    for i, row in df.iterrows():
        if i in used:
            continue

        cluster = [i]
        for j, other in df.iterrows():
            if j == i or j in used:
                continue

            if row["country"] != other["country"]:
                continue

            score = similarity(row["normalized_item"], other["normalized_item"])
            same_brand = row["brand"] and row["brand"] == other["brand"]

            if score > 0.6 or (same_brand and score > 0.5):
                cluster.append(j)

        for idx in cluster:
            used.add(idx)

        groups.append(cluster)

    final_rows = []
    for cluster in groups:
        subset = df.loc[cluster]

        urls = []
        for u in subset["urls"]:
            if isinstance(u, list):
                urls.extend(u)
            elif isinstance(u, str):
                try:
                    urls.extend(eval(u))
                except Exception:
                    pass

        final_rows.append({
            "item": subset.iloc[0]["item"],
            "country": subset.iloc[0]["country"],
            "market_type": subset.iloc[0]["amazon_market_type"],
            "trend_strength": subset["trend_strength"].sum().round(2),
            "platform_count": subset["platform_count"].max(),
            # Rename sources to marketplace to match dashboard expectation
            "marketplace": ", ".join(sorted(set(", ".join(subset["sources"]).split(", ")))),
            "urls": list(set(urls))
        })

    return pd.DataFrame(final_rows).sort_values("trend_strength", ascending=False)

# =============================
# STEP 4: SNAPSHOT LIFECYCLE (UNCHANGED)
# =============================
def assign_lifecycle(df):
    def classify(row):
        if row["platform_count"] >= 2:
            return "Validated"
        if row["trend_strength"] >= 70:
            return "Rising"
        if row["trend_strength"] >= 40:
            return "Emerging"
        return "Watch"

    df["lifecycle_stage"] = df.apply(classify, axis=1)
    return df

# =============================
# STEP 5: OPTIONAL HISTORY SAVE
# =============================
def save_history(df):
    df = df.copy()
    df["snapshot_date"] = date.today().isoformat()

    if os.path.exists(HISTORY_FILE):
        history = pd.read_csv(HISTORY_FILE)
        df = pd.concat([history, df], ignore_index=True)

    df.to_csv(HISTORY_FILE, index=False)

# =============================
# MAIN PIPELINE
# =============================
def run_pipeline():
    print("Pipeline started")

    merged = load_and_merge()
    scored = aggregate_and_score(merged)
    deduped = deduplicate(scored)
    lifecycle = assign_lifecycle(deduped)

    lifecycle.to_csv(DEDUP_OUTPUT, index=False)

    if SAVE_HISTORY:
        save_history(lifecycle)

    print("Pipeline complete | Records:", len(lifecycle))

if __name__ == "__main__":
    run_pipeline()
