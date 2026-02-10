import json
from duckduckgo_search import DDGS

try:
    with DDGS() as ddgs:
        print("--- Trying 'smart watch amazon' ---")
        results = list(ddgs.text("smart watch amazon", max_results=5))
        print("Count:", len(results))
        if results:
            print("First Result:", results[0].get('href'))
        else:
            print("No results found.")
            
        print("\n--- Trying 'site:amazon.com smart watch' again ---")
        results = list(ddgs.text("site:amazon.com smart watch", max_results=5))
        print("Count:", len(results))

except Exception as e:
    print("Error:", e)
