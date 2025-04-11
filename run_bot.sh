#!/bin/bash

# Colors for better output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Starting SMPanel Bot ===${NC}"

# Activate Python virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Run the bot
echo -e "${YELLOW}Running the bot...${NC}"
echo -e "${GREEN}Bot started successfully!${NC}"
echo -e "${YELLOW}To stop the bot, press Ctrl+C${NC}"
echo

# Run the main bot file
python src/bot/index.py 