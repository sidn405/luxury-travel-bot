#!/usr/bin/env python3
"""
Eco Friendly Luxury Travels - AI Travel Assistant
Version 2.3.3 - Getaway improvements: better titles, affiliate links, clickable links
"""

import datetime
import os
import json
import re
import logging
import sys

from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_compress import Compress
import requests

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.enums import TA_CENTER

# Setup logging
env = os.getenv("ENV", "production")
logging_level = logging.DEBUG if env == "development" else logging.INFO

logging.basicConfig(
    level=logging_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("eco_friendly_luxury_travels")

# Initialize Flask with static folder configuration
app = Flask(__name__, 
            static_folder='templates/static',
            static_url_path='/static')
Compress(app)

APP_VERSION = "2.3.3-Getaway-Fix"

# Storage
STORAGE_DIR = os.getenv("STORAGE_DIR", "/tmp/travel-pdfs")
os.makedirs(STORAGE_DIR, exist_ok=True)

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY environment variable is missing!")
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {OPENAI_API_KEY.strip()}",
    "Content-Type": "application/json",
}

# Branding
BRAND_NAME = "Eco Friendly Luxury Travels"
BRAND_COLOR = HexColor("#004444")
ACCENT_COLOR = HexColor("#006666")

# Local file paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "templates/static/logo.png")
BANNER_DIR = os.path.join(BASE_DIR, "graphics/Banner_ads")

# PDF Styles
title_style = ParagraphStyle(
    name="BrandTitle",
    fontName="Helvetica-Bold",
    fontSize=28,
    alignment=TA_CENTER,
    textColor=BRAND_COLOR,
    spaceAfter=20,
)

subtitle_style = ParagraphStyle(
    name="Subtitle",
    fontName="Helvetica-Bold",
    fontSize=20,
    alignment=TA_CENTER,
    textColor=BRAND_COLOR,
    spaceAfter=10,
)

section_title_style = ParagraphStyle(
    name="SectionTitle",
    fontName="Helvetica-Bold",
    fontSize=16,
    textColor=BRAND_COLOR,
    spaceAfter=8,
)

normal_style = ParagraphStyle(
    name="Normal",
    fontName="Helvetica",
    fontSize=11,
    textColor=black,
    leading=14,
)

small_style = ParagraphStyle(
    name="Small",
    fontName="Helvetica",
    fontSize=9,
    textColor=black,
    leading=11,
)

# Affiliate links configuration
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
    },
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
            }
}

transport_links = [
    {"name": "Villiers Jets", "url": "https://www.villiersjets.com/?id=7275"},
    {"name": "Sea Radar", "url": "https://searadar.tp.st/wOulUd7g"},
]

BANNER_ADS = [
    {
        "path": os.path.join(BANNER_DIR, "banner-1.jpg"),  # Local file
        "link": "https://www.villiersjets.com/?id=7275",
        "alt": "Villiers Jets - Book Private Jet"
    },
    {
        "path": os.path.join(BANNER_DIR, "banner-2.jpg"),  # Local file
        "link": "https://searadar.tp.st/wOulUd7g",
        "alt": "SeaRadar - Yacht Charter"
    },
    {
        "path": os.path.join(BANNER_DIR, "banner-3.jpg"),  # Local file
        "link": "https://www.skippercity.com/?ref=sidneym",
        "alt": "Skippercity - Yacht Charter"
    },
]



def load_local_image(file_path):
    """Load image from local file for PDF."""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                return f.read()
        else:
            logger.warning(f"Image file not found: {file_path}")
            return None
    except Exception as e:
        logger.error(f"Error loading image from {file_path}: {e}")
        return None


def clean_text_for_pdf(text):
    """Clean and escape text for safe PDF generation."""
    if not text:
        return ""
    
    # Escape HTML special characters
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    
    # Now convert markdown bold to HTML (after escaping)
    # This prevents issues with < > in user text
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    
    return text.strip()


def load_local_image(file_path):
    """Load image from local file for PDF."""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                return f.read()
        else:
            logger.warning(f"Image file not found: {file_path}")
            return None
    except Exception as e:
        logger.error(f"Error loading image from {file_path}: {e}")
        return None


def clean_text_for_pdf(text):
    """Clean and escape text for safe PDF generation."""
    if not text:
        return ""
    
    # Escape HTML special characters
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    
    # Now convert markdown bold to HTML (after escaping)
    # This prevents issues with < > in user text
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    
    return text.strip()


def extract_parameters(user_message):
    """Extract structured parameters from message."""
    try:
        prompt = f"""Extract travel parameters from: "{user_message}"

Return JSON with these fields (null if not mentioned):
{{
  "destination": ["string"],          // Extract mentioned destinations, or null if none mentioned
  "number_of_days": number,           // Extract number of days
  "budget": "string",                 // Extract budget with currency
  "preferred_activities": ["string"], // Extract ALL activities (skiing, snowboarding, hiking, etc)
  "family_size": number,              // Number of people traveling
  "ages": [number],                   // Ages if mentioned
  "travel_dates": "string",           // Dates or season (e.g., "winter", "December")
  "climate_preferences": "string",    // Weather preference (cold, warm, tropical, etc)
  "geography_scenery": "string"       // Type of scenery (mountains, beach, desert, etc)
}}

Examples:
"7-day Paris trip for 2, $5000" → 
{{"destination":["Paris"],"number_of_days":7,"family_size":2,"budget":"$5000","preferred_activities":null,"ages":null,"travel_dates":null,"climate_preferences":null,"geography_scenery":null}}

"Winter ski vacation for family of 4, love snowboarding" →
{{"destination":null,"number_of_days":null,"family_size":4,"budget":null,"preferred_activities":["skiing","snowboarding"],"ages":null,"travel_dates":"winter","climate_preferences":"cold","geography_scenery":"mountains"}}

Extract ALL activities mentioned, and infer geography from activities (skiing=mountains, beach activities=beach, etc)."""

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json={
                "model": "gpt-4",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
                "temperature": 0.3,
            },
            timeout=30
        )
        
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                params = json.loads(json_match.group())
                return normalize_parameters(params)
        
        return get_default_parameters()
    except Exception as e:
        logger.error(f"Error extracting parameters: {e}")
        return get_default_parameters()


def normalize_parameters(params):
    """Normalize extracted parameters."""
    # Ensure destination is always a list
    if params.get("destination"):
        if not isinstance(params["destination"], list):
            params["destination"] = [params["destination"]]
        # Filter out None or empty values
        params["destination"] = [d for d in params["destination"] if d]
    
    # Set defaults for missing values
    if not params.get("destination") or len(params["destination"]) == 0:
        params["destination"] = ["Paris"]
    
    params.setdefault("number_of_days", 7)
    params.setdefault("family_size", 2)
    params.setdefault("budget", "$5000")
    
    return params


def get_default_parameters():
    """Default parameters."""
    return {
        "destination": ["Paris"],
        "number_of_days": 7,
        "budget": "$5000",
        "preferred_activities": None,
        "family_size": 2,
        "ages": None,
        "travel_dates": None,
        "climate_preferences": None,
        "geography_scenery": None
    }


def generate_itinerary(parameters):
    """Generate detailed itinerary."""
    try:
        # Ensure destination is a list and not empty
        destinations_list = parameters.get("destination", ["Paris"])
        if not destinations_list or not isinstance(destinations_list, list):
            destinations_list = ["Paris"]
        
        destinations = ", ".join(destinations_list)
        prompt = f"""Create detailed luxury itinerary for Eco Friendly Luxury Travels:

Destination: {destinations}
Days: {parameters['number_of_days']}
Budget: {parameters['budget']}
Travelers: {parameters['family_size']}
{f"Activities: {', '.join(parameters['preferred_activities'])}" if parameters.get('preferred_activities') else ""}
{f"Climate: {parameters['climate_preferences']}" if parameters.get('climate_preferences') else ""}

Include:
- Day-by-day breakdown with specific times
- Luxury eco-friendly hotels with exact prices
- Sustainable fine dining (breakfast/lunch/dinner) with restaurant names
- Exclusive eco-conscious activities
- Green transportation options
- Daily cost estimates
- Sustainability tips

Be specific with hotel names, restaurant names, and actual prices."""
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json={
                "model": "gpt-4",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 3000,
                "temperature": 0.7,
            },
            timeout=90
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return None
    except Exception as e:
        logger.error(f"Error generating itinerary: {e}")
        return None


def generate_getaway(parameters):
    """Generate getaway recommendations."""
    try:
        budget = parameters.get('budget', '$3000')
        activities = parameters.get('preferred_activities', [])
        climate = parameters.get('climate_preferences')
        geography = parameters.get('geography_scenery')
        travelers = parameters.get('family_size', 2)
        
        # Build activity string
        activity_str = ', '.join(activities) if activities and isinstance(activities, list) else "various activities"
        
        # Build list of affiliate destinations to prioritize
        affiliate_destinations = list(affiliate_links.keys())
        affiliate_str = ', '.join(affiliate_destinations)
        
        prompt = f"""Suggest 3 eco-friendly luxury getaways for Eco Friendly Luxury Travels:

Budget: {budget}
Travelers: {travelers} people"""
        
        if activities and isinstance(activities, list) and len(activities) > 0:
            prompt += f"\nActivities: {activity_str}"
        if climate:
            prompt += f"\nClimate: {climate}"
        if geography:
            prompt += f"\nScenery: {geography}"
        
        prompt += f"""

IMPORTANT: Select destinations ONLY from this list (we have affiliate partnerships):
{affiliate_str}

Match destinations to the requested activities and preferences. For example:
- Skiing/snowboarding → Aspen, Vail, Whistler, St. Moritz
- Beach/tropical → Maldives, Bali, Hawaii, Thailand
- Culture/city → Paris, Rome, London, Dubai

For each destination:
**Option X: [Destination Name] - [Catchy Title]**

**Destination Description:**
[Detailed description focusing on eco-friendly aspects and matching the requested activities]

**Family Activities:** (if travelers > 2)
[Activities suitable for families]

**Scenery Preference:** [Type]
**Climate Preference:** [Type]
**Estimated Cost:** [Amount]

[Compelling closing paragraph about sustainability]

Use destinations from the affiliate list only. Format exactly like this with clear sections."""
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json={
                "model": "gpt-4",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2500,
                "temperature": 0.7,
            },
            timeout=90
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return None
    except Exception as e:
        logger.error(f"Error generating getaway: {e}")
        return None


def create_pdf(content, filename, parameters, doc_type="itinerary"):
    """Create branded PDF with local banner ads."""
    try:
        pdf_path = os.path.join(STORAGE_DIR, filename)
        doc = SimpleDocTemplate(pdf_path, pagesize=letter,
                               topMargin=0.5*inch, bottomMargin=0.5*inch,
                               leftMargin=0.75*inch, rightMargin=0.75*inch)
        story = []
        
        # Brand title
        story.append(Paragraph(BRAND_NAME, title_style))
        story.append(Spacer(1, 0.1 * inch))
        
        # Document title and subtitle
        if doc_type == "itinerary":
            doc_title = "Luxury Travel Itinerary"
            doc_subtitle = f"{', '.join(parameters['destination'])} - {parameters['number_of_days']} Days"
            # Add 1 banner under title for itineraries
            banner = BANNER_ADS[0]
            img_data = load_local_image(banner['path'])
            if img_data:
                from io import BytesIO
                img = Image(BytesIO(img_data), width=6*inch, height=1.5*inch)
                img.hAlign = 'CENTER'
                story.append(img)
                story.append(Spacer(1, 0.1 * inch))
                # Add clickable link text
                link_para = Paragraph(f'<a href="{banner["link"]}">{banner["alt"]}</a>', 
                                    ParagraphStyle(name='Link', alignment=TA_CENTER, textColor=BRAND_COLOR, fontSize=10))
                story.append(link_para)
                story.append(Spacer(1, 0.3 * inch))
        else:
            doc_title = "Luxury Getaway Recommendations"
            
            # Build descriptive subtitle
            days = parameters.get('number_of_days', 5)
            travelers = parameters.get('family_size', 2)
            activities = parameters.get('preferred_activities', [])
            climate = parameters.get('climate_preferences', '')
            
            subtitle_parts = []
            subtitle_parts.append(f"{days}-Day")
            
            if climate:
                subtitle_parts.append(climate.title())
            
            if activities and isinstance(activities, list):
                activity_desc = '/'.join(activities[:2]).title()
                subtitle_parts.append(activity_desc)
            
            subtitle_parts.append("Getaway")
            subtitle_parts.append(f"for {travelers}")
            
            doc_subtitle = " ".join(subtitle_parts)
        
        story.append(Paragraph(doc_title, subtitle_style))
        story.append(Paragraph(doc_subtitle, section_title_style))
        story.append(Spacer(1, 0.2 * inch))
        
        # Trip details
        details = f"<b>Budget:</b> {parameters['budget']} | <b>Travelers:</b> {parameters['family_size']}"
        story.append(Paragraph(details, normal_style))
        story.append(Spacer(1, 0.3 * inch))
        
        # Content - for getaways, split by options to insert banners
        if doc_type == "getaway":
            # Split content by options
            sections = re.split(r'(Option \d+:)', content)
            banner_idx = 0
            
            for i, section in enumerate(sections):
                if section.strip():
                    # Add text
                    for line in section.split('\n'):
                        if line.strip():
                            # Clean text safely for PDF
                            line_clean = clean_text_for_pdf(line)
                            
                            # If line starts with Option, make it bold
                            if line.strip().startswith('Option'):
                                if '<b>' not in line_clean:
                                    line_clean = f'<b>{line_clean}</b>'
                                story.append(Paragraph(line_clean, section_title_style))
                            else:
                                story.append(Paragraph(line_clean, normal_style))
                            story.append(Spacer(1, 0.08 * inch))
                    
                    # Add banner after each option (3 total for getaways)
                    if 'Option' in section and banner_idx < 3:
                        story.append(Spacer(1, 0.2 * inch))
                        banner = BANNER_ADS[banner_idx % len(BANNER_ADS)]
                        img_data = load_local_image(banner['path'])
                        if img_data:
                            from io import BytesIO
                            img = Image(BytesIO(img_data), width=6*inch, height=1.5*inch)
                            img.hAlign = 'CENTER'
                            story.append(img)
                            story.append(Spacer(1, 0.05 * inch))
                            # Clickable link
                            link_para = Paragraph(f'<a href="{banner["link"]}">{banner["alt"]}</a>', 
                                                ParagraphStyle(name='Link', alignment=TA_CENTER, textColor=BRAND_COLOR, fontSize=10))
                            story.append(link_para)
                            story.append(Spacer(1, 0.3 * inch))
                        banner_idx += 1
        else:
            # Itinerary - regular content
            for line in content.split('\n'):
                if line.strip():
                    # Clean text safely for PDF
                    line_clean = clean_text_for_pdf(line)
                    
                    # Check if it's a day header
                    original_line = line.strip()
                    if original_line.startswith('Day ') or original_line.startswith('**Day '):
                        if '<b>' not in line_clean:
                            line_clean = f'<b>{line_clean}</b>'
                        story.append(Paragraph(line_clean, section_title_style))
                    else:
                        story.append(Paragraph(line_clean, normal_style))
                    story.append(Spacer(1, 0.08 * inch))
        
        # Booking links section
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph("<b>Booking Links:</b>", section_title_style))
        story.append(Spacer(1, 0.1 * inch))
        
        # For getaways, extract destinations from content
        if doc_type == "getaway":
            # Find destinations mentioned in content that match our affiliate links
            destinations_found = []
            for dest in affiliate_links.keys():
                if dest in content:
                    destinations_found.append(dest)
            
            # Use found destinations, fallback to parameters if none found
            if destinations_found:
                destinations_to_link = destinations_found
            else:
                destinations_to_link = parameters['destination'] if parameters.get('destination') else []
        else:
            # For itineraries, use parameter destinations
            destinations_to_link = parameters['destination']
        
        # Add clickable links with color
        link_style = ParagraphStyle(
            name='BookingLink',
            fontName='Helvetica-Bold',
            fontSize=12,
            textColor=BRAND_COLOR,
            leading=16,
        )
        
        for dest in destinations_to_link:
            if dest in affiliate_links:
                link = f'<a href="{affiliate_links[dest]}" color="blue"><u>{dest} - Book Now →</u></a>'
                story.append(Paragraph(link, link_style))
                story.append(Spacer(1, 0.08 * inch))
        
        # Build PDF
        doc.build(story)
        logger.info(f"PDF created: {pdf_path}")
        return pdf_path
    except Exception as e:
        logger.error(f"Error creating PDF: {e}")
        logger.exception(e)
        return None


def generate_filename(parameters, doc_type="itinerary"):
    """Generate filename based on parameters."""
    # For getaways, use meaningful description
    if doc_type == "getaway":
        activities = parameters.get('preferred_activities', [])
        climate = parameters.get('climate_preferences', '')
        
        # Build descriptive name
        if activities and isinstance(activities, list):
            desc = "-".join(activities[:2])  # First 2 activities
        elif climate:
            desc = climate
        elif parameters.get('geography_scenery'):
            desc = parameters.get('geography_scenery')
        else:
            desc = "luxury"
        
        desc = desc.replace(" ", "-")[:30]
        travelers = parameters.get('family_size', 2)
        days = parameters.get('number_of_days', 5)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"getaway-{days}day-{travelers}ppl-{desc}-{timestamp}.pdf"
    
    # For itineraries, use destination
    else:
        dest = "-".join(parameters["destination"])[:30].replace(" ", "-")
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"itinerary-{dest}-{timestamp}.pdf"


# ============================================================================
# ROUTES
# ============================================================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "healthy", "version": APP_VERSION}), 200


@app.route("/api/chat", methods=["POST"])
def chat():
    """Main chat endpoint."""
    try:
        data = request.get_json()
        message = data.get("message", "")
        
        if not message:
            return jsonify({"error": "Message required"}), 400
        
        logger.info(f"Chat: {message}")
        
        # Extract parameters
        parameters = extract_parameters(message)
        message_lower = message.lower()
        
        # Route to appropriate generator (prioritize getaway keywords)
        if any(w in message_lower for w in ["getaway", "vacation", "escape", "weekend"]):
            # Getaway has priority - more specific intent
            content = generate_getaway(parameters)
            doc_type = "getaway"
        elif any(w in message_lower for w in ["itinerary", "plan", "trip", "schedule", "day-by-day"]):
            content = generate_itinerary(parameters)
            doc_type = "itinerary"
        else:
            return jsonify({
                "response": "Hi! I'm Dave from Eco Friendly Luxury Travels. I can:\n\n"
                           "📅 Create detailed sustainable travel itineraries\n"
                           "🏖️ Suggest eco-friendly luxury getaways\n\n"
                           "What would you like to explore?",
                "parameters": parameters
            })
        
        if not content:
            return jsonify({"error": "Failed to generate content"}), 500
        
        # Create PDF
        filename = generate_filename(parameters, doc_type)
        pdf_path = create_pdf(content, filename, parameters, doc_type)
        
        response = {
            "response": content,
            "parameters": parameters,
            "intent": doc_type
        }
        
        if pdf_path:
            response["pdf_url"] = f"/download/{filename}"
            response["pdf_filename"] = filename
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        logger.exception(e)
        return jsonify({"error": str(e)}), 500


@app.route("/download/<filename>")
def download_pdf(filename):
    """Download PDF."""
    try:
        return send_from_directory(STORAGE_DIR, filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({"error": "File not found"}), 404


@app.route("/version")
def version():
    return APP_VERSION, 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting {BRAND_NAME} Bot v{APP_VERSION} on port {port}")
    
    # Check if required files exist
    if not os.path.exists(LOGO_PATH):
        logger.warning(f"Logo file not found at: {LOGO_PATH}")
    if not os.path.exists(BANNER_DIR):
        logger.warning(f"Banner directory not found at: {BANNER_DIR}")
    else:
        for i in range(1, 4):
            banner_path = os.path.join(BANNER_DIR, f"banner-{i}.jpg")
            if not os.path.exists(banner_path):
                logger.warning(f"Banner file not found: {banner_path}")
    
    app.run(host="0.0.0.0", port=port, debug=(env == "development"))