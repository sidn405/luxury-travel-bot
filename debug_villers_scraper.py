#!/usr/bin/env python3
"""
Debug script to inspect Villers Jets empty legs page structure
Run this to see what HTML elements are available
"""

import requests
from bs4 import BeautifulSoup
import re

def debug_villers_jets():
    """Fetch and inspect the Villers Jets empty legs page."""
    
    url = "https://www.villiersjets.com/empty-legs/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    print(f"Fetching: {url}\n")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}\n")
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch page")
            return
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Method 1: Look for links to individual empty leg pages
        print("=" * 60)
        print("METHOD 1: Looking for empty leg links")
        print("=" * 60)
        
        links = soup.find_all('a', href=re.compile(r'/empty-legs/.+'))
        print(f"Found {len(links)} empty leg links\n")
        
        for i, link in enumerate(links[:5], 1):
            href = link.get('href')
            text = link.get_text(strip=True)
            print(f"{i}. URL: {href}")
            print(f"   Text: {text}\n")
        
        # Method 2: Look for elements with "airport" in class or id
        print("\n" + "=" * 60)
        print("METHOD 2: Looking for airport-related elements")
        print("=" * 60)
        
        airport_elements = soup.find_all(class_=re.compile(r'airport|route|leg', re.I))
        print(f"Found {len(airport_elements)} airport-related elements\n")
        
        for i, elem in enumerate(airport_elements[:5], 1):
            print(f"{i}. Tag: {elem.name}, Class: {elem.get('class')}")
            print(f"   Text: {elem.get_text(strip=True)[:100]}\n")
        
        # Method 3: Look for price elements
        print("\n" + "=" * 60)
        print("METHOD 3: Looking for prices")
        print("=" * 60)
        
        # Search for dollar amounts in text
        all_text = soup.get_text()
        prices = re.findall(r'\$\s*\d{1,3}(?:,\d{3})*', all_text)
        print(f"Found {len(set(prices))} unique prices: {set(prices)}\n")
        
        # Method 4: Look for specific keywords
        print("\n" + "=" * 60)
        print("METHOD 4: Looking for 'Lakefront' keyword")
        print("=" * 60)
        
        lakefront_mentions = soup.find_all(text=re.compile(r'lakefront', re.I))
        print(f"Found {len(lakefront_mentions)} mentions of 'Lakefront'\n")
        
        for mention in lakefront_mentions[:3]:
            parent = mention.parent
            print(f"Found in: {parent.name} tag")
            print(f"Text: {mention.strip()[:100]}\n")
        
        # Method 5: Look for all <a> tags with text
        print("\n" + "=" * 60)
        print("METHOD 5: All links with 'to' or 'airport' in text")
        print("=" * 60)
        
        relevant_links = soup.find_all('a', text=re.compile(r'to|airport', re.I))
        print(f"Found {len(relevant_links)} relevant links\n")
        
        for i, link in enumerate(relevant_links[:10], 1):
            href = link.get('href', 'No href')
            text = link.get_text(strip=True)
            if 'to' in text.lower() or 'airport' in text.lower():
                print(f"{i}. {text}")
                print(f"   URL: {href}\n")
        
        # Method 6: Save HTML to file for inspection
        print("\n" + "=" * 60)
        print("Saving full HTML to villers_jets_page.html")
        print("=" * 60)
        
        with open('villers_jets_page.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        
        print("✅ Saved! Check villers_jets_page.html")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_villers_jets()