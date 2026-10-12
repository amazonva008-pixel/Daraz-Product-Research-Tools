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
