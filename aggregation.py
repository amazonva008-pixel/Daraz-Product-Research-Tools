import json
from scraping import scrape_listings, scrape_total_listings, get_trend_score, create_driver
from scores import normalize_all_signals, calculate_opportunity_score
import csv
import re
import statistics
import sqlite3
from datetime import datetime

def save_scrape(keyword, signals):
    conn = sqlite3.connect("keyword_data.db")
    cursor = conn.cursor()
    scraped_at = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO keyword_scrapes 
        (keyword, scraped_at, median_reviews, median_sold, median_price, dominance, sale_to_review, total_listings, median_rating)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        keyword,
        scraped_at,
        signals["median_reviews"],
        signals["median_sold"],
        signals["median_price"],
        signals["dominance"],
        signals["sale_to_review"],
        signals["total_listings"],
        signals["median_rating"],
    ))
    conn.commit()
    conn.close()

def create_database():
    conn = sqlite3.connect("keyword_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS keyword_scrapes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            scraped_at TEXT NOT NULL,
            median_reviews REAL,
            median_sold REAL,
            median_price REAL,
            dominance REAL,
            sale_to_review REAL,
            total_listings REAL,
            median_rating REAL
        )
    """)
    conn.commit()
    conn.close()




def review_dominance_ratio(all_listings):
    median_value = get_median(all_listings, "Review_Count")

    if not median_value:
        return None

    else:
        review_count = extract_values(all_listings, "Review_Count")
        mean_value = statistics.mean(review_count)
        dominance = mean_value/median_value

        return dominance

def sale_to_review_ratio(sold_count, review_count):                   
                                                                      
    if review_count and sold_count is not None and review_count != 0:
        ratio = sold_count / review_count                             
        return ratio                                                  
    else:                                                             
        return None                                                   


def extract_values(all_listings, key):
    values = []
    for listing in all_listings:
        value = listing[key]
        if value is not None:
            values.append(value)
    return values


def get_median(data, key=None):
    if not data:
        return 0.0

    # If a key string is passed, extract values from dictionary list
    if key is not None:
        values = [item[key] for item in data if isinstance(item, dict) and item.get(key) is not None]
    else:
        # If no key is passed, assume data is already a list of numbers
        values = [v for v in data if isinstance(v, (int, float))]

    if not values:
        return 0.0

    return round(float(statistics.median(values)), 2)





def median_sale_to_review_ratio(all_listings):
    ratios = []   # will collect one ratio per listing

    for listing in all_listings:
        sold = listing["Sold_count"]
        reviews = listing["Review_Count"]
        ratio = sale_to_review_ratio(sold, reviews)   # reuse the function you already built
        if ratio is not None:
           ratios.append(ratio)   # <- which list are we building up?

    if not ratios:
        return None
    else:
        median_value = statistics.median(ratios)
        return median_value









def build_trend_scores(keywords: list):
    trend_scores = {}
    for kw in keywords:

            g_scores = get_trend_score(kw)
            trend_scores[kw] = g_scores
    if not trend_scores:
        return None
    else:
        return trend_scores




def collect_all_signals(keyword_urls):
    all_signals = {
        "median_reviews": {},
        "median_sold": {},
        "median_price": {},
        "dominance": {},
        "sale_to_review": {},
        "total_listings": {},
        "median_rating": {}
    }
    driver = create_driver()
    try:
        for keyword in keyword_urls:
            url = keyword_urls[keyword]
            listings = scrape_listings(url, driver)
            if not listings:
                continue
            all_signals["median_rating"][keyword] = get_median(listings, "Ratings")
            all_signals["median_reviews"][keyword] = get_median(listings, "Review_Count")
            all_signals["median_sold"][keyword] = get_median(listings, "Sold_count")
            all_signals["median_price"][keyword] = get_median(listings, "Price")
            all_signals["dominance"][keyword] = review_dominance_ratio(listings)
            all_signals["sale_to_review"][keyword] = median_sale_to_review_ratio(listings)
            all_signals["total_listings"][keyword] = scrape_total_listings(url, driver)
    finally:
        driver.quit()

    return all_signals


def restructure_by_keyword(normalized_signals, keywords):
    by_keyword = {}
    for kw in keywords:
        kw_scores = {}
        for signal_name in normalized_signals:
            value = normalized_signals[signal_name][kw]
            kw_scores[signal_name] = value
        by_keyword[kw] = kw_scores
    return by_keyword

def save_signals(all_signals, filename="all_signals.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(all_signals, f, indent=2)

def load_signals(filename="all_signals.json"):
    with open(filename, "r", encoding="utf-8") as f:
        all_signals = json.load(f)
    return all_signals

def get_keyword_history(keyword):
    conn = sqlite3.connect("keyword_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM keyword_scrapes
        WHERE keyword = ?
        ORDER BY scraped_at ASC
    """, (keyword,))
    rows = cursor.fetchall()
    conn.close()
    return rows




# if __name__ == "__main__":
#     keyword_urls = {
#         "mini fan": "https://www.daraz.pk/catalog/?q=mini+fan",
#         "handheld mini fan": "https://www.daraz.pk/catalog/?q=handheld+mini+fan",
#         "desk fan": "https://www.daraz.pk/catalog/?q=desk+fan",
#         'cooling fan': 'https://www.daraz.pk/catalog/?q=cooling+fan',
#         'rechargeable mini fan': 'https://www.daraz.pk/catalog/?q=rechargeable+mini+fan',
#         'handheld fan': 'https://www.daraz.pk/catalog/?q=handheld+fan'
#     }
#
#
#
#
#
#     all_signals = collect_all_signals(keyword_urls)
#
#

#
#
#
# if __name__ == "__main__":
#     all_signals = load_signals()
#     normalized_signals = normalize_all_signals(all_signals)
#     weights = {"median_reviews": 0.12, "median_sold": 0.2, "median_price": 0.05, "dominance": 0.2, "sale_to_review": 0.2, "total_listings": 0.07, "median_rating": 0.16}
#     keywords = list(all_signals["median_reviews"].keys())  # safer, matches your earlier fix
#
#     raw_by_keyword = restructure_by_keyword(all_signals, keywords)
#     normalized_by_keyword = restructure_by_keyword(normalized_signals, keywords)
#     keyword_totals = {}
#     for kw in raw_by_keyword:
#         save_scrape(kw, raw_by_keyword[kw])
#         scores = normalized_by_keyword[kw]
#         result = calculate_opportunity_score(scores, weights)
#         print(kw, "->", result)
#         keyword_totals[kw] = result["total"]
