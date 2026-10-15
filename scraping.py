import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pytrends.request import TrendReq
import logging
import re
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from typing import List, Optional

logger = logging.getLogger("price_spi")
def parse_sold_count(text):
    if "K" in text:
        search_string = re.search(r"\d+.\d+", text)
        cleaned_string = search_string.group()
        cleaned_int = float(cleaned_string)
        total_sale_count = cleaned_int * 1000
        return total_sale_count
    elif "M" in text:
        search_string = re.search(r"\d+.\d+", text)
        cleaned_string = search_string.group()
        cleaned_int = float(cleaned_string)
        total_sale_count = cleaned_int * 1000000
        return total_sale_count

    else:
        search_string = re.search(r"\d+", text)
        cleaned_string = search_string.group()
        cleaned_int = float(cleaned_string)
        return cleaned_int


from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


def create_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--log-level=3")

    # Hide automation flags natively
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")

    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    service = Service()
    driver = webdriver.Chrome(service=service, options=options)

    # Strip navigator.webdriver attribute dynamically
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
    )

    driver.implicitly_wait(10)
    return driver

logger = logging.getLogger(__name__)

import re
import time
import logging
from typing import List
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)


def extract_real_daraz_category(driver) -> str:
    """
    Extracts the official category directly from Daraz sidebar markup
    using the locaid=d1 tracking attribute.
    """
    try:
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Primary: Target Daraz's explicit #1 category tracking attribute
        top_cat_el = soup.select_one("a[data-spm-click*='locaid=d1']")
        if top_cat_el and top_cat_el.text.strip():
            return top_cat_el.text.strip()

        # Secondary: Class container inside Category filter box
        fallback_cat_el = soup.select_one(".y9-OE a.DMfHy")
        if fallback_cat_el and fallback_cat_el.text.strip():
            return fallback_cat_el.text.strip()

    except Exception as e:
        logger.debug(f"Category extraction error: {e}")

    # Explicitly return 'Uncategorized' on missing selector (no fake keyword spoofing)
    return "Uncategorized"


def scrape_listings(url: str, driver, search_query: str = "") -> List[dict]:
    try:
        logger.info(f"Opening chrome for: {url}")
        driver.get(url)

        # Scroll to ensure sidebar filter renders
        driver.execute_script("window.scrollTo(0, 400);")
        time.sleep(1.5)

        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-qa-locator='product-item'], .buTCk"))
            )
        except Exception:
            print(f"⚠️ Timeout waiting for listings on: {url}")

        # Extract true category from sidebar markup
        page_category = extract_real_daraz_category(driver)
        print(f"📌 Detected Category: '{page_category}'")

        # Parse product listing cards
        listing_cards = driver.find_elements(By.CSS_SELECTOR, "[data-qa-locator='product-item']")
        if not listing_cards:
            listing_cards = driver.find_elements(By.CLASS_NAME, "buTCk")

        all_listings = []

        for card in listing_cards:
            title_text = None
            try:
                title_element = card.find_element(By.CLASS_NAME, "RfADt")
                title_text = title_element.text.strip()
            except Exception:
                try:
                    title_element = card.find_element(By.CSS_SELECTOR, "a[title]")
                    title_text = title_element.get_attribute("title") or title_element.text.strip()
                except Exception:
                    title_text = None

            sold_number = None
            try:
                sold_element = card.find_element(By.CLASS_NAME, "_1cEkb")
                sold_text = sold_element.text.strip()
                match = re.search(r"(\d+(?:\.\d+)?[kK]?)", sold_text)
                if match:
                    val = match.group(1).lower()
                    sold_number = int(float(val.replace('k', '')) * 1000) if 'k' in val else int(val)
            except Exception:
                sold_number = None

            review_count = None
            try:
                review_element = card.find_element(By.CLASS_NAME, "qzqFw")
                review_text = review_element.text.strip()
                match = re.search(r"\d+", review_text)
                review_count = int(match.group()) if match else None
            except Exception:
                review_count = None

            price = None
            try:
                price_element = card.find_element(By.CLASS_NAME, "ooOxS")
                price_text = price_element.text.strip().replace(",", "")
                match = re.search(r"\d+", price_text)
                price = int(match.group()) if match else None
            except Exception:
                price = None

            if title_text or price:
                all_listings.append({
                    "Title": title_text,
                    "Category": page_category,
                    "Sold_count": sold_number or 0,
                    "Price": price or 0,
                    "Review_Count": review_count or 0
                })

        return all_listings

    except Exception as e:
        print(f"Error Scraping {url}: {e}")
        return []


def scrape_total_listings(url, driver):


    try:
        logger.info(f"Opening chrome for: {url}")
        driver.get(url)



        wait = WebDriverWait(driver, 15)
        listing_count = wait.until(
            EC.presence_of_element_located(
                (By.CLASS_NAME, "M4pDu")
            )
        )
        scraped_text = listing_count.text.strip()
        text = scraped_text
        text_clean = text.replace(",", "")
        match = re.search(r"\d+", text_clean)
        count_str = match.group()
        count_int = int(count_str)

        return count_int

    except Exception as e:
        print(f"Error Scraping {url}: {e}")
        return None

def scrape_autocomplete(keyword):
    driver = create_driver()

    try:
        driver.get("https://www.daraz.pk/")

        search_box = driver.find_element(By.ID, "q")
        search_box.send_keys(keyword)
        time.sleep(2)  # let the dropdown render

        suggestion_elements = driver.find_elements(By.CLASS_NAME, "suggest-item-content--20px")  # what class goes here?

        suggestions = []
        for element in suggestion_elements:
            text = element.text.strip()
            suggestions.append(text)  # which list are you building up?

        return suggestions

        # collect their text into a list, return it


    except Exception as e:
        print(f"Error scraping autocomplete for '{keyword}': {e}")
        return None

    finally:
        driver.quit()
def get_trend_score(keyword):
    try:
        pytrends = TrendReq(hl='en-US', tz=360)
        pytrends.build_payload(kw_list=[keyword], timeframe='today 3-m', geo='PK')
        data = pytrends.interest_over_time()

        if data.empty:
            return None

        mean_score = data[keyword].mean()
        return mean_score

    except Exception as e:
        print(f"Trends failed for '{keyword}': {type(e).__name__}: {e}")
        return None
if __name__ == "__main__":
    listing = "https://www.daraz.pk/catalog/?spm=a2a0e.tm80335142.search.d_go&q=mini%20fan"
    driver = create_driver()
    print(scrape_listings(listing, driver))