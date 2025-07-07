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

def setup_driver():
    """Set up Chrome WebDriver with error suppression and stealth"""
    chrome_options = Options()
    
    # Suppress unnecessary logs and errors
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--disable-gcm')
    chrome_options.add_argument('--disable-component-update')
    chrome_options.add_argument('--disable-background-networking')
    
    # Stealth settings
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    service = Service(r'C:\Users\ytars\Downloads\chromedriver-win64\chromedriver.exe')
    
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(60)
        
        # Additional stealth
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
            """
        })
        return driver
    except Exception as e:
        print(f"Driver initialization failed: {e}")
        return None

def wait_for_captcha(driver):
    """Pause execution and wait for user to manually solve CAPTCHA"""
    print("\n" + "="*50)
    print("MANUAL CAPTCHA VERIFICATION REQUIRED")
    print("1. Please solve any CAPTCHA that appears in the browser")
    print("2. After solving, return here and press Enter to continue")
    print("="*50 + "\n")
    
    input("Press Enter after solving CAPTCHA to continue scraping...")
    
    # Verify if we're still on the same page
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        print("Continuing with scraping...")
        return True
    except:
        print("Page verification failed after CAPTCHA")
        return False

def parse_date(date_text):
    """Parse date text into date object."""
    try:
        if 'Today' in date_text:
            return datetime.now().date()
        elif 'Tomorrow' in date_text:
            return datetime.now().date() + timedelta(days=1)
        else:
            date_str = date_text.split(',')[-1].strip()
            return datetime.strptime(date_str + ' ' + str(datetime.now().year), '%d %b %Y').date()
    except Exception as e:
        print(f"Date parsing error: {e}")
        return datetime.now().date()

def extract_match_data(match, match_date):
    """Extract match information from a match element."""
    try:
        # Try multiple class names for team names
        team_selectors = ['team-name', 'participant-name', 'team']
        home_team = away_team = ""
        
        for selector in team_selectors:
            teams = match.find_all('div', class_=selector)
            if len(teams) >= 2:
                home_team = teams[0].get_text(strip=True)
                away_team = teams[1].get_text(strip=True)
                break
        
        if not home_team or not away_team:
            return None
            
        # Get match time
        time_element = match.find('div', class_='event-time')
        match_time = time_element.get_text(strip=True) if time_element else "TBD"
        
        # Get odds - try multiple class names
        odds_selectors = ['odds-button', 'price', 'odd-button']
        home_odds = draw_odds = away_odds = "N/A"
        
        for selector in odds_selectors:
            odds = match.find_all('button', class_=selector)
            if len(odds) >= 3:
                home_odds = odds[0].get_text(strip=True)
                draw_odds = odds[1].get_text(strip=True)
                away_odds = odds[2].get_text(strip=True)
                break
        
        # Get league name
        league_selectors = ['sports-tournament-header', 'league-name', 'tournament-header']
        league = "Unknown League"
        
        for selector in league_selectors:
            league_element = match.find_previous('div', class_=selector)
            if league_element:
                league = league_element.get_text(strip=True)
                break
        
        return {
            'date': match_date.strftime('%Y-%m-%d'),
            'time': match_time,
            'league': league,
            'home_team': home_team,
            'away_team': away_team,
            'home_odds': home_odds,
            'draw_odds': draw_odds,
            'away_odds': away_odds
        }
    except Exception as e:
        print(f"Error extracting match data: {e}")
        return None

def scrape_stake_soccer_data(driver):
    """Scrape soccer betting data with CAPTCHA handling"""
    if not driver:
        return None

    base_url = "https://stake1022.com/sports/soccer"
    print(f"\nAttempting to access: {base_url}")

    try:
        print("Loading page...")
        driver.get(base_url)
        
        # Wait for CAPTCHA to potentially appear
        time.sleep(5)
        
        # Check if CAPTCHA is present
        captcha_frames = driver.find_elements(By.XPATH, "//iframe[contains(@src, 'captcha') or contains(@src, 'recaptcha')]")
        if captcha_frames:
            if not wait_for_captcha(driver):
                return None
        
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        print("Page loaded successfully")
        
        # Take screenshot for debugging
        driver.save_screenshot("page_load.png")
        print("Screenshot saved as page_load.png")

        # Rest of scraping logic
        print("\nLooking for upcoming matches...")
        upcoming_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Upcoming')]")))
        upcoming_button.click()
        time.sleep(2)
        
        today = datetime.now().date()
        date_range = [today + timedelta(days=i) for i in range(4)]
        matches_data = []
        
        print("\nFinding match sections...")
        date_sections = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.sports-group")))
        
        print(f"Found {len(date_sections)} sections")
        
        for i, section in enumerate(date_sections):
            try:
                driver.execute_script("arguments[0].scrollIntoView();", section)
                time.sleep(1)
                
                section_html = section.get_attribute('outerHTML')
                soup = BeautifulSoup(section_html, 'html.parser')
                
                date_header = soup.find('div', class_='sports-group-header')
                if not date_header:
                    continue
                    
                date_text = date_header.get_text(strip=True)
                section_date = parse_date(date_text)
                
                if section_date not in date_range:
                    continue
                    
                match_items = soup.find_all('div', class_='sports-event')
                print(f"Section {i+1} ({date_text}): {len(match_items)} matches")
                
                for match in match_items:
                    match_data = extract_match_data(match, section_date)
                    if match_data:
                        matches_data.append(match_data)
                        
            except Exception as e:
                print(f"Error processing section {i+1}: {str(e)}")
                continue
                
        return matches_data
        
    except Exception as e:
        print(f"\nScraping error: {str(e)}")
        return None
    finally:
        driver.save_screenshot("final_state.png")
        print("Final page screenshot saved as final_state.png")

def main():
    print("=== Stake1022.com Soccer Data Scraper ===")
    print("Initializing with CAPTCHA support...")
    
    driver = setup_driver()
    if not driver:
        print("Failed to initialize WebDriver. Exiting.")
        return

    try:
        matches = scrape_stake_soccer_data(driver)
        
        if matches:
            df = pd.DataFrame(matches)
            print("\n=== SCRAPING RESULTS ===")
            print(f"\nFound {len(df)} matches:")
            print(df[['date', 'time', 'league', 'home_team', 'away_team', 'home_odds', 'draw_odds', 'away_odds']].to_string(index=False))
            
            filename = f'stake_matches_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
            df.to_csv(filename, index=False)
            print(f"\nData saved to {filename}")
            
            try:
                os.startfile(filename)
            except:
                print(f"Open {filename} manually to view data")
        else:
            print("\nNo matches found or scraping failed")
            
    finally:
        if driver:
            driver.quit()
        print("\nScraping completed")

if __name__ == "__main__":
    main()