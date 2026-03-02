#!/usr/bin/env python3
from src.scrapers.bazaraki_scraper import BazarakiScraper
import os

print('Quick scraper test...')
scraper = BazarakiScraper()

try:
    # Scrape Nicosia only with 5 listings
    print("Scraping Nicosia with 5 listings...")
    properties = scraper.get_property_listings(city='nicosia', max_pages=1, max_listings=5)
    
    print(f"\nGot {len(properties)} properties")
    
    if properties:
        print(f"\nFirst property:")
        import json
        print(json.dumps(properties[0], indent=2, default=str))
    
    # Save to file
    output_dir = 'data/raw'
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, 'bazaraki_properties.json')
    scraper.save_to_json(properties, output_file)
    print(f"\nSaved to {output_file}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    
finally:
    scraper.close_driver()
