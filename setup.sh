#!/bin/bash

# Luxury Travel Bot - Quick Setup Script
# This script helps you set up the bot for local development

echo "======================================"
echo "Luxury Travel Bot - Setup"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo "Please install Python 3.9+ and try again"
    exit 1
fi

echo -e "${GREEN}✓ Python 3 found${NC}"
python3 --version
echo ""

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}Error: pip is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ pip found${NC}"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment already exists${NC}"
else
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Dependencies installed successfully${NC}"
else
    echo -e "${RED}Error installing dependencies${NC}"
    exit 1
fi
echo ""

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo -e "${YELLOW}⚠ Please edit .env and add your OPENAI_API_KEY${NC}"
    echo ""
fi

# Create storage directory
echo "Creating storage directory..."
mkdir -p tmp/travel-pdfs
echo -e "${GREEN}✓ Storage directory created${NC}"
echo ""

echo "======================================"
echo "Setup Complete! ✨"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your OPENAI_API_KEY"
echo "2. Run the bot:"
echo "   source venv/bin/activate"
echo "   python Luxury_Travel_Bot.py"
echo ""
echo "3. Test the bot:"
echo "   python test_bot.py"
echo ""
echo "4. Open in browser:"
echo "   http://localhost:8080"
echo ""