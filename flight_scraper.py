#!/usr/bin/env python3
"""
Private Jet Flight Scraper using Aviapages API
Integrates with Villers Jets affiliate program
"""

import os
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)

# Aviapages API Configuration
AVIAPAGES_API_KEY = os.getenv("AVIAPAGES_API_KEY")
AVIAPAGES_BASE_URL = "https://api.aviapages.com/v1"

# Villers Jets Affiliate Configuration
VILLERS_JETS_AFFILIATE_URL = os.getenv(
    "VILLERS_JETS_AFFILIATE_URL",
    "https://www.villersjets.com/?ref=YOUR_AFFILIATE_ID"
)

# IATA Airport Codes for luxury travel destinations
LUXURY_AIRPORTS = {
    "miami": "MIA",
    "new york": "TEB",  # Teterboro - private jet airport
    "los angeles": "VNY",  # Van Nuys - private jet airport
    "las vegas": "LAS",
    "aspen": "ASE",
    "dubai": "DXB",
    "london": "LTN",  # Luton - popular private jet airport
    "paris": "LBG",  # Le Bourget - private jet airport
    "monaco": "MCM",
    "ibiza": "IBZ",
    "maldives": "MLE",
    "bali": "DPS",
    "mykonos": "JMK",
    "st barths": "SBH",
    "cabo": "SJD",
    "bahamas": "PID",
    "tulum": "CUN",
    "nice": "NCE",
    "zurich": "ZRH",
    "tokyo": "NRT",
}

class FlightScraper:
    """Scrape and format private jet flight options using Aviapages API."""
    
    def __init__(self):
        self.api_key = AVIAPAGES_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
    def get_airport_code(self, location: str) -> Optional[str]:
        """Convert location name to IATA airport code."""
        location_lower = location.lower()
        
        # Direct match
        if location_lower in LUXURY_AIRPORTS:
            return LUXURY_AIRPORTS[location_lower]
        
        # Partial match
        for key, code in LUXURY_AIRPORTS.items():
            if key in location_lower or location_lower in key:
                return code
        
        # If exact code provided (3 letters)
        if len(location) == 3:
            return location.upper()
        
        return None
    
    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: Optional[str] = None,
        passengers: int = 4,
        aircraft_type: Optional[str] = None
    ) -> Dict:
        """
        Search for private jet flights using Aviapages API.
        
        Args:
            origin: Departure location or IATA code
            destination: Arrival location or IATA code
            departure_date: Date in YYYY-MM-DD format (defaults to tomorrow)
            passengers: Number of passengers (default 4)
            aircraft_type: Specific aircraft type filter (optional)
        
        Returns:
            Dict with flight results and affiliate link
        """
        try:
            # Convert locations to airport codes
            origin_code = self.get_airport_code(origin)
            dest_code = self.get_airport_code(destination)
            
            if not origin_code or not dest_code:
                logger.warning(f"Could not resolve airport codes: {origin} -> {destination}")
                return self._fallback_response(origin, destination)
            
            # Set default date (tomorrow) if not provided
            if not departure_date:
                tomorrow = datetime.now() + timedelta(days=1)
                departure_date = tomorrow.strftime("%Y-%m-%d")
            
            # Build API request
            params = {
                "origin": origin_code,
                "destination": dest_code,
                "date": departure_date,
                "passengers": passengers,
            }
            
            if aircraft_type:
                params["aircraft_type"] = aircraft_type
            
            # Make API request to Aviapages
            logger.info(f"Searching flights: {origin_code} -> {dest_code} on {departure_date}")
            
            # Note: Aviapages free tier endpoints may vary. Common endpoints:
            # /flights/search or /charter/quote
            response = requests.get(
                f"{AVIAPAGES_BASE_URL}/charter/quote",
                headers=self.headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._format_flight_results(data, origin, destination)
            elif response.status_code == 401:
                logger.error("Aviapages API authentication failed. Check API key.")
                return self._fallback_response(origin, destination)
            else:
                logger.warning(f"Aviapages API returned status {response.status_code}")
                return self._fallback_response(origin, destination)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return self._fallback_response(origin, destination)
        except Exception as e:
            logger.error(f"Flight search error: {e}")
            return self._fallback_response(origin, destination)
    
    def _format_flight_results(self, api_data: Dict, origin: str, destination: str) -> Dict:
        """Format Aviapages API response into user-friendly output."""
        flights = []
        
        # Parse API response (structure depends on Aviapages format)
        # This is a generic parser - adjust based on actual API response
        if "quotes" in api_data:
            for quote in api_data.get("quotes", [])[:5]:  # Top 5 results
                flight = {
                    "aircraft": quote.get("aircraft_name", "Luxury Private Jet"),
                    "aircraft_type": quote.get("aircraft_type", "Heavy Jet"),
                    "price": quote.get("price", 0),
                    "currency": quote.get("currency", "USD"),
                    "passengers": quote.get("max_passengers", 8),
                    "flight_time": quote.get("flight_time", "TBD"),
                    "operator": quote.get("operator", "Private Operator"),
                }
                flights.append(flight)
        elif "flights" in api_data:
            for flight_data in api_data.get("flights", [])[:5]:
                flight = {
                    "aircraft": flight_data.get("aircraft", "Private Jet"),
                    "aircraft_type": flight_data.get("type", "Heavy Jet"),
                    "price": flight_data.get("cost", 0),
                    "currency": "USD",
                    "passengers": flight_data.get("capacity", 8),
                    "flight_time": flight_data.get("duration", "TBD"),
                    "operator": flight_data.get("company", "Private Operator"),
                }
                flights.append(flight)
        
        # Build formatted response
        result = {
            "origin": origin,
            "destination": destination,
            "flights": flights,
            "affiliate_link": self._build_villers_jets_link(origin, destination),
            "total_results": len(flights),
        }
        
        return result
    
    def _fallback_response(self, origin: str, destination: str) -> Dict:
        """Return generic response when API fails (with affiliate link)."""
        logger.info("Using fallback flight response")
        
        # Generic luxury jet options
        generic_flights = [
            {
                "aircraft": "Gulfstream G650",
                "aircraft_type": "Heavy Jet",
                "price": 0,  # Call for quote
                "currency": "USD",
                "passengers": 14,
                "flight_time": "TBD",
                "operator": "Available via Villers Jets",
            },
            {
                "aircraft": "Bombardier Global 7500",
                "aircraft_type": "Heavy Jet", 
                "price": 0,
                "currency": "USD",
                "passengers": 19,
                "flight_time": "TBD",
                "operator": "Available via Villers Jets",
            },
            {
                "aircraft": "Cessna Citation X",
                "aircraft_type": "Midsize Jet",
                "price": 0,
                "currency": "USD",
                "passengers": 8,
                "flight_time": "TBD",
                "operator": "Available via Villers Jets",
            },
        ]
        
        return {
            "origin": origin,
            "destination": destination,
            "flights": generic_flights,
            "affiliate_link": self._build_villers_jets_link(origin, destination),
            "total_results": len(generic_flights),
            "note": "Contact our partner Villers Jets for real-time availability and pricing"
        }
    
    def _build_villers_jets_link(self, origin: str, destination: str) -> str:
        """Build Villers Jets affiliate link with route parameters."""
        # Add route info to affiliate URL for tracking
        base_url = VILLERS_JETS_AFFILIATE_URL
        
        # Add UTM parameters for better tracking
        tracking_params = f"&utm_source=ecofriendly&utm_medium=chatbot&route={origin}-{destination}"
        
        return f"{base_url}{tracking_params}"
    
    def format_for_chat(self, flight_data: Dict) -> str:
        """Format flight results for chat display."""
        if not flight_data.get("flights"):
            return f"No flights found from {flight_data['origin']} to {flight_data['destination']}."
        
        output = [
            f"✈️ **Private Jet Options: {flight_data['origin']} → {flight_data['destination']}**\n"
        ]
        
        for i, flight in enumerate(flight_data["flights"], 1):
            price_str = f"${flight['price']:,.0f}" if flight['price'] > 0 else "Call for Quote"
            
            output.append(
                f"**{i}. {flight['aircraft']}**\n"
                f"   • Type: {flight['aircraft_type']}\n"
                f"   • Passengers: Up to {flight['passengers']}\n"
                f"   • Flight Time: {flight['flight_time']}\n"
                f"   • Price: {price_str}\n"
                f"   • Operator: {flight['operator']}\n"
            )
        
        output.append(
            f"\n🔗 **Book Now:** {flight_data['affiliate_link']}\n"
            f"\n💚 *Experience eco-conscious luxury travel with our partner Villers Jets*"
        )
        
        if flight_data.get("note"):
            output.append(f"\nℹ️ {flight_data['note']}")
        
        return "\n".join(output)
    
    def search_empty_legs(self, region: Optional[str] = None) -> Dict:
        """
        Search for empty leg flights (one-way repositioning flights at discount).
        
        Args:
            region: Geographic region (e.g., "US", "Europe", "Global")
        
        Returns:
            Dict with empty leg deals
        """
        try:
            params = {}
            if region:
                params["region"] = region
            
            # Empty legs endpoint (may vary by provider)
            response = requests.get(
                f"{AVIAPAGES_BASE_URL}/empty-legs",
                headers=self.headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._format_empty_legs(data)
            else:
                return {"empty_legs": [], "note": "Check with Villers Jets for current empty leg deals"}
                
        except Exception as e:
            logger.error(f"Empty leg search error: {e}")
            return {"empty_legs": [], "note": "Check with Villers Jets for current empty leg deals"}
    
    def _format_empty_legs(self, api_data: Dict) -> Dict:
        """Format empty leg results."""
        deals = []
        
        if "legs" in api_data:
            for leg in api_data.get("legs", [])[:10]:
                deal = {
                    "route": f"{leg.get('origin', 'TBD')} → {leg.get('destination', 'TBD')}",
                    "date": leg.get("departure_date", "TBD"),
                    "aircraft": leg.get("aircraft", "Private Jet"),
                    "price": leg.get("price", 0),
                    "savings": leg.get("discount_percent", 0),
                }
                deals.append(deal)
        
        return {
            "empty_legs": deals,
            "affiliate_link": VILLERS_JETS_AFFILIATE_URL,
            "total_deals": len(deals)
        }


# Convenience function for direct import
def search_private_jets(origin: str, destination: str, **kwargs) -> Dict:
    """Quick search function."""
    scraper = FlightScraper()
    return scraper.search_flights(origin, destination, **kwargs)


def format_flight_response(origin: str, destination: str, **kwargs) -> str:
    """Search and format in one step."""
    scraper = FlightScraper()
    results = scraper.search_flights(origin, destination, **kwargs)
    return scraper.format_for_chat(results)


if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    
    print("Testing Flight Scraper...\n")
    
    scraper = FlightScraper()
    
    # Test flight search
    results = scraper.search_flights("Miami", "Aspen", passengers=6)
    print(scraper.format_for_chat(results))
    
    print("\n" + "="*50 + "\n")
    
    # Test empty legs
    empty_legs = scraper.search_empty_legs(region="US")
    print(f"Found {empty_legs['total_deals']} empty leg deals")