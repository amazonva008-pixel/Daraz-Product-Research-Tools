
from aggregation import save_scrape, get_median, review_dominance_ratio, median_sale_to_review_ratio, scrape_total_listings, scrape_listings
from aggregation import get_keyword_history
from datetime import datetime, timedelta
from scraping import create_driver
from spacy_ai_tagger import get_top_phrases, build_expansion_urls
from scores import normalize, normalize_dict

# Defined globally before functions that reference it
NICHE_INVERT_RULES = {
    "total_demand": False,            # more demand = better
    "avg_dominance": True,            # higher dominance = worse for new sellers
    "avg_rating": False,              # at niche level, low ratings = red flag
    "price_gap": False,               # bigger gap = more room for positioning
    "total_review_volume": True,      # more reviews = harder to break in
    "review_to_listing_ratio": False, # higher ratio = healthier demand
    "keyword_score_spread": False     # high spread = keyword choice matters
}


def row_to_signals_minimal(row):
    """
    Convert a DB row (tuple or sqlite3.Row/dict) into a signals dict.
    Handles two tuple layouts:
      - (keyword, scraped_at, median_reviews, ...)
      - (id, keyword, scraped_at, median_reviews, ...)
    """
    if hasattr(row, "keys") or isinstance(row, dict):
        r = dict(row)
        return {
            "median_reviews": int(r.get("median_reviews")) if r.get("median_reviews") not in (None, "") else None,
            "median_sold": float(r.get("median_sold")) if r.get("median_sold") not in (None, "") else None,
            "median_price": float(r.get("median_price")) if r.get("median_price") not in (None, "") else None,
            "dominance": float(r.get("dominance")) if r.get("dominance") not in (None, "") else None,
            "sale_to_review": float(r.get("sale_to_review")) if r.get("sale_to_review") not in (None, "") else None,
            "total_listings": float(r.get("total_listings")) if r.get("total_listings") not in (None, "") else None,
            "median_rating": float(r.get("median_rating")) if r.get("median_rating") not in (None, "") else None,
        }

    row = list(row)
    if len(row) >= 1 and (isinstance(row[0], int) or (isinstance(row[0], str) and row[0].isdigit())):
        base = 3
    else:
        base = 2

    def s_int(i):
        idx = base + i
        if idx < len(row) and row[idx] not in (None, ""):
            return int(row[idx])
        return None

    def s_float(i):
        idx = base + i
        if idx < len(row) and row[idx] not in (None, ""):
            return float(row[idx])
        return None

    return {
        "median_reviews": s_int(0),
        "median_sold": s_float(1),
        "median_price": s_float(2),
        "dominance": s_float(3),
        "sale_to_review": s_float(4),
        "total_listings": s_float(5),
        "median_rating": s_float(6),
    }


def get_or_scrape(keyword, url, driver, max_age_hours=24):
    history = get_keyword_history(keyword)

    if history:
        most_recent_row = history[-1]
        scraped_at_str = most_recent_row[2]
        scraped_at = datetime.fromisoformat(scraped_at_str)
        age = datetime.now() - scraped_at

        if age < timedelta(hours=max_age_hours):
            print(f"Using cached data for '{keyword}'")
            return row_to_signals_minimal(most_recent_row)

    print(f"No recent data for '{keyword}' — scraping fresh")

    listings = scrape_listings(url, driver)
    if not listings:
        return None

    signals = {
        "median_reviews": get_median(listings, "Review_Count"),
        "median_sold": get_median(listings, "Sold_count"),
        "median_price": get_median(listings, "Price"),
        "dominance": review_dominance_ratio(listings),
        "sale_to_review": median_sale_to_review_ratio(listings),
        "total_listings": scrape_total_listings(url, driver),
        "median_rating": get_median(listings, "Ratings"),
    }
    save_scrape(keyword, signals)
    return signals


def scrape_niche_keywords(keywords_dict):
    """
    keywords_dict looks like: {"kitchen scale": "url1", "digital kitchen scale": "url2", ...}
    """
    driver = create_driver()
    keyword_first_data = {}

    try:
        for kw, url in keywords_dict.items():
            keyword_first_data[kw] = get_or_scrape(kw, url, driver)
    finally:
        driver.quit()

    return keyword_first_data


def total_demand(all_signals):
    if not isinstance(all_signals, dict):
        return 0
    if "median_sold" in all_signals and isinstance(all_signals["median_sold"], dict):
        values = [v for v in all_signals["median_sold"].values() if v is not None]
    else:
        values = [kw.get("median_sold") for kw in all_signals.values() if isinstance(kw, dict) and kw.get("median_sold") is not None]
    return sum(values) if values else 0


def avg_dominance(all_signals):
    if not isinstance(all_signals, dict):
        return 0
    if "dominance" in all_signals and isinstance(all_signals["dominance"], dict):
        values = [v for v in all_signals["dominance"].values() if v is not None]
    else:
        values = [kw.get("dominance") for kw in all_signals.values() if isinstance(kw, dict) and kw.get("dominance") is not None]
    return sum(values) / len(values) if values else 0


def avg_rating(all_signals):
    if not isinstance(all_signals, dict):
        return 0
    if "median_rating" in all_signals and isinstance(all_signals["median_rating"], dict):
        values = [v for v in all_signals["median_rating"].values() if v is not None]
    else:
        values = [kw.get("median_rating") for kw in all_signals.values() if isinstance(kw, dict) and kw.get("median_rating") is not None]
    return sum(values) / len(values) if values else 0


def price_gap(all_signals):
    if not isinstance(all_signals, dict):
        return 0
    if "median_price" in all_signals and isinstance(all_signals["median_price"], dict):
        values = [v for v in all_signals["median_price"].values() if v is not None]
    else:
        values = [kw.get("median_price") for kw in all_signals.values() if isinstance(kw, dict) and kw.get("median_price") is not None]
    return max(values) - min(values) if len(values) >= 2 else 0


def total_review_volume(all_signals):
    if not isinstance(all_signals, dict):
        return 0
    if "median_reviews" in all_signals and isinstance(all_signals["median_reviews"], dict):
        values = [v for v in all_signals["median_reviews"].values() if v is not None]
    else:
        values = [kw.get("median_reviews") for kw in all_signals.values() if isinstance(kw, dict) and kw.get("median_reviews") is not None]
    return sum(values) if values else 0


def keyword_score_spread(keyword_scores):
    if not keyword_scores or not isinstance(keyword_scores, dict):
        return 0

    values = [v for v in keyword_scores.values() if v is not None]
    return max(values) - min(values) if len(values) >= 2 else 0


def rating_dominance_flag(all_signals, rating_threshold=3.0, dominance_threshold=15.0):
    rating = avg_rating(all_signals)
    dominance = avg_dominance(all_signals)
    if rating < rating_threshold and dominance > dominance_threshold:
        return "Low ratings + high dominance detected — a captive-demand opportunity may exist."
    return None


def normalize_all_niche_signals(signal_first_niches):
    normalized = {}

    for signal_name, raw_scores in signal_first_niches.items():
        should_invert = NICHE_INVERT_RULES.get(signal_name, False)
        normalized[signal_name] = normalize_dict(raw_scores, invert=should_invert)

    return normalized


def restructure_by_signal(all_signals: dict) -> dict:
    """
    Restructure signals by type, ensuring values are numeric.
    Input: {keyword: {signal_name: value, ...}, ...}
    Output: {signal_name: {keyword: value, ...}, ...}
    """
    restructured = {}

    for keyword, signals_for_this_kw in all_signals.items():
        if not signals_for_this_kw or not isinstance(signals_for_this_kw, dict):
            continue

        for signal_name, raw_value in signals_for_this_kw.items():
            try:
                value = float(raw_value)
            except (ValueError, TypeError):
                value = None

            if signal_name not in restructured:
                restructured[signal_name] = {}

            restructured[signal_name][keyword] = value

    return restructured


def review_to_listing_ratio(all_signals):
    if not isinstance(all_signals, dict):
        return 0
    if "median_reviews" in all_signals and isinstance(all_signals["median_reviews"], dict):
        reviews = [v for v in all_signals["median_reviews"].values() if v is not None]
        listings = [v for v in all_signals.get("total_listings", {}).values() if v is not None]
    else:
        reviews = [kw.get("median_reviews") for kw in all_signals.values() if isinstance(kw, dict) and kw.get("median_reviews") is not None]
        listings = [kw.get("total_listings") for kw in all_signals.values() if isinstance(kw, dict) and kw.get("total_listings") is not None]

    if reviews and listings and sum(listings) > 0:
        return sum(reviews) / sum(listings)
    return 0


def calculate_niche_metrics(niche_all_signals, keyword_scores):
    return {
        "total_demand": total_demand(niche_all_signals),
        "avg_dominance": avg_dominance(niche_all_signals),
        "avg_rating": avg_rating(niche_all_signals),
        "price_gap": price_gap(niche_all_signals),
        "total_review_volume": total_review_volume(niche_all_signals),
        "review_to_listing_ratio": review_to_listing_ratio(niche_all_signals),
        "keyword_spread": keyword_score_spread(keyword_scores)
    }


def calculate_niche_score(niche_signals: dict, all_niches: list, weights: dict):
    normalized = {}
    for signal in niche_signals:
        values = [n[signal] for n in all_niches if n[signal] is not None]
        min_val, max_val = min(values), max(values)
        invert_flag = NICHE_INVERT_RULES.get(signal, False)
        normalized[signal] = normalize(niche_signals[signal], min_val, max_val, invert=invert_flag)

    usable_weights = {s: w for s, w in weights.items() if normalized[s] is not None}
    total_weight = sum(usable_weights.values())
    score = sum(normalized[s] * (usable_weights[s] / total_weight) for s in usable_weights)
    return {"total": score, "breakdown": normalized}


def calculate_final_niche_scores(niche_first_normalized: dict) -> dict:
    results = {}

    for niche_name, metrics in niche_first_normalized.items():
        scores_list = [v for v in metrics.values() if v is not None]
        avg_score = sum(scores_list) / len(scores_list) if scores_list else 0

        results[niche_name] = {
            "total_score": round(avg_score, 2),
            "breakdown": {signal: round(val, 2) if val is not None else 0.0 for signal, val in metrics.items()}
        }

    return results


def print_niche_summary(final_results: dict):
    for niche, data in final_results.items():
        print(f"\n=== {niche.upper()} (Score: {data['total_score']}) ===")
        for signal, score in data["breakdown"].items():
            print(f"  - {signal:<25}: {score:>5.1f} / 100")


def discover_niche_phrases(seed_keyword, url, driver):
    clean_seed = seed_keyword.replace("_", " ")
    listings = scrape_listings(url, driver)
    phrases = get_top_phrases(listings, seed_keyword=clean_seed, top_n=10)
    print(f"Top phrases for '{seed_keyword}': {phrases}")
    return phrases


def process_selected_niche_phrases(selected_phrases: list):
    niche_urls = build_expansion_urls(selected_phrases)
    raw_niche_data = scrape_niche_keywords(niche_urls)
    signal_first_niche = restructure_by_signal(raw_niche_data)
    return signal_first_niche

