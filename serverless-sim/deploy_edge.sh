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
    echo "  --central-url <URL>   Central node URL (e.g., http://localhost:8000)"
    echo ""
    echo "Optional arguments:"
    echo "  --port <PORT>         Host port to expose (forwards to container port 5000)"
    echo "  --host <HOST>         Host to bind to (default: 0.0.0.0)"
    echo "  --log-level <LEVEL>   Log level: DEBUG, INFO, WARNING, ERROR (default: INFO)"
    echo "  --cpus <CORES>        Number of CPU cores to use (e.g., 1, 0.5, 2)"
    echo "  --memory <RAM>        Memory limit (e.g., 512m, 1g, 2g)"
    echo "  --detach              Run in detached mode (don't remove on exit)"
    echo "  --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --node-id edge_001 --central-url http://localhost:8000 --port 8001"
    echo "  $0 --node-id edge_lab1 --central-url http://localhost:8000 --port 5002 --cpus 2 --memory 1g"
    echo "  $0 --node-id edge_002 --central-url http://localhost:8000 --port 8002 --detach"
    echo ""
}

# Cleanup function to stop and remove container
cleanup() {
    echo ""
    echo "🛑 Stopping edge node container..."
    if docker ps --filter "name=$CONTAINER_NAME" --format '{{.Names}}' | grep -q "$CONTAINER_NAME"; then
        docker stop "$CONTAINER_NAME" > /dev/null 2>&1
        echo "✅ Container stopped"
    fi
    
    if [ "$DETACHED" = false ]; then
        echo "🧹 Removing container..."
        docker rm "$CONTAINER_NAME" > /dev/null 2>&1
        echo "✅ Container removed"
    else
        echo "ℹ️  Container kept (detached mode)"
    fi
    
    echo ""
    echo "👋 Edge node deployment terminated"
    exit 0
}

# Set up trap to catch Ctrl+C and other signals
trap cleanup SIGINT SIGTERM

# Parse command line arguments
NODE_ID=""
CENTRAL_URL=""
EDGE_PORT=""
EDGE_HOST="${EDGE_HOST:-0.0.0.0}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"
EDGE_CPUS="${EDGE_CPUS:-}"
EDGE_MEMORY="${EDGE_MEMORY:-}"
DETACHED=false

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
        --cpus)
            EDGE_CPUS="$2"
            shift 2
            ;;
        --memory)
            EDGE_MEMORY="$2"
            shift 2
            ;;
        --detach)
            DETACHED=true
            shift
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

# Convert localhost/127.0.0.1 to Docker host gateway
CONTAINER_CENTRAL_URL="$CENTRAL_URL"
if [[ "$CENTRAL_URL" == *"localhost"* ]] || [[ "$CENTRAL_URL" == *"127.0.0.1"* ]]; then
    CONTAINER_CENTRAL_URL="${CENTRAL_URL//localhost/host.docker.internal}"
    CONTAINER_CENTRAL_URL="${CONTAINER_CENTRAL_URL//127.0.0.1/host.docker.internal}"
    echo "ℹ️  Converting $CENTRAL_URL to $CONTAINER_CENTRAL_URL for Docker container"
fi

# Set default port if not specified
if [[ -z "$EDGE_PORT" ]]; then
    EDGE_PORT="5000"
    echo "ℹ️  No port specified, using default: $EDGE_PORT"
fi

# Check if Docker is installed and running
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is required but not installed"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "✅ Docker is running"

# Build or check for edge-node image
if ! docker images | grep -q "edge-node"; then
    echo "🔨 Building edge-node Docker image..."
    if [ -f "Dockerfile" ]; then
        docker build -t edge-node:latest . || {
            echo "❌ Failed to build Docker image"
            exit 1
        }
    else
        echo "❌ Dockerfile not found. Please ensure you're in the correct directory."
        exit 1
    fi
else
    echo "✅ Edge-node Docker image found"
fi

# Stop and remove existing container
CONTAINER_NAME="edge_${NODE_ID}"
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "🧹 Removing existing container: $CONTAINER_NAME"
    docker stop "$CONTAINER_NAME" > /dev/null 2>&1
    docker rm "$CONTAINER_NAME" > /dev/null 2>&1
fi

echo ""
echo "🚀 Starting Edge Node in Docker container..."
echo "   Node ID: $NODE_ID"
echo "   Central Node (original): $CENTRAL_URL"
echo "   Central Node (container): $CONTAINER_CENTRAL_URL"
echo "   Port Mapping: Host $EDGE_PORT -> Container 5000"
echo "   Log Level: $LOG_LEVEL"
if [[ -n "$EDGE_CPUS" ]]; then
    echo "   CPU Limit: $EDGE_CPUS cores"
fi
if [[ -n "$EDGE_MEMORY" ]]; then
    echo "   Memory Limit: $EDGE_MEMORY"
fi
if [ "$DETACHED" = true ]; then
    echo "   Mode: Detached (container will persist)"
else
    echo "   Mode: Interactive (container removed on Ctrl+C)"
fi
echo ""

# Build docker run command array
DOCKER_ARGS=(
    "run" "-d"
    "--name" "$CONTAINER_NAME"
    "-p" "$EDGE_PORT:5000"
    "-v" "/var/run/docker.sock:/var/run/docker.sock"
)

# Add host.docker.internal support for Linux
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    DOCKER_ARGS+=("--add-host=host.docker.internal:host-gateway")
    echo "ℹ️  Added host.docker.internal mapping for Linux"
fi

# Add CPU limit if specified
if [[ -n "$EDGE_CPUS" ]]; then
    DOCKER_ARGS+=("--cpus=$EDGE_CPUS")
fi

# Add memory limit if specified
if [[ -n "$EDGE_MEMORY" ]]; then
    DOCKER_ARGS+=("--memory=$EDGE_MEMORY")
fi

# Add environment variables
DOCKER_ARGS+=(
    "-e" "NODE_ID=$NODE_ID"
    "-e" "CENTRAL_URL=$CONTAINER_CENTRAL_URL"
    "-e" "EDGE_PORT=5000"
    "-e" "EDGE_HOST=$EDGE_HOST"
    "-e" "LOG_LEVEL=$LOG_LEVEL"
)

# Add image and command arguments
DOCKER_ARGS+=(
    "edge-node:latest"
    "--node-id" "$NODE_ID"
    "--central-url" "$CONTAINER_CENTRAL_URL"
    "--port" "5000"
    "--host" "$EDGE_HOST"
    "--log-level" "$LOG_LEVEL"
)

# Print the full command for debugging
echo "🐳 Docker command:"
echo "   docker ${DOCKER_ARGS[*]}"
echo ""

# Run Docker container
docker "${DOCKER_ARGS[@]}"

if [ $? -eq 0 ]; then
    echo "✅ Edge node container started successfully"
    echo "🌐 Access edge node at: http://localhost:$EDGE_PORT"
    echo ""
    echo "📋 Useful commands:"
    echo "   View logs: docker logs -f $CONTAINER_NAME"
    echo "   Stop: docker stop $CONTAINER_NAME"
    echo "   Remove: docker rm $CONTAINER_NAME"
    echo "   Restart: docker restart $CONTAINER_NAME"
    echo "   Inspect: docker inspect $CONTAINER_NAME"
    echo ""
    echo "🔍 Verifying container startup..."
    sleep 3
    
    # Check if container is still running
    if docker ps --filter "name=$CONTAINER_NAME" --format '{{.Names}}' | grep -q "$CONTAINER_NAME"; then
        echo "✅ Container is running"
        echo ""
        if [ "$DETACHED" = true ]; then
            echo "🎯 Container is running in detached mode"
            echo "   Use 'docker logs -f $CONTAINER_NAME' to view logs"
            echo "   Use 'docker stop $CONTAINER_NAME' to stop"
            exit 0
        else
            echo "📺 Following logs (Press Ctrl+C to stop and remove container)..."
            docker logs -f "$CONTAINER_NAME"
        fi
    else
        echo "❌ Container stopped unexpectedly. Showing logs:"
        docker logs "$CONTAINER_NAME"
        exit 1
    fi
else
    echo "❌ Failed to start container"
    exit 1
fi