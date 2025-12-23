#!/bin/bash

# Luxury Travel Bot - Local Run Script
# Run this to start the bot locally: ./run.sh

echo "======================================"
echo "Luxury Travel Bot - Starting..."
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found!${NC}"
    echo -e "${YELLOW}Please run setup.sh first${NC}"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found!${NC}"
    echo -e "${YELLOW}Creating .env from template...${NC}"
    cp .env.example .env
    echo ""
    echo -e "${YELLOW}Please edit .env and add your OPENAI_API_KEY${NC}"
    echo -e "${YELLOW}Then run this script again${NC}"
    exit 1
fi

# Load environment variables from .env
export $(grep -v '^#' .env | xargs)

# Set default PORT if not set
if [ -z "$PORT" ]; then
    export PORT=8080
fi

echo ""
echo -e "${GREEN}Starting bot on http://localhost:$PORT${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Run the bot
python Luxury_Travel_Bot.py