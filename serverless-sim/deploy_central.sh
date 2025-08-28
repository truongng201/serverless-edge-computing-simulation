#!/bin/bash
# Central Node Deployment Script

echo "=================================="
echo "SERVERLESS CENTRAL NODE DEPLOYMENT"
echo "=================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is required but not installed"
    exit 1
fi

# Install dependencies
# echo "📦 Installing dependencies..."
# pip3 install -r requirements.txt

# Check if Docker is installed and running
if ! command -v docker &> /dev/null; then
    echo "⚠️  Docker is not installed. Some features may not work."
    echo "   Please install Docker from: https://docs.docker.com/get-docker/"
else
    if ! docker info &> /dev/null; then
        echo "⚠️  Docker is not running. Starting Docker..."
        # Try to start Docker (platform-specific)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            open /Applications/Docker.app
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo systemctl start docker
        fi
    else
        echo "✅ Docker is running"
    fi
fi

echo "🚀 Starting Central Node..."
echo "🛑 Press Ctrl+C to stop"
echo ""

# Start the central node
python3 central_main.py "$@"
