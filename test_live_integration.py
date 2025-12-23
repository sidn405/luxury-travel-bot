import unittest
import sys
import os
import logging
import requests
import base64
import json
from datetime import datetime, timedelta
from urllib.parse import quote

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestLiveIntegration(unittest.TestCase):
    def setUp(self):
        """Set up test-level fixtures with Read/Write credentials"""
        self.account_sid = "IRFyVWCwACP63572276p6cyTgKgnk5hFo1"
        self.auth_token = "-Cp-BpNPZpNoc4FByRzKJymYNpQZ6CYo"
        self.logger = logging.getLogger(__name__)
        self.logger.info("Test fixture setup complete")

    def test_impact_auth(self):  # This name must match exactly
        """Test Impact API write access endpoints"""
        self.logger.info("Testing Impact API write access")

        # Test tracking link creation (POST)
        endpoint = f"https://api.impact.com/Mediapartners/:IRFyVWCwACP63572276p6cyTgKgnk5hFo1/Ads"
        
        # Create auth header
        auth_string = f"{self.account_sid}:{self.auth_token}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Basic {encoded_auth}"
        }

        # Test data for creating a tracking link
        data = {
            "Uri": "https://luxuryescapes.com/us/offer/test-tracking",
            "Type": "DIRECT",
            "CampaignId": "3572276"
        }

        self.logger.info(f"Testing endpoint: {endpoint}")
        self.logger.debug(f"Request data: {data}")

        try:
            response = requests.post(
                url=endpoint,
                headers=headers,
                json=data
            )
            
            self.logger.debug(f"Response status: {response.status_code}")
            self.logger.debug(f"Response headers: {dict(response.headers)}")
            
            if response.status_code in [200, 201, 202]:
                self.logger.info("Write operation successful")
                self.logger.debug(f"Response data: {response.text[:200]}...")
                return True
            else:
                self.logger.error(f"Request failed: {response.status_code}")
                self.logger.error(f"Response body: {response.text}")
                
                # Log request details for debugging
                self.logger.debug("Request details:")
                self.logger.debug(f"Method: {response.request.method}")
                self.logger.debug(f"URL: {response.request.url}")
                self.logger.debug(f"Headers: {response.request.headers}")
                self.logger.debug(f"Body: {response.request.body}")
                
                self.fail(f"Request failed with status code {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Request failed with error: {str(e)}")
            self.fail(f"Test failed with error: {str(e)}")

    def tearDown(self):
        """Clean up after each test"""
        self.logger.info("Test cleanup complete")

if __name__ == '__main__':
    unittest.main(verbosity=2)