import sqlite3
from datetime import datetime
import pandas as pd
import streamlit as st

# Modules from local pipeline
from scraping import create_driver, scrape_listings
from aggregation_niche import (
    process_selected_niche_phrases,
    calculate_niche_metrics,
    restructure_by_signal,
    normalize_all_niche_signals,
    calculate_final_niche_scores,
    discover_niche_phrases
)
from scores import normalize_all_signals, calculate_opportunity_score


# On-demand harvester integration
from blackbox_harvest import harvest_single_niche

st.set_page_config(
    page_title="Daraz tools",
    page_icon="🎯",
    layout="wide"
)


def get_freshness_badge(last_updated_str: str) -> str:
    """Returns a visual freshness indicator string based on data age."""
    if not last_updated_str:
        return "⚪ Unknown"
    try:
        clean_str = str(last_updated_str).split('.')[0]
        updated_at = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
        days = (datetime.now() - updated_at).days

        if days == 0:
            return "🟢 Updated today"
        elif days <= 3:
            return f"🟢 {days}d ago"
        elif days <= 5:
            return f"🟡 {days}d ago"
        else:
            return f"🔴 {days}d ago (Stale)"
    except Exception:
        return f"📅 {last_updated_str}"


def query_blackbox_niches(min_price, max_price, min_sold, max_reviews, min_score, category):
    conn = sqlite3.connect('daraz_intelligence.db')

    sql = """
        SELECT 
            niche_name AS "Niche Name",
            category AS "Category",
            median_price AS "Median Price (PKR)",
            median_sold AS "Median Sold",
            median_reviews AS "Median Reviews",
            opportunity_score AS "Opportunity Score",
            last_updated AS "Last Updated"
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

    df = pd.read_sql_query(sql, conn, params=tuple(params))
    conn.close()
    return df


def render_blackbox_tab():
    st.header("📦 Black Box Niche Discovery")
    col1, col2, col3 = st.columns(3)
    with col1:
        price_range = st.slider("Price Range (PKR)", 0, 10000, (500, 3000))
        min_sold = st.number_input("Min Monthly Sold", min_value=0, value=30)
    with col2:
        max_reviews = st.number_input("Max Review Count", min_value=0, value=500)
        min_score = st.slider("Min Opportunity Score", 0.0, 100.0, 0.0)
    with col3:
        category = st.selectbox("Category", ["All", "Electronics", "Home & Living", "Fashion"])
        search_btn = st.button("Find Opportunities", type="primary")

    # Fetch data on initial load or search button click
    results = query_blackbox_niches(
        price_range[0],
        price_range[1],
        min_sold,
        max_reviews,
        min_score,
        category
    )

    if results.empty:
        st.info("No saved niches match these filter criteria.")
    else:
        # Generate Data Freshness badge column
        results["Data Freshness"] = results["Last Updated"].apply(get_freshness_badge)

        # Display formatted dataframe
        display_df = results.drop(columns=["Last Updated"])
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.divider()

        # On-Demand Re-harvest Controls
        st.subheader("🔄 On-Demand Niche Refresh")
        st.caption("Notice stale data (🟡 or 🔴)? Trigger an on-demand live crawl for any keyword.")

        reharvest_col1, reharvest_col2 = st.columns([3, 1])
        with reharvest_col1:
            selected_niche_to_refresh = st.selectbox(
                "Select Niche to Re-harvest:",
                options=results["Niche Name"].tolist()
            )
        with reharvest_col2:
            st.write("##")  # Alignment spacer
            if st.button("🔄 Re-harvest Niche Now", type="secondary"):
                with st.spinner(f"Live crawling Daraz for fresh data on '{selected_niche_to_refresh}'..."):
                    success = harvest_single_niche(selected_niche_to_refresh)
                    if success:
                        st.success(f"Successfully refreshed '{selected_niche_to_refresh}'!")
                        st.rerun()
                    else:
                        st.error(f"Failed to refresh '{selected_niche_to_refresh}'. Check scraper logs.")


# --- SESSION STATE INITIALIZATION ---
if "compared_niches" not in st.session_state:
    st.session_state.compared_niches = {}
if "step" not in st.session_state:
    st.session_state.step = 1
if "seed_keyword" not in st.session_state:
    st.session_state.seed_keyword = ""
if "raw_listings" not in st.session_state:
    st.session_state.raw_listings = []
if "candidate_phrases" not in st.session_state:
    st.session_state.candidate_phrases = []
if "selected_phrases" not in st.session_state:
    st.session_state.selected_phrases = []
if "was_corrected" not in st.session_state:
    st.session_state.was_corrected = False
if "raw_user_input" not in st.session_state:
    st.session_state.raw_user_input = ""


def fetch_niche_data(seed_keyword: str):
    """Scrapes live Daraz listings for the given seed keyword."""
    clean_query = seed_keyword.strip().replace(" ", "+")
    url = f"https://www.daraz.pk/catalog/?q={clean_query}"

    driver = create_driver()
    try:
        listings = scrape_listings(url, driver)
        return listings if listings else []
    finally:
        driver.quit()


# --- HEADER & NAVIGATION ---
st.title("🎯 Daraz Keyword & Niche Discovery Tool")
tab_blackbox, tab_deepdive = st.tabs(["📦 Black Box Discovery", "🔍 Niche Deep Dive"])

with tab_blackbox:
    render_blackbox_tab()

with tab_deepdive:
    st.subheader("Enter Product Search Term")

    steps = ["1. Keyword Input", "2. Phrase Selection", "3. Keyword Opportunity Scores", "4. Multi-Niche Comparison"]
    cols = st.columns(4)
    for idx, name in enumerate(steps, start=1):
        if st.session_state.step == idx:
            cols[idx - 1].markdown(f"**👉 {name}**")
        elif st.session_state.step > idx:
            cols[idx - 1].markdown(f"✅ ~~{name}~~")
        else:
            cols[idx - 1].markdown(f"🔒 {name}")

    st.divider()

    # STEP 1: KEYWORD INPUT
    if st.session_state.step == 1:
        st.subheader("Enter Product Search Term")
        st.caption("We will fetch scraped market data (or instant cache) to extract niche candidate search terms.")

        with st.form("seed_input_form"):
            user_input = st.text_input(
                "What product or niche are you researching on Daraz?",
                value=st.session_state.seed_keyword,
                placeholder="e.g., mini fan, car phone holder, wireless earbuds",
                help="Enter a primary seed term. We'll find all related sub-phrases."
            )
            submit_button = st.form_submit_button("🔍 Discover Niche Keywords", type="primary")

        if submit_button:
            if not user_input.strip():
                st.warning("Please enter a search term first.")
            else:
                clean_keyword = user_input.strip()
                st.session_state.seed_keyword = clean_keyword

                with st.spinner(f"Extracting keyword phrases for '{clean_keyword}'..."):
                    target_url = f"https://www.daraz.pk/catalog/?q={clean_keyword.replace(' ', '+')}"
                    driver = create_driver()
                    try:
                        phrases = discover_niche_phrases(clean_keyword, target_url, driver)
                        st.session_state.candidate_phrases = phrases if phrases else []
                        st.session_state.selected_phrases = st.session_state.candidate_phrases.copy()
                    finally:
                        driver.quit()

                st.session_state.step = 2
                st.rerun()

    # STEP 2: PHRASE SELECTION
    elif st.session_state.step == 2:
        st.subheader(f"Select Top Keywords for '{st.session_state.seed_keyword.title()}'")

        if st.session_state.get("was_corrected"):
            st.info(
                f"💡 Typo detected! Auto-corrected **'{st.session_state.raw_user_input}'** ➔ **'{st.session_state.seed_keyword}'**")

        st.write("Uncheck any irrelevant phrases before generating opportunity metrics.")

        c1, c2, _ = st.columns([1, 1, 4])

        if c1.button("Select All"):
            for phrase in st.session_state.candidate_phrases:
                st.session_state[f"cb_{phrase}"] = True
            st.session_state.selected_phrases = st.session_state.candidate_phrases.copy()
            st.rerun()

        if c2.button("Deselect All"):
            for phrase in st.session_state.candidate_phrases:
                st.session_state[f"cb_{phrase}"] = False
            st.session_state.selected_phrases = []
            st.rerun()

        st.write("---")

        col_left, col_right = st.columns(2)
        current_selected = []

        if not st.session_state.candidate_phrases:
            st.warning(
                "No candidate phrases were extracted for this term. Try returning to Step 1 with a broader keyword.")
        else:
            for i, phrase in enumerate(st.session_state.candidate_phrases):
                target_col = col_left if i % 2 == 0 else col_right
                is_checked = phrase in st.session_state.selected_phrases

                if target_col.checkbox(f"**{i + 1}.** {phrase}", value=is_checked, key=f"cb_{phrase}"):
                    current_selected.append(phrase)

        st.session_state.selected_phrases = current_selected

        st.write("---")
        b_col1, b_col2 = st.columns([1, 5])
        if b_col1.button("⬅️ Back"):
            st.session_state.step = 1
            st.rerun()

        if b_col2.button(f"📊 Generate Opportunity Scores ({len(current_selected)} selected)", type="primary"):
            if not current_selected:
                st.error("Select at least 1 keyword phrase to proceed.")
            else:
                st.session_state.step = 3
                st.rerun()

    # STEP 3: OPPORTUNITY SCORES
    elif st.session_state.step == 3:
        st.subheader(f"Keyword & Niche Analysis: '{st.session_state.seed_keyword.title()}'")

        if st.session_state.seed_keyword not in st.session_state.compared_niches:
            with st.spinner(
                    f"Scraping & scoring keyword signals for {len(st.session_state.selected_phrases)} phrases..."):
                niche_signals = process_selected_niche_phrases(st.session_state.selected_phrases)

                normalized_kw_signals = normalize_all_signals(niche_signals)
                kw_weights = {
                    "median_reviews": 0.12, "median_sold": 0.20, "median_price": 0.05,
                    "dominance": 0.20, "sale_to_review": 0.20, "total_listings": 0.07,
                    "median_rating": 0.16
                }

                kw_scores = {}
                kw_table_data = []

                for phrase in st.session_state.selected_phrases:
                    phrase_scores = {sig: normalized_kw_signals[sig].get(phrase) for sig in normalized_kw_signals if
                                     sig in normalized_kw_signals}
                    res = calculate_opportunity_score(phrase_scores, kw_weights)
                    score_val = res["total"] if res else 0
                    kw_scores[phrase] = score_val

                    raw_sold = niche_signals.get("median_sold", {}).get(phrase, 0)
                    raw_price = niche_signals.get("median_price", {}).get(phrase, 0)
                    raw_reviews = niche_signals.get("median_reviews", {}).get(phrase, 0)

                    kw_table_data.append({
                        "Keyword Phrase": phrase,
                        "Est. Sold": raw_sold,
                        "Avg Price (PKR)": raw_price,
                        "Median Reviews": raw_reviews,
                        "Opportunity Score": round(score_val, 1)
                    })

                niche_metrics = calculate_niche_metrics(niche_signals, kw_scores)

                st.session_state.compared_niches[st.session_state.seed_keyword] = {
                    "signals": niche_signals,
                    "kw_scores": kw_scores,
                    "metrics": niche_metrics,
                    "table": pd.DataFrame(kw_table_data)
                }

        current_data = st.session_state.compared_niches[st.session_state.seed_keyword]

        st.markdown("**Keyword-Level Performance Breakdown**")
        st.dataframe(current_data["table"], use_container_width=True, hide_index=True)

        st.divider()

        st.info(
            f"Currently Staged Niches: **{len(st.session_state.compared_niches)}** ({', '.join(st.session_state.compared_niches.keys())})")

        col1, col2 = st.columns(2)
        if col1.button("➕ Add / Select Another Niche"):
            st.session_state.seed_keyword = ""
            st.session_state.selected_phrases = []
            st.session_state.step = 1
            st.rerun()

        if col2.button("⚖️ Compare All Staged Niches (Step 4)", type="primary"):
            st.session_state.step = 4
            st.rerun()

    # STEP 4: MULTI-NICHE COMPARISON
    elif st.session_state.step == 4:
        st.subheader("Multi-Niche Comparison Matrix")

        if not st.session_state.compared_niches:
            st.warning("No niches staged yet. Please analyze at least one niche in Step 1.")
            if st.button("Go to Step 1"):
                st.session_state.step = 1
                st.rerun()
        else:
            raw_niche_comparison = {
                niche: data["metrics"]
                for niche, data in st.session_state.compared_niches.items()
            }

            signal_first_niches = restructure_by_signal(raw_niche_comparison)
            normalized_signals = normalize_all_niche_signals(signal_first_niches)
            niche_first_normalized = restructure_by_signal(normalized_signals)

            final_niche_scores = calculate_final_niche_scores(niche_first_normalized)

            comparison_rows = []
            for niche, score_data in final_niche_scores.items():
                metrics = raw_niche_comparison[niche]
                comparison_rows.append({
                    "Niche": niche.title(),
                    "Overall Niche Score": score_data["total_score"],
                    "Total Demand (Units)": metrics.get("total_demand", 0),
                    "Avg Dominance": round(metrics.get("avg_dominance", 0), 2),
                    "Price Gap (PKR)": metrics.get("price_gap", 0),
                    "Total Reviews": metrics.get("total_review_volume", 0)
                })

            df_comparison = pd.DataFrame(comparison_rows).sort_values(by="Overall Niche Score", ascending=False)
            st.dataframe(df_comparison, use_container_width=True, hide_index=True)

            st.divider()

            col1, col2 = st.columns(2)
            if col1.button("➕ Stage Another Niche"):
                st.session_state.seed_keyword = ""
                st.session_state.step = 1
                st.rerun()

            if col2.button("📊 View Deep Dive Breakdown (Step 5)", type="primary"):
                st.session_state.step = 5
                st.rerun()

    # STEP 5: DEEP DIVE REPORT
    elif st.session_state.step == 5:
        st.subheader("Niche Deep Dive Report")

        selected_niche = st.selectbox(
            "Select staged niche to inspect:",
            options=list(st.session_state.compared_niches.keys())
        )

        if selected_niche:
            niche_data = st.session_state.compared_niches[selected_niche]

            st.markdown(f"### Keywords inside '{selected_niche.title()}'")
            st.dataframe(niche_data["table"], use_container_width=True, hide_index=True)

            st.markdown("### Niche Signal Metrics")
            st.json(niche_data["metrics"])

        st.divider()

        if st.button("🔄 Reset All Staged Data"):
            st.session_state.compared_niches = {}
            st.session_state.seed_keyword = ""
            st.session_state.selected_phrases = []
            st.session_state.step = 1
            st.rerun()