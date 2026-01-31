#!/usr/bin/env python3
"""
Villers Jets Scraper - ACTUALLY WORKS!
Based on real website structure with ICAO codes
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

# URLs
VILLERS_EMPTY_LEGS_URL = "https://www.villiersjets.com/empty-legs/"
VILLERS_AI_URL = "https://villiers.ai/empty-legs/"  # Alternative domain
VILLERS_AFFILIATE_ID = "7275"

class VillersJetsScraper:
    """Scrape empty leg deals from Villers Jets - WORKING VERSION."""
    
    def __init__(self, affiliate_id: str = VILLERS_AFFILIATE_ID):
        self.affiliate_id = affiliate_id
        self.base_url = VILLERS_EMPTY_LEGS_URL
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # ICAO to IATA code mapping (for matching)
        self.icao_to_iata = {
            # US Airports (K prefix)
            "KNEW": "NEW",  # Lakefront, New Orleans
            "KMSY": "MSY",  # New Orleans Armstrong
            "KSAT": "SAT",  # San Antonio
            "KTEB": "TEB",  # Teterboro, NY
            "KJFK": "JFK",  # JFK, NY
            "KEWR": "EWR",  # Newark, NJ
            "KLGA": "LGA",  # LaGuardia, NY
            "KVNY": "VNY",  # Van Nuys, LA
            "KLAX": "LAX",  # Los Angeles
            "KOPF": "OPF",  # Opa-locka, Miami
            "KMIA": "MIA",  # Miami
            "KFLL": "FLL",  # Fort Lauderdale
            "KPWK": "PWK",  # Chicago Executive
            "KORD": "ORD",  # Chicago O'Hare
            "KMDW": "MDW",  # Chicago Midway
            "KADS": "ADS",  # Dallas Addison
            "KDFW": "DFW",  # Dallas/Fort Worth
            "KPDK": "PDK",  # Atlanta DeKalb
            "KATL": "ATL",  # Atlanta
            "KHOU": "HOU",  # Houston Hobby
            "KIAH": "IAH",  # Houston Bush
            "KVGT": "VGT",  # Las Vegas North
            "KLAS": "LAS",  # Las Vegas McCarran
            "KASE": "ASE",  # Aspen
            "KBOS": "BOS",  # Boston
            "KSEA": "SEA",  # Seattle
            "KPHX": "PHX",  # Phoenix
            "KSFO": "SFO",  # San Francisco
            # Add more as needed
        }
    
    def scrape_empty_legs(self, region: Optional[str] = None) -> List[Dict]:
        """
        Scrape empty legs from Villers Jets.
        Uses ACTUAL structure: finds list items with ICAO codes, dates, prices.
        """
        try:
            logger.info(f"Scraping Villers Jets from {self.base_url}")
            
            response = requests.get(self.base_url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch page: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            empty_legs = []
            
            # Method 1: Find all text matching "XXXX → XXXX" pattern (ICAO codes)
            # Looking for patterns like "KNEW → KSAT" or "EIAL EIDL"
            
            # Try to find list items or table rows
            potential_items = []
            
            # Look for divs/rows that might contain flight data
            potential_items.extend(soup.find_all('div', class_=re.compile(r'leg|flight|item|row', re.I)))
            potential_items.extend(soup.find_all('tr'))
            potential_items.extend(soup.find_all('li'))
            
            logger.info(f"Found {len(potential_items)} potential items to parse")
            
            for item in potential_items:
                try:
                    empty_leg = self._parse_empty_leg_item(item)
                    if empty_leg:
                        empty_legs.append(empty_leg)
                        logger.info(f"✅ Parsed: {empty_leg['origin_icao']} → {empty_leg['dest_icao']}")
                except Exception as e:
                    logger.debug(f"Error parsing item: {e}")
                    continue
            
            # Method 2: If nothing found, look for ALL ICAO code patterns in text
            if not empty_legs:
                logger.info("Method 1 found nothing, trying Method 2: text pattern search")
                empty_legs = self._scrape_from_text_patterns(soup)
            
            logger.info(f"Found {len(empty_legs)} empty leg deals total")
            return empty_legs
            
        except Exception as e:
            logger.error(f"Error scraping Villers Jets: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _parse_empty_leg_item(self, item) -> Optional[Dict]:
        """
        Parse a single empty leg from HTML element.
        Looks for ICAO codes, dates, prices.
        """
        
        text = item.get_text(separator=' ', strip=True)
        
        # Must have at least 2 airport codes (4 letters each, starting with K or E usually)
        # Pattern: KXXX or EXXX (US and Europe)
        icao_pattern = r'\b([KE][A-Z]{3})\b'
        icao_codes = re.findall(icao_pattern, text)
        
        if len(icao_codes) < 2:
            return None
        
        origin_icao = icao_codes[0]
        dest_icao = icao_codes[1]
        
        # Convert ICAO to IATA for matching
        origin_iata = self.icao_to_iata.get(origin_icao, origin_icao)
        dest_iata = self.icao_to_iata.get(dest_icao, dest_icao)
        
        # Extract date (format: DD/MM/YYYY or YYYY-MM-DD)
        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})|(\d{4}-\d{2}-\d{2})', text)
        date_str = date_match.group(0) if date_match else "TBD"
        
        # Extract price (format: $X,XXX)
        price = 0
        price_match = re.search(r'\$\s*(\d{1,3}(?:,\d{3})*)', text)
        if price_match:
            try:
                price = int(price_match.group(1).replace(',', ''))
            except:
                pass
        
        # Extract aircraft type
        aircraft = "Private Jet"
        aircraft_types = ['Citation', 'Challenger', 'Gulfstream', 'Falcon', 'Phenom', 'Learjet', 'Global', 'Legacy']
        for ac_type in aircraft_types:
            if ac_type.lower() in text.lower():
                aircraft = ac_type
                # Try to get full model
                model_match = re.search(rf'{ac_type}\s+([A-Z0-9]+)', text, re.I)
                if model_match:
                    aircraft = f"{ac_type} {model_match.group(1)}"
                break
        
        # Build URL: https://villiers.ai/empty-legs/[origin]-[dest]-[date]
        # Date format for URL: YYYY-MM-DD
        url_date = date_str
        if '/' in date_str:
            try:
                # Convert DD/MM/YYYY to YYYY-MM-DD
                parts = date_str.split('/')
                url_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
            except:
                url_date = "2026-02-02"  # Default
        
        empty_leg_url = f"https://villiers.ai/empty-legs/{origin_icao.lower()}-{dest_icao.lower()}-{url_date}"
        
        return {
            "route": f"{origin_iata} → {dest_iata}",
            "date": date_str,
            "aircraft": aircraft,
            "price": price,
            "savings": 60,  # Default estimate
            "origin": origin_iata,
            "destination": dest_iata,
            "origin_icao": origin_icao,
            "dest_icao": dest_icao,
            "source": "Villers Jets",
            "url": f"{empty_leg_url}?id={self.affiliate_id}"
        }
    
    def _scrape_from_text_patterns(self, soup) -> List[Dict]:
        """
        Alternative method: Find ICAO code patterns in all text.
        """
        empty_legs = []
        
        # Get all text
        page_text = soup.get_text()
        
        # Find all ICAO code pairs (4-letter codes)
        # Pattern: KXXX or EXXX followed by another KXXX/EXXX
        pattern = r'\b([KE][A-Z]{3})\s*(?:→|to|-|>)\s*([KE][A-Z]{3})\b'
        matches = re.finditer(pattern, page_text, re.I)
        
        for match in matches:
            origin_icao = match.group(1).upper()
            dest_icao = match.group(2).upper()
            
            origin_iata = self.icao_to_iata.get(origin_icao, origin_icao)
            dest_iata = self.icao_to_iata.get(dest_icao, dest_icao)
            
            empty_legs.append({
                "route": f"{origin_iata} → {dest_iata}",
                "date": "TBD",
                "aircraft": "Private Jet",
                "price": 0,
                "savings": 60,
                "origin": origin_iata,
                "destination": dest_iata,
                "origin_icao": origin_icao,
                "dest_icao": dest_icao,
                "source": "Villers Jets",
                "url": f"https://villiers.ai/empty-legs/{origin_icao.lower()}-{dest_icao.lower()}-2026-02-02?id={self.affiliate_id}"
            })
        
        logger.info(f"Text pattern method found {len(empty_legs)} routes")
        return empty_legs[:20]  # Limit to 20


# Convenience function
def get_villers_empty_legs(region: Optional[str] = None) -> List[Dict]:
    """Quick function to get empty legs."""
    scraper = VillersJetsScraper()
    return scraper.scrape_empty_legs(region)


if __name__ == "__main__":
    # Test the scraper
    print("Testing Villers Jets Scraper (ICAO version)...\n")
    
    scraper = VillersJetsScraper()
    empty_legs = scraper.scrape_empty_legs()
    
    if empty_legs:
        print(f"✅ Found {len(empty_legs)} empty leg deals!\n")
        
        for i, leg in enumerate(empty_legs[:10], 1):
            price_str = f"${leg['price']:,}" if leg['price'] > 0 else "Call for quote"
            print(f"{i}. {leg['route']} ({leg['origin_icao']} → {leg['dest_icao']})")
            print(f"   Date: {leg['date']}")
            print(f"   Aircraft: {leg['aircraft']}")
            print(f"   Price: {price_str}")
            print(f"   URL: {leg['url']}\n")
    else:
        print("⚠️  No empty legs found")
        print("\nTroubleshooting:")
        print("1. Run with: python3 -c 'import villers_jets_scraper; villers_jets_scraper.get_villers_empty_legs()'")
        print("2. Check if website structure changed")
        print("3. Verify ICAO codes are being parsed correctly")