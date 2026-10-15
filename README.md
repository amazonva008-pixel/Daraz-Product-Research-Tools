## ⚙️ Installation & Usage

### 1. Access the Niche Intelligence Dashboard (Online)
You don't need to install anything to use the Black Box and Keyword tools! 
👉 **[Launch Live Streamlit Dashboard Here](#)** *(Insert your Streamlit Cloud URL once deployed)*

### 2. Install the Daraz X-Ray Chrome Extension (Sideloading)
To use the real-time catalog analytics overlay directly on Daraz.pk:
1. Download or clone the `extension/` folder from this repository.
2. Open Google Chrome and navigate to `chrome://extensions/`.
3. Enable **Developer Mode** in the top-right corner.
4. Click **Load unpacked** and select the `extension/` folder.
5. Head over to [Daraz.pk](https://www.daraz.pk), search for a product category, and click **"🎯 Launch Daraz X-Ray"**!

# 🎯 Daraz Niche Intelligence Suite

An end-to-end e-commerce market research and product hunting platform built specifically for **Daraz.pk**, inspired by industry tools like Helium 10. This project combines a high-performance **Chrome Extension** for real-time catalog analytics with a **Python & Streamlit backend** for advanced niche opportunity scoring and keyword harvesting.

---

## 🚀 Key Features

### 1. 🔍 Daraz X-Ray (Chrome Extension)
* **Real-Time Injection:** Injects seamlessly into Daraz search and category pages via Main World context and resilient DOM fallback mechanisms.
* **Catalog Metrics:** Instantly calculates niche-wide statistics including total listings, estimated units sold, total revenue, and average product price.
* **Interactive Table & Sorting:** Multi-column sorting by Price, Est. Revenue, Units Sold, Ratings, Discounts, and Location with instant updates.

### 2. 📦 Black Box Niche Discovery
* **Market Filtering:** Filter thousands of product categories by price range, monthly sales volume, review counts, and custom opportunity scores.
* **On-Demand Live Crawling:** Trigger live Python scrapers directly from the dashboard to refresh stale data instantly.

### 3. 📊 Keyword Opportunity & Harvester Tool
* **NLP Phrase Extraction:** Scrapes top related search terms and uses Natural Language Processing (SpaCy) to surface high-demand sub-niches.
* **Signal Normalization:** Automatically normalizes market signals (review counts, search volume, price gaps) and weights them to calculate a robust **Opportunity Score**.

---

## 🛠️ Tech Stack

* **Frontend Extension:** JavaScript (Manifest V3), HTML5, CSS3, DOM Parsing, `window.pageData` extraction.
* **Dashboard:** Streamlit (Python UI Framework), Pandas.
* **Backend & Scraping:** Python, Selenium, BeautifulSoup, SQLite.
* **NLP & Data Processing:** SpaCy, Statistical Normalization Algorithms.

---

## 📂 Project Architecture

```text
├── extension/
│   ├── manifest.json      # Chrome Extension configuration (Manifest V3)
│   └── content.js         # X-Ray injection, UI modal, and data extractor engine
├── backend/
│   ├── APP.py             # Streamlit dashboard for Black Box & Niche Deep Dive
│   ├── blackbox_harvest.py# Automated and on-demand scraping engine
│   ├── aggregation_niche.py# Multi-niche metric calculation and scoring
│   ├── scores.py          # Signal normalization and opportunity scoring logic
│   └── spacy_ai_tagger.py # NLP keyword extraction and phrase clustering
└── daraz_intelligence.db  # SQLite database storing historical keyword & niche scans
