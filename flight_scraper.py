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

# ✅ Set up logging properly
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from villers_jets_scraper import VillersJetsScraper
    VILLERS_SCRAPER_AVAILABLE = True
    logger.info("✅ Villers Jets scraper available")
except ImportError:
    VILLERS_SCRAPER_AVAILABLE = False
    logger.warning("⚠️ Villers Jets scraper not available")

# Aviapages API Configuration
AVIAPAGES_API_KEY = os.getenv("AVIAPAGES_API_KEY")
AVIAPAGES_BASE_URL = "https://api.aviapages.com"

# Villers Jets Affiliate Configuration
VILLERS_JETS_AFFILIATE_URL = os.getenv(
    "VILLERS_JETS_AFFILIATE_URL",
    "https://www.villersjets.com/?ref=YOUR_AFFILIATE_ID"
)

class FlightScraper:
    """Scrape and format private jet flight options using Aviapages API."""
    
    def __init__(self):
        self.api_key = AVIAPAGES_API_KEY
        self.villers_jets_url = VILLERS_JETS_AFFILIATE_URL
        self.villers_affiliate_id = '7275'
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _get_airport_codes(self, location: str) -> list:
        """
        Get ALL possible airport codes for a location.
        Returns list of codes to check (prioritized by private jet usage).
        """
        location_lower = location.lower().strip()
        
        # Multi-airport cities (private jet + commercial with FBOs)
        airport_mapping = {
            # NEW ORLEANS - Multiple options
            "new orleans": ["NEW", "MSY"],  # Lakefront (private), Armstrong (FBO)
            
            # NEW YORK - Multiple options
            "new york": ["TEB", "HPN", "FRG", "JFK", "EWR", "LGA"],
            "teterboro": ["TEB"],
            "white plains": ["HPN"],
            
            # LOS ANGELES - Multiple options  
            "los angeles": ["VNY", "BUR", "SMO", "LGB", "LAX"],
            "van nuys": ["VNY"],
            "burbank": ["BUR"],
            "santa monica": ["SMO"],
            
            # MIAMI - Multiple options
            "miami": ["OPF", "FXE", "MIA", "FLL"],
            "fort lauderdale": ["FXE", "FLL"],
            
            # CHICAGO - Multiple options
            "chicago": ["PWK", "MDW", "ORD"],
            
            # DALLAS - Multiple options
            "dallas": ["ADS", "DAL", "DFW"],
            "addison": ["ADS"],
            
            # ATLANTA - Multiple options
            "atlanta": ["PDK", "ATL"],
            
            # HOUSTON - Multiple options
            "houston": ["HOU", "IAH"],
            
            # LAS VEGAS - Multiple options
            "las vegas": ["VGT", "LAS", "HND"],
            "vegas": ["VGT", "LAS"],
            
            # PHOENIX/SCOTTSDALE - Multiple options
            "phoenix": ["SDL", "PHX"],
            "scottsdale": ["SDL", "PHX"],
            
            # SAN FRANCISCO - Multiple options
            "san francisco": ["SFO", "OAK", "SJC", "HWD"],
            
            # WASHINGTON DC - Multiple options
            "washington": ["IAD", "DCA"],
            "dc": ["DCA", "IAD"],
            
            # BOSTON - Multiple options
            "boston": ["BED", "BOS"],
            
            # DENVER - Multiple options
            "denver": ["APA", "DEN"],
            
            # Single airport cities
            "san antonio": ["SAT"],
            "aspen": ["ASE"],
            "nashville": ["BNA"],
            "charlotte": ["CLT"],
            "philadelphia": ["PHL"],
            "seattle": ["SEA", "BFI"],
            "orlando": ["MCO", "ISM"],
            "tampa": ["TPA"],
            "west palm beach": ["PBI"],
            "palm beach": ["PBI"],
            
            # International
            "dubai": ["DXB", "DWC"],
            "london": ["LTN", "FAB", "LHR", "LCY"],
            "paris": ["LBG", "CDG"],
            "geneva": ["GVA"],
            "zurich": ["ZRH"],
            "nice": ["NCE"],
            "ibiza": ["IBZ"],
            "tokyo": ["NRT", "HND"],
            "hong kong": ["HKG"],
            "singapore": ["SIN"],
            "bali": ["DPS"],
            "cabo": ["SJD"],
            "cancun": ["CUN"],
        }
        
        # Try exact match first
        if location_lower in airport_mapping:
            codes = airport_mapping[location_lower]
            logger.info(f"Resolved '{location}' to multiple codes: {codes}")
            return codes
        
        # Try partial match
        for city, codes in airport_mapping.items():
            if city in location_lower or location_lower in city:
                logger.info(f"Partially resolved '{location}' to codes: {codes} via '{city}'")
                return codes
        
        # Fallback - single code
        fallback = location.upper()[:3]
        logger.warning(f"Could not resolve '{location}', using fallback: [{fallback}]")
        return [fallback]
    
    def _get_iata_code(self, location: str) -> str:
        """
        Get primary airport code for a location.
        Returns first (prioritized) code from the list.
        """
        codes = self._get_airport_codes(location)
        return codes[0]
    
    def format_for_chat(self, flight_data: Dict) -> str:
        """Format flight results for chat display."""
        
        if not flight_data.get("flights"):
            return f"No flights found from {flight_data['origin']} to {flight_data['destination']}."
        
        is_fallback = flight_data.get("is_fallback", False)
        
        if is_fallback:
            output = [
                f"✈️ Private Jet Charter: {flight_data['origin']} → {flight_data['destination']}\n",
                "📋 Example Aircraft Available:\n"
            ]
        else:
            output = [
                f"✈️ Available Private Jets: {flight_data['origin']} → {flight_data['destination']}\n"
            ]
        
        for i, flight in enumerate(flight_data["flights"], 1):
            price_str = f"${flight['price']:,.0f}" if flight['price'] > 0 else "Request Quote"
            
            output.append(
                f"{i}. {flight['aircraft']}\n"
                f"   • Type: {flight['aircraft_type']}\n"
                f"   • Passengers: Up to {flight['passengers']}\n"
                f"   • Flight Time: {flight['flight_time']}\n"
                f"   • Price: {price_str}\n"
            )
        
        output.append(
            f"\n🔗 Get Real-Time Quote & Book:\n"
            f"{flight_data['affiliate_link']}\n"
        )
        
        output.append("\n💚 Eco-conscious luxury travel with Villers Jets")
        
        if flight_data.get("note"):
            output.append(f"\n{flight_data['note']}")
        
        return "\n".join(output)

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
            origin_code = self._get_iata_code(origin)
            dest_code = self._get_iata_code(destination)
            
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
            
            # Use Aviapages price_calculator endpoint (POST request based on docs)
            payload = {
                "departure_airport": origin_code,
                "arrival_airport": dest_code,
                "departure_date": departure_date,
                "passengers": passengers,
            }
            
            try:
                # Try price calculator first (most relevant for quotes)
                response = requests.post(
                    f"{AVIAPAGES_BASE_URL}/price_calculator/",
                    headers=self.headers,
                    json=payload,
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._format_flight_results(data, origin, destination)
                    
                # If price calculator fails, try availabilities endpoint (GET)
                elif response.status_code in [404, 405]:
                    logger.info("Trying availabilities endpoint...")
                    response = requests.get(
                        f"{AVIAPAGES_BASE_URL}/availabilities/",
                        headers=self.headers,
                        params=params,
                        timeout=15
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        return self._format_flight_results(data, origin, destination)
                
                # Check for auth error
                if response.status_code == 401:
                    logger.error("Aviapages API authentication failed. Check API key.")
                    return self._fallback_response(origin, destination)
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"API request failed: {e}")
            
            # Fallback if all attempts fail
            logger.warning("Using fallback response")
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
        
        # Parse API response - handle different response structures
        # Price Calculator response structure
        if "results" in api_data:
            for result in api_data.get("results", [])[:5]:
                flight = {
                    "aircraft": result.get("aircraft_name") or result.get("aircraft", "Luxury Private Jet"),
                    "aircraft_type": result.get("aircraft_type") or result.get("category", "Heavy Jet"),
                    "price": result.get("total_price") or result.get("price", 0),
                    "currency": result.get("currency", "USD"),
                    "passengers": result.get("max_passengers") or result.get("capacity", 8),
                    "flight_time": result.get("flight_duration") or result.get("flight_time", "TBD"),
                    "operator": result.get("operator_name") or result.get("operator", "Private Operator"),
                }
                flights.append(flight)
        
        # Availabilities response structure
        elif "data" in api_data:
            for item in api_data.get("data", [])[:5]:
                flight = {
                    "aircraft": item.get("aircraft_name") or item.get("name", "Private Jet"),
                    "aircraft_type": item.get("type") or item.get("category", "Heavy Jet"),
                    "price": item.get("estimated_price") or item.get("price", 0),
                    "currency": "USD",
                    "passengers": item.get("max_passengers") or item.get("seats", 8),
                    "flight_time": item.get("duration") or "TBD",
                    "operator": item.get("operator") or "Private Operator",
                }
                flights.append(flight)
        
        # Legacy format support (from previous implementation)
        elif "quotes" in api_data:
            for quote in api_data.get("quotes", [])[:5]:
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
        
        # Direct array of aircraft
        elif isinstance(api_data, list):
            for item in api_data[:5]:
                flight = {
                    "aircraft": item.get("name") or item.get("aircraft", "Private Jet"),
                    "aircraft_type": item.get("category") or item.get("type", "Heavy Jet"),
                    "price": item.get("price", 0),
                    "currency": "USD",
                    "passengers": item.get("max_passengers") or item.get("seats", 8),
                    "flight_time": item.get("duration", "TBD"),
                    "operator": item.get("operator", "Private Operator"),
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
        
        villers_matches = self._check_villers_for_route(origin, destination)
        if villers_matches:
            logger.info(f"🔥 Using {len(villers_matches)} empty leg matches from Villers Jets")
            return {
                "origin": origin,
                "destination": destination,
                "flights": villers_matches,
                "affiliate_link": self._build_villers_jets_link(origin, destination),
                "total_results": len(villers_matches),
                "note": "🔥 Empty leg deals available - Save up to 75%!",
                "source": "villers_jets_empty_leg_match"
            }
            
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
    
    def _check_villers_for_route(self, origin: str, destination: str) -> Optional[List[Dict]]:
        """
        Check if Villers Jets has empty legs matching this route.
        NOW CHECKS ALL AIRPORT COMBINATIONS!
        """
        if not VILLERS_SCRAPER_AVAILABLE:
            return None
        
        try:
            # Get ALL possible airport codes for origin and destination
            origin_codes = self._get_airport_codes(origin)
            dest_codes = self._get_airport_codes(destination)
            
            logger.info(f"🔍 Checking Villers Jets for {origin} ({origin_codes}) → {destination} ({dest_codes})")
            
            villers_scraper = VillersJetsScraper(affiliate_id='7275')
            empty_legs = villers_scraper.scrape_empty_legs()
            
            if not empty_legs:
                logger.info("No empty legs found on Villers Jets")
                return None
            
            # Check all combinations
            matching = []
            for leg in empty_legs:
                leg_origin = leg['origin'].upper()
                leg_dest = leg['destination'].upper()
                
                # Check if ANY of our origin codes match AND ANY of our dest codes match
                origin_match = any(code in leg_origin or leg_origin in code for code in origin_codes)
                dest_match = any(code in leg_dest or leg_dest in code for code in dest_codes)
                
                if origin_match and dest_match:
                    logger.info(f"✅ MATCH FOUND: {leg['route']} matches {origin} → {destination}")
                    matching.append({
                        "aircraft": leg['aircraft'],
                        "aircraft_type": "Private Jet (Empty Leg)",
                        "price": leg['price'],
                        "currency": "USD",
                        "passengers": 8,
                        "flight_time": leg['date'],
                        "operator": "Villers Jets",
                        "savings": leg['savings'],
                        "note": f"🔥 Save {leg['savings']}% on this empty leg!"
                    })
            
            if matching:
                logger.info(f"✅ Found {len(matching)} matching empty legs!")
                return matching
            
            logger.info("No matching empty legs for this specific route")
            return None
            
        except Exception as e:
            logger.error(f"Error checking Villers for route: {e}")
            return None
    
    def search_empty_legs(self, region: Optional[str] = None) -> Dict:
        """
        Search for empty leg deals.
        Now uses Villers Jets scraper for REAL deals!
        """
        logger.info("Searching for empty leg deals...")
        
        # Try Villers Jets scraper first for REAL data
        if VILLERS_SCRAPER_AVAILABLE:
            try:
                logger.info("🔍 Using Villers Jets scraper for real empty legs")
                villers_scraper = VillersJetsScraper(
                    affiliate_id=self.villers_affiliate_id.split('=')[-1] if '=' in self.villers_affiliate_id else '7275'
                )
                
                empty_legs = villers_scraper.scrape_empty_legs(region)
                
                if empty_legs and len(empty_legs) > 0:
                    logger.info(f"✅ Found {len(empty_legs)} REAL empty legs from Villers Jets!")
                    
                    # Format for our response
                    formatted_legs = []
                    for leg in empty_legs[:10]:  # Limit to top 10
                        formatted_legs.append({
                            "route": leg['route'],
                            "date": leg['date'],
                            "aircraft": leg['aircraft'],
                            "price": leg['price'],
                            "savings": leg['savings'],
                            "origin": leg['origin'],
                            "destination": leg['destination']
                        })
                    
                    return {
                        "empty_legs": formatted_legs,
                        "total_deals": len(formatted_legs),
                        "affiliate_link": self._build_villers_jets_link("", ""),
                        "note": "🔥 Live empty leg deals from Villers Jets - Save up to 75%!",
                        "source": "villers_jets_live"
                    }
                else:
                    logger.info("ℹ️ No empty legs found on Villers Jets at this time")
                    
            except Exception as e:
                logger.error(f"❌ Villers scraper error: {e}")
                logger.exception(e)
        
        # Fallback: No real data available
        logger.info("Using fallback empty legs response")
        return {
            "empty_legs": [],
            "total_deals": 0,
            "affiliate_link": self._build_villers_jets_link("", ""),
            "note": "Contact Villers Jets for current empty leg availability"
        }
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
    
    def get_aircraft_info(self, aircraft_id: Optional[int] = None) -> Dict:
        """
        Get aircraft information from Aviapages.
        
        Args:
            aircraft_id: Specific aircraft ID (optional - returns list if None)
        
        Returns:
            Dict with aircraft details
        """
        try:
            url = f"{AVIAPAGES_BASE_URL}/aircraft/"
            if aircraft_id:
                url = f"{url}{aircraft_id}/"
            
            response = requests.get(
                url,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Aircraft info request failed: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Aircraft info error: {e}")
            return {}


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