#!/usr/bin/env python3
import datetime
import os
import json
import re
import traceback
import threading
import logging
import sys
import time
import itertools
import shutil
from io import BytesIO
from time import sleep
from xml.sax.saxutils import escape
from html import escape as html_escape

from flask import Flask, request, jsonify, send_file, url_for
from flask_compress import Compress
import requests

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, 
    TableStyle, Image, Flowable
)

from google.cloud import storage, secretmanager
from google.auth import default
from google.oauth2 import service_account
from google.auth.transport.requests import Request

from gunicorn import glogging
from bs4 import BeautifulSoup

# Setup logging
env = os.getenv("ENV", "production")  # Default to "production" if ENV is not set

if env == "development":
    logging_level = logging.DEBUG
else:
    logging_level = logging.INFO

logging.basicConfig(
    level=logging_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)  # Log to console
    ],
)
logger = logging.getLogger("luxury_travel_bot")

# Custom Gunicorn logger
class CustomGunicornLogger(glogging.Logger):
    def setup(self, cfg):
        super().setup(cfg)

        # Add our custom logger
        self.error_log.addHandler(stdout_handler)
        self.access_log.addHandler(stdout_handler)

# Initialize Flask app
app = Flask(__name__)
Compress(app)  # Enables GZIP compression for all responses

def setup_google_adc_from_secret(secret_name="TravelManager"):
    try:
        # Access the secret JSON from Secret Manager
        secret_value = access_secret_version(secret_name)
        credentials_path = "/tmp/google_adc.json"

        # Write the secret to a temporary file
        with open(credentials_path, "w") as f:
            f.write(secret_value)

        # Set the GOOGLE_APPLICATION_CREDENTIALS environment variable
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        logger.info("Google Application Default Credentials set successfully.")
    except Exception as e:
        logger.error(f"Failed to set up ADC from Secret Manager: {e}")
        raise
    
# Function to access the secret value from Google Secret Manager
def access_secret_version(secret_name, version_id="latest"):
    """
    Access the secret value from Google Secret Manager.
    """
    try:
        # Create the Secret Manager client
        client = secretmanager.SecretManagerServiceClient()

        # Get project ID dynamically from the environment variable
        project_id = os.getenv(
            "GOOGLE_CLOUD_PROJECT", "luxury-travel-bot-439000"
        )  # Default as fallback

        # Build the secret resource name
        name = f"projects/{project_id}/secrets/{secret_name}/versions/{version_id}"

        # Access the secret
        response = client.access_secret_version(request={"name": name})
        secret_value = response.payload.data.decode("UTF-8")

        return secret_value
    except Exception as e:
        logger.error(f"Failed to access secret {secret_name}: {e}")
        raise


# Load the OpenAI API key
def get_openai_api_key():
    """
    Retrieve the OpenAI API key from the environment variable.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is missing!")
    return api_key


# Usage
api_key = get_openai_api_key()
headers = {
    "Authorization": f"Bearer {api_key.strip()}",
    "Content-Type": "application/json",
}


# Function to load service account credentials from a secret
def load_service_account_credentials_from_secret(secret_name):
    """
    Load service account credentials from Secret Manager.
    """
    try:
        # Fetch the secret value
        key_data = access_secret_version(secret_name)

        # Convert the JSON string to a dictionary
        key_dict = json.loads(key_data)

        # Load the credentials
        credentials = service_account.Credentials.from_service_account_info(
            key_dict,
            scopes=["https://www.googleapis.com/auth/devstorage.read_write"],
        )
        return credentials
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON: {e}")
        raise
    except Exception as e:
        print(f"Failed to load service account credentials: {e}")
        raise


# Function to dynamically set GOOGLE_APPLICATION_CREDENTIALS
def setup_service_account_from_secret(secret_name="TravelManager"):
    """
    Fetch the service account JSON from Secret Manager and set it up dynamically.
    """
    try:
        # Retrieve the service account key JSON from Secret Manager
        service_account_json = access_secret_version(secret_name)

        # Write the JSON to a temporary file
        service_account_path = "/tmp/service_account.json"
        with open(service_account_path, "w") as f:
            f.write(service_account_json)

        # Set the GOOGLE_APPLICATION_CREDENTIALS environment variable
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_account_path
        logger.info("Service account credentials set from Secret Manager.")
    except Exception as e:
        logger.error(f"Error setting up service account from secret: {e}")
        raise


# Function to authenticate and print scopes and project ID
def authenticate_service_account():
    """
    Authenticate using service account loaded from Secret Manager.
    """
    try:
        secret_name = "TravelManager"  # Your secret name in Secret Manager
        credentials = load_service_account_credentials_from_secret(secret_name)
        logger.info(f"Scopes: {credentials.scopes}")
        logger.info(f"Project: {credentials.project_id}")
        return credentials
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise


# Define link style globally
link_style = ParagraphStyle(
    name="Link",
    fontName="Helvetica-Bold",
    fontSize=18,
    leading=12,
    textColor=HexColor("#004444"),
    underline=True,
)

title_style = ParagraphStyle(
    name="Title",
    fontName="Helvetica-Bold",
    fontSize=24,
    alignment=1,
    textColor=HexColor("#004444"),  # Adjust as needed
)

subtitle_style = ParagraphStyle(
    name="Subtitle",
    fontName="Helvetica",
    fontSize=16,
    leading=18,
    underline=False,
    textColor=HexColor("#004444"),
)

normal_style = ParagraphStyle(
    name="Normal",
    fontName="Helvetica",
    fontSize=16,
    textColor=black,
    leading=15,
)
# Define banners globally
banners = [
    {
        "path": "https://storage.googleapis.com/lux-travel-2/ads/banner-1.jpg",
        "link": "https://www.villiersjets.com/?id=7275",
    },
    {
        "path": "https://storage.googleapis.com/lux-travel-2/ads/banner-2.jpg",
        "link": "https://searadar.tp.st/wOulUd7g",
    },
    {
        "path": "https://storage.googleapis.com/lux-travel-2/ads/banner-3.jpg",
        "link": "https://www.skippercity.com/?ref=sidneym",
    },
]

# Global definition
affiliate_links = {}


# 1. Example of global access
def initialize_affiliate_links():
    global affiliate_links
    affiliate_links = {
        "getaways": {
            "Africa": [
                {
                    "destination": "Félicité",
                    "hotel": "Six Senses Zil Pasyon",
                    "link": "https://luxuryescapes.sjv.io/dOOZ3j",
                },
                {
                    "destination": "Mbombela",
                    "hotel": "Jock Safari Lodge",
                    "link": "https://luxuryescapes.sjv.io/mOObrM",
                },
                {
                    "destination": "Serengeti",
                    "hotel": "Four Seasons Safari Lodge Serengeti",
                    "link": "https://luxuryescapes.sjv.io/Dyy11y",
                },
                {
                    "destination": "Cape Town",
                    "hotel": "One&Only Cape Town",
                    "link": "https://luxuryescapes.sjv.io/e11BBg",
                },
                {
                    "destination": "Maasai Mara",
                    "hotel": "Neptune Mara Rianta Luxury Camp",
                    "link": "https://luxuryescapes.sjv.io/XmmZZ5",
                },
            ],
            "Australia": [
                {
                    "destination": "The Trio at Rubus Residences",
                    "hotel": "Rubus Residences",
                    "link": "https://luxuryescapes.sjv.io/mOOr7M",
                },
                {
                    "destination": "Luxico Victoria on Portsea",
                    "hotel": "Luxico Victoria",
                    "link": "https://luxuryescapes.sjv.io/raae7v",
                },
                {
                    "destination": "Linnaeus Farm Berry",
                    "hotel": "Linnaeus Farm Berry",
                    "link": "https://luxuryescapes.sjv.io/xLLXWk",
                },
                {
                    "destination": "Southern Ocean Lodge",
                    "hotel": "Southern Ocean Lodge",
                    "link": "https://luxuryescapes.sjv.io/kOOQeM",
                },
                {
                    "destination": "Orpheus Island Lodge",
                    "hotel": "Orpheus Island Lodge",
                    "link": "https://luxuryescapes.sjv.io/JKKoGQ",
                },
            ],
            "Bali": [
                {
                    "destination": "Bali",
                    "hotel": "Akashi Residence",
                    "link": "https://luxuryescapes.sjv.io/POOY6Q",
                },
                {
                    "destination": "Bali",
                    "hotel": "Bvlgari Resort Bali",
                    "link": "https://luxuryescapes.sjv.io/raae2v",
                },
                {
                    "destination": "Bali",
                    "hotel": "Villa Ambra",
                    "link": "https://luxuryescapes.sjv.io/Kjn7Qe",
                },
                {
                    "destination": "Bali",
                    "hotel": "Tanah Gajah",
                    "link": "https://luxuryescapes.sjv.io/xk4G4R",
                },
                {
                    "destination": "Bali",
                    "hotel": "Hanging Gardens of Bali",
                    "link": "https://luxuryescapes.sjv.io/7aaLMg",
                },
            ],
            "Dubai": [
                {
                    "destination": "Burj Al Arab Jumeirah",
                    "hotel": "Burj Al Arab Jumeirah",
                    "link": "https://luxuryescapes.sjv.io/0ZLb7M",
                },
                {
                    "destination": "W Dubai The Palm Jumeriah",
                    "hotel": "W Dubai The Palm Jumeriah",
                    "link": "https://luxuryescapes.sjv.io/EKnAxQ",
                },
                {
                    "destination": "The Ritz-Carlton",
                    "hotel": "The Ritz-Carlton",
                    "link": "https://luxuryescapes.sjv.io/GKKoVm",
                },
                {
                    "destination": "ME Dubai by Meliá",
                    "hotel": "ME Dubai by Meliá",
                    "link": "https://luxuryescapes.sjv.io/gOOL6A",
                },
                {
                    "destination": "Al Maha",
                    "hotel": "Al Maha",
                    "link": "https://luxuryescapes.sjv.io/EEEGe2",
                },
            ],
            "Fiji": [
                {
                    "destination": "Wakaya Club and Spa",
                    "hotel": "Wakaya Club and Spa",
                    "link": "https://luxuryescapes.sjv.io/21x4kQ",
                },
                {
                    "destination": "Sheraton Denarau Villas",
                    "hotel": "Sheraton Denarau Villas",
                    "link": "https://luxuryescapes.sjv.io/9g5KW5",
                },
                {
                    "destination": "Malolo Island Resort",
                    "hotel": "Malolo Island Resort",
                    "link": "https://luxuryescapes.sjv.io/xLLXWk",
                },
                {
                    "destination": "Tokoriki Island Resort",
                    "hotel": "Tokoriki Island Resort",
                    "link": "https://luxuryescapes.sjv.io/g1Z3P9",
                },
                {
                    "destination": "Royal Davui Island Resort",
                    "hotel": "Royal Davui Island Resort",
                    "link": "https://luxuryescapes.sjv.io/jeeDon",
                },
            ],
            "England": [
                {
                    "destination": "London",
                    "hotel": "Kinnerton Street",
                    "link": "https://luxuryescapes.sjv.io/gOOLZ5",
                },
                {
                    "destination": "London",
                    "hotel": "Corinthia London",
                    "link": "https://luxuryescapes.sjv.io/099XL3",
                },
                {
                    "destination": "Slough",
                    "hotel": "The Langley",
                    "link": "https://luxuryescapes.sjv.io/EEEGoX",
                },
                {
                    "destination": "London",
                    "hotel": "Mandarin Oriental Hyde Park",
                    "link": "https://luxuryescapes.sjv.io/2aaXxD",
                },
                {
                    "destination": "London",
                    "hotel": "Shangri-La Hotel",
                    "link": "https://luxuryescapes.sjv.io/dOO31Q",
                },
            ],
            "France": [
                {
                    "destination": "Chamonix-Mont-Blanc",
                    "hotel": "Chalet Freya",
                    "link": "https://luxuryescapes.sjv.io/qzzkRn",
                },
                {
                    "destination": "Paris",
                    "hotel": "Hôtel Plaza Athénée",
                    "link": "https://luxuryescapes.sjv.io/raaevG",
                },
                {
                    "destination": "Paris",
                    "hotel": "Rue Custine II",
                    "link": "https://luxuryescapes.sjv.io/GKKoaB",
                },
                {
                    "destination": "Cassis",
                    "hotel": "Hôtel Les Roches Blanches",
                    "link": "https://luxuryescapes.sjv.io/gOOLz0",
                },
                {
                    "destination": "Paris",
                    "hotel": "Grand Hotel du Palais Royal",
                    "link": "https://luxuryescapes.sjv.io/3JJX2A",
                },
            ],
            "Greece": [
                {
                    "destination": "Zakynthos",
                    "hotel": "Lesante Cape Resort & Villas",
                    "link": "https://luxuryescapes.sjv.io/DyyA5q",
                },
                {
                    "destination": "Rethymno",
                    "hotel": "Grecotel LUX ME White Palace",
                    "link": "https://luxuryescapes.sjv.io/POOYoq",
                },
                {
                    "destination": "Athens",
                    "hotel": "Hotel Grande Bretagne",
                    "link": "https://luxuryescapes.sjv.io/GKKoaB",
                },
                {
                    "destination": "Mykonos",
                    "hotel": "Mykonos Princess Hotel",
                    "link": "https://luxuryescapes.sjv.io/Xmmo6M",
                },
                {
                    "destination": "Santorini",
                    "hotel": "One of One Hotel",
                    "link": "https://luxuryescapes.sjv.io/099XbL",
                },
            ],
            "Germany": [
                {
                    "destination": "Düsseldorf",
                    "hotel": "Breidenbacher Hof",
                    "link": "https://luxuryescapes.sjv.io/2aaXOG",
                },
                {
                    "destination": "Berlin",
                    "hotel": "Waldorf Astoria Berlin",
                    "link": "https://luxuryescapes.sjv.io/RGGYAy",
                },
                {
                    "destination": "Berlin",
                    "hotel": "SO/ Berlin Das Stue",
                    "link": "https://luxuryescapes.sjv.io/N99o5N",
                },
                {
                    "destination": "Hamburg",
                    "hotel": "The Westin Hamburg",
                    "link": "https://luxuryescapes.sjv.io/7aaLEO",
                },
                {
                    "destination": "Heringsdorf",
                    "hotel": "Das Ahlbeck Hotel & Spa",
                    "link": "https://luxuryescapes.sjv.io/kOOQyv",
                },
            ],
            "Italy": [
                {
                    "destination": "Taormina",
                    "hotel": "San Domenico Palace",
                    "link": "https://luxuryescapes.sjv.io/o44Pme",
                },
                {
                    "destination": "Bellagio",
                    "hotel": "Hotel Belvedere",
                    "link": "https://luxuryescapes.sjv.io/nXXjrR",
                },
                {
                    "destination": "Portoferraio",
                    "hotel": "Hotel Hermitage",
                    "link": "https://luxuryescapes.sjv.io/xLLXWk",
                },
                {
                    "destination": "Tremezzina",
                    "hotel": "Grand Hotel Tremezzo",
                    "link": "https://luxuryescapes.sjv.io/mOOr9y",
                },
                {
                    "destination": "Praiano",
                    "hotel": "Casa Angelina",
                    "link": "https://luxuryescapes.sjv.io/DyyA9G",
                },
            ],
            "Portugal": [
                {
                    "destination": "Funchal",
                    "hotel": "Pestana Grand Premium Ocean Resort",
                    "link": "https://luxuryescapes.sjv.io/Dyy1Wa",
                },
                {
                    "destination": "Évora",
                    "hotel": "Imani Country House",
                    "link": "https://luxuryescapes.sjv.io/MAAjK2",
                },
                {
                    "destination": "Calheta",
                    "hotel": "Calheta Beach",
                    "link": "https://luxuryescapes.sjv.io/bOOy7b",
                },
                {
                    "destination": "Loulé",
                    "hotel": "Hotel Quinta do Lago",
                    "link": "https://luxuryescapes.sjv.io/3JJO7k",
                },
                {
                    "destination": "Vila Nova de Gaia",
                    "hotel": "Vinha Boutique Hotel",
                    "link": "https://luxuryescapes.sjv.io/4GGKdr",
                },
            ],
            "Spain": [
                {
                    "destination": "Capdepera",
                    "hotel": "Cap Vermell Grand Hotel",
                    "link": "https://luxuryescapes.sjv.io/kOObVL",
                },
                {
                    "destination": "Barcelona",
                    "hotel": "Alma Barcelona GL",
                    "link": "https://luxuryescapes.sjv.io/XmmZrX",
                },
                {
                    "destination": "Barcelona",
                    "hotel": "Monument Hotel",
                    "link": "https://luxuryescapes.sjv.io/WyyK9A",
                },
                {
                    "destination": "Madrid",
                    "hotel": "Mandarin Oriental Ritz",
                    "link": "https://luxuryescapes.sjv.io/EEEVx2",
                },
                {
                    "destination": "Barcelona",
                    "hotel": "Mandarin Oriental",
                    "link": "https://luxuryescapes.sjv.io/3JJORM",
                },
            ],
            "Maldives": [
                {
                    "destination": "Sonera Jani",
                    "hotel": "Sonera Jani",
                    "link": "https://luxuryescapes.sjv.io/rQvLJG",
                },
                {
                    "destination": "Soneva Fushi",
                    "hotel": "Soneva Fushi",
                    "link": "https://luxuryescapes.sjv.io/zNLYeG",
                },
                {
                    "destination": "One & Only Reethi Rah",
                    "hotel": "One & Only Reethi Rah",
                    "link": "https://luxuryescapes.sjv.io/Wqm733",
                },
                {
                    "destination": "Gili Lankanfushi",
                    "hotel": "Gili Lankanfushi",
                    "link": "https://luxuryescapes.sjv.io/xk4G4R",
                },
                {
                    "destination": "Kudadoo Maldives",
                    "hotel": "Kudadoo Maldives",
                    "link": "https://luxuryescapes.sjv.io/gOONLA",
                },
            ],
            "Thailand": [
                {
                    "destination": "Phuket",
                    "hotel": "The Chava Resort",
                    "link": "https://luxuryescapes.sjv.io/QjjeWY",
                },
                {
                    "destination": "Phuket",
                    "hotel": "Banyan Tree Phuket",
                    "link": "https://luxuryescapes.sjv.io/POOkW6",
                },
                {
                    "destination": "Phuket",
                    "hotel": "InterContinental Phuket Resort",
                    "link": "https://luxuryescapes.sjv.io/APPaGR",
                },
                {
                    "destination": "Phuket",
                    "hotel": "Trisara",
                    "link": "https://luxuryescapes.sjv.io/XmmZK5",
                },
                {
                    "destination": "Phuket",
                    "hotel": "The Shore at Katathani",
                    "link": "https://luxuryescapes.sjv.io/WyyK03",
                },
                {
                    "destination": "Koh Samui",
                    "hotel": "Baan Kilee",
                    "link": "https://luxuryescapes.sjv.io/kOOqAx",
                },
                {
                    "destination": "Koh Samui",
                    "hotel": "Villa Akatsuki",
                    "link": "https://luxuryescapes.sjv.io/Oee5WA",
                },
                {
                    "destination": "Koh Samui",
                    "hotel": "Panacea Retreat | Praana Residence",
                    "link": "https://luxuryescapes.sjv.io/4GGKq1",
                },
                {
                    "destination": "Koh Samui",
                    "hotel": "Ban Suriya",
                    "link": "https://luxuryescapes.sjv.io/K009Wa",
                },
                {
                    "destination": "Koh Samui",
                    "hotel": "Villa Riva",
                    "link": "https://luxuryescapes.sjv.io/e11Bjg}",
                },
                {
                    "destination": "Koh Samui",
                    "hotel": "Conrad Koh Samui Residences",
                    "link": "https://luxuryescapes.sjv.io/Dyy1aq",
                },
                {
                    "destination": "Krabi",
                    "hotel": "Banyan Tree Krabi",
                    "link": "https://luxuryescapes.sjv.io/K00NYv",
                },
                {
                    "destination": "Bangkok",
                    "hotel": "The Athenee Hotel",
                    "link": "https://luxuryescapes.sjv.io/yqqLxy",
                },
                {
                    "destination": "Khoa Lak",
                    "hotel": "JW Marriott Khao Lak Resort Suites",
                    "link": "https://luxuryescapes.sjv.io/9LLQBQ",
                },
                {
                    "destination": "Khoa Lak",
                    "hotel": "Devasom Khao Lak",
                    "link": "https://luxuryescapes.sjv.io/aOO6ZQ",
                },
                {
                    "destination": "Khoa Lak",
                    "hotel": "Avani+ Khao Lak Resort",
                    "link": "https://luxuryescapes.sjv.io/gOONQ0",
                },
                {
                    "destination": "Khoa Lak",
                    "hotel": "Le Meridien Khao Lak Resort & Spa",
                    "link": "https://luxuryescapes.sjv.io/WyyKPn",
                },
                {
                    "destination": "Khoa Lak",
                    "hotel": "Mai Khao Lak Beach Resort & Spa",
                    "link": "https://luxuryescapes.sjv.io/RGGaNy",
                },
            ],
            "Japan": [
                {
                    "destination": "Tokyo",
                    "hotel": "Mandarin Oriental Tokyo",
                    "link": "https://luxuryescapes.sjv.io/raaP1j",
                },
                {
                    "destination": "Tokyo",
                    "hotel": "Shangri-La Tokyo",
                    "link": "https://luxuryescapes.sjv.io/Vxx5v6",
                },
                {
                    "destination": "Appi",
                    "hotel": "Kogen ANA Crowne Plaza Resort",
                    "link": "https://luxuryescapes.sjv.io/099NMO",
                },
            ],
            "Jamaica": [
                {
                    "destination": "Montego Bay",
                    "hotel": "Breathless Motego Bay",
                    "link": "https://luxuryescapes.sjv.io/K00Nv7",
                },
                {
                    "destination": "Green Island",
                    "hotel": "Princess Senses The Mangrove Resort",
                    "link": "https://luxuryescapes.sjv.io/gOOE7g",
                },
                {
                    "destination": "Falmouth",
                    "hotel": "Royalton Blue Waters Montego Bay",
                    "link": "https://luxuryescapes.sjv.io/kOOqv0",
                },
                {
                    "destination": "Lucea",
                    "hotel": "Grand Palladium Lady Hamilton Resort & Spa",
                    "link": "https://luxuryescapes.sjv.io/Vxx5K6",
                },
            ],
            "China": [
                {
                    "destination": "Beijing",
                    "hotel": "The Peninsula Beijing",
                    "link": "https://luxuryescapes.sjv.io/099N5O",
                },
                {
                    "destination": "Shenzhen",
                    "hotel": "Park Hyatt Shenzhen",
                    "link": "https://luxuryescapes.sjv.io/bOOoKg",
                },
                {
                    "destination": "Guangzhou",
                    "hotel": "Jumeirah Guangzhou",
                    "link": "https://luxuryescapes.sjv.io/yqq1vN",
                },
                {
                    "destination": "Shanghai",
                    "hotel": "Shanghai Marriott Marquis City Centre",
                    "link": "https://luxuryescapes.sjv.io/QjjQXa",
                },
            ],
            "Hong Kong": [
                {
                    "destination": "Kowloon",
                    "hotel": "Rosewood Hong Kong",
                    "link": "https://luxuryescapes.sjv.io/DyyNdb",
                },
                {
                    "destination": "Hong Kong",
                    "hotel": "Four Seasons Hotel",
                    "link": "https://luxuryescapes.sjv.io/APPNMa",
                },
                {
                    "destination": "Kowloon",
                    "hotel": "The Peninsula Hong Kong",
                    "link": "https://luxuryescapes.sjv.io/Vxx5Dj",
                },
                {
                    "destination": "Kowloon",
                    "hotel": "The Ritz Carlton Hong Kong",
                    "link": "https://luxuryescapes.sjv.io/WyykQe",
                },
                {
                    "destination": "Hong Kong",
                    "hotel": "Grand Hyatt Hong Kong",
                    "link": "https://luxuryescapes.sjv.io/dOOzJ2",
                },
            ],
            "Norway": [
                {
                    "destination": "Ullensvang",
                    "hotel": "Hotel Ullensvang",
                    "link": "https://luxuryescapes.sjv.io/7aaNk5",
                },
                {
                    "destination": "Voss",
                    "hotel": "Fleischer's Hotel",
                    "link": "https://luxuryescapes.sjv.io/kOOqGV",
                },
                {
                    "destination": "Hol",
                    "hotel": "Highland Lodge Fjellandsby",
                    "link": "https://luxuryescapes.sjv.io/o449ZW",
                },
            ],
            "Switzerland": [
                {
                    "destination": "St Moritz",
                    "hotel": "Carlton Hotel St Moritz",
                    "link": "https://luxuryescapes.sjv.io/xLLGPR",
                },
                {
                    "destination": "St Moritz",
                    "hotel": "Suvretta House",
                    "link": "https://luxuryescapes.sjv.io/jeeLg6",
                },
                {
                    "destination": "Geneva",
                    "hotel": "The Ritz-Carlton, Hotel de la Paix",
                    "link": "https://luxuryescapes.sjv.io/199N3x",
                },
                {
                    "destination": "Arosa",
                    "hotel": "Tschuggen Grand Hotel",
                    "link": "https://luxuryescapes.sjv.io/BnnMQW",
                },
                {
                    "destination": "Lenk",
                    "hotel": "Lenkerhof Gourmet Spa Resort",
                    "link": "https://luxuryescapes.sjv.io/OeexQr",
                },
            ],
            "Mexico": [
                {
                    "destination": "Los Cabos",
                    "hotel": "Esperanza Auberge Resorts",
                    "link": "https://luxuryescapes.sjv.io/q4b1GN",
                },
                {
                    "destination": "Cancun",
                    "hotel": "Hyatt Ziva",
                    "link": "https://luxuryescapes.sjv.io/VmrdVa",
                },
                {
                    "destination": "Cancun",
                    "hotel": "Marriott Cancun",
                    "link": "https://luxuryescapes.sjv.io/AWz5ax",
                },
                {
                    "destination": "Cancun",
                    "hotel": "Ava Resort",
                    "link": "https://luxuryescapes.sjv.io/anJDJY",
                },
                {
                    "destination": "Los Cabos",
                    "hotel": "One & Only",
                    "link": "https://luxuryescapes.sjv.io/21xOyG",
                },
            ],
            "Hawaii": [
                {
                    "destination": "Timbers Kauai Ocean Club and Residences",
                    "hotel": "Timbers Kauai Ocean Club and Residences",
                    "link": "https://luxuryescapes.sjv.io/21PdzA",
                },
                {
                    "destination": "The Lodge at Kukuiula",
                    "hotel": "The Lodge at Kukuiula",
                    "link": "https://luxuryescapes.sjv.io/Y95NPr",
                },
                {
                    "destination": " Four Seasons Resort Hualalai",
                    "hotel": " Four Seasons Resort",
                    "link": "https://luxuryescapes.sjv.io/GKKq46",
                },
                {
                    "destination": "Ko'a Kea Resort on Po'ipu Beach",
                    "hotel": "Ko'a Kea Resort",
                    "link": "https://luxuryescapes.sjv.io/o44bve",
                },
                {
                    "destination": "Beverly Hills",
                    "hotel": "Waldorf Astoria",
                    "link": "https://luxuryescapes.sjv.io/6yyq1E",
                },
                {
                    "destination": "Fairmont Kea Lani Maui",
                    "hotel": "Fairmont Kea Lani Maui",
                    "link": "https://luxuryescapes.sjv.io/zxxqvx",
                },
            ],
            "California": [
                {
                    "destination": "Santa Barbara",
                    "hotel": "El Encanto",
                    "link": "https://luxuryescapes.sjv.io/RGGao2",
                },
                {
                    "destination": "Los Angeles",
                    "hotel": "Four Seasons Los AnMeadowood Napa Valleygeles",
                    "link": "https://luxuryescapes.sjv.io/N99PJP",
                },
                {
                    "destination": "St. Helena",
                    "hotel": "Meadowood Napa Valley",
                    "link": "https://luxuryescapes.sjv.io/xLLbv3",
                },
                {
                    "destination": "Beverly Hills",
                    "hotel": "The Peninsula Beverly Hills",
                    "link": "https://luxuryescapes.sjv.io/QjjeX9",
                },
            ],
            "Las Vegas": [
                {
                    "destination": "Four Seasons Hotel",
                    "hotel": "Four Seasons Hotel",
                    "link": "https://luxuryescapes.sjv.io/gOON7v",
                },
                {
                    "destination": "Waldorf Astoria",
                    "hotel": "Waldorf Astoria",
                    "link": "https://luxuryescapes.sjv.io/WyyKQO",
                },
                {
                    "destination": "The Cosmopolitan Of Las Vegas",
                    "hotel": "The Cosmopolitan Of Las Vegas",
                    "link": "https://luxuryescapes.sjv.io/nXXb6R",
                },
                {
                    "destination": "Secret Suites at Vdara",
                    "hotel": "Secret Suites at Vdara",
                    "link": "https://luxuryescapes.sjv.io/4GGKnL",
                },
                {
                    "destination": "The Palazzo at The Venetian",
                    "hotel": "The Palazzo at The Venetian",
                    "link": "https://luxuryescapes.sjv.io/N99PyP",
                },
            ],
            "New Orleans": [
                {
                    "destination": "The Windsor Court",
                    "hotel": "The Windsor Court",
                    "link": "https://luxuryescapes.sjv.io/Qjjed9",
                },
                {
                    "destination": "The Ritz-Carlton",
                    "hotel": "The Ritz-Carlton",
                    "link": "https://luxuryescapes.sjv.io/kOOb2x",
                },
                {
                    "destination": "W New Orleans",
                    "hotel": "W New Orleans",
                    "link": "https://luxuryescapes.sjv.io/555LPb",
                },
                {
                    "destination": "Hotel Monteleone",
                    "hotel": "Hotel Monteleone",
                    "link": "https://luxuryescapes.sjv.io/199OQD",
                },
                {
                    "destination": "Hyatt Regency New Orleans",
                    "hotel": "Hyatt Regency",
                    "link": "https://luxuryescapes.sjv.io/nXXbJV",
                },
            ],
            "Miami": [
                {
                    "destination": "South Beach",
                    "hotel": "The Retreat Collection at 1 Hotel & Homes",
                    "link": "https://luxuryescapes.sjv.io/APPaDK",
                },
                {
                    "destination": "Miami Beach",
                    "hotel": "The Setai Residence",
                    "link": "https://luxuryescapes.sjv.io/o44bWo",
                },
                {
                    "destination": "Miami Beach",
                    "hotel": "Faena Hotel",
                    "link": "https://luxuryescapes.sjv.io/YRRoxe",
                },
                {
                    "destination": "The Setai",
                    "hotel": "The Setai",
                    "link": "https://luxuryescapes.sjv.io/raabxj",
                },
                {
                    "destination": "South Beach",
                    "hotel": "W",
                    "link": "https://luxuryescapes.sjv.io/APPaVa",
                },
            ],
            "tours": {
                "Africa": "https://luxuryescapes.com/us/search/tours?destinationId=le_b02e6098244d867ef9e033afaf097d81&destinationName=Africa",
                "Australia": "https://luxuryescapes.com/us/search/tours?destinationId=le_d3d9446802a44259755d38e6d163e820&destinationName=Australia",
                "Vietnam": "https://luxuryescapes.com/us/search/tours?destinationId=le_a597e50502f5ff68e3e25b9114205d4a&destinationName=Vietnam",
                "India": "https://luxuryescapes.com/us/search/tours?destinationId=le_f033ab37c30201f73f142449d037028d&destinationName=India",
                "Japan": "https://luxuryescapes.com/us/search/tours?destinationId=le_7647966b7343c29048673252e490f736&destinationName=Japan",
                "Spain": "https://luxuryescapes.com/us/search/tours?destinationId=le_7e7757b1e12abcb736ab9a754ffb617a&destinationName=Spain",
                "Sri Lanka": "https://luxuryescapes.com/us/search/tours?destinationId=le_5878a7ab84fb43402106c575658472fa&destinationName=Sri%20Lanka",
                "Turkey": "https://luxuryescapes.com/us/search/tours?destinationId=le_cedebb6e872f539bef8c3f919874e9d7&destinationName=Turkey",
                "Egypt": "https://luxuryescapes.com/us/search/tours?destinationId=le_9a1158154dfa42caddbd0694a4e9bdc8&destinationName=Egypt",
            },
        }
    }
    logger.debug(f"Initialized affiliate_links: {affiliate_links}")


initialize_affiliate_links()


# 2. Debug affiliate links to ensure proper access
def debug_affiliate_links():
    global affiliate_links
    if not isinstance(affiliate_links, dict):
        logger.error(
            f"'affiliate_links' is not a dictionary. Found: {type(affiliate_links)}"
        )
    else:
        logger.debug(f"'affiliate_links' contains keys: {list(affiliate_links.keys())}")
        getaways = affiliate_links.get("getaways", {})
        if isinstance(getaways, dict):
            logger.debug(f"'getaways' contains regions: {list(getaways.keys())}")
        else:
            logger.error(f"'getaways' is not a dictionary. Found: {type(getaways)}")


# 3. Add a new destination as an example
def add_destination():
    global affiliate_links
    if "getaways" in affiliate_links and "Africa" in affiliate_links["getaways"]:
        affiliate_links["getaways"]["Africa"].append(
            {
                "destination": "New Place",
                "hotel": "New Hotel",
                "link": "https://example.com",
            }
        )
        logger.info("Successfully added a new destination to Africa.")
    else:
        logger.error("'getaways' or 'Africa' is missing in affiliate_links.")


# Debugging calls
debug_affiliate_links()
add_destination()
debug_affiliate_links()


logger.debug(f"OpenAI API Key: {os.getenv('OPENAI_API_KEY')}")
logger.debug(
    f"Google Application Credentials: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}"
)


# Persistent storage client for Google Cloud Storage
try:
    storage_client = storage.Client()
    logger.debug("Google Cloud Storage client initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing Google Cloud Storage client: {str(e)}")
    traceback.print_exc()

# Persistent session for OpenAI API requests
session = requests.Session()
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    session.headers.update({"Authorization": f"Bearer {openai_api_key}"})
    logging.info("OpenAI API session initialized successfully.")
else:
    logger.error("OpenAI API key is missing!")


# 4. Function to sanitize filenames
def sanitize_filename(filename):
    logger.debug(f"Sanitizing filename: {filename}")
    # Removes or replaces any invalid characters from the filename and ensures it's safe for GCS.

    # Replace multiple spaces with a single space and strip leading/trailing spaces
    filename = re.sub(r"\s+", " ", filename).strip()

    # Only allow alphanumeric characters, spaces, periods, and hyphens
    filename = re.sub(r"[^A-Za-z0-9 .-]", "", filename)

    return filename


# 5. Generates a filename dynamically based on the parameters.
def generate_filename(parameters, file_type="getaway"):
    try:
        # Extract destination, number of days, and fallback to defaults if not available
        destination_list = parameters.get(
            "destination", [{"original": "default_destination"}]
        )
        destination = " ".join(
            [
                item["original"]
                for item in destination_list
                if isinstance(item, dict) and "original" in item
            ]
        )

        # Safely extract and format the number_of_days
        number_of_days = parameters.get("number_of_days", "unknown")
        try:
            number_of_days = int(float(number_of_days))  # Handle numbers like "10.0"
        except (ValueError, TypeError):
            logger.error("Invalid number_of_days format")
            number_of_days = "unknown"

        # Determine the filename based on the file_type
        if file_type == "getaway":
            filename = f"{number_of_days} day {destination.capitalize()} getaway.pdf"
        elif file_type == "itinerary":
            filename = f"{number_of_days} day {destination.capitalize()} itinerary.pdf"
        else:
            filename = f"{number_of_days} day {destination.capitalize()}.pdf"

        # Sanitize the filename to make it valid for GCS
        filename = sanitize_filename(filename)

        logger.info(f"Generated filename: {filename}")
        return filename
    except Exception as e:
        logger.error(f"Error generating filename: {str(e)}")
        return "default-filename.pdf"

# 7. Refresh Google token
def refresh_google_token():
    global credentials
    credentials.refresh(Request())
    logger.info("Google Cloud token refreshed")
    # Schedule the next refresh in 50 minutes (before the 1-hour expiration)
    threading.Timer(3000, refresh_google_token).start()


# Get ADC and refresh token if necessary
credentials, project = default()

# 8. Get Google access token
def get_google_access_token():
    # Automatically refresh token if needed
    if credentials.expired:
        credentials.refresh(Request())
    return credentials.token

# 10. Make Objects Public
def make_object_public(bucket_name, object_name):
    from google.cloud import storage

    storage_client = storage.Client()
    bucket = storage_client.bucket(lux - travel - 2)
    blob = bucket.blob(ads)

    blob.make_public()
    print(f"The object {object_name} is now publicly accessible at {blob.public_url}")
    return blob.public_url


# 11. Make Objects Publicly Accessible
def make_gcs_object_public(bucket_name, blob_name):
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        logger.debug(
            f"Attempting to make public: Bucket: {bucket_name}, Blob: {blob_name}"
        )
        blob = bucket.blob(blob_name)
        blob.make_public()  # Makes the object publicly accessible
        logger.info(
            f"The file {blob_name} is now publicly accessible at {blob.public_url}"
        )
        return blob.public_url
    except Exception as e:
        logger.error(f"Failed to make object public: {str(e)}")
        traceback.print_exc()
        return None


# 12. Function to upload a PDF to GCS using JSON API
def upload_to_gcs_with_public_acl(bucket_name, blob_name, file_path):
    """
    Uploads a file to Google Cloud Storage with public-read access directly.
    """
    try:
        # Check if the file exists
        if not os.path.exists(file_path):
            logger.error(f"File not found for upload: {file_path}")
            return None

        # Initialize the Google Cloud Storage client
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        # Upload the file and set public-read ACL during upload
        blob.upload_from_filename(file_path)
        blob.acl.all().grant_read()  # Grant public-read access
        blob.acl.save()  # Save the ACL changes

        # Log the public URL of the uploaded file
        logger.info(f"File uploaded and made public at: {blob.public_url}")
        return {"public_url": blob.public_url}
    except Exception as e:
        logger.error(f"Error uploading and setting public ACL: {e}")
        return None


# 13. Function to download a PDF from GCS using JSON API
def generate_download_json_api(bucket_name, blob_name, destination_file_path):
    """
    Downloads a file from Google Cloud Storage using the JSON API.
    """

    try:
        access_token = authenticate_service_account()
        logger.info(f"Access Token: {access_token}")

    except Exception as e:
        logger.error(f"Authentication error: {e}")
        metadata_url = f"https://storage.googleapis.com/storage/v1/b/lux-travel-2/o/{blob_name}?alt=media"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(metadata_url, headers=headers)
        if response.status_code == 200:
            logger.info(f"File {blob_name} is available for download.")
            return metadata_url
        else:
            logger.error(f"Error generating download URL: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error downloading from GCS using JSON API: {str(e)}")
        traceback.print_exc()
        return None


# 14. Refresh the OpenAI API key periodically
def refresh_openai_key():
    global OPENAI_API_KEY
    # Reload API key from environment or secure storage
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        logger.error("OpenAI API key is missing!")
    else:
        session.headers.update({"Authorization": f"Bearer {OPENAI_API_KEY}"})
        logger.info("OpenAI API key refreshed")
    # Schedule the next refresh in 24 hours
    threading.Timer(86400, refresh_openai_key).start()


# In-memory session storage
session_storage = {}

# Mock data store (replace with actual data store queries)
LuxTravel = {
    "Kenya": {
        "destination": "Kenya",
        "budget": "$5000 - $15000",
        "days": 7,
        "accommodations": [
            {
                "name": "Eco-Friendly Safari Lodge",
                "description": "A luxury lodge in the heart of the savannah with a focus on sustainable tourism.",
                "features": [
                    "Solar-powered electricity",
                    "Local community engagement",
                    "Conservation-focused safari",
                ],
            }
        ],
        "activities": [
            "Safari adventure in Maasai Mara",
            "Guided nature walks with local guides",
            "Visit to local villages for cultural experiences",
        ],
        "public_url": "https://ecofriendlyluxurytravels.com/kenya-eco-safari",
    },
    "Maldives": {
        "destination": "Maldives",
        "budget": "$7000 - $20000",
        "days": 5,
        "accommodations": [
            {
                "name": "Sustainable Beach Villa",
                "description": "Luxurious beachfront villas committed to sustainable practices.",
                "features": [
                    "Overwater villas",
                    "Zero waste policy",
                    "Coral reef restoration programs",
                ],
            }
        ],
        "activities": [
            "Snorkeling and diving in marine protected areas",
            "Eco-friendly water sports",
            "Guided reef restoration activities",
        ],
        "public_url": "https://ecofriendlyluxurytravels.com/maldives-sustainable-getaway",
    },
    "Costa Rica": {
        "destination": "Costa Rica",
        "budget": "$4000 - $12000",
        "days": 10,
        "accommodations": [
            {
                "name": "Eco Lodge in the Rainforest",
                "description": "A luxury eco-lodge set in the lush Costa Rican rainforest, with sustainable practices.",
                "features": [
                    "Solar-powered hot water",
                    "Rainforest conservation",
                    "Organic farm-to-table dining",
                ],
            }
        ],
        "activities": [
            "Rainforest hikes",
            "Wildlife spotting and conservation tours",
            "Yoga and wellness retreats",
        ],
        "public_url": "https://ecofriendlyluxurytravels.com/costa-rica-rainforest-retreat",
    },
}

#  Function to call OpenAI for itinerary generation or use existing data
cache = {}  # Simple in-memory cache

#  15. Function to call OpenAI or data store
def call_openai_or_data_store(prompt, destination):
    search_term = " ".join(destination).lower().strip()
    if search_term in cache:
        return cache[search_term]  # Return cached response if available

    # Extract parameters
    req = request.get_json(silent=True, force=True)
    parameters = req.get("queryResult", {}).get("parameters", {})

    logger.debug(f"Generated OpenAI prompt: {prompt}")
    user_query = req.get("queryResult", {}).get("queryText", "")
    response = call_openai(user_query, affiliate_links, parameters)
    if not response:
        logger.error("OpenAI API returned no response or an empty response.")
        return None

    logger.debug(f"OpenAI API response: {response}")
    cache[search_term] = response  # Cache the new response
    return response


# 16. Function to call OpenAI Getaways
def call_openai_getaways(user_query, affiliate_links, parameters):
    """
    Calls OpenAI API to generate luxury getaway options with high detail and user-specified parameters.

    :param user_query: The user's input query.
    :param affiliate_links: A dictionary of predefined affiliate destinations with links.
    :param parameters: Extracted parameters like budget, number_of_days, and preferences.
    :return: OpenAI response text strictly based on affiliate_links.
    """
    logger.debug(f"Calling OpenAI with user query: {user_query}")

    # Convert affiliate_links into a readable text format for OpenAI
    destinations_list = []
    for region, destinations in affiliate_links.get("getaways", {}).items():
        for destination in destinations:
            if (
                isinstance(destination, dict)
                and "destination" in destination
                and "hotel" in destination
            ):
                destinations_list.append(
                    f"{destination['destination']} - {destination['hotel']}"
                )
    destinations_text = "\n".join(destinations_list)
    logger.debug(f"Destinations Text for OpenAI: {destinations_text}")

    # Extract parameters
    number_of_days = int(parameters.get("number_of_days", 5))
    budget = int(parameters.get("budget", 27900))  # Default to $27900
    climate_preferences = parameters.get("climate_preferences", "warm and sunny")
    activities_interests = parameters.get(
        "activities_interests", "sightseeing, spa treatments, and adventure sports"
    )
    family_size = parameters.get("family_size", 4)
    ages = parameters.get("ages", [35, 32, 10, 7])
    geography_scenery = parameters.get("geography_scenery", "serene and flat")
    travel_distance = parameters.get("travel_distance", "close to home")

    # Log extracted parameters for debugging
    logger.debug(
        f"Parameters: Days: {number_of_days}, Budget: {budget}, Climate: {climate_preferences}"
    )

    # Updated OpenAI Prompt
    prompt = (
        f"Create three luxury getaway options for a {number_of_days}-day trip within a budget of ${budget}. "
        f"Each option must include:\n"
        f"1. A unique and detailed description of the destination, including highlights, luxury accommodations, "
        f"   exclusive amenities (private pools, fine dining, spa treatments), and cultural experiences.\n"
        f"2. Activities tailored for families of {family_size} with ages {ages}.\n"
        f"3. Scenery preference: {geography_scenery} and climate preference: {climate_preferences}.\n"
        f"4. An estimated cost close to the budget of ${budget}.\n"
        f"5. A persuasive call-to-action encouraging the user to book or explore further, but do not includ the heading 'Call-to-Action'.\n\n"
        f"Only use the following available destinations:\n{destinations_text}\n\n"
        f"Ensure the options reflect a luxurious, high-end travel experience that matches the user's preferences."
    )

    return _call_openai_api(prompt)




#  17. Function to call OpenAI Itinerary
def call_openai_itinerary(user_query, affiliate_links, parameters):
    """
    Calls OpenAI API to generate a detailed itinerary for a specific destination based on user preferences.

    :param user_query: The user's input query.
    :param affiliate_links: A dictionary of predefined affiliate destinations with links.
    :param parameters: Extracted parameters like budget, number_of_days, and preferences.
    :return: OpenAI response text containing a detailed itinerary.
    """
    logger.debug(
        f"Calling OpenAI for a detailed itinerary with user query: {user_query}"
    )

    # Extract the user's specific destination
    destination_list = parameters.get("destination", [{"original": "default"}])
    if destination_list and isinstance(destination_list[0], dict):
        user_destination = destination_list[0].get("original", "default").lower()
    else:
        logger.warning(
            "Destination list is malformed or empty. Using default destination."
        )
        user_destination = "default"

    logger.debug(f"User-selected destination: {user_destination}")

    # Check for affiliate tours matching the user's destination
    affiliate_tour = None
    for region, destinations in affiliate_links.get("getaways", {}).items():
        for destination in destinations:
            # Ensure destination is a dictionary and matches the user's input
            if isinstance(destination, dict) and "destination" in destination:
                if destination["destination"].lower() == user_destination:
                    affiliate_tour = destination.get(
                        "link"
                    )  # Extract the affiliate tour link
                    logger.info(
                        f"Matched affiliate tour for {user_destination}: {affiliate_tour}"
                    )
                    break  # Exit once a match is found
        if affiliate_tour:
            break  # Stop searching if a match has been found

    # Log if no affiliate tour was found
    if not affiliate_tour:
        logger.info(f"No affiliate tour found for {user_destination}.")

        # Extract user preferences
        number_of_days = int(parameters.get("number_of_days", 5))
        raw_budget = parameters.get("budget", "27900")  # Default to "27900" if missing
        budget = int(
            re.sub(r"[^\d]", "", raw_budget)
        )  # Remove non-numeric characters like "$"
        family_size = parameters.get("family_size", 4)
        ages = parameters.get("ages", [35, 32, 10, 7])
        activities_interests = parameters.get(
            "activities_interests", "sightseeing, spa treatments, and adventure sports"
        )

    # OpenAI prompt for a single detailed itinerary
    prompt = (
        f"Create a detailed {number_of_days}-day luxury itinerary for a family of {family_size} "
        f"(ages: {', '.join(map(str, ages))}) visiting {user_destination.capitalize()}. "
        f"The budget is ${budget}. Activities of interest include {activities_interests}.\n\n"
        f"Include the following details:\n"
        f"1. A day-by-day schedule with specific activities, cultural highlights, and relaxation options.\n"
        f"2. Highlight exclusive experiences such as fine dining, spa treatments, and private tours.\n"
        f"3. Provide an estimated total cost and end with a warm salutation."
    )

    return _call_openai_api(prompt)

#  18. Function to call OpenAI
def _call_openai_api(prompt):
    """Handles OpenAI API calls and returns the response content."""
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key is not set.")

        headers = {"Authorization": f"Bearer {api_key}"}
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant specializing in luxury travel.",
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 1500,
        }
        response = session.post("https://api.openai.com/v1/chat/completions", json=data)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        logger.debug(f"OpenAI Response: {content}")
        return content
    except requests.exceptions.RequestException as e:
        logger.error(f"OpenAI API call failed: {e}")
        logger.debug(traceback.format_exc())
        return None

#  19. Extract destinations with affiliate links
def extract_destinations_with_links(affiliate_links):
    """
    Safely extract destinations with links from the affiliate_links dictionary.
    """
    destinations_with_links = []
    for region, destinations in affiliate_links.get("getaways", {}).items():
        if not isinstance(destinations, list):
            logger.warning(f"Invalid destinations for region {region}: {destinations}")
            continue

        for destination in destinations:
            if (
                isinstance(destination, dict)
                and "destination" in destination
                and "link" in destination
            ):
                destinations_with_links.append(
                    (destination["destination"], destination["link"])
                )
            else:
                logger.warning(f"Invalid destination entry: {destination}")

    return destinations_with_links

#  20. Select destinations with affiliate links
def select_destination_with_affiliate_links(response_text, link_style, story):
    """
    Extract destination names from OpenAI's response and attach affiliate links.
    """
    try:
        logger.debug("Starting to select destinations with affiliate links.")
        logger.debug(
            f"Response Text: {response_text[:500]}"
        )  # Log the first 500 characters

        # Fetch global affiliate_links (ensure it is defined)
        global affiliate_links
        destinations_with_links = extract_destinations_with_links(affiliate_links)
        logger.debug(f"Available Destinations with Links: {destinations_with_links}")

        if not destinations_with_links:
            logger.warning("No destinations with links found.")
            return []

        # Match destinations in response_text with destinations_with_links
        matched_destinations = [
            (dest, link)
            for dest, link in destinations_with_links
            if dest in response_text
        ]
        logger.debug(f"Matched Destinations: {matched_destinations}")

        if not matched_destinations:
            logger.warning("No matching destinations found in the response text.")
            return []

        # Add clickable links to the PDF story
        for destination, link in matched_destinations:
            safe_link = escape(link)  # Escape the link for safety
            link_text = f"<a href='{safe_link}'>{destination}</a>"
            story.append(Paragraph(link_text, link_style))
            story.append(Spacer(1, 0.2 * inch))  # Add spacing after each link

        logger.info(f"Successfully added {len(matched_destinations)} destinations.")
        return matched_destinations

    except Exception as e:
        logger.error(f"Error processing destinations: {e}")
        return None

# 21. Enhanced Banner class
# --- EnhancedBanner (production) --------------------------------------------
from reportlab.platypus import Flowable
from reportlab.lib.utils import ImageReader
from io import BytesIO
import requests
import logging


class EnhancedBanner(Flowable):
    """
    Centered, clickable banner that fits an image into a target box while
    preserving aspect ratio, aligned to the *frame* (column) center.
    """

    def __init__(self, image_url, link_url=None, width=520, height=100,
                 padding_top=6, padding_bottom=6):
        super().__init__()
        self.image_url = image_url
        self.link_url = link_url
        self.max_w = width
        self.max_h = height
        self.pad_top = padding_top
        self.pad_bottom = padding_bottom

        # internal state
        self._image = None
        self._img_w = None
        self._img_h = None
        self._availW = None
        self._draw_w = None
        self._draw_h = None

        self._load_image()

    def _load_image(self):
        try:
            resp = requests.get(
                self.image_url,
                timeout=10,
                headers={"User-Agent": "LuxuryTravelPDF/1.0"}
            )
            resp.raise_for_status()
            self._image = ImageReader(BytesIO(resp.content))
            self._img_w, self._img_h = self._image.getSize()
        except Exception as e:
            logging.getLogger(__name__).error(
                f"EnhancedBanner: failed to load {self.image_url}: {e}"
            )
            self._image = None
            self._img_w = self._img_h = None

    def wrap(self, availWidth, availHeight):
        # Remember the frame width we’re flowing into
        self._availW = availWidth

        target_w = min(self.max_w, availWidth)
        if self._image and self._img_w and self._img_h:
            scale = min(target_w / self._img_w, self.max_h / self._img_h)
            self._draw_w = self._img_w * scale
            self._draw_h = self._img_h * scale
        else:
            # Reserve space even if the image failed
            self._draw_w = target_w
            self._draw_h = self.max_h

        total_h = self.pad_top + self._draw_h + self.pad_bottom
        return (self._draw_w, total_h)

    def draw(self):
        frame_w = self._availW if self._availW is not None else self.canv._pagesize[0]
        x = (frame_w - self._draw_w) / 2.0
        y = self.pad_bottom

        if self._image:
            self.canv.drawImage(
                self._image, x, y, width=self._draw_w, height=self._draw_h, mask="auto"
            )
            if self.link_url:
                self.canv.linkURL(
                    self.link_url, (x, y, x + self._draw_w, y + self._draw_h),
                    relative=1, thickness=0
                )
        else:
            # Simple placeholder so layout stays stable Shows dashed box around banner for center alignment
            #self.canv.saveState()
            #self.canv.setLineWidth(0.7)
            #self.canv.setStrokeColorRGB(0.85, 0.2, 0.2)
            #self.canv.rect(x, y, self._draw_w, self._draw_h)
            #self.canv.setFont("Helvetica", 9)
            #self.canv.drawCentredString(
                #x + self._draw_w / 2.0, y + self._draw_h / 2.0 - 4,
                #"Banner image unavailable"
            #)
            #self.canv.restoreState()
            pass
# ---------------------------------------------------------------------------

# 22. integrate banner
def integrate_banner(story, image_url, link_url):
    """Add a banner to the story with proper spacing and error handling"""
    try:
        logger.info(f"Integrating banner: {image_url} with link: {link_url}")
        # Add pre-banner spacing
        story.append(Spacer(1, 0.2 * inch))

        # Create and add banner
        banner = EnhancedBanner(image_url, link_url)
        story.append(banner)

        # Add post-banner spacing
        story.append(Spacer(1, 0.2 * inch))

        logger.info(f"Successfully integrated banner from {image_url}")
        return True
    except Exception as e:
        logger.error(f"Error integrating banner: {e}")
        return False

# 23. Create pdf with banners and affiliate links
def create_pdf_with_banners_and_affiliate_links(content, days, destinations_with_links):
    """Create a PDF with styled, clickable option titles and affiliate banners."""
    try:
        logger.info("Starting PDF creation.")

        # Define file name and save path
        filename = f"{days}daygetawayoptions.pdf"
        save_path = os.path.join("/tmp", filename)

        # Initialize PDF document
        doc = SimpleDocTemplate(save_path, pagesize=letter)
        styles = getSampleStyleSheet()

        hyperlink_style = ParagraphStyle(
            name="HyperlinkSubtitle",
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=18,
            textColor=HexColor("#004444"),
            underline=True,
        )

        normal_style = styles["Normal"]

        # Initialize the story
        story = []

        # Add title
        story.append(Paragraph("Eco-Friendly Luxury Travels", title_style))
        story.append(Spacer(1, 0.2 * inch))

        # Split content into options
        options = content.split("Option")
        options = [
            "Option" + opt for opt in options[1:]
        ]  # Reconstruct with "Option" prefix

        # Process each option
        for i, option_content in enumerate(options, 1):
            # Add appropriate banner before each option
            if i == 1:
                integrate_banner(
                    story,
                    "https://storage.googleapis.com/lux-travel-2/ads/banner-1.jpg",
                    "https://www.villiersjets.com/?id=7275",
                )
            elif i == 2:
                integrate_banner(
                    story,
                    "https://storage.googleapis.com/lux-travel-2/ads/banner-2.jpg",
                    "https://searadar.tp.st/wOulUd7g",
                )
            elif i == 3:
                integrate_banner(
                    story,
                    "https://storage.googleapis.com/lux-travel-2/ads/banner-3.jpg",
                    "https://www.skippercity.com/?ref=sidneym",
                )

            # Process option content
            lines = option_content.strip().split("\n")
            option_title = lines[0].strip()

            # Extract and add clickable option title
            destination_link = next(
                (url for dest, url in destinations_with_links if dest in option_title),
                None,
            )
            if destination_link:
                clickable_title = f'<a href="{destination_link}" color="#004444"><u>{option_title}</u></a>'
                story.append(Paragraph(clickable_title, hyperlink_style))
            else:
                story.append(Paragraph(option_title, title_style))

            story.append(Spacer(1, 0.1 * inch))

            # Add remaining option content
            for line in lines[1:]:
                line = line.strip()
                if line:
                    story.append(Paragraph(line, normal_style))
                    story.append(Spacer(1, 0.1 * inch))

        # Build the PDF
        doc.build(story)
        logger.info(f"PDF successfully created: {save_path}")
        return save_path

    except Exception as e:
        logger.error(f"Error creating PDF: {e}")
        return None

# 24. Process option
def _process_option(story, option, content, destination_links, styles, hyperlink_style):
    """Helper function to process each option and its content."""
    try:
        destination = None
        for line in content:
            if "Destination:" in line:
                location = line.split("Destination:")[1].split(",")[0].strip()
                for dest in destination_links:
                    if dest in location:
                        destination = dest
                        break
                break

        if destination and destination in destination_links:
            # Add appropriate banner based on option number
            option_num = option.split(":")[0].strip()
            banner_links = {
                "Option 1": (
                    "https://storage.googleapis.com/lux-travel-2/ads/banner-1.jpg",
                    "https://www.villiersjets.com/?id=7275",
                ),
                "Option 2": (
                    "https://storage.googleapis.com/lux-travel-2/ads/banner-2.jpg",
                    "https://searadar.tp.st/wOulUd7g",
                ),
                "Option 3": (
                    "https://storage.googleapis.com/lux-travel-2/ads/banner-3.jpg",
                    "https://www.skippercity.com/?ref=sidneym",
                ),
            }

            if option_num in banner_links:
                banner_img, banner_link = banner_links[option_num]
                integrate_banner(story, banner_img, banner_link)

            # Add clickable option title
            link = destination_links[destination]
            clickable_text = f'<a href="{link}" color="#004444"><u>{option}</u></a>'
            story.append(Paragraph(clickable_text, hyperlink_style))

            # Add remaining content
            for line in content[1:]:
                # Check if this is a destination line
                if "Destination:" in line:
                    line = f'{line} <a href="{link}">[View Details]</a>'
                story.append(Paragraph(line, styles["Normal"]))
    except Exception as e:
        logger.error(f"Error processing option: {e}")
        # Add content without links if there's an error
        for line in content:
            story.append(Paragraph(line, styles["Normal"]))

# 25. Hyperlink class
class Hyperlink(Flowable):
    def __init__(self, url, text, style):
        Flowable.__init__(self)
        self.url = url
        self.text = text
        self.style = style

    def draw(self):
        # Draw the hyperlink text
        self.canv.setFont(self.style.fontName, self.style.fontSize)
        self.canv.setFillColor(self.style.textColor)
        self.canv.drawString(0, 0, self.text)
        # Add hyperlink annotation
        self.canv.linkURL(
            self.url,
            (0, 0, self.canv.stringWidth(self.text), self.style.leading),
            relative=1,
        )


# Set up logging specifically for PDF generation
pdf_logger = logging.getLogger("pdf_generator")
pdf_logger.setLevel(logging.DEBUG)

# Handler for console output
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("PDF_GEN - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
pdf_logger.addHandler(console_handler)

# 26. Create pdf Itinerary
def create_pdf_itinerary(
    content, days, destinations_with_links, user_destination, user_query
):
    """
    Create a PDF for a detailed itinerary based on user preferences.
    Includes a single banner, user-personalized itinerary, and affiliate tours if available.
    """
    try:
        print("=== Starting PDF Generation Process ===", flush=True)
        pdf_logger.debug(
            f"Content received - Length: {len(content) if content else 0} chars"
        )
        pdf_logger.debug(f"Destination: {user_destination}, Days: {days}")

        filename = (
            f"{days}day_{user_destination.replace(' ', '_').lower()}_itinerary.pdf"
        )
        save_path = os.path.join("/tmp", filename)
        logger.info(f"Output filename: {filename}")

        # Initialize PDF document
        doc = SimpleDocTemplate(
            save_path,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )

        styles = getSampleStyleSheet()

        # Enhanced styles
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Title"],
            fontSize=24,
            fontName="Helvetica-Bold",
            textColor=HexColor("#004444"),
            alignment=1,
            spaceAfter=30,
        )

        day_style = ParagraphStyle(
            "DayTitle",
            fontSize=16,
            textColor=HexColor("#004444"),
            spaceBefore=15,
            spaceAfter=10,
            fontName="Helvetica-Bold",
        )

        activity_style = ParagraphStyle(
            "Activity", fontSize=12, leading=16, leftIndent=20, fontName="Helvetica"
        )

        cost_style = ParagraphStyle(
            "Cost", fontSize=12, leading=16, leftIndent=10, fontName="Helvetica"
        )

        story = []

        # Add title
        story.append(Paragraph("Eco-Friendly Luxury Travels", title_style))
        story.append(Spacer(1, 0.3 * inch))

        # Add banner
        integrate_banner(
            story,
            "https://storage.googleapis.com/lux-travel-2/ads/banner-1.jpg",
            "https://www.villiersjets.com/?id=7275",
        )
        story.append(Spacer(1, 0.3 * inch))

        # Add itinerary title
        story.append(
            Paragraph(f"{days}-Day Luxury Itinerary in {user_destination}", day_style)
        )
        story.append(Spacer(1, 0.2 * inch))

        # Process content with proper parsing
        if content:
            lines = content.split("\n")
            current_day = None

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                try:
                    # Day headers
                    if "Day" in line and any(str(i) in line for i in range(1, 32)):
                        story.append(Spacer(1, 0.3 * inch))
                        story.append(
                            Paragraph(line.replace("*", "").strip(), day_style)
                        )
                        current_day = line

                    # Activities
                    elif line.startswith("-"):
                        activity_text = line[1:].strip()
                        story.append(Paragraph(f"• {activity_text}", activity_style))

                    # Cost breakdowns
                    elif any(
                        cost_type in line
                        for cost_type in [
                            "Accommodation:",
                            "Dining:",
                            "Activities:",
                            "Spa:",
                            "Miscellaneous:",
                        ]
                    ):
                        story.append(Paragraph(line.strip(), cost_style))

                    # Total costs or estimates
                    elif line.startswith(("*Estimated", "**Total")):
                        story.append(Spacer(1, 0.2 * inch))
                        story.append(
                            Paragraph(line.replace("*", "").strip(), day_style)
                        )

                    # Other content
                    else:
                        story.append(Paragraph(line, activity_style))

                    pdf_logger.debug(f"Processed line: {line[:50]}...")

                except Exception as line_error:
                    logger.error(
                        f"Error processing line: {line[:50]}... Error: {str(line_error)}"
                    )
                    continue

        # Add affiliate tour link if available
        affiliate_link = next(
            (
                url
                for dest, url in destinations_with_links.items()
                if dest.lower() == user_destination.lower()
            ),
            None,
        )

        if affiliate_link:
            story.append(Spacer(1, 0.3 * inch))
            story.append(Paragraph("Exclusive Tour Offer:", day_style))
            tour_link = f'<a href="{affiliate_link}" color="#004444"><u>Click here to explore exclusive tours in {user_destination}!</u></a>'
            story.append(Paragraph(tour_link, activity_style))

        # Build PDF
        doc.build(story)
        logger.info(f"PDF created successfully at: {save_path}")
        print(f"=== PDF Generation Complete: {filename} ===", flush=True)

        return save_path

    except Exception as e:
        logger.error(f"Error in create_pdf_itinerary: {str(e)}")
        raise

    return None

# 27. Clear tmp directory
def clear_tmp_directory():
    """Clear the temporary directory and log the result"""
    tmp_dir = "/tmp"
    try:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        logger.info("Successfully cleared /tmp directory.")
    except Exception as e:
        logger.error(f"Failed to clear /tmp directory: {e}")

# not using
def search_luxury_escapes(destination):
    try:
        logger.info(f"Searching for luxury escapes for destination: {destination}")
        search_url = f"https://luxuryescapes.com/us"
        logger.debug(f"Search URL: {search_url}")

        response = requests.get(search_url)
        if response.status_code != 200:
            logger.error(
                f"Failed to fetch search results. HTTP Status Code: {response.status_code}"
            )
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract getaway links
        getaways = []
        for result in soup.select(".getaway-item"):
            title = result.select_one(".getaway-title").text.strip()
            url = result.select_one("a")["href"]
            full_url = f"https://www.luxuryescapes.com{url}"
            getaways.append({"title": title, "url": full_url})
            logger.debug(f"Found getaway: {title} - {full_url}")

        if not getaways:
            logger.info("No getaways found on the website.")
        return getaways
    except Exception as e:
        logger.error(f"An error occurred while searching for getaways: {e}")
        return []
    
def detect_intent(req_data: dict) -> str:
    # 1) Dialogflow CX tag (your current method)
    tag = req_data.get("fulfillmentInfo", {}).get("tag")
    if tag:
        return tag

    # 2) Dialogflow ES display name (fallback)
    name = req_data.get("queryResult", {}).get("intent", {}).get("displayName")
    if name:
        return name

    # 3) Soft keyword rescue from user text
    text = (req_data.get("queryResult", {}).get("queryText") or "").lower()
    if "getaway" in text or "weekend trip" in text or "short trip" in text:
        return "Getaways"
    if "itinerary" in text:
        return "Itineraries"

    return "Unknown"


# 28. Not using the search function
def handle_getaway_request(destination):
    try:
        logger.info(f"Handling getaway request for destination: {destination}")

        # Search for getaways
        getaways = search_luxury_escapes(destination)
        if not getaways:
            logger.info("No getaways found for the given destination.")
            return "No getaways found."

        # Log the options for debugging
        logger.info("Found getaways:")
        for i, getaway in enumerate(getaways):
            logger.info(f"{i + 1}: {getaway['title']} - {getaway['url']}")

        # Simulate user selection
        selected_index = 0  # Assume the first option is selected
        logger.info(f"User selected getaway index: {selected_index + 1}")
        selected_url = getaways[selected_index]["url"]

        # Generate affiliate link
        impact_api_key = "YOUR_IMPACT_API_KEY"
        affiliate_link = create_vanity_link(impact_api_key, selected_url)
        if not affiliate_link:
            logger.error("Failed to generate affiliate link.")
            return "Failed to generate affiliate link."

        logger.info(f"Generated affiliate link: {affiliate_link}")

        # Add to PDF and return
        filename = "getaway.pdf"
        pdf_path = create_pdf_with_affiliate_links(
            f"Selected getaway: {getaways[selected_index]['title']}",
            filename,
            [(destination, affiliate_link)],
        )
        if pdf_path:
            logger.info(f"PDF created successfully: {pdf_path}")
            return f"PDF created: {pdf_path}"
        else:
            logger.error("Failed to create PDF.")
            return "Failed to create PDF."
    except Exception as e:
        logger.error(f"An error occurred while handling the getaway request: {e}")
        return "An error occurred while processing the request."


# 29. Itineraries Intent:
@app.route("/dialogflowWebhook", methods=["POST"])
def dialogflow_webhook():
    logger.debug("Webhook received a request.")  # Entry log

    try:
        req_data = request.get_json()
        logger.debug(f"Request JSON: {json.dumps(req_data, indent=2)}")

        session_info = req_data.get("sessionInfo", {})
        parameters = session_info.get("parameters", {})
        user_query = req_data.get("queryResult", {}).get("queryText", "")

        intent = detect_intent(req_data)
        logger.info(f"Handling intent: {intent}")


        # Intent-specific logic
        if intent == "Itineraries":
            destination_list = parameters.get(
                "destination", [{"original": "default_destination"}]
            )
            # Extract 'original' from each destination dictionary and join them into a string
            destination = " ".join([item["original"] for item in destination_list])
            number_of_days = parameters.get("number_of_days", 7)
            budget = parameters.get("budget", "$25000")
            logger.info(
                f"Processing Itineraries for {destination}, {number_of_days} days, budget {budget}"
            )

            try:
                # Generate the OpenAI prompt
                prompt = f"Create a luxury itinerary for {destination}, {number_of_days} days within {budget}."

                # Validate response_text
                response_text = call_openai_itinerary(
                    user_query, affiliate_links, parameters
                )

                if not response_text:
                    logger.error(
                        "OpenAI API returned no response or an empty response."
                    )
                    return (
                        jsonify(
                            {
                                "fulfillmentText": "Error: Unable to generate getaway options."
                            }
                        ),
                        500,
                    )

                # Log the response text for debugging
                logger.debug(f"OpenAI response: {response_text}")

                # Correct number_of_days formatting
                try:
                    number_of_days = int(float(parameters.get("number_of_days", 7)))
                except (ValueError, TypeError):
                    number_of_days = "unknown"

                # Generate a clean filename with proper formatting
                filename = (
                    f"{number_of_days} day {destination.capitalize()} itinerary.pdf"
                )

                # Sanitize the filename
                filename = sanitize_filename(filename)
                logger.info(f"Generated filename: {filename}")

                # Parse destinations with affiliate links
                story = []  # Initialize story
                parsed_destinations = select_destination_with_affiliate_links(
                    response_text, link_style, story
                )
                logger.debug(f"Parsed destinations: {parsed_destinations}")

                # Create the PDF with affiliate links
                pdf_path = create_pdf_itinerary(
                    content=response_text,
                    days=number_of_days,
                    destinations_with_links=affiliate_links,
                    user_destination=destination,
                    user_query=user_query,
                )
                logger.info(f"PDF generated at: {pdf_path}")

                # Upload the PDF to Google Cloud Storage
                upload_response = upload_to_gcs_with_public_acl(
                    "lux-travel-2", f"pdfs/{filename}", pdf_path
                )
                if upload_response:
                    # Generate a public URL for the uploaded file
                    public_url = upload_response["public_url"]
                    logger.info(f"Public URL: {public_url}")

                    # Create the response with the download URL
                    response_data = {
                        "fulfillmentMessages": [
                            {"text": {"text": ["Here's your luxury itinerary."]}},
                            {
                                "payload": {
                                    "richContent": [
                                        [
                                            {
                                                "title": "Download Itinerary",
                                                "subtitle": "Click the link below to download your itinerary.",
                                                "type": "info",
                                                "actionLink": public_url,  # Include the actual download URL
                                            }
                                        ]
                                    ]
                                }
                            },
                        ],
                        "sessionInfo": {"parameters": {"download_url": public_url}},
                    }
                    logger.debug(
                        f"Response sent: {json.dumps(response_data, indent=2)}"
                    )
                    return jsonify(response_data)
                else:
                    # Handle upload failure
                    logger.error("Error uploading PDF to GCS.")
                    return jsonify({"fulfillmentText": "Error uploading PDF."}), 500

            except Exception as e:
                # Handle any errors in the process
                logger.error(f"Error during itinerary processing: {e}")
                logger.debug(traceback.format_exc())
                return jsonify({"fulfillmentText": "Error processing itinerary."}), 500

        # 30. Handle Getaways Intent
        elif intent == "Getaways":
            try:
                # Extract and process parameters
                destination_list = parameters.get(
                    "destination", [{"original": "default_destination"}]
                )
                try:
                    # Extract 'original' from each destination dictionary and join them into a string
                    destination = " ".join(
                        [
                            item["original"]
                            for item in destination_list
                            if isinstance(item, dict) and "original" in item
                        ]
                    )
                except Exception as e:
                    logger.error(f"Error processing destination: {e}")
                    destination = "default_destination"
                    logger.debug(f"Raw destination_list parameter: {destination_list}")

                number_of_days = parameters.get("number_of_days", 7)
                budget = parameters.get("budget", 10000)  # Default budget
                climate_preferences = parameters.get(
                    "climate_preferences", "warm and sunny"
                )
                activities_interests = parameters.get(
                    "activities_interests", "sightseeing, spa treatments"
                )
                family_size = parameters.get("family_size", 4)
                ages = parameters.get("ages", [30, 28, 7, 5])
                geography_scenery = parameters.get(
                    "geography_scenery", "serene and flat"
                )
                travel_distance = parameters.get("travel_distance", "close to home")

                # Log parameter values for debugging
                logger.debug(
                    f"Extracted Parameters: number_of_days={number_of_days}, budget={budget}, "
                    f"climate_preferences={climate_preferences}, activities_interests={activities_interests}, "
                    f"family_size={family_size}, ages={ages}, geography_scenery={geography_scenery}, "
                    f"travel_distance={travel_distance}"
                )

                # Create the prompt for OpenAI
                prompt = (
                    f"Create three luxury getaway options for a {number_of_days}-day trip within a budget of {budget}. "
                    f"The getaway should consider a climate preference of {climate_preferences}, include activities like {activities_interests}, "
                    f"and accommodate a family size of {family_size} with ages of {ages}. The scenery preference is {geography_scenery} "
                    f"and the travel distance is {travel_distance}. "
                    f"Provide three unique and diverse options, each with:"
                    f" - A detailed destination description, including highlights and specific activities."
                    f" - A short list of luxury accommodations."
                    f" - An estimated cost."
                    f" - A persuasive call-to-action that encourages the user to explore or book the option, but do not includ the heading 'Call-to-Action'."
                    f"Ensure that the response is engaging, professional, and matches only the available destinations:\n"
                    f"{destination_list}\n"
                    f"Choose the closest match to the user's query and emphasize the luxury experience."
                )

                logger.debug(f"Affiliate links: {affiliate_links}")
                #req = request.get_json(silent=True, force=True)
                #parameters = req.get("queryResult", {}).get("parameters", {})

                # Call OpenAI with user query, affiliate links, and extracted parameters
                #user_query = req.get("queryResult", {}).get("queryText", "")
                response_text = call_openai_getaways(
                    user_query, affiliate_links, parameters
                )

                story = []
                select_destination_with_affiliate_links(
                    response_text, link_style, story
                )
                if not response_text:
                    logger.error(
                        "OpenAI API returned no response or an empty response."
                    )
                    return (
                        jsonify(
                            {
                                "fulfillmentText": "Error: Unable to generate getaway options."
                            }
                        ),
                        500,
                    )

                # Log the response text for debugging
                logger.debug(f"Response Text from OpenAI: {response_text}")

                # Pull days from session parameters (fallback to 7 only if missing)
                try:
                    days = int(float(parameters.get("number_of_days", 7)))
                except (ValueError, TypeError):
                    days = "unknown"

                logger.info(f"Getaways: days={days}, budget={budget}, family_size={family_size}")

                filename = f"{days}daygetawayoptions.pdf"  # single, consistent naming
                parsed_destinations = select_destination_with_affiliate_links(response_text, link_style, [])
                pdf_path = create_pdf_with_banners_and_affiliate_links(
                    response_text, days, parsed_destinations
                )


                # Sanitize the filename
                filename = sanitize_filename(filename)

                logger.info(f"Generated filename: {filename}")

                # Extract destinations with affiliate links
                story = []  # Initialize story
                #parsed_destinations = select_destination_with_affiliate_links(
                    #response_text, link_style, story
                #)
                logger.debug(f"Parsed destinations with links: {parsed_destinations}")

                # Format the results for the PDF
                formatted_content = format_getaway_results(
                    parsed_destinations, response_text
                )

                # Generate destinations with affiliate links
                destination = select_destination_with_affiliate_links(
                    response_text, link_style, story
                )
                pdf_content = format_getaway_results(destination, response_text)

                # Create the PDF with affiliate links and upload it
                parsed_destinations = select_destination_with_affiliate_links(
                    response_text, link_style, story
                )
                logger.debug(f"Parsed destinations: {parsed_destinations}")

                pdf_path = create_pdf_with_banners_and_affiliate_links(
                    response_text, number_of_days, parsed_destinations
                )
                logger.info(f"PDF generated at: {pdf_path}")

                if pdf_path:
                    # Upload PDF to Google Cloud Storage
                    upload_response = upload_to_gcs_with_public_acl(
                        "lux-travel-2", f"pdfs/{filename}", pdf_path
                    )
                    if upload_response:
                        public_url = upload_response["public_url"]
                        logger.info(f"Public URL: {public_url}")

                        # Log the generated download URL
                        logger.info(
                            f"Generated download URL for Getaways: {public_url}")

                        # Respond to Dialogflow with the download link
                        return jsonify(
                            {
                                "fulfillmentMessages": [
                                    {
                                        "text": {
                                            "text": [
                                                "Great! Here's your custom getaway."
                                            ]
                                        }
                                    },
                                    {
                                        "payload": {
                                            "richContent": [
                                                {
                                                    "title": "Your Getaway",
                                                    "subtitle": "Click below to download.",
                                                    "actionLink": public_url,
                                                    "type": "info",
                                                }
                                            ]
                                        }
                                    },
                                    {
                                        "text": {
                                            "text": [
                                                "Is there anything else I can help you with today?"
                                            ]
                                        }
                                    },
                                ],
                                "sessionInfo": {
                                    "parameters": {"download_url": public_url}
                                },
                            }
                        )
                    else:
                        logger.error("Error uploading the PDF to Google Cloud Storage.")
                        return (
                            jsonify(
                                {"fulfillmentText": "Error uploading the getaway PDF."}
                            ),
                            500,
                        )
                else:
                    logger.error("Error creating the getaway PDF.")
                    return (
                        jsonify({"fulfillmentText": "Error creating the getaway PDF."}),
                        500,
                    )

            except Exception as e:
                logger.error(f"Error in Getaways intent: {e}")
                traceback.print_exc()
                return (
                    jsonify(
                        {
                            "fulfillmentText": "An error occurred while creating the getaway."
                        }
                    ),
                    500,
                )
        else:
            logger.debug("Unknown intent received.")
            return jsonify({"fulfillmentText": "Unknown intent"}), 200
    except Exception as e:
        logger.error(f"Error in dialogflowWebhook: {e}")
        traceback.print_exc()
        return jsonify({"fulfillmentText": "An error occurred in the webhook."}), 500


# 31. Parse OpenAI response to identify destinations
def parse_destinations(response_text, affiliate_links):
    """Parse the response text to identify matching destinations from affiliate links."""
    parsed_destinations = []

    try:
        logger.debug("Starting to parse destinations from the response text.")
        logger.debug(
            f"Response text: {response_text[:500]}")  # Log first 500 characters
        # Create a mapping of known destinations
        destinations = {
            hotel["destination"]: hotel["link"]
            for hotel in affiliate_links.get("getaways", {}).get("Thailand", [])
        }

        # Debug log for available destinations
        logger.debug(f"Available destinations: {destinations}")

        # Process the response text
        for line in response_text.splitlines():
            if "Destination:" in line:
                location = line.split("Destination:")[1].split(",")[0].strip()
                logger.debug(f"Extracted location: {location}")

                for dest in destinations.keys():
                    if dest in location:
                        parsed_destinations.append((location, destinations[location]))
                        logger.info(
                            f"Matched destination: {location} -> {destinations[location]}")
                        # Search for links in affiliate_links
                        if (
                            "getaways" in affiliate_links
                            and "Thailand" in affiliate_links["getaways"]
                        ):
                            for hotel in affiliate_links["getaways"]["Thailand"]:
                                if dest.lower() in hotel["destination"].lower():
                                    destinations[dest] = hotel["link"]
                                    break

        # Convert to a list of tuples
        parsed_destinations = [
            (dest, link) for dest, link in destinations.items() if link
        ]
        if not parsed_destinations:
            logger.warning("No destinations matched in the response text.")
        return parsed_destinations
    except Exception as e:
        logger.error(f"Error parsing destinations: {e}")
        return []

# 32. Format getaway results
def format_getaway_results(parsed_destinations, response_text):
    """
    Formats the getaway results with clickable affiliate links.
    """
    try:
        if not parsed_destinations:
            logger.error("No parsed destinations available to format.")
            return response_text  # Or some fallback logic

        # Convert parsed_destinations to dictionary more safely
        destination_links = {}
        for item in parsed_destinations:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                dest, link = item
                destination_links[dest] = link

        # Process text line by line
        lines = response_text.splitlines()
        formatted_lines = []

        for line in lines:
            modified_line = line
            # Check for destinations in the line
            for dest, link in destination_links.items():
                if dest.lower() in line.lower():
                    if "Option" in line:
                        if "[Book Now]" not in line:  # Prevent duplicate links
                            modified_line = f"{line} [Book Now]({link})"
                    elif "Destination:" in line:
                        if "[View Details]" not in line:  # Prevent duplicate links
                            modified_line = f"{line} [View Details]({link})"
                    break
            formatted_lines.append(modified_line)

        # Add Quick Links section if we have any destinations
        if destination_links:
            formatted_lines.extend(["", "Quick Links:"])
            for dest, link in sorted(destination_links.items()):
                formatted_lines.append(f"• {dest}: [View Details]({link})")

        return "\n".join(formatted_lines)

    except Exception as e:
        logger.error(f"Error formatting getaway results: {e}")
        logger.error(f"parsed_destinations: {parsed_destinations}")  # Debug info
        return response_text  # Return original text if formatting fails


# 33. Helper function to normalize destination names
def normalize_destination(destination):
    """Normalize destination names for consistent matching."""
    return destination.lower().strip()


# 34. Match user query to links
def match_links(user_query):
    try:
        # Search for the query in getaways or tours
        for category, links in affiliate_links.items():
            for destination, url in links.items():
                if destination.lower() in user_query.lower():
                    logger.info(f"Match found: {destination}")
                    return url
        logger.info("No matching link found.")
        return None
    except Exception as e:
        logger.error(f"Error matching links: {e}")
        return None


# 35. Fetch options from the URL
def fetch_options(url):
    try:
        response = requests.get(url)
        if response.status_code != 200:
            logger.error(f"Failed to fetch URL: {url}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        options = []
        # Modify selectors based on page structure
        for item in soup.select(".getaway-item"):
            title = item.select_one(".getaway-title").text.strip()
            link = item.select_one("a")["href"]
            full_url = f"https://www.luxuryescapes.com{link}"
            options.append({"title": title, "url": full_url})

        logger.info(f"Fetched {len(options)} options from the URL.")
        return options[:3]  # Return the top 3 options
    except Exception as e:
        logger.error(f"Error fetching options: {e}")
        return []


# 36. Handle user query for getaways
def handle_getaway_query(user_query):
    try:
        matched_url = match_links(user_query)
        if not matched_url:
            return "No matching getaways found."

        options = fetch_options(matched_url)
        if not options:
            return "No options found for the selected destination."

        # Generate PDF with options and transport links
        content = "Selected Getaways:\n" + "\n".join(
            [f"{opt['title']} - {opt['url']}" for opt in options]
        )
        content += "\n\nTransport Options:\n" + "\n".join(
            [f"{trans['name']} - {trans['url']}" for trans in transport_links]
        )

        filename = "getaway_options.pdf"
        pdf_path = create_pdf_with_affiliate_links(
            content, filename, [(opt["title"], opt["url"]) for opt in options]
        )

        if pdf_path:
            logger.info(f"PDF generated successfully: {pdf_path}")
            return f"PDF created: {pdf_path}"
        else:
            logger.error("Failed to generate PDF.")
            return "Error creating PDF."
    except Exception as e:
        logger.error(f"Error handling getaway query: {e}")
        return "An error occurred while processing your request."


# 37. Welcome Intent: Sends a greeting message when a session starts
@app.route("/welcome", methods=["POST"])
def welcome():
    try:
        logger.info("Received a request for the welcome webhook.")

        # Log the request body for debugging
        request_data = request.get_json()
        logger.debug(f"Request JSON: {json.dumps(request_data, indent=2)}")

        # Respond with a welcome message
        response = jsonify(
            {
                "fulfillmentMessages": [
                    {
                        "text": {
                            "text": [
                                "Hi! I'm Dave, an AI chatbot. I can create a travel itinerary or suggest a getaway. How can I assist you?"
                            ]
                        }
                    }
                ]
            }
        )

        logger.info("Welcome message successfully created.")
        logger.debug(f"Response JSON: {response.get_json()}")

        return response

    except Exception as e:
        # Log the error message and traceback for debugging
        logger.error(f"Error in welcome webhook: {str(e)}")
        logger.debug(traceback.format_exc())

        # Return an error response to Dialogflow
        return (
            jsonify({"fulfillmentText": "An error occurred in the welcome webhook."}),
            500,
        )


# 38. Download PDF route: Allows downloading PDF files
@app.route("/download/<filename>")
def download_pdf(filename):
    try:
        file_path = os.path.join("/tmp", filename)
        logger.info(f"Attempting to send file from: {file_path}")
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        logger.error(f"Error sending file: {e}")
        return jsonify({"error": "File not found."}), 404


@app.route("/ping", methods=["GET"])
def ping():
    return "pong", 200


@app.route("/")
def home():
    return "This is the root endpoint for the Luxury Travels application."


@app.route("/test", methods=["GET"])
def test():
    try:
        logger.info("Test endpoint hit!")
        parameters = {
            "destination": ["Maldives"],
            "number_of_days": "5",
            "budget": "$10000",
            "family_size": 4,
        }
        filename = generate_filename(parameters)
        content = "Sample itinerary content"
        pdf_path = create_pdf_with_reportlab(content, filename)
        if pdf_path:
            logger.info("Test PDF created successfully.")
        return jsonify({"message": "Test successful!"})
    except Exception as e:
        logger.exception("Test endpoint error.")
        return jsonify({"error": str(e)}), 500
    
@app.route("/version")
def version():
    return APP_VERSION, 200


# Run the Flask app
if __name__ == "__main__":
    try:
        # Set up Google ADC from Secret Manager
        setup_google_adc_from_secret()
        
        # Setup service account from Secret Manager
        setup_service_account_from_secret(secret_name="TravelManager")

        # Confirm credentials are loaded
        credentials, project = default()
        logger.info(f"Credentials loaded successfully. Project: {project}")
    except Exception as e:
        logger.error(f"Application failed to initialize: {str(e)}")
        sys.exit(1)
    port = int(
        os.environ.get("PORT", 8080)
    )  # Use PORT environment variable or default to 8080
    app.run(host="0.0.0.0", port=port, debug=False)  # Ensure your app listens on all IPs
    logger.info(f"Starting server on port: {port}")
