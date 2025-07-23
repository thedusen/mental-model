#!/bin/bash
set -e

echo "🚀 Starting Supabase local development..."

# Create necessary directories
mkdir -p supabase/data
mkdir -p supabase/logs

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📋 Copying .env.example to .env"
    cp .env.example .env
    echo "⚠️  Please update .env with your actual values"
fi

# Start only the essential Supabase services for now
echo "🐘 Starting Supabase database..."
docker-compose up -d supabase-db

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Check if database is ready
if docker-compose exec supabase-db pg_isready -U postgres > /dev/null 2>&1; then
    echo "✅ Database is ready!"
else
    echo "❌ Database is not ready. Checking logs..."
    docker-compose logs supabase-db
    exit 1
fi

echo "🎉 Supabase database is running!"
echo ""
echo "📊 Database connection info:"
echo "  Host: localhost"
echo "  Port: 5432" 
echo "  Database: postgres"
echo "  Username: postgres"
echo "  Password: your-super-secret-and-long-postgres-password"
echo ""
echo "🔧 Next steps:"
echo "  1. Test database connection"
echo "  2. Run migrations to set up schema"
echo "  3. Start Kong API gateway and Auth service"
echo ""
echo "🛑 To stop: docker-compose down"