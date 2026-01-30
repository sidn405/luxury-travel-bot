#!/usr/bin/env python3
"""
Debug Script - Test Flight Response Format
Run this to see what's being returned
"""

import os
os.environ["AVIAPAGES_API_KEY"] = "test"
os.environ["VILLERS_JETS_AFFILIATE_URL"] = "https://www.villersjets.com/?ref=TEST"

from flight_scraper import FlightScraper
import json

def test_response_format():
    """Test if the response can be properly JSON serialized."""
    
    print("="*60)
    print("Testing Flight Response Format")
    print("="*60)
    
    scraper = FlightScraper()
    
    # Test flight search
    results = scraper.search_flights("Miami", "Aspen", passengers=6)
    
    print("\n1. RAW RESULTS (Dict):")
    print(json.dumps(results, indent=2))
    
    print("\n2. FORMATTED FOR CHAT (String):")
    formatted = scraper.format_for_chat(results)
    print(formatted)
    
    print("\n3. JSON RESPONSE (What API Returns):")
    response = {
        "response": formatted,
        "parameters": {
            "origin": "Miami",
            "destination": "Aspen",
            "passengers": 6
        },
        "intent": "flight"
    }
    
    try:
        json_str = json.dumps(response, indent=2)
        print("✅ JSON serialization successful!")
        print(json_str)
    except Exception as e:
        print(f"❌ JSON serialization failed: {e}")
    
    print("\n4. TEST SIMULATED API CALL:")
    print("This is what your frontend should receive:")
    print("-" * 60)
    print(json_str)
    print("-" * 60)

if __name__ == "__main__":
    test_response_format()