#!/bin/bash
# Edge Node Deployment Script

echo "=================================="
echo "SERVERLESS EDGE NODE DEPLOYMENT"
echo "=================================="

# Function to display usage
usage() {
    echo "Usage: $0 --node-id <NODE_ID> --central-url <CENTRAL_URL> [OPTIONS]"
    echo ""
    echo "Required arguments:"
    echo "  --node-id <ID>        Unique identifier for this edge node"
    echo "  --central-url <URL>   Central node URL (e.g., http://192.168.1.100:5001)"
    echo ""
    echo "Optional arguments:"
    echo "  --port <PORT>         Port to run on (auto-detect if not specified)"
    echo "  --host <HOST>         Host to bind to (default: 0.0.0.0)"
    echo "  --log-level <LEVEL>   Log level: DEBUG, INFO, WARNING, ERROR (default: INFO)"
    echo "  --help               Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  NODE_ID              Edge node ID"
    echo "  CENTRAL_URL          Central node URL"
    echo "  EDGE_PORT            Edge node port"
    echo "  EDGE_HOST            Edge node host"
    echo "  LOG_LEVEL            Logging level"
    echo ""
    echo "Examples:"
    echo "  $0 --node-id edge_001 --central-url http://192.168.1.100:5001"
    echo "  $0 --node-id edge_lab1 --central-url http://10.0.0.50:5001 --port 5002"
    echo ""
}

# Parse command line arguments
NODE_ID=""
CENTRAL_URL=""
EDGE_PORT=""
EDGE_HOST="${EDGE_HOST:-0.0.0.0}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --node-id)
            NODE_ID="$2"
            shift 2
            ;;
        --central-url)
            CENTRAL_URL="$2"
            shift 2
            ;;
        --port)
            EDGE_PORT="$2"
            shift 2
            ;;
        --host)
            EDGE_HOST="$2"
            shift 2
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "❌ Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Use environment variables if command line arguments not provided
NODE_ID="${NODE_ID:-$NODE_ID}"
CENTRAL_URL="${CENTRAL_URL:-$CENTRAL_URL}"
EDGE_PORT="${EDGE_PORT:-$EDGE_PORT}"

# Validate required arguments
if [[ -z "$NODE_ID" ]]; then
    echo "❌ Error: --node-id is required"
    echo ""
    usage
    exit 1
fi

if [[ -z "$CENTRAL_URL" ]]; then
    echo "❌ Error: --central-url is required"
    echo ""
    usage
    exit 1
fi

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
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

# Check if Docker is installed and running
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is required but not installed"
    echo "   Please install Docker from: https://docs.docker.com/get-docker/"
    exit 1
else
    if ! docker info &> /dev/null; then
        echo "⚠️  Docker is not running. Starting Docker..."
        # Try to start Docker (platform-specific)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            open /Applications/Docker.app
            echo "   Please wait for Docker to start and run this script again"
            exit 1
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo systemctl start docker
            sleep 5
        fi
        
        # Check again
        if ! docker info &> /dev/null; then
            echo "❌ Failed to start Docker. Please start Docker manually and try again."
            exit 1
        fi
    fi
    echo "✅ Docker is running"
fi

# Test central node connectivity
echo "🔗 Testing connection to central node..."
if command -v curl &> /dev/null; then
    if curl -s --connect-timeout 5 "$CENTRAL_URL/api/v1/central/health" > /dev/null; then
        echo "✅ Central node is reachable"
    else
        echo "⚠️  Cannot reach central node at $CENTRAL_URL"
        echo "   Please ensure:"
        echo "   1. Central node is running"
        echo "   2. URL is correct"
        echo "   3. Network connectivity exists"
        echo ""
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
else
    echo "⚠️  curl not found, skipping connectivity test"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs

# Get local IP
LOCAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | head -n1)
if [[ -z "$LOCAL_IP" ]]; then
    LOCAL_IP="localhost"
fi

echo "🚀 Starting Edge Node..."
echo "   Node ID: $NODE_ID"
echo "   Central Node: $CENTRAL_URL"
echo "   Host: $EDGE_HOST"
if [[ -n "$EDGE_PORT" ]]; then
    echo "   Port: $EDGE_PORT"
else
    echo "   Port: Auto-detect"
fi
echo "   Local IP: $LOCAL_IP"
echo "   Log Level: $LOG_LEVEL"
echo ""
echo "📝 Logs will be written to ${NODE_ID}.log"
echo "🛑 Press Ctrl+C to stop"
echo ""

# Build the command
CMD="python3 edge_main.py --node-id \"$NODE_ID\" --central-url \"$CENTRAL_URL\" --host \"$EDGE_HOST\" --log-level \"$LOG_LEVEL\""

if [[ -n "$EDGE_PORT" ]]; then
    CMD="$CMD --port \"$EDGE_PORT\""
fi

# Start the edge node
eval $CMD
