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
from datetime import datetime
from typing import Dict, List, Optional
import re
import random
import os
import sys


# Allow importing sibling package: src/database/db_connection.py
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

from database.db_connection import DBConnection


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
            
            # Minimal delay between cities
            time.sleep(0.05)
        
        # Save results
        output_dir = 'data/raw'
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'bazaraki_properties.json')
        scraper.save_to_json(all_properties, output_file)

        # Upload to database
        if all_properties:
            try:
                with DBConnection() as db:
                    inserted = db.insert_properties(all_properties)
                print(f"Uploaded to DB: {inserted} new row(s) inserted")
            except Exception as db_error:
                print(f"Database upload failed: {db_error}")
        else:
            print("No properties scraped; skipping database upload.")
        
        print(f"\n{'='*60}")
        print(f"Scraping completed!")
        print(f"Total properties collected: {len(all_properties)}")
        print(f"Saved to: {output_file}")
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
            'limassol': 'lemesos-district-limassol',  # Corrected mapping
            'larnaka': 'larnaka-district-larnaca',
            'paphos': 'pafos-district-paphos'
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
                
                # No delay between pages
                time.sleep(0.05)
                
            except Exception as e:
                print(f"Error fetching page {page}: {e}")
                break
        
        print(f"Total properties scraped: {len(properties)}")
        return properties
    
    def _setup_driver(self):
        """Initialize Chrome WebDriver with stealth options"""
        try:
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
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Apply selenium-stealth
            stealth(self.driver,
                    user_agent=self._user_agent,
                    languages=["en-US", "en"],
                    vendor="Google Inc.",
                    platform="Win32",
                    webgl_vendor="Intel Inc.",
                    renderer="Intel Iris OpenGL Engine",
                    fix_hairline=False)
            
            print("WebDriver ready")
        except Exception as e:
            print(f"Error initializing WebDriver: {e}")
            raise
        except Exception as e:
            print(f"Error initializing WebDriver: {e}")
            raise
        except Exception as e:
            print(f"Error initializing WebDriver: {e}")
            raise
    
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
                'scraped_date': datetime.now().isoformat(),
            }
            
            return property_data
            
        except Exception as e:
            print(f"Error parsing listing: {e}")
            return None
    
    def _fetch_property_details(self, property_url: str) -> Optional[Dict]:
        """Fetch detail page using a separate Chrome instance to avoid Cloudflare"""
        detail_driver = None
        try:
            # Create a separate browser instance for the detail page
            ua = UserAgent()
            detail_ua = ua.random
            chrome_options = Options()
            chrome_options.add_argument(f"--user-agent={detail_ua}")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--headless=new")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            prefs = {"profile.managed_default_content_settings.images": 2}
            chrome_options.add_experimental_option("prefs", prefs)
            
            service = Service(ChromeDriverManager().install())
            detail_driver = webdriver.Chrome(service=service, options=chrome_options)
            
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
            price_sqm_match = re.search(r'\u20ac([\d,.]+)/m\u00b2', page_text)
            if price_sqm_match:
                detail_data['price_per_sqm'] = price_sqm_match.group(1).replace(',', '')
            
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
            
            # Desktop params
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
