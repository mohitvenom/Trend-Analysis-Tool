from fastapi import FastAPI, BackgroundTasks, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pandas as pd
import json
import os
from typing import List, Optional, Dict, Any
import pipeline
import festival_product_discovery as festival_module

from pydantic import BaseModel, Field

class FestivalFetchRequest(BaseModel):
    countries: Optional[List[str]] = Field(
        None, 
        description="List of countries to fetch data for.",
        examples=[["India", "USA"]]
    )
    festival_filter: Optional[Dict[str, List[str]]] = Field(
        None,
        description="Dictionary mapping Country Name to a list of specific Festivals to filter.",
        examples=[{"India": ["Diwali", "Holi"], "UAE": ["Christmas"]}]
    )


class PipelineRunRequest(BaseModel):
    queries: Optional[List[str]] = Field(
        None,
        description="Search queries for Amazon & YouTube, e.g. ['headphones', 'air fryer'].",
    )
    subreddits: Optional[Dict[str, List[str]]] = Field(
        None,
        description="Reddit subreddits by vertical, e.g. {'tech': ['gadgets'], 'fitness': ['fitness']}.",
    )


class QueriesUpdateRequest(BaseModel):
    amazon_queries: Optional[List[str]] = None
    youtube_queries: Optional[List[str]] = None
    reddit_subreddits: Optional[Dict[str, List[str]]] = None


class FestivalSearchRequest(BaseModel):
    keyword: str = Field(..., description="Search keyword for Amazon (e.g. 'diwali gifts')")
    festival_name: str = Field(..., description="Name of the festival (e.g. 'Diwali')")
    country: str = Field(
        ...,
        description="Country name or Amazon domain (e.g. 'India' or 'amazon.in')",
    )


app = FastAPI(
    title="Trend Intelligence API",
    description="API for accessing global trend intelligence data and triggering collection pipelines.",
    version="1.0.0"
)

# Enable CORS for Streamlit Cloud connectivity
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Constants
OUTPUT_DIR = "outputs"
FINAL_OUTPUT_FILE = os.path.join(OUTPUT_DIR, "final_trending_products_deduped.csv")
FESTIVAL_OUTPUT_FILE = "festival_trending_products.json"

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/queries")
def get_queries():
    """Get current scraper queries configuration."""
    try:
        from query_config import load_config
        return load_config()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/queries")
def update_queries(
    amazon_queries: Optional[List[str]] = Body(None),
    youtube_queries: Optional[List[str]] = Body(None),
    reddit_subreddits: Optional[Dict[str, List[str]]] = Body(None),
):
    """Update scraper queries (saved to scraper_queries_config.json)."""
    try:
        from query_config import save_queries, load_config
        save_queries(
            amazon_queries=amazon_queries,
            youtube_queries=youtube_queries,
            reddit_subreddits=reddit_subreddits,
        )
        return {"message": "Queries updated", "config": load_config()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trends")
def get_trends(
    country: Optional[str] = Query(None, description="Filter by country"),
    category: Optional[str] = Query(None, description="Filter by category (inferred)"),
    limit: int = Query(50, description="Max number of records to return")
):
    """
    Retrieve trending products from the deduplicated output CSV.
    """
    if not os.path.exists(FINAL_OUTPUT_FILE):
        raise HTTPException(status_code=404, detail="Trend data not found. Please run the pipeline first.")
    
    try:
        df = pd.read_csv(FINAL_OUTPUT_FILE)
        
        # Apply filters
        if country:
            df = df[df["country"].str.lower() == country.lower()]

        # Fill missing market_type with 'Global' for Reddit/YouTube items
        if "market_type" in df.columns:
            df["market_type"] = df["market_type"].fillna("Global")
        else:
            df["market_type"] = "Global"
            
        # Category inference (reusing logic from dashboard or just relying on what's available if we saved it)
        # The CSV might not have 'category' column if it was only calculated in dashboard.py.
        # Let's check if we need to add category inference here or if we should update pipeline to save it.
        # For now, let's include the simple inference logic here to ensure filtering works as expected by the dashboard logic.
        
        CATEGORY_KEYWORDS = {
            "Electronics": ["earbuds", "headphone", "laptop", "phone", "camera", "charger", "smart", "tech", "device", "usb", "cable"],
            "Fitness": ["fitness", "gym", "workout", "dumbbell", "yoga", "treadmill", "protein", "supplement", "weight", "training", "sport", "mat", "bottle"],
            "Beauty": ["skincare", "serum", "cream", "beauty", "makeup", "shampoo", "conditioner", "soap", "lotion", "perfume", "fragrance", "oil", "balm"],
            "Fashion": ["shoes", "sneaker", "watch", "jacket", "clothing", "sweater", "hoodie", "shirt", "pants", "dress", "jeans", "coat", "wool", "wear"],
            "Home & Kitchen": ["kitchen", "mixer", "cookware", "vacuum", "air fryer", "decor", "light", "lamp", "desk", "chair", "organizer", "cup", "muga"]
        }

        def infer_category(item):
            text = str(item).lower()
            for cat, keywords in CATEGORY_KEYWORDS.items():
                if any(k in text for k in keywords):
                    return cat
            return "Others"

        if "category" not in df.columns:
            df["category"] = df["item"].apply(infer_category)

        if category:
             df = df[df["category"].str.lower() == category.lower()]
             
        # Normalize urls field from string representation of list to actual list
        # The CSV saves lists as strings like "['url1', 'url2']"
        def parse_urls(url_str):
            try:
                # Basic safety check before eval or use json.loads if format allows
                # given the previous code used eval(), we might need to be careful.
                # Ideally, we should fix the pipeline to save as valid JSON string or handle it safely.
                # For this MVP, we'll try basic string manipulation or ast.literal_eval
                import ast
                return ast.literal_eval(url_str)
            except:
                return []

        if "urls" in df.columns:
             df["urls"] = df["urls"].apply(parse_urls)

        # Sort and limit
        if "trend_strength" in df.columns:
            df = df.sort_values("trend_strength", ascending=False)
            
        # Handle NaN values automatically via to_json (NaN -> null)
        data = json.loads(df.head(limit).to_json(orient="records"))
        return data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading trend data: {str(e)}")

@app.get("/festivals")
def get_festivals(
    country: Optional[str] = Query(None, description="Filter by country")
):
    """
    Retrieve festival trend data.
    """
    if not os.path.exists(FESTIVAL_OUTPUT_FILE):
         raise HTTPException(status_code=404, detail="Festival data not found.")
         
    try:
        with open(FESTIVAL_OUTPUT_FILE, "r") as f:
            data = json.load(f)
            
        if country:
            data = [item for item in data if item.get("country", "").lower() == country.lower()]
            
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading festival data: {str(e)}")

@app.post("/pipeline/run")
def trigger_pipeline(
    background_tasks: BackgroundTasks,
    request: Optional[PipelineRunRequest] = Body(None),
):
    """
    Trigger the main trend analysis pipeline in the background.
    Optionally pass custom queries for scrapers in the request body.
    """
    queries_str = None
    subreddits_str = None
    if request:
        if request.queries:
            import query_config
            query_config.save_queries(
                amazon_queries=request.queries,
                youtube_queries=request.queries,
            )
            queries_str = ",".join(request.queries)
        if request.subreddits:
            import query_config
            query_config.save_queries(reddit_subreddits=request.subreddits)
            subreddits_str = ";".join(
                f"{k}:{','.join(v)}" for k, v in request.subreddits.items()
            )

    def run_full_pipeline():
        import subprocess
        import run_all
        steps = run_all.build_steps(queries=queries_str, subreddits=subreddits_str)
        for step_name, cmd in steps:
            result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
            if result.returncode != 0:
                return

    background_tasks.add_task(run_full_pipeline)
    msg = "Pipeline started in background"
    if queries_str:
        msg += f" with queries: {queries_str}"
    return {"message": msg}

@app.post("/festivals/fetch")
def fetch_festivals(request: FestivalFetchRequest, background_tasks: BackgroundTasks):
    """
    Trigger the festival product discovery pipeline for specific countries.
    """
    target_countries = set(request.countries) if request.countries else None
    
    # Convert list to set for internal logic of festival module
    festival_filter = None
    if request.festival_filter:
        festival_filter = {k: set(v) for k, v in request.festival_filter.items()}
        
    def run_wrapper():
        # Wrapper to handle the actual execution and file saving which is normally done in __main__ block of the script
        # The run_pipeline function returns results but doesn't save them inside the function itself unless we modifying it.
        # Checking festival_product_discovery.py:
        # It returns 'output'. The saving logic is in `if __name__ == "__main__":`.
        # We need to reimplement the saving logic here or extract it.
        
        results = festival_module.run_pipeline(target_countries=target_countries, festival_filter=festival_filter)
        
        # Mock logic if needed (matching the script's behavior)
        if festival_module.USE_MOCK_IF_NO_RESULTS and len(results) == 0:
             seasonal_data = festival_module.load_seasonal_data("seasonal_config.json")
             results = festival_module._mock_products(seasonal_data)
        
        # Save results
        existing = festival_module._load_existing_results("festival_trending_products.json")
        combined = festival_module._dedupe_results(existing + results)
        with open("festival_trending_products.json", "w", encoding="utf-8") as f:
            json.dump(combined, f, indent=2)
            
    background_tasks.add_task(run_wrapper)
    
    msg = "Festival fetch started"
    if target_countries:
        msg += f" for countries: {', '.join(target_countries)}"
    return {"message": msg}


@app.post("/festivals/search")
def festival_search(request: FestivalSearchRequest, background_tasks: BackgroundTasks):
    """
    User-driven festival search: keyword + festival name + Amazon country.
    Results are saved to festival_trending_products.json and appear in Festival Intelligence.
    """
    def run_search():
        festival_module.run_custom_festival_search(
            keyword=request.keyword,
            festival_name=request.festival_name,
            country=request.country,
        )

    background_tasks.add_task(run_search)
    return {
        "message": f"Festival search started for '{request.keyword}' on {request.country}",
    }