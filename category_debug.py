import json
import re
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By


def run_category_diagnostic(search_term="wireless earbuds"):
    print(f"\n==================================================")
    print(f"🧪 DIAGNOSTIC RUN FOR: '{search_term}'")
    print(f"==================================================")

    url = f"https://www.daraz.pk/catalog/?q={search_term.replace(' ', '%20')}"

    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")

    print("🚀 Launching Chrome via undetected-chromedriver...")
    driver = uc.Chrome(options=options)

    try:
        print(f"🔍 Navigating to: {url}")
        driver.get(url)
        time.sleep(3)

        # Step 0: Check for WAF / Captcha blocks
        current_url = driver.current_url
        page_title = driver.title
        print(f"\n[STEP 0: Security & URL Check]")
        print(f"  • Current URL: {current_url}")
        print(f"  • Page Title:  {page_title}")

        if "punish" in current_url or "captcha" in current_url:
            print("  ❌ BLOCKED: Daraz triggered a captcha/bot check page.")
            return

        # ---------------------------------------------------------------------
        # TIER 1: Live Window JS Data Object Evaluation
        # ---------------------------------------------------------------------
        print(f"\n[TIER 1: Window Object Inspection (`window.pageData` / `window.__MODULE_DATA__`)]")
        js_data = driver.execute_script(
            "return (window.pageData || window.__MODULE_DATA__ || window.__PAGE_DATA__);"
        )
        if js_data and isinstance(js_data, dict):
            print("  ✓ JS Global State Object Found!")
            # Check filter list
            filters = js_data.get("mods", {}).get("filter", {}).get("list", [])
            print(f"  • Filter List Items Count: {len(filters)}")
            for f in filters:
                if f.get("type") == "category" or str(f.get("title")).lower() in ["category", "categories"]:
                    print(f"  • Raw Filter Category Option: {f.get('options') or f.get('values')}")

            # Check first list item
            items = js_data.get("mods", {}).get("listItems", [])
            if items:
                print(f"  • Item 0 'categoryName': {items[0].get('categoryName')}")
                print(f"  • Item 0 'categories':   {items[0].get('categories')}")
        else:
            print("  ❌ JS Global State Object is NULL or empty.")

        # ---------------------------------------------------------------------
        # TIER 2: Internal AJAX Endpoint Fetch
        # ---------------------------------------------------------------------
        print(f"\n[TIER 2: Asynchronous Internal Endpoint Fetch (`?ajax=true`)]")
        ajax_url = url + "&ajax=true"
        js_fetch = f"""
            var done = arguments[0];
            fetch('{ajax_url}')
                .then(res => res.json())
                .then(data => done(data))
                .catch(err => done({{error: err.toString()}}));
        """
        driver.set_script_timeout(10)
        ajax_res = driver.execute_async_script(js_fetch)

        if ajax_res and isinstance(ajax_res, dict) and "error" not in ajax_res:
            print("  ✓ Internal AJAX response received!")
            list_items = ajax_res.get("mods", {}).get("listItems", [])
            if not list_items and "data" in ajax_res:
                list_items = ajax_res.get("data", {}).get("mods", {}).get("listItems", [])

            if list_items:
                print(f"  • AJAX Item 0 'categoryName': {list_items[0].get('categoryName')}")
                print(f"  • AJAX Item 0 'categories':   {list_items[0].get('categories')}")
            else:
                print("  ❌ No listItems found in AJAX response.")
        else:
            err = ajax_res.get("error") if isinstance(ajax_res, dict) else "No data returned"
            print(f"  ❌ AJAX Fetch failed: {err}")

        # ---------------------------------------------------------------------
        # TIER 3: JSON-LD Breadcrumbs
        # ---------------------------------------------------------------------
        print(f"\n[TIER 3: JSON-LD Breadcrumb Schema Scraping]")
        scripts = driver.find_elements(By.XPATH, "//script[@type='application/ld+json']")
        print(f"  • Found {len(scripts)} JSON-LD script tags.")
        found_schema = False
        for s in scripts:
            content = s.get_attribute("innerHTML")
            if content and "BreadcrumbList" in content:
                found_schema = True
                print(f"  ✓ Found BreadcrumbList Schema payload:")
                print(f"    {content.strip()[:300]}...")
        if not found_schema:
            print("  ❌ No BreadcrumbList schema found on search page.")

        # ---------------------------------------------------------------------
        # TIER 4: DOM Elements Inspection
        # ---------------------------------------------------------------------
        print(f"\n[TIER 4: DOM Filter Sidebar Selectors]")
        selectors = [
            "div[data-spm='filter_category']",
            "[data-qa-locator='filter-category']",
            ".ant-tree-title",
            "ul.ant-menu-inline"
        ]
        for sel in selectors:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            print(f"  • Selector '{sel}': {len(els)} element(s) found.")
            for el in els[:3]:
                txt = el.text.strip().replace("\n", " | ")
                if txt:
                    print(f"    -> Text snippet: '{txt[:80]}'")

    finally:
        print("\n🏁 Diagnostic complete. Closing browser...")
        driver.quit()


if __name__ == "__main__":
    run_category_diagnostic("wireless earbuds")