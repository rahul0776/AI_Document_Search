#!/bin/bash
# Quick start script for AI Document Search

set -e

echo "🚀 AI Document Search - Quick Start"
echo "===================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp env.example .env
    echo "✅ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and set your OPENAI_API_KEY"
    echo "   nano .env"
    echo ""
    read -p "Press Enter after setting your API key..."
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "📦 Building and starting services..."
echo ""

# Start services
docker-compose up --build -d

echo ""
echo "✅ Services started!"
echo ""
echo "🌐 Access the application:"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "📊 View logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Stop services:"
echo "   docker-compose down"
echo ""
echo "🔧 For development without Docker, see DEPLOYMENT.md"
echo ""

