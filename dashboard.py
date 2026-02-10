import streamlit as st
import pandas as pd
import requests
import altair as alt
import ast
import os
import json

# =========================
# Page Configuration
# =========================
st.set_page_config(
    page_title="Trend Intelligence Command Center",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #ff4b4b;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: transparent;
        border-bottom: 2px solid #ff4b4b;
    }
</style>
""", unsafe_allow_html=True)

# API Configuration
# Initialize session state for API URL if not present
if "api_url" not in st.session_state:
    st.session_state.api_url = "http://127.0.0.1:8000"

# Sidebar configuration for API URL
with st.sidebar:
    st.divider()
    with st.expander("🔌 Connection Settings"):
        new_api_url = st.text_input("Backend API URL", value=st.session_state.api_url, help="Enter ngrok URL if running remotely")
        if new_api_url != st.session_state.api_url:
            st.session_state.api_url = new_api_url
            st.rerun()

API_BASE_URL = st.session_state.api_url
OUTPUT_DIR = "outputs"
FINAL_OUTPUT_FILE = os.path.join(OUTPUT_DIR, "final_trending_products_deduped.csv")
FESTIVAL_OUTPUT_FILE = "festival_trending_products.json"

# =========================
# Helpers
# =========================
def normalize_urls(value):
    if isinstance(value, list):
        return [u for u in value if isinstance(u, str) and u.strip()]
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
            if isinstance(parsed, list):
                return [u for u in parsed if isinstance(u, str) and u.strip()]
        except Exception:
            return []
    return []

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

# =========================
# Data Loading
# =========================
@st.cache_data(ttl=60)
def fetch_trends(country=None):
    # Try API first
    try:
        params = {"limit": 2000}
        if country and country != "All":
            params["country"] = country
        
        response = requests.get(f"{API_BASE_URL}/trends", params=params, timeout=2)
        response.raise_for_status()
        return pd.DataFrame(response.json())
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException):
        # Fallback to local file
        if os.path.exists(FINAL_OUTPUT_FILE):
            try:
                df = pd.read_csv(FINAL_OUTPUT_FILE)
                if country and country != "All":
                    df = df[df["country"].str.lower() == country.lower()]
                
                # Apply same processing as API
                if "market_type" not in df.columns:
                    df["market_type"] = "Global"
                else:
                     df["market_type"] = df["market_type"].fillna("Global")

                if "category" not in df.columns:
                    df["category"] = df["item"].apply(infer_category)
                
                if "urls" in df.columns:
                    df["urls"] = df["urls"].apply(normalize_urls)
                    
                return df
            except Exception as e:
                st.error(f"Error reading local file: {e}")
                return pd.DataFrame()
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def fetch_festivals(country=None):
    try:
        params = {}
        if country and country != "All":
            params["country"] = country
        response = requests.get(f"{API_BASE_URL}/festivals", params=params, timeout=2)
        if response.status_code == 404: return pd.DataFrame()
        response.raise_for_status()
        return pd.DataFrame(response.json())
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException):
        # Fallback
        if os.path.exists(FESTIVAL_OUTPUT_FILE):
            try:
                with open(FESTIVAL_OUTPUT_FILE, "r") as f:
                    data = json.load(f)
                if country and country != "All":
                    data = [item for item in data if item.get("country", "").lower() == country.lower()]
                return pd.DataFrame(data)
            except Exception:
                return pd.DataFrame()
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def check_api_health():
    try:
        # Strip trailing slash from API_BASE_URL to avoid double slashes
        base_url = API_BASE_URL.rstrip("/")
        # Increase timeout to 15s for Render cold starts
        r = requests.get(f"{base_url}/health", timeout=15)
        return r.status_code == 200
    except:
        return False

# =========================
# Sidebar
# =========================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3094/3094918.png", width=50) # Placeholder Icon
    st.title("Trend Command")
    
    # API Status
    api_ok = check_api_health()
    if api_ok:
        st.success("✅ System Online")
    else:
        st.warning("⚠️ Standalone Mode")
        st.caption("Backend unavailable. Viewing cached data.")

    st.divider()
    
    st.subheader("Global Filters")
    # Load Data for Filters
    df = fetch_trends()
    
    if df.empty:
        st.warning("No data found.")
        selected_country = "All"
        selected_categories = []
        selected_market = []
        selected_lifecycle = []
    else:
        # Country Filter
        all_countries = sorted(df["country"].dropna().unique().tolist())
        selected_country = st.selectbox("Geography", ["All"] + all_countries)
        
        # Category Filter
        if "category" not in df.columns: df["category"] = "Others"
        cats = sorted(df["category"].dropna().unique().tolist())
        selected_categories = st.multiselect("Category", cats, default=cats)
        
        # Market Type
        if "market_type" in df.columns:
            mkts = sorted(df["market_type"].dropna().unique().tolist())
            selected_market = st.multiselect("Market Type", mkts, default=mkts)
        else:
            selected_market = []
        
        # Marketplace Filter (Amazon, eBay, etc.)
        if "marketplace" in df.columns:
            marketplaces = sorted(df["marketplace"].dropna().unique().tolist())
            selected_marketplaces = st.multiselect("Marketplace", marketplaces, default=marketplaces)
        else:
            selected_marketplaces = []
            
        # Lifecycle
        if "lifecycle_stage" in df.columns:
            stages = sorted(df["lifecycle_stage"].dropna().unique().tolist())
            selected_lifecycle = st.multiselect("Lifecycle", stages, default=stages)
        else:
            selected_lifecycle = []


# Main Filtering Logic
# =========================
if not df.empty:
    filtered_df = df.copy()
    if selected_country != "All":
        filtered_df = filtered_df[filtered_df["country"] == selected_country]
    
    if selected_categories:
        filtered_df = filtered_df[filtered_df["category"].isin(selected_categories)]
    if selected_market and "market_type" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["market_type"].isin(selected_market)]
    if selected_marketplaces and "marketplace" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["marketplace"].isin(selected_marketplaces)]
    if selected_lifecycle and "lifecycle_stage" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["lifecycle_stage"].isin(selected_lifecycle)]
else:
    filtered_df = pd.DataFrame()

# =========================
# Application Tabs
# =========================
tab_overview, tab_market, tab_festival, tab_ops = st.tabs([
    "📊 Executive Overview", 
    "🛍️ Market Intelligence", 
    "🎉 Festival Radar", 
    "⚙️ Operations Center"
])

# -------------------------
# TAB 1: EXECUTIVE OVERVIEW
# -------------------------
with tab_overview:
    if filtered_df.empty:
        st.info("Awaiting Data...")
    else:
        # Top Level Metrics
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Active Signals", len(filtered_df), delta_color="normal")
        m2.metric("Countries Analyzed", filtered_df["country"].nunique())
        
        # Marketplace count
        marketplace_count = filtered_df["marketplace"].nunique() if "marketplace" in filtered_df.columns else 0
        m3.metric("Marketplaces", marketplace_count)
        
        m4.metric("Avg Trend Strength", f"{filtered_df['trend_strength'].mean():.1f}")
        validated_count = len(filtered_df[filtered_df["lifecycle_stage"] == "Validated"]) if "lifecycle_stage" in filtered_df else 0
        m5.metric("Validated Opportunities", validated_count)

        st.divider()
        
        # Analytics Charts
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("Category Distribution")
            cat_counts = filtered_df["category"].value_counts().reset_index()
            cat_counts.columns = ["category", "count"]
            chart_cat = alt.Chart(cat_counts).mark_arc(innerRadius=50).encode(
                theta="count",
                color="category",
                tooltip=["category", "count"]
            )
            st.altair_chart(chart_cat, use_container_width=True)
            
        with c2:
            st.subheader("Trend Strength by Lifecycle")
            if "lifecycle_stage" in filtered_df:
                chart_life = alt.Chart(filtered_df).mark_bar().encode(
                    x="lifecycle_stage",
                    y="count()",
                    color="lifecycle_stage",
                    tooltip=["lifecycle_stage", "count()"]
                ).interactive()
                st.altair_chart(chart_life, use_container_width=True)

        st.subheader("Top Performers (Strength > 80)")
        top_performers = filtered_df[filtered_df["trend_strength"] >= 80].head(5)
        if not top_performers.empty:
            st.dataframe(
                top_performers[["item", "category", "country", "trend_strength"]],
                hide_index=True,
                use_container_width=True
            )

# -------------------------
# TAB 2: MARKET INTELLIGENCE
# -------------------------
with tab_market:
    st.subheader("Deep Dive Analysis")
    
    if filtered_df.empty:
        st.warning("No data available based on current filters.")
    else:
        col_list, col_detail = st.columns([1.5, 1])
        
        with col_list:
            st.caption("Select a product to view detailed intelligence.")
            
            # Formatted Table
            display_cols = ["item", "trend_strength", "category", "country"]
            if "marketplace" in filtered_df: 
                display_cols.append("marketplace")
            if "lifecycle_stage" in filtered_df:
                display_cols.append("lifecycle_stage")
            if "market_type" in filtered_df: 
                display_cols.append("market_type")
            
            # Use dataframe with selection if possible, else selectbox
            # st.dataframe with on_select is newer, sticking to safe selectbox for compatibility unless confirmed
            
            # Let's show the table first
            st.dataframe(
                filtered_df[display_cols].sort_values("trend_strength", ascending=False),
                use_container_width=True,
                height=500,
                hide_index=True
            )
            
            # Export
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Export Filtered Data",
                csv,
                "trend_intelligence_export.csv",
                "text/csv",
                key='download-csv'
            )

        with col_detail:
            st.markdown("### 🕵️ Product Inspector")
            product_list = filtered_df["item"].unique().tolist()
            selected_product_name = st.selectbox("Search / Select Product", product_list)
            
            if selected_product_name:
                product_rows = filtered_df[filtered_df["item"] == selected_product_name]

                # If multiple countries exist and user is viewing "All", allow an aggregate view or a country drilldown
                if selected_country == "All" and "country" in product_rows.columns:
                    countries = sorted(product_rows["country"].dropna().unique().tolist())
                    if len(countries) > 1:
                        country_choice = st.selectbox(
                            "Country Context",
                            ["All (aggregate)"] + countries
                        )
                        if country_choice != "All (aggregate)":
                            product_rows = product_rows[product_rows["country"] == country_choice]

                row = product_rows.iloc[0]

                # Aggregate across matching rows to avoid losing links
                all_urls = []
                for u in product_rows.get("urls", []):
                    # Check if already list (direct mode) or string (needs parse)
                    # normalize_urls handles both
                    all_urls.extend(normalize_urls(u))

                all_urls = list(dict.fromkeys(all_urls))  # de-dupe, preserve order

                # Aggregate sources and metrics
                source_col = "marketplace" if "marketplace" in product_rows.columns else "sources"
                
                if source_col in product_rows.columns:
                    source_text = ", ".join(product_rows[source_col].fillna("").astype(str).tolist())
                else:
                    source_text = ""
                    
                all_sources = [s.strip() for s in source_text.split(",") if s.strip()]
                all_sources = sorted(set(all_sources))

                trend_score = product_rows["trend_strength"].max()
                
                platform_count = 0
                if "platform_count" in product_rows.columns:
                    platform_count = product_rows["platform_count"].max()

                country_summary = ""
                if selected_country == "All" and "country" in product_rows.columns:
                    countries = sorted(product_rows["country"].dropna().unique().tolist())
                    if len(countries) > 1:
                        country_summary = f"Countries: {', '.join(countries[:6])}"
                        if len(countries) > 6:
                            country_summary += f" (+{len(countries) - 6} more)"
                
                with st.container(border=True):
                    st.markdown(f"#### {row['item']}")
                    st.caption(f"Category: {row.get('category', 'N/A')}")
                    if country_summary:
                        st.caption(country_summary)
                    
                    m1, m2 = st.columns(2)
                    m1.metric("Trend Score", trend_score)
                    m2.metric("Platform Count", platform_count)
                    
                    st.markdown("**Validation Sources:**")
                    for s in all_sources:
                        if "Amazon" in s: st.markdown("- 🛒 **Amazon** (Commercial)")
                        elif "eBay" in s: st.markdown("- 🏷️ **eBay** (Commercial - Auction/BIN)")
                        elif "AliExpress" in s: st.markdown("- 📦 **AliExpress** (Global Marketplace)")
                        elif "Reddit" in s: st.markdown("- 💬 **Reddit** (Community)")
                        elif "YouTube" in s: st.markdown("- 📺 **YouTube** (Content)")
                        else: st.markdown(f"- {s}")
                        
                    st.markdown("**Direct Links:**")
                    if not all_urls:
                        st.write("No direct URLs captured.")
                    else:
                        for i, u in enumerate(all_urls[:5]):
                            st.link_button(f"🔗 Source Link {i+1}", u)

# -------------------------
# TAB 3: FESTIVAL RADAR
# -------------------------
with tab_market: # Keeping consistent
    pass

with tab_festival:
    st.subheader("Seasonal & Cultural Event Signals")
    
    festival_df = fetch_festivals()
    
    if festival_df.empty:
        st.info("No festival data. Trigger a festival fetch in Operations Center (Requires Backend).")
    else:
        if "fetch_timestamp" in festival_df:
            festival_df["fetch_timestamp"] = pd.to_datetime(festival_df["fetch_timestamp"], errors="coerce")
            
        # Festival Filters
        f1, f2 = st.columns(2)
        with f1:
            f_country = st.selectbox("Festival Country", ["All"] + sorted(festival_df["country"].dropna().unique().tolist()))
        with f2:
            f_name = st.selectbox("Festival Name", ["All"] + sorted(festival_df["festival_name"].dropna().unique().tolist()))
            
        f_filtered = festival_df.copy()
        if f_country != "All": f_filtered = f_filtered[f_filtered["country"] == f_country]
        if f_name != "All": f_filtered = f_filtered[f_filtered["festival_name"] == f_name]
        
        # Display
        st.dataframe(
            f_filtered[[
                "festival_name", "country", "product_title", "price", "rating", "keyword_used", "product_url", "fetch_timestamp"
            ]].sort_values("fetch_timestamp", ascending=False),
            column_config={
                "product_url": st.column_config.LinkColumn(
                    "Product Link",
                    display_text="View Product"
                ),
                 "fetch_timestamp": st.column_config.DatetimeColumn(
                    "Fetched At",
                    format="D MMM YYYY, HH:mm"
                ),
                 "rating": st.column_config.NumberColumn(
                    "Rating",
                    format="%.1f ⭐"
                )
            },
            use_container_width=True,
            hide_index=True
        )

# -------------------------
# TAB 4: OPERATIONS CENTER
# -------------------------
with tab_ops:
    st.header("⚙️ Pipeline Operations")
    
    if not api_ok:
        st.error("🚫 Backend Offline")
        st.info("Operations are disabled in Standalone Mode. To run pipelines, please start `main.py` locally.")
    else: 
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("🚀 General Trend Pipeline")
            st.markdown("Scrapes Amazon, YouTube, and Reddit for high-momentum products based on configured queries.")
            
            # Load Queries
            try:
                q_resp = requests.get(f"{API_BASE_URL}/queries", timeout=2)
                if q_resp.status_code == 200:
                    q_config = q_resp.json()
                    current_queries = "\n".join(q_config.get("amazon_queries", []))
                else:
                    current_queries = ""
            except:
                current_queries = "Error loading queries"

            new_queries = st.text_area("Search Queries (one per line)", value=current_queries, height=150)
            
            if st.button("💾 Save & Run Pipeline", type="primary"):
                 queries_list = [x.strip() for x in new_queries.split("\n") if x.strip()]
                 try:
                     r = requests.post(f"{API_BASE_URL}/pipeline/run", json={"queries": queries_list}, timeout=5)
                     if r.status_code == 200:
                         st.toast("Pipeline Triggered Successfully!", icon="🚀")
                     else:
                         st.error(f"Failed: {r.text}")
                 except Exception as e:
                     st.error(f"Error: {e}")

        with c2:
            st.subheader("🎊 Festival Discovery")
            st.markdown("Targeted search for specific festival keywords.")
            
            with st.form("festival_form"):
                fest_kw = st.text_input("Product Keyword", "diwali gifts")
                fest_nm = st.text_input("Festival Name", "Diwali")
                try:
                    from country_config import COUNTRIES
                    country_options = sorted(list(COUNTRIES.keys()))
                except:
                    country_options = ["India", "UAE", "USA", "UK"] # Fallback

                fest_ct = st.selectbox("Marketplace", country_options)
                
                submitted = st.form_submit_button("Run Festival Search")
                if submitted:
                    try:
                        payload = {"keyword": fest_kw, "festival_name": fest_nm, "country": fest_ct}
                        r = requests.post(f"{API_BASE_URL}/festivals/search", json=payload, timeout=5)
                        if r.status_code == 200:
                            st.toast("Festival Search Started!", icon="🎉")
                        else:
                            st.error(f"Failed: {r.text}")
                    except Exception as e:
                        st.error(f"Error: {e}")

st.divider()
st.caption("Trend Intelligence Platform v2.0 | Deepmind Advanced Co-Pilot Optimized")
