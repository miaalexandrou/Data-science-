"""
Bazaraki.com Property Scraper
Scrapes real estate listings from Bazaraki.com for Cyprus properties
"""

import requests
from bs4 import BeautifulSoup
import time
import json
from datetime import datetime
from typing import Dict, List, Optional
import re


class BazarakiScraper:
    """
    Web scraper for Bazaraki.com real estate listings
    """
    
    def __init__(self):
        self.base_url = "https://www.bazaraki.com"
        self.properties_url = f"{self.base_url}/real-estate-for-sale/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def get_property_listings(self, city: Optional[str] = None, max_pages: int = 5) -> List[Dict]:
        """
        Fetch property listings from Bazaraki
        
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
            url = f"{url}{city.lower()}/"
            
        print(f"Starting to scrape Bazaraki: {url}")
        
        for page in range(1, max_pages + 1):
            page_url = f"{url}?page={page}" if page > 1 else url
            print(f"Scraping page {page}...")
            
            try:
                response = self.session.get(page_url, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find property listings (adjust selectors based on actual HTML structure)
                listings = soup.find_all('li', class_='announcement-container')
                
                if not listings:
                    print(f"No listings found on page {page}")
                    break
                
                for listing in listings:
                    property_data = self._parse_listing(listing)
                    if property_data:
                        properties.append(property_data)
                
                # Respect rate limiting
                time.sleep(2)
                
            except requests.RequestException as e:
                print(f"Error fetching page {page}: {e}")
                break
        
        print(f"Total properties scraped: {len(properties)}")
        return properties
    
    def _parse_listing(self, listing) -> Optional[Dict]:
        """
        Parse individual property listing
        
        Args:
            listing: BeautifulSoup element containing listing data
            
        Returns:
            Dictionary with property details or None if parsing fails
        """
        try:
            # Extract basic information (adjust selectors based on actual HTML)
            title_elem = listing.find('a', class_='announcement-title')
            price_elem = listing.find('div', class_='announcement-price')
            location_elem = listing.find('div', class_='announcement-location')
            
            if not (title_elem and price_elem):
                return None
            
            # Property URL and ID
            property_url = title_elem.get('href', '')
            property_id = self._extract_id_from_url(property_url)
            
            # Price extraction
            price_text = price_elem.get_text(strip=True)
            price = self._extract_price(price_text)
            
            # Location
            location = location_elem.get_text(strip=True) if location_elem else ''
            city, district, area = self._parse_location(location)
            
            # Additional details
            details_elem = listing.find('div', class_='announcement-details')
            bedrooms, bathrooms, size_sqm = self._parse_details(details_elem)
            
            property_data = {
                'source': 'bazaraki',
                'external_id': property_id,
                'url': f"{self.base_url}{property_url}",
                'title': title_elem.get_text(strip=True),
                'price': price,
                'city': city,
                'district': district,
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
            response = self.session.get(property_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
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
            
        except requests.RequestException as e:
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
    
    for city in cities:
        print(f"\n{'='*50}")
        print(f"Scraping {city.upper()}")
        print(f"{'='*50}")
        
        properties = scraper.get_property_listings(city=city, max_pages=3)
        all_properties.extend(properties)
        
        time.sleep(3)  # Delay between cities
    
    # Save results
    scraper.save_to_json(all_properties, 'data/raw/bazaraki_properties.json')
    
    print(f"\n{'='*50}")
    print(f"Scraping completed!")
    print(f"Total properties collected: {len(all_properties)}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
