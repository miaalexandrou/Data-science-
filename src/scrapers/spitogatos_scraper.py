"""
Spitogatos.com.cy Property Scraper
Scrapes real estate listings from Spitogatos for Cyprus properties
"""

import requests
from bs4 import BeautifulSoup
import time
import json
from datetime import datetime
from typing import Dict, List, Optional
import re


class SpitoGatosScraper:
    """
    Web scraper for Spitogatos.com.cy real estate listings
    """
    
    def __init__(self):
        self.base_url = "https://www.spitogatos.com.cy"
        self.search_url = f"{self.base_url}/en/properties/for-sale"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def get_property_listings(
        self, 
        city: Optional[str] = None, 
        property_type: Optional[str] = None,
        max_pages: int = 5
    ) -> List[Dict]:
        """
        Fetch property listings from Spitogatos
        
        Args:
            city: Filter by city (e.g., 'nicosia', 'limassol')
            property_type: Filter by type (e.g., 'house', 'apartment')
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of property dictionaries
        """
        properties = []
        
        # Build URL with filters
        url = self.search_url
        params = []
        
        if city:
            params.append(f"location={city.lower()}")
        if property_type:
            params.append(f"type={property_type.lower()}")
            
        if params:
            url = f"{url}?{'&'.join(params)}"
            
        print(f"Starting to scrape Spitogatos: {url}")
        
        for page in range(1, max_pages + 1):
            page_url = f"{url}&page={page}" if '?' in url else f"{url}?page={page}"
            print(f"Scraping page {page}...")
            
            try:
                response = self.session.get(page_url, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find property listings (adjust selectors based on actual HTML structure)
                listings = soup.find_all('div', class_='property-card')
                
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
            title_elem = listing.find('h3', class_='property-title')
            price_elem = listing.find('span', class_='property-price')
            location_elem = listing.find('span', class_='property-location')
            
            if not (title_elem and price_elem):
                return None
            
            # Property URL and ID
            link_elem = listing.find('a', class_='property-link')
            property_url = link_elem.get('href', '') if link_elem else ''
            property_id = self._extract_id_from_url(property_url)
            
            # Price extraction
            price_text = price_elem.get_text(strip=True)
            price = self._extract_price(price_text)
            
            # Location
            location = location_elem.get_text(strip=True) if location_elem else ''
            city, district, area = self._parse_location(location)
            
            # Property details
            details_container = listing.find('div', class_='property-details')
            property_type = self._extract_property_type(details_container)
            bedrooms = self._extract_number(details_container, 'bedroom')
            bathrooms = self._extract_number(details_container, 'bathroom')
            size_sqm = self._extract_size(details_container)
            
            property_data = {
                'source': 'spitogatos',
                'external_id': property_id,
                'url': f"{self.base_url}{property_url}" if not property_url.startswith('http') else property_url,
                'title': title_elem.get_text(strip=True),
                'price': price,
                'city': city,
                'district': district,
                'area': area,
                'property_type': property_type,
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
                'year_built': self._extract_year_built(soup),
                'floor_level': self._extract_floor(soup),
                'has_parking': self._check_amenity(soup, 'parking'),
                'has_pool': self._check_amenity(soup, 'swimming pool'),
                'has_garden': self._check_amenity(soup, 'garden'),
                'energy_rating': self._extract_energy_rating(soup),
                'listing_date': self._extract_listing_date(soup),
                'photos_count': len(soup.find_all('img', class_='property-photo')),
                'latitude': self._extract_coordinate(soup, 'latitude'),
                'longitude': self._extract_coordinate(soup, 'longitude'),
            }
            
            time.sleep(2)  # Rate limiting
            return details
            
        except requests.RequestException as e:
            print(f"Error fetching property details: {e}")
            return None
    
    # Helper methods for data extraction
    
    def _extract_id_from_url(self, url: str) -> str:
        """Extract property ID from URL"""
        match = re.search(r'/property/(\d+)', url)
        if match:
            return match.group(1)
        # Fallback: use last part of URL
        return url.split('/')[-1].split('-')[0] if url else ''
    
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
        city = parts[-1] if len(parts) > 0 else ''  # Usually city is last
        district = parts[-2] if len(parts) > 1 else ''
        area = parts[0] if len(parts) > 2 else ''
        return city, district, area
    
    def _extract_property_type(self, details_elem) -> Optional[str]:
        """Extract property type"""
        if not details_elem:
            return None
        
        type_elem = details_elem.find('span', class_='property-type')
        if type_elem:
            return type_elem.get_text(strip=True).lower()
        
        # Try to infer from text
        details_text = details_elem.get_text().lower()
        if 'apartment' in details_text:
            return 'apartment'
        elif 'house' in details_text:
            return 'house'
        elif 'villa' in details_text:
            return 'villa'
        
        return None
    
    def _extract_number(self, details_elem, keyword: str) -> Optional[int]:
        """Extract numeric value associated with keyword (e.g., bedrooms)"""
        if not details_elem:
            return None
        
        pattern = rf'(\d+)\s*{keyword}'
        match = re.search(pattern, details_elem.get_text(), re.IGNORECASE)
        return int(match.group(1)) if match else None
    
    def _extract_size(self, details_elem) -> Optional[int]:
        """Extract property size in square meters"""
        if not details_elem:
            return None
        
        size_elem = details_elem.find('span', class_='property-size')
        if size_elem:
            size_text = size_elem.get_text()
            match = re.search(r'(\d+)', size_text)
            return int(match.group(1)) if match else None
        
        return None
    
    def _extract_description(self, soup) -> str:
        """Extract property description"""
        desc_elem = soup.find('div', class_='property-description')
        return desc_elem.get_text(strip=True) if desc_elem else ''
    
    def _extract_year_built(self, soup) -> Optional[int]:
        """Extract year built"""
        year_elem = soup.find('span', text=re.compile('Year Built|Construction Year', re.IGNORECASE))
        if year_elem:
            year_text = year_elem.find_next().get_text(strip=True)
            match = re.search(r'\d{4}', year_text)
            return int(match.group()) if match else None
        return None
    
    def _extract_floor(self, soup) -> Optional[int]:
        """Extract floor level"""
        floor_elem = soup.find('span', text=re.compile('Floor', re.IGNORECASE))
        if floor_elem:
            floor_text = floor_elem.find_next().get_text(strip=True)
            match = re.search(r'\d+', floor_text)
            return int(match.group()) if match else None
        return None
    
    def _check_amenity(self, soup, amenity: str) -> bool:
        """Check if property has a specific amenity"""
        amenities_section = soup.find('div', class_='amenities')
        if amenities_section:
            amenities_text = amenities_section.get_text().lower()
            return amenity.lower() in amenities_text
        return False
    
    def _extract_energy_rating(self, soup) -> Optional[str]:
        """Extract energy efficiency rating"""
        energy_elem = soup.find('span', text=re.compile('Energy Class|Energy Rating', re.IGNORECASE))
        if energy_elem:
            return energy_elem.find_next().get_text(strip=True)
        return None
    
    def _extract_listing_date(self, soup) -> Optional[str]:
        """Extract listing publication date"""
        date_elem = soup.find('span', class_='listing-date')
        if date_elem:
            return date_elem.get('datetime') or date_elem.get_text(strip=True)
        return None
    
    def _extract_coordinate(self, soup, coord_type: str) -> Optional[float]:
        """Extract GPS coordinates"""
        map_elem = soup.find('div', {'data-' + coord_type: True})
        if map_elem:
            try:
                return float(map_elem.get('data-' + coord_type))
            except (ValueError, TypeError):
                return None
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
    scraper = SpitoGatosScraper()
    
    # Scrape properties from all major cities
    cities = ['nicosia', 'limassol', 'larnaca', 'paphos']
    all_properties = []
    
    for city in cities:
        print(f"\n{'='*50}")
        print(f"Scraping {city.upper()}")
        print(f"{'='*50}")
        
        properties = scraper.get_property_listings(city=city, max_pages=3)
        all_properties.extend(properties)
        
        time.sleep(3)  # Delay between cities
    
    # Save results
    scraper.save_to_json(all_properties, 'data/raw/spitogatos_properties.json')
    
    print(f"\n{'='*50}")
    print(f"Scraping completed!")
    print(f"Total properties collected: {len(all_properties)}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
