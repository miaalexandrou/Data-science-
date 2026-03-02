"""
Bazaraki.com Property Scraper
Scrapes real estate listings from Bazaraki.com for Cyprus properties
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
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


class BazarakiScraper:
    """
    Web scraper for Bazaraki.com real estate listings using Selenium
    """
    
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
        
    def _setup_driver(self):
        """Initialize Chrome WebDriver with stealth options"""
        try:
            ua = UserAgent()
            chrome_options = Options()
            chrome_options.add_argument(f"--user-agent={ua.random}")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--disable-web-resources")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-images")  # Skip images
            chrome_options.add_argument("--blink-settings=imagesEnabled=false")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Apply selenium-stealth to avoid detection
            stealth(self.driver,
                    user_agent=ua.random,
                    languages=["en-US", "en"],
                    vendor="Google Inc.",
                    platform="Win32",
                    webgl_vendor="Intel Inc.",
                    renderer="Intel Iris OpenGL Engine",
                    fix_hairline=False)
            
            print("WebDriver ready (images disabled)")
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
    
    def get_property_listings(self, city: Optional[str] = None, max_pages: int = 999) -> List[Dict]:
        """
        Fetch property listings from Bazaraki using Selenium
        
        Args:
            city: Filter by city (e.g., 'nicosia', 'limassol', 'larnaka')
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of property dictionaries
        """
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
                
                # Ultra-fast minimal wait
                time.sleep(0.3)
                
                # Try to wait for listings with very minimal timeout
                try:
                    WebDriverWait(self.driver, 2).until(
                        EC.presence_of_all_elements_located((By.CLASS_NAME, "CardGrid_container"))
                    )
                except:
                    pass
                
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Find property listings - look for CardGrid containers (CSS modules)
                listings = soup.find_all(class_=lambda x: x and 'CardGrid_container' in x)
                
                if not listings:
                    # Try alternative: find all divs with CardGrid classes
                    listings = soup.find_all('div', class_=lambda x: x and 'CardGrid' in x and 'container' in x.lower())
                
                if not listings:
                    print(f"No listings found on page {page}. Checking page content...")
                    # Debug: print how many elements have 'CardGrid' in their class
                    cardgrid_elements = soup.find_all(class_=lambda x: x and 'CardGrid' in x)
                    print(f"Found {len(cardgrid_elements)} elements with 'CardGrid' in class name")
                    break
                
                print(f"Found {len(listings)} listings on page {page}")
                
                for listing in listings:
                    property_data = self._parse_listing(listing)
                    if property_data:
                        properties.append(property_data)
                
                # No delay between pages
                time.sleep(0.05)
                
            except Exception as e:
                print(f"Error fetching page {page}: {e}")
                break
        
        print(f"Total properties scraped: {len(properties)}")
        return properties
    
    def _parse_listing(self, listing) -> Optional[Dict]:
        """
        Parse individual property listing from Bazaraki's CardGrid structure
        
        Args:
            listing: BeautifulSoup element containing listing data
            
        Returns:
            Dictionary with property details or None if parsing fails
        """
        try:
            # Extract title - look for class containing 'CardGrid_title'
            title_elem = listing.find(class_=lambda x: x and 'CardGrid_title' in x)
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            title_link = title_elem.find_parent('a')
            property_url = title_link.get('href', '') if title_link else ''
            
            # Extract price - look for class containing 'CardGrid_price'
            price_elem = listing.find(class_=lambda x: x and 'CardGrid_price' in x)
            price_text = price_elem.get_text(strip=True) if price_elem else ''
            price = self._extract_price(price_text)
            
            # Extract location info from text content
            all_text = listing.get_text(strip=True)
            
            # Try to find property details - bedrooms, bathrooms, area
            bedrooms = None
            bathrooms = None
            size_sqm = None
            
            # Look for patterns like "3-bedroom" or "3 bed"
            if '4-bedroom' in all_text or '4 bed' in all_text.lower():
                bedrooms = 4
            elif '3-bedroom' in all_text or '3 bed' in all_text.lower():
                bedrooms = 3
            elif '2-bedroom' in all_text or '2 bed' in all_text.lower():
                bedrooms = 2
            elif '5-bedroom' in all_text or '5 bed' in all_text.lower():
                bedrooms = 5
            
            # Look for size in m²
            import re as regex_module
            size_match = regex_module.search(r'(\d+)\s*m²', all_text)
            if size_match:
                size_sqm = int(size_match.group(1))
            
            property_id = self._extract_id_from_url(property_url)
            
            # Extract location from the text (usually appears after property type)
            location_parts = all_text.split('—')
            city = 'Nicosia'  # Default, could be extracted from page context
            area = location_parts[-1].strip() if len(location_parts) > 1 else ''
            
            property_data = {
                'source': 'bazaraki',
                'external_id': property_id,
                'url': property_url if property_url.startswith('http') else f"{self.base_url}{property_url}",
                'title': title,
                'price': price,
                'city': city,
                'district': '',
                'area': area,
                'bedrooms': bedrooms,
                'bathrooms': bathrooms,
                'size_sqm': size_sqm,
                'scraped_date': datetime.now().isoformat(),
            }
            
            return property_data
            
        except Exception as e:
            print(f"Error parsing listing: {e}")
            return None
    
    def get_property_details(self, property_url: str) -> Optional[Dict]:
        """
        Fetch detailed information for a specific property
        
        Args:
            property_url: URL of the property listing
            
        Returns:
            Dictionary with detailed property information
        """
        try:
            self.driver.get(property_url)
            time.sleep(2)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract detailed information
            details = {
                'description': self._extract_description(soup),
                'property_type': self._extract_property_type(soup),
                'year_built': self._extract_year_built(soup),
                'floor_level': self._extract_floor(soup),
                'has_parking': self._check_feature(soup, 'parking'),
                'has_pool': self._check_feature(soup, 'pool'),
                'has_garden': self._check_feature(soup, 'garden'),
                'energy_rating': self._extract_energy_rating(soup),
                'listing_date': self._extract_listing_date(soup),
                'photos_count': len(soup.find_all('img', class_='property-image')),
            }
            
            time.sleep(2)  # Rate limiting
            return details
            
        except Exception as e:
            print(f"Error fetching property details: {e}")
            return None
    
    # Helper methods for data extraction
    
    def _extract_id_from_url(self, url: str) -> str:
        """Extract property ID from URL"""
        match = re.search(r'/(\d+)/?$', url)
        return match.group(1) if match else url
    
    def _extract_price(self, price_text: str) -> Optional[float]:
        """Extract numeric price from text"""
        # Remove currency symbols and convert to float
        price_text = re.sub(r'[^\d,.]', '', price_text)
        price_text = price_text.replace(',', '')
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
        
        # Extract bedrooms
        bedrooms_match = re.search(r'(\d+)\s*bed', details_text, re.IGNORECASE)
        bedrooms = int(bedrooms_match.group(1)) if bedrooms_match else None
        
        # Extract bathrooms
        bathrooms_match = re.search(r'(\d+)\s*bath', details_text, re.IGNORECASE)
        bathrooms = int(bathrooms_match.group(1)) if bathrooms_match else None
        
        # Extract size
        size_match = re.search(r'(\d+)\s*m²', details_text)
        size_sqm = int(size_match.group(1)) if size_match else None
        
        return bedrooms, bathrooms, size_sqm
    
    def _extract_description(self, soup) -> str:
        """Extract property description"""
        desc_elem = soup.find('div', class_='description')
        return desc_elem.get_text(strip=True) if desc_elem else ''
    
    def _extract_property_type(self, soup) -> Optional[str]:
        """Extract property type (house, apartment, villa, etc.)"""
        type_elem = soup.find('span', text=re.compile('Property Type', re.IGNORECASE))
        if type_elem:
            return type_elem.find_next_sibling().get_text(strip=True)
        return None
    
    def _extract_year_built(self, soup) -> Optional[int]:
        """Extract year built"""
        year_elem = soup.find('span', text=re.compile('Year Built', re.IGNORECASE))
        if year_elem:
            year_text = year_elem.find_next_sibling().get_text(strip=True)
            match = re.search(r'\d{4}', year_text)
            return int(match.group()) if match else None
        return None
    
    def _extract_floor(self, soup) -> Optional[int]:
        """Extract floor level"""
        floor_elem = soup.find('span', text=re.compile('Floor', re.IGNORECASE))
        if floor_elem:
            floor_text = floor_elem.find_next_sibling().get_text(strip=True)
            match = re.search(r'\d+', floor_text)
            return int(match.group()) if match else None
        return None
    
    def _check_feature(self, soup, feature: str) -> bool:
        """Check if property has a specific feature"""
        features_elem = soup.find('div', class_='features')
        if features_elem:
            features_text = features_elem.get_text().lower()
            return feature.lower() in features_text
        return False
    
    def _extract_energy_rating(self, soup) -> Optional[str]:
        """Extract energy efficiency rating"""
        energy_elem = soup.find('span', text=re.compile('Energy', re.IGNORECASE))
        if energy_elem:
            return energy_elem.find_next_sibling().get_text(strip=True)
        return None
    
    def _extract_listing_date(self, soup) -> Optional[str]:
        """Extract listing publication date"""
        date_elem = soup.find('span', class_='date-published')
        if date_elem:
            return date_elem.get('datetime') or date_elem.get_text(strip=True)
        return None
    
    def save_to_json(self, properties: List[Dict], filename: str):
        """
        Save scraped properties to JSON file
        
        Args:
            properties: List of property dictionaries
            filename: Output filename
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(properties, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(properties)} properties to {filename}")


def main():
    """Main execution function"""
    scraper = BazarakiScraper()
    
    # Scrape properties from all major cities
    cities = ['nicosia', 'limassol', 'larnaka', 'paphos']
    all_properties = []
    
    try:
        for city in cities:
            print(f"\n{'='*50}")
            print(f"Scraping {city.upper()}")
            print(f"{'='*50}")
            
            properties = scraper.get_property_listings(city=city, max_pages=999)
            all_properties.extend(properties)
            
            # Almost no delay between cities
            time.sleep(0.05)
        
        # Save results
        scraper.save_to_json(all_properties, 'data/raw/bazaraki_properties.json')
        
        print(f"\n{'='*50}")
        print(f"Scraping completed!")
        print(f"Total properties collected: {len(all_properties)}")
        print(f"{'='*50}")
    except Exception as e:
        print(f"Error during scraping: {e}")
    finally:
        # Clean up driver
        scraper.close_driver()


if __name__ == "__main__":
    main()
