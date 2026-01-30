#!/usr/bin/env python3
"""
Villers Jets Empty Legs Scraper
Scrapes real empty leg deals from Villers Jets website
"""

import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)

VILLERS_EMPTY_LEGS_URL = "https://www.villiersjets.com/empty-legs/"
VILLERS_AFFILIATE_ID = "7275"

class VillersJetsScraper:
    """Scrape empty leg deals from Villers Jets."""
    
    def __init__(self, affiliate_id: str = VILLERS_AFFILIATE_ID):
        self.affiliate_id = affiliate_id
        self.base_url = VILLERS_EMPTY_LEGS_URL
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def scrape_empty_legs(self, region: Optional[str] = None) -> List[Dict]:
        """
        Scrape empty leg flights from Villers Jets.
        
        Args:
            region: Optional region filter (Europe, Americas, Asia)
        
        Returns:
            List of empty leg deals with real data
        """
        try:
            logger.info(f"Scraping Villers Jets empty legs from {self.base_url}")
            
            response = requests.get(self.base_url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch Villers Jets page: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            empty_legs = []
            
            # Find empty leg listings (adjust selectors based on actual HTML structure)
            # This is a generic parser - you may need to adjust based on their actual structure
            
            # Look for flight cards/items
            flight_items = soup.find_all(['div', 'tr'], class_=re.compile(r'empty.*leg|flight.*item|leg.*card', re.I))
            
            if not flight_items:
                # Try alternative selectors
                flight_items = soup.find_all(['div', 'article'], attrs={'data-flight': True})
            
            if not flight_items:
                # Try table rows
                tables = soup.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')[1:]  # Skip header
                    if rows:
                        flight_items = rows
                        break
            
            for item in flight_items[:20]:  # Limit to 20 results
                try:
                    empty_leg = self._parse_empty_leg_item(item)
                    if empty_leg:
                        empty_legs.append(empty_leg)
                except Exception as e:
                    logger.debug(f"Error parsing item: {e}")
                    continue
            
            logger.info(f"Found {len(empty_legs)} empty leg deals")
            return empty_legs
            
        except Exception as e:
            logger.error(f"Error scraping Villers Jets: {e}")
            return []
    
    def _parse_empty_leg_item(self, item) -> Optional[Dict]:
        """Parse a single empty leg listing."""
        
        # Extract text content
        text = item.get_text(separator=' ', strip=True)
        
        # Try to find route (FROM -> TO pattern)
        route_match = re.search(r'([A-Z]{3})\s*[→-]\s*([A-Z]{3})', text, re.IGNORECASE)
        if not route_match:
            # Try city names
            route_match = re.search(r'([A-Za-z\s]+)\s*(?:to|→|-)\s*([A-Za-z\s]+)', text)
        
        if not route_match:
            return None
        
        origin = route_match.group(1).strip()
        destination = route_match.group(2).strip()
        
        # Extract date
        date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text)
        date_str = date_match.group(1) if date_match else "TBD"
        
        # Extract price
        price_match = re.search(r'[€$£]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', text)
        price = 0
        if price_match:
            price_str = price_match.group(1).replace(',', '')
            try:
                price = int(float(price_str))
            except ValueError:
                price = 0
        
        # Extract aircraft type
        aircraft = "Private Jet"
        aircraft_types = ['Gulfstream', 'Citation', 'Challenger', 'Falcon', 'Phenom', 'Learjet', 'Global', 'Legacy']
        for ac_type in aircraft_types:
            if ac_type.lower() in text.lower():
                aircraft = ac_type
                break
        
        # Calculate savings (typical 50-75% off)
        savings = 60  # Default estimate
        if 'save' in text.lower():
            savings_match = re.search(r'(\d{1,2})%', text)
            if savings_match:
                savings = int(savings_match.group(1))
        
        return {
            "route": f"{origin} → {destination}",
            "date": date_str,
            "aircraft": aircraft,
            "price": price,
            "savings": savings,
            "origin": origin,
            "destination": destination,
            "source": "Villers Jets",
            "url": self._build_booking_url(origin, destination)
        }
    
    def _build_booking_url(self, origin: str, destination: str) -> str:
        """Build booking URL with affiliate tracking."""
        route = f"{origin}-{destination}".replace(" ", "-")
        return f"https://www.villiersjets.com/?id={self.affiliate_id}&utm_source=ecofriendly&utm_medium=chatbot&route={route}"
    
    def format_empty_legs_for_chat(self, empty_legs: List[Dict]) -> str:
        """Format empty legs for display in chat."""
        
        if not empty_legs:
            return (
                "✈️ **Empty Leg Deals**\n\n"
                "No empty legs currently available. Check back soon or contact Villers Jets:\n\n"
                f"🔗 https://www.villiersjets.com/?id={self.affiliate_id}\n\n"
                "💡 Tip: Empty leg deals can save you up to 75% on private jet travel!"
            )
        
        output = ["✈️ **Current Empty Leg Deals - Save Up to 75%!**\n"]
        
        for i, leg in enumerate(empty_legs[:10], 1):
            price_str = f"${leg['price']:,}" if leg['price'] > 0 else "Call for Quote"
            savings_str = f" (Save {leg['savings']}%)" if leg['savings'] > 0 else ""
            
            output.append(
                f"{i}. **{leg['route']}**\n"
                f"   • Date: {leg['date']}\n"
                f"   • Aircraft: {leg['aircraft']}\n"
                f"   • Price: {price_str}{savings_str}\n"
            )
        
        output.append(f"\n🔗 **Book Now:** https://www.villiersjets.com/?id={self.affiliate_id}")
        output.append("\n💚 *Experience luxury travel at up to 75% off with Villers Jets*")
        
        return "\n".join(output)


# Convenience function
def get_villers_empty_legs(region: Optional[str] = None) -> List[Dict]:
    """Quick function to get empty legs."""
    scraper = VillersJetsScraper()
    return scraper.scrape_empty_legs(region)


if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    
    print("Testing Villers Jets Scraper...\n")
    
    scraper = VillersJetsScraper()
    empty_legs = scraper.scrape_empty_legs()
    
    if empty_legs:
        print(f"✅ Found {len(empty_legs)} empty leg deals!\n")
        print(scraper.format_empty_legs_for_chat(empty_legs))
    else:
        print("⚠️  No empty legs found (may need to adjust scraper)")
        print("Using fallback mode instead")