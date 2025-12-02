#!/bin/bash

# Arzaq Backend - Development Server Runner
# This script activates virtual environment and runs the FastAPI server

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Arzaq Backend API...${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found!${NC}"
    echo -e "${BLUE}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${BLUE}📦 Activating virtual environment...${NC}"
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo -e "${BLUE}Creating .env from .env.example...${NC}"
    cp .env.example .env
    echo -e "${RED}⚠️  Please update .env with your configuration!${NC}"
    exit 1
fi

# Install dependencies if needed
if [ ! -f "venv/installed.flag" ]; then
    echo -e "${BLUE}📥 Installing dependencies...${NC}"
    pip install --upgrade pip
    pip install -r requirements.txt
    touch venv/installed.flag
fi

# Run migrations
echo -e "${BLUE}🗄️  Checking database migrations...${NC}"
alembic upgrade head

# Start server
echo -e "${GREEN}✅ Starting server on http://localhost:8000${NC}"
echo -e "${GREEN}📚 API Documentation: http://localhost:8000/docs${NC}"
echo -e "${GREEN}🏥 Health Check: http://localhost:8000/health${NC}"

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
