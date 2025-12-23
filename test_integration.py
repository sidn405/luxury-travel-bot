import unittest
import sys
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Adjust path to be relative to the script location
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from Luxury_Travel_Bot_old import select_destination_with_affiliate_links, create_vanity_link

class TestLiveIntegration(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.logger = logging.getLogger(__name__)
        self.impact_api_key = "~Cp~BpNPZpNoc4FByRzKJymYNpQZ6CYo"  # Your actual Impact API key
        
        # Test getaway URLs for Bali
        self.test_getaways = [
            "https://luxuryescapes.com/us/offer/villa-voyage-bali-indonesia",
            "https://luxuryescapes.com/us/offer/the-legian-bali-indonesia",
            "https://luxuryescapes.com/us/offer/como-uma-ubud-bali-indonesia"
        ]

    def test_live_bali_search_and_links(self):
        """Test live search for Bali getaways and generate real vanity links"""
        self.logger.info("Starting live Bali search and vanity link test")
        
        # 1. Search for Bali destinations
        search_text = "Looking for luxury getaways in Bali"
        results = select_destination_with_affiliate_links(search_text, None, [])
        
        # Log the search results
        self.logger.info(f"Search results: {results}")
        self.assertTrue(len(results) > 0, "No destinations found in search")
        
        # Find Bali in results
        bali_result = next((r for r in results if r['destination'] == 'Bali'), None)
        self.assertIsNotNone(bali_result, "Bali not found in search results")
        self.logger.info(f"Found Bali search URL: {bali_result['url']}")

        # 2. Generate vanity links for specific getaways
        generated_links = []
        for getaway_url in self.test_getaways:
            self.logger.info(f"Generating vanity link for: {getaway_url}")
            try:
                vanity_link = create_vanity_link(self.impact_api_key, getaway_url)
                self.assertIsNotNone(vanity_link, f"Failed to generate vanity link for {getaway_url}")
                self.assertTrue(vanity_link.startswith('http'), "Invalid vanity link format")
                
                generated_links.append({
                    'original_url': getaway_url,
                    'vanity_link': vanity_link
                })
                
                self.logger.info(f"Successfully generated vanity link: {vanity_link}")
            except Exception as e:
                self.logger.error(f"Error generating vanity link: {e}")
                raise

        # Log all generated links
        self.logger.info("\nGenerated Vanity Links Summary:")
        for link in generated_links:
            self.logger.info(f"\nOriginal: {link['original_url']}\nVanity: {link['vanity_link']}")

        # Verify we generated all expected links
        self.assertEqual(len(generated_links), len(self.test_getaways), 
                        "Not all vanity links were generated")

if __name__ == "__main__":
    unittest.main()