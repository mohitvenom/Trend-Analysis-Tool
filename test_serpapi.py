import requests
import json

SERP_API_KEY = "13b700df766fb5eaaacc4afebc175579cf1f96aca2e9b67b207631741bebd36e" # Using the first key from the list
SERP_ENDPOINT = "https://serpapi.com/search.json"

def test_serpapi():
    params = {
        "engine": "amazon",
        "k": "smart watch",
        "api_key": SERP_API_KEY,
        "amazon_domain": "amazon.com"
    }
    
    print(f"Testing SerpApi with key: {SERP_API_KEY[:5]}...")
    try:
        response = requests.get(SERP_ENDPOINT, params=params, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "organic_results" in data:
                print(f"Success! Found {len(data['organic_results'])} organic results.")
                print("First item:", data['organic_results'][0].get("title"))
            elif "shopping_results" in data:
                 print(f"Success! Found {len(data['shopping_results'])} shopping results.")
            elif "error" in data:
                print(f"API Error: {data['error']}")
            else:
                 print("Response keys:", data.keys())
        else:
            print("Error response:", response.text)
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_serpapi()
