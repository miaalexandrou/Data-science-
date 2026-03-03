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
from selenium_stealth import stealth
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import time
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional
import re
import random

# Allow imports from the src/ root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.database.db_connection import DBConnection


# ==================== MAIN FUNCTION ====================

def main():
    """Main execution function with user input for locations"""
    
    # Available cities
    available_cities = ['nicosia', 'limassol', 'larnaka', 'paphos']
    
    print("=" * 60)
    print("BAZARAKI PROPERTY SCRAPER")
    print("=" * 60)
    print("\nAvailable locations:")
    for i, city in enumerate(available_cities, 1):
        print(f"  {i}. {city.capitalize()}")
    print(f"  {len(available_cities) + 1}. All locations")
    
    # Get user input
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
            
            break
        except (ValueError, IndexError):
            print("Invalid input. Please enter valid numbers.")
    
    print(f"\nSelected cities: {', '.join([c.capitalize() for c in selected_cities])}")
    
    # Get number of pages to scrape
    print("\nHow many pages to scrape per city?")
    print("  1. First page only")
    print("  2. First 5 pages")
    print("  3. First 10 pages")
    print("  4. All available pages")
    print("  5. First 5 listings (testing)")
    
    while True:
        try:
            page_choice = input("\nEnter your choice (1-5): ").strip()
            
            page_map = {
                '1': (1, None),      # 1 page, no limit
                '2': (5, None),      # 5 pages, no limit
                '3': (10, None),     # 10 pages, no limit
                '4': (999, None),    # all pages, no limit
                '5': (1, 5)          # 1 page, limit to 5 listings
            }
            
            if page_choice not in page_map:
                print("Invalid choice. Please enter 1-5.")
                continue
            
            max_pages, max_listings = page_map[page_choice]
            labels = ['First page only', 'First 5 pages', 'First 10 pages', 'All pages', 'First 5 listings (testing)']
            page_label = labels[int(page_choice) - 1]
            break
        except ValueError:
            print("Invalid input. Please enter a number 1-4.")
    
    print(f"Will scrape: {page_label} per city")
    print("\nStarting scrape...\n")
    
    # Initialize scraper
    scraper = BazarakiScraper()
    all_properties = []
    
    try:
        # Scrape selected cities
        for city in selected_cities:
            print(f"\n{'='*60}")
            print(f"Scraping {city.upper()}")
            print(f"{'='*60}")
            
            properties = scraper.get_property_listings(city=city, max_pages=max_pages, max_listings=max_listings)
            all_properties.extend(properties)
            
            # Human-like pause between cities
            city_pause = random.uniform(10, 20)
            print(f"Pausing {city_pause:.1f}s before next city...")
            time.sleep(city_pause)
        
        # ── Save to database ──────────────────────────────────────
        print(f"\nSaving {len(all_properties)} properties to database...")
        with DBConnection() as db:
            inserted = db.insert_properties(all_properties)

        # ── Save JSON backup ─────────────────────────────────────────
        output_dir = 'data/raw'
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'bazaraki_properties.json')
        scraper.save_to_json(all_properties, output_file)

        print(f"\n{'='*60}")
        print(f"Scraping completed!")
        print(f"Total properties collected : {len(all_properties)}")
        print(f"New rows inserted to DB    : {inserted}")
        print(f"JSON backup saved to       : {output_file}")
        print(f"{'='*60}")
    except Exception as e:
        print(f"Error during scraping: {e}")
    finally:
        # Clean up driver
        scraper.close_driver()


# ==================== BAZARAKI SCRAPER CLASS ====================

class BazarakiScraper:
    """Web scraper for Bazaraki.com real estate listings using Selenium"""
    
    def __init__(self):
        self.base_url = "https://www.bazaraki.com"
        self.properties_url = f"{self.base_url}/real-estate-for-sale/houses/"
        self.driver = None
        self._setup_driver()
        
        # City to district mapping for Bazaraki URLs
        self.city_mapping = {
            'nicosia': 'lefkosia-district-nicosia',
            'limassol': 'lemesou-district-limassol',
            'larnaka': 'larnakas-district-larnaca',
            'paphos': 'pafou-district-paphos'
        }
    
    def get_property_listings(self, city: Optional[str] = None, max_pages: int = 999, max_listings: int = None) -> List[Dict]:
        """Fetch property listings from Bazaraki using Selenium"""
        properties = []
        
        # Build URL with filters
        url = self.properties_url
        if city:
            district = self.city_mapping.get(city.lower(), city.lower())
            url = f"{self.properties_url}{district}/"
            
        print(f"Starting to scrape Bazaraki: {url}")
        
        for page in range(1, max_pages + 1):
            page_url = f"{url}?page={page}" if page > 1 else url
            print(f"Scraping page {page}...")
            
            try:
                self.driver.get(page_url)
                
                # Human-like wait for page to load
                time.sleep(random.uniform(2.5, 5.0))
                
                # Try to wait for listings
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_all_elements_located((By.CLASS_NAME, "CardGrid_container"))
                    )
                except:
                    pass
                
                # Simulate human scrolling down the page
                self._human_scroll()
                
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Find property listings - look for CardGrid containers  
                listings = soup.find_all(class_=lambda x: x and 'CardGrid_container' in x)
                
                if not listings:
                    # Try Features_item selector
                    listings = soup.find_all(class_=lambda x: x and 'Features_item' in x)
                
                if not listings:
                    # Try advert-grid containers
                    listings = soup.find_all(class_=lambda x: x and 'advert-grid__item' in x)
                
                if not listings:
                    print(f"No listings found on page {page}. Stopping...")
                    break
                
                print(f"Found {len(listings)} listings on page {page}")
                
                for listing in listings:
                    # Stop if we've reached max_listings
                    if max_listings and len(properties) >= max_listings:
                        break
                    
                    property_data = self._parse_listing(listing)
                    if property_data:
                        properties.append(property_data)
                
                # Stop if we've reached max_listings
                if max_listings and len(properties) >= max_listings:
                    break
                
                # Human-like pause between pages
                page_pause = random.uniform(4, 9)
                print(f"  Pausing {page_pause:.1f}s before next page...")
                time.sleep(page_pause)
                
            except Exception as e:
                print(f"Error fetching page {page}: {e}")
                break
        
        print(f"Total properties scraped: {len(properties)}")
        return properties
    
    def _setup_driver(self):
        """Initialize Chrome WebDriver with stealth options"""
        try:
            ua = UserAgent()
            chrome_options = Options()
            chrome_options.add_argument(f"--user-agent={ua.random}")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--disable-gpu")
            # Randomise window size to a common desktop resolution
            width  = random.choice([1280, 1366, 1440, 1536, 1920])
            height = random.choice([768, 800, 900, 1080])
            chrome_options.add_argument(f"--window-size={width},{height}")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Apply selenium-stealth to avoid detection
            stealth(self.driver,
                    user_agent=ua.random,
                    languages=["en-US", "en"],
                    vendor="Google Inc.",
                    platform="MacIntel",
                    webgl_vendor="Intel Inc.",
                    renderer="Intel Iris OpenGL Engine",
                    fix_hairline=True)
            
            # Warm-up: visit the homepage first so later requests look like
            # natural in-site navigation rather than direct bot hits
            print("Warming up — visiting homepage...")
            self.driver.get(self.base_url)
            time.sleep(random.uniform(3, 6))
            self._human_scroll()
            
            print("WebDriver ready")
        except Exception as e:
            print(f"Error initializing WebDriver: {e}")
            raise
    
    def _human_scroll(self):
        """Simulate a human slowly scrolling down then back up a page"""
        try:
            total_height = self.driver.execute_script("return document.body.scrollHeight")
            viewport    = self.driver.execute_script("return window.innerHeight")
            steps       = random.randint(3, 7)
            step_size   = total_height // (steps + 1)
            for i in range(1, steps + 1):
                scroll_to = min(step_size * i, total_height - viewport)
                self.driver.execute_script(f"window.scrollTo(0, {scroll_to});")
                time.sleep(random.uniform(0.3, 0.9))
            # Small scroll back up — humans rarely stay at the bottom
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(0.2, 0.5))
        except Exception:
            pass

    def close_driver(self):
        """Safely close the WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
            except:
                pass
    
    def _parse_listing(self, listing) -> Optional[Dict]:
        """Parse individual property listing from Bazaraki's CardGrid structure"""
        try:
            # Extract title
            title_elem = listing.find(class_=lambda x: x and 'CardGrid_title' in x)
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
            price_elem = listing.find(class_=lambda x: x and 'CardGrid_price' in x)
            price_text = price_elem.get_text(strip=True) if price_elem else ''
            price = self._extract_price(price_text)
            
            # Extract location info from text content
            all_text = listing.get_text(strip=True)
            
            # Extract bedrooms from title
            bedrooms = None
            bed_match = re.search(r'(\d+)-?bedroom', all_text, re.IGNORECASE)
            if bed_match:
                bedrooms = int(bed_match.group(1))
            
            property_id = self._extract_id_from_url(property_url)
            
            # Extract location from the text
            location_parts = all_text.split('—')
            area = location_parts[-1].strip() if len(location_parts) > 1 else ''
            
            # Build full URL
            full_url = f"{self.base_url}{property_url}"
            
            # Fetch all details from property detail page
            print(f"  Fetching details: {property_id}...")
            detail_data = self._fetch_property_details(full_url)
            
            # Use detail data for everything
            d = detail_data if detail_data else {}
            
            property_data = {
                'source': 'bazaraki',
                'reference_number': d.get('reference_number', property_id),
                'external_id': property_id,
                'url': full_url,
                'title': title,
                'price': price,
                'city': d.get('city', 'Nicosia'),
                'district': d.get('district', ''),
                'area': d.get('area', area),
                'bedrooms': d.get('bedrooms', bedrooms),
                'bathrooms': d.get('bathrooms'),
                'property_area_sqm': d.get('property_area_sqm'),
                'plot_area_sqm': d.get('plot_area_sqm'),
                'property_type': d.get('property_type'),
                'parking': d.get('parking'),
                'condition': d.get('condition'),
                'furnishing': d.get('furnishing'),
                'included': d.get('included'),
                'postal_code': d.get('postal_code'),
                'construction_year': d.get('construction_year'),
                'online_viewing': d.get('online_viewing'),
                'air_conditioning': d.get('air_conditioning'),
                'energy_efficiency': d.get('energy_efficiency'),
                'price_per_sqm': d.get('price_per_sqm'),
                'scraped_date': datetime.now().isoformat(),
            }
            
            return property_data
            
        except Exception as e:
            print(f"Error parsing listing: {e}")
            return None
    
    def _fetch_property_details(self, property_url: str) -> Optional[Dict]:
        """Fetch detailed information from individual property page"""
        try:
            self.driver.get(property_url)
            time.sleep(random.uniform(2, 5))
            self._human_scroll()
            
            # Click "Show more features" button using JavaScript (more reliable than .click())
            try:
                show_more_buttons = self.driver.find_elements(By.CSS_SELECTOR, '[class*="Features_show-more"]')
                for btn in show_more_buttons:
                    try:
                        self.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.5)
                    except:
                        pass
            except:
                pass
            
            # Also try clicking any "Show more" text links
            try:
                show_more_links = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Show more')]")
                for link in show_more_links:
                    try:
                        self.driver.execute_script("arguments[0].click();", link)
                        time.sleep(0.5)
                    except:
                        pass
            except:
                pass
            
            # Re-parse after clicking show more
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            detail_data = {}
            
            # Extract location from detail page
            for div in soup.find_all(class_=lambda x: x and 'Detail_block' in x):
                text = div.get_text(strip=True)
                if text.startswith('Location:'):
                    loc = text.replace('Location:', '').strip()
                    # Format: "Nicosia — Strovolos - Chryseleousa"
                    parts = loc.split('—')
                    if len(parts) >= 1:
                        detail_data['city'] = parts[0].strip()
                    if len(parts) >= 2:
                        sub_parts = parts[1].strip().split(' - ')
                        detail_data['district'] = sub_parts[0].strip() if sub_parts else ''
                        detail_data['area'] = sub_parts[-1].strip() if len(sub_parts) > 1 else ''
                    break
            
            # Extract price per sqm from header
            price_text = soup.get_text()
            price_sqm_match = re.search(r'€([\d,.]+)/m²', price_text)
            if price_sqm_match:
                detail_data['price_per_sqm'] = price_sqm_match.group(1).replace(',', '')
            
            # Parse all Features_item divs — these are the key-value property details
            feature_items = soup.find_all(class_=lambda x: x and 'Features_item' in x and 'show-more' not in x)
            
            # Map of label → key name
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
                'Bedrooms': 'bedrooms',
                'Bathrooms': 'bathrooms',
                'Square meter price': 'price_per_sqm',
            }
            
            for item in feature_items:
                item_text = item.get_text(strip=True)
                
                for label, key in field_map.items():
                    if item_text.startswith(label):
                        value = item_text[len(label):].strip()
                        
                        # Parse numeric fields
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
                            m = re.search(r'[\d,.]+', value)
                            if m:
                                detail_data[key] = m.group(0).replace(',', '')
                        else:
                            detail_data[key] = value
                        break
            
            return detail_data if detail_data else None
            
        except Exception as e:
            print(f"  Error fetching details: {e}")
            return None
    
    
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
