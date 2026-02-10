import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def search_bing(query):
    url = f"https://www.bing.com/search?q=site:amazon.com+{query.replace(' ', '+')}"
    print(f"Fetching {url}")
    try:
        res = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {res.status_code}")
        
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Bing organic results are usually in li.b_algo
        results = soup.select("li.b_algo")
        print(f"Found {len(results)} results")
        
        for i, res in enumerate(results[:3]):
            h2 = res.select_one("h2 a")
            if h2:
                title = h2.text
                link = h2['href']
                print(f"{i+1}. {title} -> {link}")
                
    except Exception as e:
        print(f"Error: {e}")

search_bing("smart watch")
