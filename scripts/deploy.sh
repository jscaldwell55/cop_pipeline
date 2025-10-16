#!/bin/bash
# File: scripts/deploy.sh

# Production Deployment Script

set -e

echo "=== CoP Pipeline Production Deployment ==="

# Check environment
if [ ! -f ".env.production" ]; then
    echo "Error: .env.production not found"
    exit 1
fi

# Load environment
source .env.production

# Build production image
echo "Building production image..."
docker-compose -f docker-compose.prod.yml build

# Stop existing services
echo "Stopping existing services..."
docker-compose -f docker-compose.prod.yml down

# Backup database
echo "Backing up database..."
mkdir -p backups
docker exec cop-postgres-prod pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} > backups/backup_$(date +%Y%m%d_%H%M%S).sql || true

# Start services
echo "Starting services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services
echo "Waiting for services to be ready..."
sleep 10

# Run database migrations
echo "Running database migrations..."
docker-compose -f docker-compose.prod.yml exec -T cop-pipeline python -c "
import asyncio
from database.models import init_db
from config.settings import get_settings

async def main():
    settings = get_settings()
    await init_db(settings.database_url)
    print('Database migrations complete')

asyncio.run(main())
"

# Health check
echo "Running health checks..."
curl -f http://localhost:9090/metrics || echo "Warning: Metrics endpoint not responding"

echo "✓ Deployment complete!"
echo ""
echo "Services:"
echo "  - CoP Pipeline: http://localhost:9090"
echo "  - Prometheus: http://localhost:9091"
echo "  - Grafana: http://localhost:3000"
echo ""
echo "Check logs: docker-compose -f docker-compose.prod.yml logs -f"
```

## Additional Helper Files

### `logs/.gitkeep`
```
# This file ensures the logs directory is tracked by git
```

### `data/.gitkeep`
```
# This file ensures the data directory is tracked by git
```

### `results/.gitkeep`
```
# This file ensures the results directory is tracked by git