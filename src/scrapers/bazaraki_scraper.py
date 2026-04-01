"""
Bazaraki.com Property Scraper
Scrapes real estate listings from Bazaraki.com for Cyprus properties
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from selenium_stealth import stealth
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import time
import json
from datetime import datetime
from typing import Dict, List, Optional
import re
import random
import os
import sys
import subprocess


# Allow importing sibling package: src/database/db_connection.py
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

from database.db_connection import DBConnection


# ==================== MAIN FUNCTION ====================

def main():
    """Main execution function with user input for locations"""
    available_cities = ['nicosia', 'limassol', 'larnaka', 'paphos']

    print("=" * 60)
    print("BAZARAKI PROPERTY SCRAPER")
    print("=" * 60)

    selected_cities = _prompt_selected_cities(available_cities)
    print(f"\nSelected cities: {', '.join([c.capitalize() for c in selected_cities])}")

    max_pages, max_listings, max_listings_per_page, page_label = _prompt_page_settings()
    
    print(f"Will scrape: {page_label} per city")
    print("\nStarting scrape...\n")
    
    # Initialize scraper and database connection
    scraper = BazarakiScraper()
    db = DBConnection()
    all_properties = []
    checkpoint = scraper.load_checkpoint()
    resume_city_index = -1
    if checkpoint and checkpoint.get('city') in selected_cities:
        resume_city_index = selected_cities.index(checkpoint.get('city'))
        print(
            f"Resuming from checkpoint: city={checkpoint.get('city')}, "
            f"page={checkpoint.get('page', 1)}, listing_index={checkpoint.get('listing_index', 0)}"
        )
    
    try:
        # Open database connection for uploading during scraping
        db.connect()
        
        # Scrape selected cities
        for idx, city in enumerate(selected_cities):
            print(f"\n{'='*60}")
            print(f"Scraping {city.upper()}")
            print(f"{'='*60}")

            if resume_city_index != -1 and idx < resume_city_index:
                print(f"Skipping {city} (already completed before checkpoint)")
                continue

            start_page = 1
            start_listing_index = 0
            if resume_city_index != -1 and idx == resume_city_index:
                start_page = max(1, int(checkpoint.get('page', 1)))
                start_listing_index = max(0, int(checkpoint.get('listing_index', 0)))

            # Save city-level checkpoint so crashes between pages can still resume correctly.
            scraper.save_checkpoint(city=city, page=start_page, listing_index=start_listing_index)
            
            properties = scraper.get_property_listings(
                city=city,
                max_pages=max_pages,
                max_listings=max_listings,
                max_listings_per_page=max_listings_per_page,
                start_page=start_page,
                start_listing_index=start_listing_index,
                db_connection=db,
            )
            all_properties.extend(properties)

            city_stats = scraper.last_city_stats or {}
            print(f"\nLocation summary for {city.capitalize()}:")
            print(f"  Listings collected: {city_stats.get('listings_collected', len(properties))}")
            print(f"  Pages processed: {city_stats.get('pages_processed', 0)}")
            print(f"  Pages skipped after retries: {city_stats.get('pages_skipped', 0)}")
            print(f"  Page retries used: {city_stats.get('page_retries_used', 0)}")

            # Move checkpoint to next city boundary after successful city loop.
            scraper.save_checkpoint(city=city, page=max_pages + 1, listing_index=0)
            
            # Minimal delay between cities
            time.sleep(0.05)

        scraper.clear_checkpoint()
        
        print(f"\n{'='*60}")
        print(f"Scraping completed!")
        print(f"Total properties collected: {len(all_properties)}")
        print("JSON export disabled (database-only mode)")
        print(f"{'='*60}")
    except Exception as e:
        print(f"Error during scraping: {e}")
    finally:
        # Clean up: close database connection and driver
        db.disconnect()
        scraper.close_driver()


def _prompt_selected_cities(available_cities: List[str]) -> List[str]:
    print("\nAvailable locations:")
    for i, city in enumerate(available_cities, 1):
        print(f"  {i}. {city.capitalize()}")
    print(f"  {len(available_cities) + 1}. All locations")

    while True:
        try:
            choice = input("\nEnter location(s) to scrape (comma-separated numbers, e.g., 1,3,4): ").strip()

            if choice == str(len(available_cities) + 1):
                selected_cities = available_cities
            else:
                choices = [int(c.strip()) - 1 for c in choice.split(',')]
                selected_cities = [available_cities[i] for i in choices if 0 <= i < len(available_cities)]

            if not selected_cities:
                print("Invalid selection. Please try again.")
                continue

            return selected_cities
        except (ValueError, IndexError):
            print("Invalid input. Please enter valid numbers.")


def _prompt_page_settings() -> tuple[int, Optional[int], Optional[int], str]:
    print("\nHow many pages to scrape per city?")
    print("  1. First page only")
    print("  2. First 5 pages")
    print("  3. First 10 pages")
    print("  4. All available pages")
    print("  5. First 5 listings (testing)")
    print("  6. Test mode: 1 listing from page 1 and 1 from page 2")

    page_map = {
        '1': (1, None, None),      # 1 page, no limits
        '2': (5, None, None),      # 5 pages, no limits
        '3': (10, None, None),     # 10 pages, no limits
        '4': (999, None, None),    # all pages, no limits
        '5': (1, 5, None),         # 1 page, cap total to 5 listings
        '6': (2, None, 1)          # 2 pages, cap each page to 1 listing
    }
    labels = [
        'First page only',
        'First 5 pages',
        'First 10 pages',
        'All pages',
        'First 5 listings (testing)',
        'Test mode: 1 listing from page 1 and 1 from page 2'
    ]

    while True:
        page_choice = input("\nEnter your choice (1-6): ").strip()
        if page_choice not in page_map:
            print("Invalid choice. Please enter 1-6.")
            continue

        max_pages, max_listings, max_listings_per_page = page_map[page_choice]
        page_label = labels[int(page_choice) - 1]
        return max_pages, max_listings, max_listings_per_page, page_label


# ==================== BAZARAKI SCRAPER CLASS ====================

class BazarakiScraper:
    """Web scraper for Bazaraki.com real estate listings using Selenium"""
    
    def __init__(self):
        self.base_url = "https://www.bazaraki.com"
        self.properties_url = f"{self.base_url}/real-estate-for-sale/houses/"
        self.driver = None
        self.checkpoint_file = os.path.join(CURRENT_DIR, 'data', 'raw', 'bazaraki_checkpoint.json')
        self.max_page_retries = 3
        self.last_city_stats = None
        self._setup_driver()
        
        # City to district mapping for Bazaraki URLs
        self.city_mapping = {
            'nicosia': 'lefkosia-district-nicosia',
            'limassol': 'lemesos-district-limassol',  # Corrected mapping
            'larnaka': 'larnaka-district-larnaca',
            'paphos': 'pafos-district-paphos'
        }
    
    def get_property_listings(
        self,
        city: Optional[str] = None,
        max_pages: int = 999,
        max_listings: int = None,
        max_listings_per_page: int = None,
        start_page: int = 1,
        start_listing_index: int = 0,
        db_connection: Optional['DBConnection'] = None,
    ) -> List[Dict]:
        """Fetch property listings from Bazaraki using Selenium"""
        properties = []
        stats = {
            'pages_processed': 0,
            'pages_skipped': 0,
            'page_retries_used': 0,
            'listings_collected': 0,
        }
        
        # Build URL with filters
        url = self.properties_url
        if city:
            district = self.city_mapping.get(city.lower(), city.lower())
            url = f"{self.properties_url}{district}/"
            
        print(f"Starting to scrape Bazaraki: {url}")
        
        for page in range(start_page, max_pages + 1):
            page_url = f"{url}?page={page}" if page > 1 else url
            print(f"Scraping page {page}...")

            page_loaded = False
            listings = []
            for attempt in range(1, self.max_page_retries + 1):
                try:
                    # Rotate browser instance and user-agent for every paginated request.
                    self.close_driver()
                    self._setup_driver()

                    self.driver.get(page_url)

                    # Wait for page to load
                    time.sleep(2)

                    # Wait for listings to appear (try desktop then mobile selectors)
                    try:
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.advert, [class*='CardGrid_container']"))
                        )
                    except:
                        pass

                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')

                    # Desktop version: .advert containers
                    listings = soup.find_all('div', class_='advert')

                    if not listings:
                        # Mobile version: CardGrid containers
                        listings = soup.find_all(class_=lambda x: x and 'CardGrid_container' in x)

                    if not listings:
                        # Fallback: advert-grid containers
                        listings = soup.find_all(class_=lambda x: x and 'advert-grid__item' in x)

                    page_loaded = True
                    break
                except Exception as e:
                    wait_time = attempt * 3
                    print(f"Error fetching page {page} (attempt {attempt}/{self.max_page_retries}): {e}")
                    stats['page_retries_used'] += 1
                    time.sleep(wait_time)

            if not page_loaded:
                print(f"Skipping page {page} after {self.max_page_retries} failed attempts")
                stats['pages_skipped'] += 1
                continue

            if not listings:
                print(f"No listings found on page {page}. Stopping...")
                break

            print(f"Found {len(listings)} listings on page {page}")
            stats['pages_processed'] += 1
            page_added = 0

            current_start_index = start_listing_index if page == start_page else 0
            for listing_idx, listing in enumerate(listings):
                if listing_idx < current_start_index:
                    continue

                # Stop if we've reached max_listings
                if max_listings and len(properties) >= max_listings:
                    break

                # Stop if we've reached per-page listing cap
                if max_listings_per_page and page_added >= max_listings_per_page:
                    break

                property_data = self._parse_listing(listing)
                if property_data:
                    properties.append(property_data)
                    page_added += 1
                    stats['listings_collected'] += 1

                    # Save checkpoint after each successful listing parse.
                    self.save_checkpoint(city=city or '', page=page, listing_index=listing_idx + 1)

                    # Upload immediately if database connection is provided
                    if db_connection:
                        try:
                            inserted = db_connection.insert_property(property_data)
                            if inserted:
                                print(f"    ✓ Uploaded to database: {property_data.get('external_id')}")
                            else:
                                print(f"    ✗ Not inserted (DB error): {property_data.get('external_id')}")
                        except Exception as db_error:
                            print(f"    ✗ Failed to upload: {db_error}")

            # Stop if we've reached max_listings
            if max_listings and len(properties) >= max_listings:
                break

            # Mark next page as resume point after finishing this page.
            self.save_checkpoint(city=city or '', page=page + 1, listing_index=0)

            # No delay between pages
            time.sleep(0.05)
        
        self.last_city_stats = stats
        print(f"Total properties scraped: {len(properties)}")
        return properties
    
    def _setup_driver(self):
        """Initialize Chrome WebDriver with stealth options"""
        ua = UserAgent()
        self._user_agent = ua.random
        chrome_options = Options()
        chrome_options.add_argument(f"--user-agent={self._user_agent}")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Disable image loading via preferences
        prefs = {"profile.managed_default_content_settings.images": 2}
        chrome_options.add_experimental_option("prefs", prefs)

        last_error = None
        for attempt in range(1, 4):
            try:
                self._cleanup_stale_driver_processes()
                if attempt < 3:
                    # Primary path: webdriver_manager cached driver
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                else:
                    # Fallback path: let Selenium Manager resolve a compatible driver
                    self.driver = webdriver.Chrome(options=chrome_options)

                stealth(self.driver,
                        user_agent=self._user_agent,
                        languages=["en-US", "en"],
                        vendor="Google Inc.",
                        platform="Win32",
                        webgl_vendor="Intel Inc.",
                        renderer="Intel Iris OpenGL Engine",
                        fix_hairline=False)

                print("WebDriver ready")
                return
            except WebDriverException as e:
                last_error = e
                self.close_driver()
                wait_time = attempt * 2
                print(f"WebDriver init attempt {attempt}/3 failed: {e}")
                time.sleep(wait_time)
            except Exception as e:
                last_error = e
                self.close_driver()
                wait_time = attempt * 2
                print(f"WebDriver init attempt {attempt}/3 failed: {e}")
                time.sleep(wait_time)

        print(f"Error initializing WebDriver after retries: {last_error}")
        raise last_error

    def _cleanup_stale_driver_processes(self):
        """Best-effort cleanup for stale chromedriver processes before startup."""
        try:
            subprocess.run(
                ["pkill", "-f", "chromedriver.*--port="],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    def load_checkpoint(self) -> Optional[Dict]:
        """Load checkpoint if available."""
        try:
            if not os.path.exists(self.checkpoint_file):
                return None
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def save_checkpoint(self, city: str, page: int, listing_index: int):
        """Persist checkpoint for resume after crashes."""
        try:
            checkpoint_dir = os.path.dirname(self.checkpoint_file)
            os.makedirs(checkpoint_dir, exist_ok=True)
            payload = {
                'city': city,
                'page': page,
                'listing_index': listing_index,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Warning: failed to save checkpoint: {e}")

    def clear_checkpoint(self):
        """Remove checkpoint after successful run completion."""
        try:
            if os.path.exists(self.checkpoint_file):
                os.remove(self.checkpoint_file)
        except Exception as e:
            print(f"Warning: failed to clear checkpoint: {e}")
    
    def close_driver(self):
        """Safely close the WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
            except:
                pass
    
    def _parse_listing(self, listing) -> Optional[Dict]:
        """Parse individual property listing — supports both desktop and mobile HTML"""
        try:
            # --- Desktop version (.advert classes) ---
            is_desktop = listing.get('class') and 'advert' in listing.get('class', [])
            
            if is_desktop:
                title_elem = listing.find(class_='advert__content-title')
                price_elem = listing.find(class_='advert__content-price')
                place_elem = listing.find(class_='advert__content-place')
                feature_elems = listing.find_all(class_='advert__content-feature')
                property_id = listing.get('data-id', '')
            else:
                # Mobile version (CardGrid classes)
                title_elem = listing.find(class_=lambda x: x and 'CardGrid_title' in x)
                price_elem = listing.find(class_=lambda x: x and 'CardGrid_price' in x)
                place_elem = None
                feature_elems = []
                property_id = ''
            
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            
            # Extract URL - find the /adv/ link in the listing
            property_url = ''
            for link in listing.find_all('a', href=True):
                href = link.get('href', '')
                if '/adv/' in href:
                    property_url = href
                    break
            
            if not property_url:
                return None
            
            # Extract price
            price_text = price_elem.get_text(strip=True) if price_elem else ''
            price = self._extract_price(price_text)
            
            # Extract property ID from URL if not from data-id
            if not property_id:
                property_id = self._extract_id_from_url(property_url)
            
            # Extract location from place element or text
            city = ''
            area = ''
            if place_elem:
                place_text = place_elem.get_text(strip=True)
                place_parts = [p.strip() for p in place_text.split(',')]
                city = place_parts[0] if len(place_parts) > 0 else ''
                area = place_parts[1] if len(place_parts) > 1 else ''
            
            # Extract basic features from listing (desktop)
            bedrooms = None
            bathrooms = None
            property_area_sqm = None
            plot_area_sqm = None
            parking = None
            
            if feature_elems:
                # Desktop features order: bedrooms, bathrooms, area, plot, parking
                feat_texts = [f.get_text(strip=True) for f in feature_elems]
                if len(feat_texts) >= 1:
                    m = re.search(r'(\d+)', feat_texts[0])
                    if m:
                        bedrooms = int(m.group(1))
                if len(feat_texts) >= 2:
                    m = re.search(r'(\d+)', feat_texts[1])
                    if m:
                        bathrooms = int(m.group(1))
                if len(feat_texts) >= 3:
                    m = re.search(r'(\d+)', feat_texts[2])
                    if m:
                        property_area_sqm = int(m.group(1))
                if len(feat_texts) >= 4:
                    m = re.search(r'(\d+)', feat_texts[3])
                    if m:
                        plot_area_sqm = int(m.group(1))
                if len(feat_texts) >= 5:
                    parking = feat_texts[4]
            else:
                # Try to extract bedrooms from title
                all_text = listing.get_text(strip=True)
                bed_match = re.search(r'(\d+)-?bedroom', all_text, re.IGNORECASE)
                if bed_match:
                    bedrooms = int(bed_match.group(1))
            
            # Build full URL
            full_url = f"{self.base_url}{property_url}"
            
            # Fetch detailed page for extra info (small delay to avoid Cloudflare)
            time.sleep(random.uniform(1.0, 2.5))
            print(f"  Fetching details: {property_id}...")
            detail_data = self._fetch_property_details(full_url)
            
            # Use detail data to override/supplement listing data
            d = detail_data if detail_data else {}
            
            property_data = {
                'source': 'bazaraki',
                'reference_number': d.get('reference_number', property_id),
                'external_id': property_id,
                'url': full_url,
                'title': title,
                'price': price,
                'city': d.get('city', city or 'Unknown'),
                'district': d.get('district', ''),
                'area': d.get('area', area),
                'bedrooms': d.get('bedrooms', bedrooms),
                'bathrooms': d.get('bathrooms', bathrooms),
                'property_area_sqm': d.get('property_area_sqm', property_area_sqm),
                'plot_area_sqm': d.get('plot_area_sqm', plot_area_sqm),
                'property_type': d.get('property_type'),
                'parking': d.get('parking', parking),
                'condition': d.get('condition'),
                'furnishing': d.get('furnishing'),
                'included': d.get('included'),
                'postal_code': d.get('postal_code'),
                'construction_year': d.get('construction_year'),
                'online_viewing': d.get('online_viewing'),
                'air_conditioning': d.get('air_conditioning'),
                'energy_efficiency': d.get('energy_efficiency'),
                'price_per_sqm': d.get('price_per_sqm'),
                'description': d.get('description'),
                'scraped_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            return property_data
            
        except Exception as e:
            print(f"Error parsing listing: {e}")
            return None
    
    def _fetch_property_details(self, property_url: str) -> Optional[Dict]:
        """Fetch detail page using an isolated browser instance"""
        detail_driver = None
        try:
            detail_ua = UserAgent().random
            detail_options = Options()
            detail_options.add_argument(f"--user-agent={detail_ua}")
            detail_options.add_argument("--no-sandbox")
            detail_options.add_argument("--disable-dev-shm-usage")
            detail_options.add_argument("--disable-blink-features=AutomationControlled")
            detail_options.add_argument("--disable-gpu")
            detail_options.add_argument("--headless=new")
            detail_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            detail_options.add_experimental_option('useAutomationExtension', False)
            detail_prefs = {"profile.managed_default_content_settings.images": 2}
            detail_options.add_experimental_option("prefs", detail_prefs)

            # Retry service startup to avoid transient chromedriver connection failures.
            last_error = None
            for attempt in range(1, 4):
                try:
                    if attempt < 3:
                        detail_service = Service(ChromeDriverManager().install())
                        detail_driver = webdriver.Chrome(service=detail_service, options=detail_options)
                    else:
                        detail_driver = webdriver.Chrome(options=detail_options)
                    break
                except Exception as e:
                    last_error = e
                    wait_time = attempt * 2
                    print(f"    Detail driver init attempt {attempt}/3 failed: {e}")
                    time.sleep(wait_time)

            if not detail_driver:
                raise last_error if last_error else RuntimeError("Failed to initialize detail driver")

            stealth(detail_driver,
                    user_agent=detail_ua,
                    languages=["en-US", "en"],
                    vendor="Google Inc.",
                    platform="Win32",
                    webgl_vendor="Intel Inc.",
                    renderer="Intel Iris OpenGL Engine",
                    fix_hairline=False)

            detail_driver.get(property_url)
            time.sleep(2.5)
            
            # Handle Cloudflare
            for _ in range(15):
                title = detail_driver.title or ''
                if 'just a moment' in title.lower():
                    time.sleep(1)
                else:
                    break
            
            soup = BeautifulSoup(detail_driver.page_source, 'html.parser')
            detail_data = {}
            
            # Check blocked
            title_tag = soup.find('title')
            if title_tag and 'just a moment' in title_tag.get_text().lower():
                print("    Cloudflare blocked detail page")
                return None
            
            # ---- LOCATION ----
            for param_item in soup.find_all('li', class_=lambda x: x and 'announcement-parameters' in str(x)):
                text = param_item.get_text(strip=True)
                if text.startswith('Location'):
                    loc = text.replace('Location', '').strip().strip(':')
                    parts = [p.strip() for p in loc.split(',')]
                    if len(parts) >= 1:
                        detail_data['city'] = parts[0]
                    if len(parts) >= 2:
                        detail_data['district'] = parts[1]
                    if len(parts) >= 3:
                        detail_data['area'] = parts[2]
            
            # Mobile: Detail_block
            if 'city' not in detail_data:
                for div in soup.find_all(class_=lambda x: x and 'Detail_block' in x):
                    text = div.get_text(strip=True)
                    if text.startswith('Location:'):
                        loc = text.replace('Location:', '').strip()
                        parts = loc.split('\u2014')
                        if len(parts) >= 1:
                            detail_data['city'] = parts[0].strip()
                        if len(parts) >= 2:
                            sub_parts = parts[1].strip().split(' - ')
                            detail_data['district'] = sub_parts[0].strip()
                            detail_data['area'] = sub_parts[-1].strip() if len(sub_parts) > 1 else ''
                        break
            
            # ---- PRICE PER SQM ----
            page_text = soup.get_text()
            price_sqm_match = re.search(r'\u20ac\s*([\d,.]+)\s*/\s*m\u00b2', page_text)
            if price_sqm_match:
                parsed = self._extract_price(price_sqm_match.group(1))
                if parsed is not None:
                    detail_data['price_per_sqm'] = parsed
            
            # ---- FEATURES / PARAMETERS ----
            field_map = {
                'Reference number': 'reference_number',
                'Property area': 'property_area_sqm',
                'Type': 'property_type',
                'Parking': 'parking',
                'Condition': 'condition',
                'Plot area': 'plot_area_sqm',
                'Furnishing': 'furnishing',
                'Included': 'included',
                'Postal code': 'postal_code',
                'Construction year': 'construction_year',
                'Online viewing': 'online_viewing',
                'Air conditioning': 'air_conditioning',
                'Energy Efficiency': 'energy_efficiency',
                'Energy efficiency': 'energy_efficiency',
                'Bedrooms': 'bedrooms',
                'Bathrooms': 'bathrooms',
                'Square meter price': 'price_per_sqm',
            }

            def _norm_label(text: str) -> str:
                return re.sub(r'\s+', ' ', (text or '')).strip().rstrip(':').lower()

            label_to_key = {_norm_label(k): v for k, v in field_map.items()}

            # Primary: announcement-characteristics (key-chars/value-chars)
            chars_div = soup.find('div', class_=lambda x: x and 'announcement-characteristics' in str(x))
            if chars_div:
                for li in chars_div.find_all('li'):
                    key_elem = li.find('span', class_='key-chars')
                    if not key_elem:
                        continue
                    key_norm = _norm_label(key_elem.get_text(' ', strip=True))
                    db_key = label_to_key.get(key_norm)
                    if not db_key:
                        continue

                    # Some keys (like Included) can have multiple values
                    value_elems = li.find_all(class_='value-chars')
                    values = [v.get_text(strip=True) for v in value_elems if v.get_text(strip=True)]
                    
                    if not values:
                        continue

                    if db_key == 'included':
                        for v in values:
                            self._set_detail_field(detail_data, db_key, v)
                    else:
                        self._set_detail_field(detail_data, db_key, values[0])

            # Fallback: announcement-parameters (older layout)
            param_items = soup.find_all('li', class_=lambda x: x and 'announcement-parameters' in str(x))
            for item in param_items:
                item_text = item.get_text(strip=True)
                for label, key in field_map.items():
                    if item_text.startswith(label):
                        value = item_text[len(label):].strip().strip(':')
                        self._set_detail_field(detail_data, key, value)
                        break
            
            # Mobile Features_item
            if not param_items:
                feature_items = soup.find_all(class_=lambda x: x and 'Features_item' in x and 'show-more' not in x)
                for item in feature_items:
                    item_text = item.get_text(strip=True)
                    for label, key in field_map.items():
                        if item_text.startswith(label):
                            value = item_text[len(label):].strip()
                            self._set_detail_field(detail_data, key, value)
                            break
            
            # ---- DESCRIPTION ----
            desc_elem = soup.find('div', class_='js-description')
            if not desc_elem:
                desc_elem = soup.find('div', class_=lambda x: x and 'announcement-description' in str(x))
            if not desc_elem:
                desc_elem = soup.find(attrs={'itemprop': 'description'})
            if not desc_elem:
                desc_elem = soup.find(class_=lambda x: x and 'Description_container' in x)
            if desc_elem:
                description = desc_elem.get_text(separator=' ', strip=True)
                description = re.sub(
                    r'(Show original|Read more|Translate to:?|Ελληνικα|English|Русский|Deutsch|Description\s*:?\s*)',
                    '', description).strip()
                description = re.sub(r'\s{2,}', ' ', description)
                if len(description) > 10:
                    detail_data['description'] = description
            
            return detail_data if detail_data else None
            
        except Exception as e:
            print(f"  Error fetching details: {e}")
            return None
        finally:
            if detail_driver:
                try:
                    detail_driver.quit()
                except:
                    pass
    
    def _set_detail_field(self, detail_data: Dict, key: str, value: str):
        """Parse and set a detail field with proper type conversion"""
        if not value:
            return
        value = re.sub(r'\s+', ' ', str(value)).strip()
        if key in ('property_area_sqm', 'plot_area_sqm'):
            m = re.search(r'(\d+)', value)
            if m:
                detail_data[key] = int(m.group(1))
        elif key in ('bedrooms', 'bathrooms'):
            m = re.search(r'(\d+)', value)
            if m:
                detail_data[key] = int(m.group(1))
        elif key == 'construction_year':
            m = re.search(r'(\d{4})', value)
            if m:
                detail_data[key] = int(m.group(1))
        elif key == 'price_per_sqm':
            parsed = self._extract_price(value)
            if parsed is not None:
                detail_data[key] = parsed
        elif key == 'included':
            items = detail_data.get('included')
            if not isinstance(items, list):
                items = []
            
            # Split comma-separated values into individual items
            for item in value.split(','):
                item = item.strip()
                if item and item not in items:
                    items.append(item)
            
            detail_data['included'] = items
        else:
            detail_data[key] = value
    
    
    def _extract_id_from_url(self, url: str) -> str:
        """Extract property ID from URL like /adv/5755577_4-bedroom-..."""
        match = re.search(r'/adv/(\d+)', url)
        if match:
            return match.group(1)
        match = re.search(r'/(\d+)/?$', url)
        return match.group(1) if match else url
    
    def _extract_price(self, price_text: str) -> Optional[float]:
        """Extract numeric price from text. Handles European format (€365.000 = 365000)"""
        # Remove currency symbols, spaces, etc.
        price_text = re.sub(r'[^\d,.]', '', price_text)
        
        if not price_text:
            return None
        
        # Detect European format: dots as thousands separators
        # E.g. "365.000" or "1.250.000" — dots separate groups of 3 digits
        # vs decimal: "365.50" — dot followed by 1-2 digits at end
        if re.match(r'^\d{1,3}(\.\d{3})+$', price_text):
            # European thousands format: 365.000 → 365000, 1.250.000 → 1250000
            price_text = price_text.replace('.', '')
        elif ',' in price_text and '.' in price_text:
            # Mixed format like 1,250.00 or 1.250,00
            if price_text.index(',') < price_text.index('.'):
                # 1,250.00 — comma is thousands
                price_text = price_text.replace(',', '')
            else:
                # 1.250,00 — dot is thousands, comma is decimal
                price_text = price_text.replace('.', '').replace(',', '.')
        elif ',' in price_text:
            # Could be 365,000 (thousands) or 365,50 (decimal)
            if re.match(r'^\d{1,3}(,\d{3})+$', price_text):
                price_text = price_text.replace(',', '')
            else:
                price_text = price_text.replace(',', '.')
        
        try:
            return float(price_text)
        except ValueError:
            return None
    
    def _parse_location(self, location: str) -> tuple:
        """Parse location string into city, district, area"""
        parts = [p.strip() for p in location.split(',')]
        city = parts[0] if len(parts) > 0 else ''
        district = parts[1] if len(parts) > 1 else ''
        area = parts[2] if len(parts) > 2 else ''
        return city, district, area
    
    def _parse_details(self, details_elem) -> tuple:
        """Parse property details (bedrooms, bathrooms, size)"""
        if not details_elem:
            return None, None, None
        
        details_text = details_elem.get_text()
        
        bedrooms_match = re.search(r'(\d+)\s*bed', details_text, re.IGNORECASE)
        bedrooms = int(bedrooms_match.group(1)) if bedrooms_match else None
        
        bathrooms_match = re.search(r'(\d+)\s*bath', details_text, re.IGNORECASE)
        bathrooms = int(bathrooms_match.group(1)) if bathrooms_match else None
        
        size_match = re.search(r'(\d+)\s*m²', details_text)
        size_sqm = int(size_match.group(1)) if size_match else None
        
        return bedrooms, bathrooms, size_sqm
    
    def save_to_json(self, properties: List[Dict], filename: str):
        """Save scraped properties to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(properties, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(properties)} properties to {filename}")


if __name__ == "__main__":
    main()
