#!/usr/bin/env python3
import datetime
import os
import json
import re
import traceback
import logging
import sys
from io import BytesIO

from flask import Flask, request, jsonify, send_file, send_from_directory, render_template
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

from bs4 import BeautifulSoup

# Setup logging
env = os.getenv("ENV", "production")

if env == "development":
    logging_level = logging.DEBUG
else:
    logging_level = logging.INFO

logging.basicConfig(
    level=logging_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("luxury_travel_bot")

# Initialize Flask app
app = Flask(__name__)
Compress(app)

# Version
APP_VERSION = "2.0.0-Railway"

# Create storage directories
STORAGE_DIR = os.getenv("STORAGE_DIR", "/tmp/travel-pdfs")
os.makedirs(STORAGE_DIR, exist_ok=True)

# Load OpenAI API key from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY environment variable is missing!")
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {OPENAI_API_KEY.strip()}",
    "Content-Type": "application/json",
}

# PDF Styles
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
    textColor=HexColor("#004444"),
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

banners = [
    {
        "url": "https://via.placeholder.com/800x200.png?text=Luxury+Travel+Banner+1",
        "link": "https://www.villiersjets.com/?id=7275",
    },
    {
        "url": "https://via.placeholder.com/800x200.png?text=Luxury+Travel+Banner+2",
        "link": "https://searadar.tp.st/wOulUd7g",
    },
    {
        "path": "https://storage.googleapis.com/lux-travel-2/ads/banner-3.jpg",
        "link": "https://www.skippercity.com/?ref=sidneym",
    },
]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_filename(parameters):
    """Generate a filename based on user parameters."""
    try:
        destination = "-".join(parameters.get("destination", ["Unknown"]))
        days = parameters.get("number_of_days", "X")
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{destination}-{days}days-{timestamp}.pdf"
        return filename
    except Exception as e:
        logger.error(f"Error generating filename: {e}")
        return f"itinerary-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.pdf"


def call_openai_api(prompt, model="gpt-4", max_tokens=2000, temperature=0.7):
    """Call OpenAI API with the given prompt."""
    try:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            response_data = response.json()
            return response_data["choices"][0]["message"]["content"]
        else:
            logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        return None


def create_pdf_with_reportlab(content, filename, parsed_destinations=None):
    """Create a PDF with reportlab."""
    try:
        pdf_path = os.path.join(STORAGE_DIR, filename)
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Add title
        title = Paragraph("Your Luxury Travel Itinerary", title_style)
        story.append(title)
        story.append(Spacer(1, 0.3 * inch))
        
        # Add content
        for line in content.split('\n'):
            if line.strip():
                p = Paragraph(line, normal_style)
                story.append(p)
                story.append(Spacer(1, 0.1 * inch))
        
        # Add affiliate links section
        if parsed_destinations:
            story.append(Spacer(1, 0.3 * inch))
            story.append(Paragraph("Booking Links:", subtitle_style))
            story.append(Spacer(1, 0.1 * inch))
            
            for dest, link in parsed_destinations:
                link_para = Paragraph(f'<a href="{link}">{dest} - Book Now</a>', link_style)
                story.append(link_para)
                story.append(Spacer(1, 0.1 * inch))
        
        # Build PDF
        doc.build(story)
        logger.info(f"PDF created successfully: {pdf_path}")
        return pdf_path
    except Exception as e:
        logger.error(f"Error creating PDF: {e}")
        return None


def parse_destinations_from_response(response_text):
    """Extract destination names from OpenAI response."""
    try:
        parsed_destinations = []
        lines = response_text.split('\n')
        
        for line in lines:
            for dest, link in affiliate_links["getaways"].items():
                if dest.lower() in line.lower():
                    parsed_destinations.append((dest, link))
                    break
        
        return list(set(parsed_destinations))  # Remove duplicates
    except Exception as e:
        logger.error(f"Error parsing destinations: {e}")
        return []


def format_getaway_results(parsed_destinations, response_text):
    """Format getaway results with clickable affiliate links."""
    try:
        if not parsed_destinations:
            return response_text
        
        destination_links = dict(parsed_destinations)
        lines = response_text.splitlines()
        formatted_lines = []
        
        for line in lines:
            modified_line = line
            for dest, link in destination_links.items():
                if dest.lower() in line.lower():
                    if "Option" in line and "[Book Now]" not in line:
                        modified_line = f"{line} [Book Now]({link})"
                    elif "Destination:" in line and "[View Details]" not in line:
                        modified_line = f"{line} [View Details]({link})"
                    break
            formatted_lines.append(modified_line)
        
        # Add Quick Links section
        if destination_links:
            formatted_lines.extend(["", "Quick Links:"])
            for dest, link in sorted(destination_links.items()):
                formatted_lines.append(f"• {dest}: [View Details]({link})")
        
        return "\n".join(formatted_lines)
    except Exception as e:
        logger.error(f"Error formatting getaway results: {e}")
        return response_text


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route("/")
def home():
    """Serve the web interface."""
    return render_template("index.html")


@app.route("/api/info")
def api_info():
    """API information endpoint."""
    return jsonify({
        "service": "Luxury Travel Bot",
        "version": APP_VERSION,
        "status": "running",
        "endpoints": {
            "chat": "/api/chat",
            "itinerary": "/api/itinerary",
            "getaway": "/api/getaway",
            "health": "/health"
        }
    })


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "version": APP_VERSION}), 200


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Main chat endpoint - replaces Dialogflow webhook.
    Accepts: {"message": "user message"}
    Returns: {"response": "bot response", "pdf_url": "optional"}
    """
    try:
        data = request.get_json()
        user_message = data.get("message", "")
        
        if not user_message:
            return jsonify({"error": "Message is required"}), 400
        
        logger.info(f"Chat request: {user_message}")
        
        # Determine intent based on keywords
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ["itinerary", "plan", "trip", "travel plan"]):
            # Redirect to itinerary generation
            return generate_itinerary_endpoint(user_message)
        
        elif any(word in message_lower for word in ["getaway", "vacation", "escape", "holiday"]):
            # Redirect to getaway suggestions
            return generate_getaway_endpoint(user_message)
        
        else:
            # General conversation
            prompt = f"""You are Dave, a luxury travel assistant AI. 
            User says: {user_message}
            
            Provide a helpful, friendly response. If they're asking about travel, 
            suggest they can ask for an itinerary or getaway recommendations."""
            
            response_text = call_openai_api(prompt, max_tokens=500)
            
            if response_text:
                return jsonify({"response": response_text})
            else:
                return jsonify({"error": "Failed to generate response"}), 500
                
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/itinerary", methods=["POST"])
def generate_itinerary_endpoint(user_message=None):
    """
    Generate travel itinerary.
    Accepts: {
        "destination": ["Paris", "Rome"],
        "days": 7,
        "budget": "$5000",
        "family_size": 2,
        "message": "optional natural language request"
    }
    """
    try:
        data = request.get_json() if not user_message else {}
        
        if user_message:
            # Parse from natural language
            prompt = f"""Extract travel parameters from this request: "{user_message}"
            Return JSON with: destination (array), days (number), budget (string), family_size (number)
            If not specified, use: days=7, budget="$5000", family_size=2"""
            
            params_text = call_openai_api(prompt, max_tokens=200)
            try:
                parameters = json.loads(params_text)
            except:
                parameters = {
                    "destination": ["Unknown"],
                    "days": 7,
                    "budget": "$5000",
                    "family_size": 2
                }
        else:
            parameters = {
                "destination": data.get("destination", ["Paris"]),
                "days": data.get("days", 7),
                "budget": data.get("budget", "$5000"),
                "family_size": data.get("family_size", 2)
            }
        
        # Generate itinerary
        destinations = ", ".join(parameters["destination"])
        prompt = f"""Create a luxury travel itinerary for:
        Destination(s): {destinations}
        Duration: {parameters['days']} days
        Budget: {parameters['budget']}
        Travelers: {parameters['family_size']} people
        
        Include: daily activities, luxury accommodations, fine dining, exclusive experiences.
        Be specific and detailed."""
        
        itinerary_text = call_openai_api(prompt, max_tokens=2000)
        
        if not itinerary_text:
            return jsonify({"error": "Failed to generate itinerary"}), 500
        
        # Parse destinations and create PDF
        parsed_destinations = parse_destinations_from_response(itinerary_text)
        filename = generate_filename({"destination": parameters["destination"], "number_of_days": parameters["days"]})
        pdf_path = create_pdf_with_reportlab(itinerary_text, filename, parsed_destinations)
        
        response_data = {
            "response": itinerary_text,
            "parameters": parameters
        }
        
        if pdf_path:
            response_data["pdf_url"] = f"/download/{filename}"
            response_data["pdf_filename"] = filename
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error generating itinerary: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/getaway", methods=["POST"])
def generate_getaway_endpoint(user_message=None):
    """
    Generate getaway recommendations.
    Accepts: {
        "budget": "$3000",
        "preferences": "beach, relaxation",
        "message": "optional natural language"
    }
    """
    try:
        data = request.get_json() if not user_message else {}
        
        if user_message:
            budget = "$3000"
            preferences = user_message
        else:
            budget = data.get("budget", "$3000")
            preferences = data.get("preferences", "luxury, relaxation")
        
        prompt = f"""Suggest 3 luxury getaway destinations for:
        Budget: {budget}
        Preferences: {preferences}
        
        For each destination provide:
        - Destination name
        - Why it's perfect
        - Best time to visit
        - Highlight activities
        - Estimated cost breakdown
        
        Focus on: Maldives, Bali, Dubai, Paris, Santorini, Thailand, or Hawaii."""
        
        response_text = call_openai_api(prompt, max_tokens=1500)
        
        if not response_text:
            return jsonify({"error": "Failed to generate getaway suggestions"}), 500
        
        # Parse and format
        parsed_destinations = parse_destinations_from_response(response_text)
        formatted_response = format_getaway_results(parsed_destinations, response_text)
        
        # Create PDF
        filename = f"getaway-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.pdf"
        pdf_path = create_pdf_with_reportlab(formatted_response, filename, parsed_destinations)
        
        response_data = {
            "response": formatted_response,
            "destinations": [dest for dest, _ in parsed_destinations]
        }
        
        if pdf_path:
            response_data["pdf_url"] = f"/download/{filename}"
            response_data["pdf_filename"] = filename
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error generating getaway: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/download/<filename>")
def download_pdf(filename):
    """Download generated PDF."""
    try:
        return send_from_directory(STORAGE_DIR, filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return jsonify({"error": "File not found"}), 404


@app.route("/files")
def list_files():
    """List all generated PDFs."""
    try:
        files = os.listdir(STORAGE_DIR)
        pdfs = [f for f in files if f.endswith('.pdf')]
        return jsonify({
            "files": pdfs,
            "count": len(pdfs),
            "storage_dir": STORAGE_DIR
        })
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/version")
def version():
    """Get app version."""
    return APP_VERSION, 200


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting Luxury Travel Bot v{APP_VERSION} on port {port}")
    app.run(host="0.0.0.0", port=port, debug=(env == "development"))