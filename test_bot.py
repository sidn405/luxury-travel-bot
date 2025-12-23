#!/usr/bin/env python3
"""
Test script for Luxury Travel Bot
Run this to verify everything works before deploying to Railway
"""

import os
import sys
import requests
import json

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_success(message):
    print(f"{GREEN}✓ {message}{RESET}")

def print_error(message):
    print(f"{RED}✗ {message}{RESET}")

def print_info(message):
    print(f"{BLUE}ℹ {message}{RESET}")

def print_warning(message):
    print(f"{YELLOW}⚠ {message}{RESET}")

def check_env_vars():
    """Check if required environment variables are set"""
    print_info("Checking environment variables...")
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print_success(f"OPENAI_API_KEY is set (length: {len(openai_key)})")
    else:
        print_error("OPENAI_API_KEY is not set!")
        print_info("Set it with: export OPENAI_API_KEY='your-key-here'")
        return False
    
    return True

def test_endpoint(base_url, endpoint, method="GET", data=None):
    """Test a specific endpoint"""
    url = f"{base_url}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=30)
        
        if response.status_code == 200:
            print_success(f"{method} {endpoint} - Status: {response.status_code}")
            return True, response.json() if response.headers.get('content-type') == 'application/json' else response.text
        else:
            print_error(f"{method} {endpoint} - Status: {response.status_code}")
            return False, response.text
    except requests.exceptions.Timeout:
        print_error(f"{method} {endpoint} - Request timeout")
        return False, "Timeout"
    except Exception as e:
        print_error(f"{method} {endpoint} - Error: {str(e)}")
        return False, str(e)

def run_tests(base_url):
    """Run all tests"""
    print_info(f"\nTesting Luxury Travel Bot at {base_url}\n")
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Health check
    print_info("Test 1: Health Check")
    success, response = test_endpoint(base_url, "/health")
    if success:
        tests_passed += 1
        print(f"  Response: {json.dumps(response, indent=2)}\n")
    else:
        tests_failed += 1
        print(f"  Response: {response}\n")
    
    # Test 2: Version check
    print_info("Test 2: Version Check")
    success, response = test_endpoint(base_url, "/version")
    if success:
        tests_passed += 1
        print(f"  Version: {response}\n")
    else:
        tests_failed += 1
        print(f"  Response: {response}\n")
    
    # Test 3: API info
    print_info("Test 3: API Info")
    success, response = test_endpoint(base_url, "/api/info")
    if success:
        tests_passed += 1
        print(f"  Response: {json.dumps(response, indent=2)}\n")
    else:
        tests_failed += 1
        print(f"  Response: {response}\n")
    
    # Test 4: Chat endpoint
    print_info("Test 4: Chat Endpoint")
    chat_data = {"message": "Hello! What can you do?"}
    success, response = test_endpoint(base_url, "/api/chat", method="POST", data=chat_data)
    if success:
        tests_passed += 1
        print(f"  Response preview: {response.get('response', '')[:200]}...\n")
    else:
        tests_failed += 1
        print(f"  Response: {response}\n")
    
    # Test 5: Generate itinerary (simple test)
    print_info("Test 5: Generate Itinerary")
    itinerary_data = {
        "destination": ["Paris"],
        "days": 3,
        "budget": "$2000",
        "family_size": 2
    }
    success, response = test_endpoint(base_url, "/api/itinerary", method="POST", data=itinerary_data)
    if success:
        tests_passed += 1
        has_pdf = 'pdf_url' in response
        print(f"  PDF generated: {'Yes' if has_pdf else 'No'}")
        if has_pdf:
            print(f"  PDF URL: {response.get('pdf_url')}")
        print(f"  Response preview: {response.get('response', '')[:200]}...\n")
    else:
        tests_failed += 1
        print(f"  Response: {response}\n")
    
    # Summary
    print("\n" + "="*60)
    print(f"Test Results: {tests_passed} passed, {tests_failed} failed")
    print("="*60 + "\n")
    
    if tests_failed == 0:
        print_success("All tests passed! ✨")
        print_info("Your bot is ready to deploy to Railway!")
        return True
    else:
        print_warning("Some tests failed. Please fix the issues before deploying.")
        return False

def main():
    print("\n" + "="*60)
    print("Luxury Travel Bot - Test Suite")
    print("="*60 + "\n")
    
    # Check environment variables
    if not check_env_vars():
        print_error("\nPlease set required environment variables first!")
        sys.exit(1)
    
    # Determine base URL
    base_url = os.getenv("TEST_URL", "http://localhost:8080")
    
    print_info(f"Testing against: {base_url}")
    print_warning("Make sure the bot is running!")
    print_info("Start it with: python Luxury_Travel_Bot.py\n")
    
    input("Press Enter to start tests...")
    
    # Run tests
    success = run_tests(base_url)
    
    if success:
        print_info("\nNext steps:")
        print("  1. Commit your code to Git")
        print("  2. Push to GitHub")
        print("  3. Deploy to Railway")
        print("  4. Set environment variables in Railway")
        print("  5. Test with Railway URL\n")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_warning("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n\nUnexpected error: {str(e)}")
        sys.exit(1)