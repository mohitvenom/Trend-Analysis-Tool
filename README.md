# 🚀 Trend Intelligence Platform

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/) 
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

A powerful, standalone dashboard for tracking e-commerce trends across **Amazon, eBay, AliExpress, and Social Media**. Built with **Streamlit** and optimized for cloud deployment.

---

## 🌟 Key Features

*   **📊 Multi-Source Intelligence:** Aggregates trend data from major e-commerce platforms.
*   **🌍 Global & Regional Views:** Filter trends by country (focus on Iceland, US, UK, etc.).
*   **🎉 Festival Radar:** Specialized module to discover products for specific cultural events.
*   **🛡️ Standalone Mode:** Runs fully on Streamlit Cloud using cached data (no live backend required).
*   **🔒 Secure:** Strict `.env` management to keep API keys safe.

---

## 🛠️ Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/mohitvenom/Trend-Analysis-Tool.git
    cd Trend-Analysis-Tool
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run Locally:**
    ```bash
    streamlit run dashboard.py
    ```

---

## 🔄 Data Update Workflow (Manual Sync)

Since the cloud app runs in "Standalone Mode", follow this workflow to update the data:

1.  **Configure Search Queries:**
    Edit `scraper_queries_config.json` to change what the scrapers look for.

2.  **Run Scrapers (Locally):**
    ```powershell
    python run_all.py
    ```
    *This fetches fresh data from Amazon, eBay, etc.*

3.  **Push to Cloud:**
    ```bash
    git add .
    git commit -m "Update trend data"
    git push
    ```
    *Streamlit Cloud will automatically detect the new data and update the dashboard in ~2 minutes.*

---

## 📁 Project Structure

*   `dashboard.py`: The main Streamlit application (Frontend).
*   `main.py`: The FastAPI backend (Local use only).
*   `scrapers/`: Individual scraper scripts (Amazon, eBay, etc.).
*   `run_all.py`: Orchestrator script to run all scrapers.
*   `outputs/`: Directory where scraped data (CSV/JSON) is saved.
*   `scraper_queries_config.json`: Configuration for search terms.

---

## 🤝 Contributing

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

---

*Verified by Deepmind Advanced Co-Pilot* 🤖
