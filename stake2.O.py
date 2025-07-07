pip install selenium beautifulsoup4 pandas



import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import os

# === CONFIG ===
CHROMEDRIVER_PATH = r"C:\Users\ytars\Downloads\chromedriver-win64\chromedriver.exe"
STAKE_URL = "https://stake.com/sports/soccer"

# === DRIVER SETUP ===
def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--start-maximized')

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver

# === CAPTCHA HANDLER ===
def wait_for_manual_captcha():
    print("\n🛑 CAPTCHA detected. Please solve it in the browser.")
    input("✅ Press Enter after solving the CAPTCHA to continue...")

# === EXTRACT MATCH DATA ===
def extract_match_data(soup, match_date):
    matches = soup.find_all('div', class_='sports-event')
    match_list = []

    for match in matches:
        try:
            teams = match.find_all('div', class_='participant-name')
            if len(teams) != 2:
                continue
            home_team = teams[0].get_text(strip=True)
            away_team = teams[1].get_text(strip=True)

            odds = match.find_all('button')
            if len(odds) >= 3:
                home_odds = odds[0].get_text(strip=True)
                draw_odds = odds[1].get_text(strip=True)
                away_odds = odds[2].get_text(strip=True)
            else:
                home_odds = draw_odds = away_odds = "N/A"

            time_elem = match.find('div', class_='event-time')
            match_time = time_elem.get_text(strip=True) if time_elem else "Unknown"

            match_list.append({
                'date': match_date.strftime('%Y-%m-%d'),
                'time': match_time,
                'home_team': home_team,
                'away_team': away_team,
                'home_odds': home_odds,
                'draw_odds': draw_odds,
                'away_odds': away_odds
            })

        except Exception as e:
            print(f"Error parsing match: {e}")
            continue

    return match_list

# === MAIN SCRAPER ===
def scrape_matches():
    driver = setup_driver()
    driver.get(STAKE_URL)
    wait_for_manual_captcha()

    try:
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        print("✅ Page loaded after CAPTCHA")

        # Scroll to load more matches
        print("🔄 Scrolling to load more matches...")
        for _ in range(10):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

        # Save page source
        with open("page_source.html", "w", encoding='utf-8') as f:
            f.write(driver.page_source)

        print("📄 Saved page source to 'page_source.html'")

        soup = BeautifulSoup(driver.page_source, "html.parser")
        today = datetime.now().date()
        data = []

        for i in range(4):
            match_date = today + timedelta(days=i)
            matches = extract_match_data(soup, match_date)
            data.extend(matches)

        driver.quit()
        return data

    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        driver.quit()
        return []

# === MAIN FUNCTION ===
def main():
    print("=== Stake Soccer Odds Scraper ===")
    data = scrape_matches()

    if data:
        df = pd.DataFrame(data)
        filename = f"stake_odds_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        df.to_csv(filename, index=False)
        print(f"\n✅ Saved {len(df)} matches to '{filename}'")
        try:
            os.startfile(filename)
        except:
            print("Please open the CSV manually.")
    else:
        print("⚠️ No data extracted.")

if __name__ == "__main__":
    main()
