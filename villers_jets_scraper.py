#!/usr/bin/env python3
"""
IMPROVED Villers Jets Empty Legs Scraper
Works with actual Villers Jets website structure
"""

import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Optional
from datetime import datetime
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

VILLERS_EMPTY_LEGS_URL = "https://www.villiersjets.com/empty-legs/"
VILLERS_AFFILIATE_ID = "7275"

class VillersJetsScraper:
    """Scrape empty leg deals from Villers Jets - IMPROVED VERSION."""
    
    def __init__(self, affiliate_id: str = VILLERS_AFFILIATE_ID):
        self.affiliate_id = affiliate_id
        self.base_url = VILLERS_EMPTY_LEGS_URL
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def scrape_empty_legs(self, region: Optional[str] = None) -> List[Dict]:
        """
        Scrape empty leg flights from Villers Jets.
        IMPROVED: Finds links on main page, then extracts route info.
        """
        try:
            logger.info(f"Scraping Villers Jets empty legs from {self.base_url}")
            
            response = requests.get(self.base_url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch Villers Jets page: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            empty_legs = []
            
            # IMPROVED METHOD 1: Find all links to /empty-legs/[route] pages
            empty_leg_links = soup.find_all('a', href=re.compile(r'/empty-legs/[a-z0-9-]+'))
            
            logger.info(f"Found {len(empty_leg_links)} potential empty leg links")
            
            for link in empty_leg_links[:30]:  # Process up to 30 links
                try:
                    href = link.get('href')
                    
                    # Skip if it's just the main page
                    if href == '/empty-legs/' or href == '/empty-legs':
                        continue
                    
                    # Extract route from URL or link text
                    empty_leg = self._parse_empty_leg_link(link, href)
                    
                    if empty_leg:
                        empty_legs.append(empty_leg)
                        logger.info(f"✅ Parsed: {empty_leg['route']}")
                
                except Exception as e:
                    logger.debug(f"Error parsing link: {e}")
                    continue
            
            # IMPROVED METHOD 2: Look for structured data or specific elements
            if not empty_legs:
                logger.info("Method 1 found nothing, trying Method 2: element search")
                empty_legs = self._scrape_from_elements(soup)
            
            logger.info(f"Found {len(empty_legs)} empty leg deals total")
            return empty_legs
            
        except Exception as e:
            logger.error(f"Error scraping Villers Jets: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _parse_empty_leg_link(self, link, href: str) -> Optional[Dict]:
        """
        Parse an empty leg from a link element.
        Example URL: /empty-legs/lakefront-airport-to-san-antonio-international-airport
        """
        
        # Get link text
        link_text = link.get_text(strip=True)
        
        # Method 1: Parse from URL
        # URL format: /empty-legs/[origin]-to-[destination]
        url_match = re.search(r'/empty-legs/(.+?)-to-(.+?)(?:-international-airport|-airport)?(?:/|$)', href, re.I)
        
        if url_match:
            origin_slug = url_match.group(1).replace('-', ' ').title()
            dest_slug = url_match.group(2).replace('-', ' ').title()
            
            # Clean up common suffixes
            origin = origin_slug.replace(' Airport', '').replace(' International', '').strip()
            destination = dest_slug.replace(' Airport', '').replace(' International', '').strip()
            
            # Try to get IATA codes
            origin_code = self._extract_iata_code(origin)
            dest_code = self._extract_iata_code(destination)
            
            # Build the empty leg object
            empty_leg = {
                "route": f"{origin} → {destination}",
                "date": "TBD",  # Will try to extract from page if needed
                "aircraft": "Private Jet",
                "price": 0,  # Will try to extract
                "savings": 60,  # Default estimate
                "origin": origin_code or origin,
                "destination": dest_code or destination,
                "source": "Villers Jets",
                "url": f"https://www.villiersjets.com{href}?id={self.affiliate_id}"
            }
            
            # Try to extract price from link text or nearby elements
            price_match = re.search(r'\$\s*(\d{1,3}(?:,\d{3})*)', link_text)
            if price_match:
                try:
                    empty_leg["price"] = int(price_match.group(1).replace(',', ''))
                except:
                    pass
            
            return empty_leg
        
        # Method 2: Parse from link text
        # Text format: "Lakefront Airport to San Antonio International Airport"
        text_match = re.search(r'(.+?)\s+(?:to|→)\s+(.+)', link_text, re.I)
        
        if text_match:
            origin = text_match.group(1).replace(' Airport', '').replace(' International', '').strip()
            destination = text_match.group(2).replace(' Airport', '').replace(' International', '').strip()
            
            origin_code = self._extract_iata_code(origin)
            dest_code = self._extract_iata_code(destination)
            
            return {
                "route": f"{origin} → {destination}",
                "date": "TBD",
                "aircraft": "Private Jet",
                "price": 0,
                "savings": 60,
                "origin": origin_code or origin,
                "destination": dest_code or destination,
                "source": "Villers Jets",
                "url": f"https://www.villiersjets.com{href}?id={self.affiliate_id}"
            }
        
        return None
    
    def _extract_iata_code(self, airport_name: str) -> str:
        """Try to extract or map to IATA code."""
        
        # Common mappings
        iata_map = {
            "lakefront": "NEW",
            "new orleans": "MSY",
            "san antonio": "SAT",
            "teterboro": "TEB",
            "new york": "TEB",
            "miami": "OPF",
            "los angeles": "VNY",
            "las vegas": "VGT",
            "chicago": "PWK",
            "dallas": "ADS",
        }
        
        name_lower = airport_name.lower()
        
        for key, code in iata_map.items():
            if key in name_lower:
                return code
        
        # If no match, return first 3 letters uppercase
        return airport_name[:3].upper()
    
    def _scrape_from_elements(self, soup) -> List[Dict]:
        """Alternative scraping method using element search."""
        
        empty_legs = []
        
        # Look for any elements containing "to" pattern
        potential_routes = soup.find_all(text=re.compile(r'.+?\s+to\s+.+', re.I))
        
        logger.info(f"Found {len(potential_routes)} potential route texts")
        
        for route_text in potential_routes[:20]:
            text = route_text.strip()
            
            # Must have "to" and be reasonable length
            if 10 < len(text) < 100 and ' to ' in text.lower():
                match = re.search(r'(.+?)\s+to\s+(.+)', text, re.I)
                
                if match:
                    origin = match.group(1).replace(' Airport', '').strip()
                    destination = match.group(2).replace(' Airport', '').strip()
                    
                    empty_legs.append({
                        "route": f"{origin} → {destination}",
                        "date": "TBD",
                        "aircraft": "Private Jet",
                        "price": 0,
                        "savings": 60,
                        "origin": self._extract_iata_code(origin),
                        "destination": self._extract_iata_code(destination),
                        "source": "Villers Jets",
                        "url": f"https://www.villiersjets.com/?id={self.affiliate_id}"
                    })
        
        return empty_legs
    
    def _build_booking_url(self, origin: str, destination: str) -> str:
        """Build booking URL with affiliate tracking."""
        route = f"{origin}-{destination}".replace(" ", "-")
        return f"https://www.villiersjets.com/?id={self.affiliate_id}&utm_source=ecofriendly&utm_medium=chatbot&route={route}"


# Convenience function
def get_villers_empty_legs(region: Optional[str] = None) -> List[Dict]:
    """Quick function to get empty legs."""
    scraper = VillersJetsScraper()
    return scraper.scrape_empty_legs(region)


if __name__ == "__main__":
    # Test the scraper
    print("Testing IMPROVED Villers Jets Scraper...\n")
    
    scraper = VillersJetsScraper()
    empty_legs = scraper.scrape_empty_legs()
    
    if empty_legs:
        print(f"✅ Found {len(empty_legs)} empty leg deals!\n")
        
        for i, leg in enumerate(empty_legs[:5], 1):
            print(f"{i}. {leg['route']}")
            print(f"   Origin: {leg['origin']}")
            print(f"   Destination: {leg['destination']}")
            print(f"   URL: {leg['url']}\n")
    else:
        print("⚠️  No empty legs found")
        print("This could mean:")
        print("1. Villers Jets website structure changed")
        print("2. No empty legs currently available")
        print("3. Need to run debug_villers_scraper.py to inspect HTML")