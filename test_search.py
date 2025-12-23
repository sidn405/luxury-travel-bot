import unittest
from unittest.mock import patch, Mock
import sys
import os

# Adjust path to be relative to the script location
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from Luxury_Travel_Bot_old import search_luxury_escapes
from bs4 import BeautifulSoup
from google.cloud import secretmanager


class TestSearchLuxuryEscapes(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.base_url = "https://www.luxuryescapes.com/us"  # Updated to include /us

    @patch("Luxury_Travel_Bot.requests.get")
    def test_valid_response(self, mock_get):
        # Mock a valid HTML response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <body>
                <div class="getaway-item">
                    <a href="/getaway1"><div class="getaway-title">Getaway 1</div></a>
                </div>
                <div class="getaway-item">
                    <a href="/getaway2"><div class="getaway-title">Getaway 2</div></a>
                </div>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response

        # Call the function
        results = search_luxury_escapes("test-destination")
        
        # Validate results
        expected_results = [
            {"title": "Getaway 1", "url": f"{self.base_url}/getaway1"},
            {"title": "Getaway 2", "url": f"{self.base_url}/getaway2"}
        ]
        self.assertEqual(results, expected_results)

    @patch("Luxury_Travel_Bot.requests.get")
    def test_empty_response(self, mock_get):
        # Mock an empty response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body></body></html>"
        mock_get.return_value = mock_response

        # Call the function
        results = search_luxury_escapes("test-destination")
        
        # Validate results
        self.assertEqual(results, [])

    @patch("Luxury_Travel_Bot.requests.get")
    def test_http_error(self, mock_get):
        # Mock a response with HTTP error
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        # Call the function
        results = search_luxury_escapes("test-destination")
        
        # Validate results
        self.assertEqual(results, [])

    @patch("Luxury_Travel_Bot.requests.get")
    def test_exception_handling(self, mock_get):
        # Mock an exception during the request
        mock_get.side_effect = Exception("Request failed")

        # Call the function
        results = search_luxury_escapes("test-destination")
        
        # Validate results
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
