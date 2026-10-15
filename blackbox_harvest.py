import sqlite3
import statistics
from urllib.parse import quote
from scraping import scrape_listings, create_driver
from blackbox_engine import upsert_blackbox_niche
from scores import calculate_opportunity_score, normalize_dict
# Standard default weights for opportunity score calculation
DEFAULT_WEIGHTS = {
    "demand": 0.4,
    "competition": 0.3,
    "margin": 0.3
}


def safe_calculate_score(median_price: float, median_sold: float, median_reviews: float, weights: dict = None) -> float:
    """Passes exactly 2 positional arguments (metrics_dict, weights) to calculate_opportunity_score."""
    if weights is None:
        weights = DEFAULT_WEIGHTS

    metrics_dict = {
        "median_price": float(median_price),
        "median_sold": float(median_sold),
        "median_reviews": float(median_reviews)
    }

    try:
        val = calculate_opportunity_score(metrics_dict, weights)
        return float(val)
    except Exception as e:
        print(f"Score calculation error: {e}")
        return 0.0










def is_niche_stale(niche_name: str, max_age_hours: int = 120, db_path: str = "daraz_intelligence.db") -> bool:
    """Considers niche data fresh for up to 5 days (120 hours)."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM blackbox_niches 
            WHERE niche_name = ? 
              AND last_updated >= datetime('now', '-' || ? || ' hours')
        """, (niche_name, max_age_hours))
        row = cursor.fetchone()
        conn.close()
        return row is None
    except Exception:
        return True


def harvest_single_niche(seed_keyword: str, driver=None) -> bool:
    """Live harvests or updates a single niche on demand."""
    close_driver_at_end = False
    if driver is None:
        driver = create_driver()
        close_driver_at_end = True

    try:
        search_url = f"https://www.daraz.pk/catalog/?q={quote(seed_keyword.strip())}"
        print(f"\n🔍 Searching URL: {search_url}")

        raw_listings = scrape_listings(search_url, driver, search_query=seed_keyword)
        listings = [item for item in raw_listings if isinstance(item, dict)]

        if not listings:
            print(f"⚠️ No listings extracted for keyword: '{seed_keyword}'")
            return False

        # Category extraction directly from sidebar markup (no fake keywords)
        category = listings[0].get("Category", "Uncategorized")

        prices = [l['Price'] for l in listings if l.get('Price') is not None]
        solds = [l['Sold_count'] for l in listings if l.get('Sold_count') is not None]
        reviews = [l['Review_Count'] for l in listings if l.get('Review_Count') is not None]

        if not prices:
            print(f"⚠️ Skipping '{seed_keyword}': Price parsing failed.")
            return False

        med_price = statistics.median(prices)
        med_sold = statistics.median(solds) if solds else 0.0
        med_reviews = statistics.median(reviews) if reviews else 0.0

        normalized_scores = {
            "median_price": normalize_dict({"val": med_price})["val"],
            "median_sold": normalize_dict({"val": med_sold})["val"],
            "median_reviews": normalize_dict({"val": med_reviews}, invert=True)["val"]
        }

        score_data = calculate_opportunity_score(normalized_scores, DEFAULT_WEIGHTS)
        if not score_data or "total" not in score_data:
            print(f"❌ Scoring failed for '{seed_keyword}'")
            return False

        opportunity_score = round(score_data["total"], 2)

        niche_data = {
            "niche_name": seed_keyword,
            "category": category,
            "median_price": med_price,
            "median_sold": med_sold,
            "median_reviews": med_reviews,
            "opportunity_score": opportunity_score
        }

        upsert_blackbox_niche(niche_data)
        print(f"✅ Harvested '{seed_keyword}' | Category: '{category}' | Score: {opportunity_score}")
        return True

    finally:
        if close_driver_at_end:
            driver.quit()


def run_smart_harvest(keyword_file: str = "seed_keywords.txt", driver=None, force_reharvest: bool = False):
    close_driver_on_exit = False
    if driver is None:
        driver = create_driver()
        close_driver_on_exit = True

    stats = {"total": 0, "harvested": 0, "skipped": 0, "failed": 0}

    try:
        with open(keyword_file, "r") as f:
            keywords = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"❌ Keyword file '{keyword_file}' not found.")
        return stats

    stats["total"] = len(keywords)

    for kw in keywords:
        if not force_reharvest and not is_niche_stale(kw, max_age_hours=48):
            print(f"Skipping '{kw}' — Fresh (scraped within 48h)")
            stats["skipped"] += 1
            continue

        print(f"\n🚀 Harvesting: '{kw}'...")
        try:
            success = harvest_single_niche(kw, driver)
            if success:
                stats["harvested"] += 1
            else:
                stats["failed"] += 1
        except Exception as e:
            print(f"❌ Error Scraping {kw}: {e}")
            stats["failed"] += 1

    if close_driver_on_exit:
        driver.quit()

    return stats


if __name__ == "__main__":
    run_smart_harvest(force_reharvest=True)