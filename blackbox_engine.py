import sqlite3

def create_blackbox_table(db_path="daraz_intelligence.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blackbox_niches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            niche_name TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            median_price REAL NOT NULL,
            median_sold INTEGER NOT NULL,
            median_reviews INTEGER NOT NULL,
            opportunity_score REAL NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def upsert_blackbox_niche(data: dict, db_path="daraz_intelligence.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO blackbox_niches 
        (niche_name, category, median_price, median_sold, median_reviews, opportunity_score)
        VALUES (:niche_name, :category, :median_price, :median_sold, :median_reviews, :opportunity_score)
        ON CONFLICT(niche_name) DO UPDATE SET
            median_price = excluded.median_price,
            median_sold = excluded.median_sold,
            median_reviews = excluded.median_reviews,
            opportunity_score = excluded.opportunity_score,
            last_updated = CURRENT_TIMESTAMP
    """, data)
    conn.commit()
    conn.close()



def query_blackbox_niches(min_price=0, max_price=999999, min_sold=0, max_reviews=99999, min_score=0, category="All",
                          db_path="daraz_intelligence.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    sql = """
        SELECT niche_name, category, median_price, median_sold, median_reviews, opportunity_score 
        FROM blackbox_niches 
        WHERE median_price BETWEEN ? AND ?
          AND median_sold >= ?
          AND median_reviews <= ?
          AND opportunity_score >= ?
    """
    params = [min_price, max_price, min_sold, max_reviews, min_score]
    if category != "All":
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY opportunity_score DESC"
    cursor.execute(sql, params)
    results = cursor.fetchall()
    conn.close()
    return results


if __name__ == "__main__":
    create_blackbox_table()