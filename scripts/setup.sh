#!/bin/bash
# File: scripts/setup.sh

# CoP Pipeline Setup Script

set -e

echo "=== CoP Pipeline Setup ==="

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python 3.11+ required, found $python_version"
    exit 1
fi

echo "✓ Python version: $python_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Copy environment file
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your API keys"
fi

# Create directories
echo "Creating directories..."
mkdir -p logs
mkdir -p data
mkdir -p config/grafana/dashboards
mkdir -p config/grafana/datasources

# Initialize database (Docker)
echo "Starting Docker services..."
docker-compose up -d postgres redis

# Wait for services
echo "Waiting for services to be ready..."
sleep 5

# Run database migrations
echo "Initializing database..."
python -c "
import asyncio
from database.models import init_db
from config.settings import get_settings

async def main():
    settings = get_settings()
    await init_db(settings.database_url)
    print('Database initialized')

asyncio.run(main())
"

echo "✓ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your API keys"
echo "2. Activate venv: source venv/bin/activate"
echo "3. Run tests: pytest tests/"
echo "4. Try CLI: python cli.py --help"
echo "5. Start services: docker-compose up -d"