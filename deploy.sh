#!/bin/bash
set -e

echo "🚀 Experto-agi Production Deployment Script"
echo "==========================================="

# Check environment
if [ -z "$ENVIRONMENT" ]; then
    echo "❌ ENVIRONMENT not set. Set it to 'production' or 'staging'"
    exit 1
fi

echo "📦 Environment: $ENVIRONMENT"

# Load environment variables if exists
if [ -f ".env" ]; then
    source .env
    echo "✓ Environment variables loaded"
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not installed"
    exit 1
fi

echo "✓ Docker is installed"

# Build images
echo "🔨 Building Docker images..."
docker-compose build --no-cache

# Pull latest code
if git rev-parse --git-dir > /dev/null 2>&1; then
    echo "📥 Pulling latest code..."
    git pull origin main || true
fi

# Backup current state
echo "💾 Backing up current deployment..."
mkdir -p backups
docker-compose exec -T web tar czf /app/backup-$(date +%Y%m%d-%H%M%S).tar.gz \
    models/ logs/ 2>/dev/null || true

# Stop old containers
echo "⛔ Stopping old containers..."
docker-compose down || true

# Start new containers
echo "▶️  Starting containers..."
docker-compose up -d

# Wait for health check
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Verify services
echo "🔍 Verifying services..."
docker-compose ps
docker-compose logs --tail=20

echo ""
echo "✅ Deployment completed successfully!"
echo "📊 Monitor logs: docker-compose logs -f web"
echo "🌐 API available at: http://localhost:8000"
echo "📈 Prometheus metrics: http://localhost:9090"
