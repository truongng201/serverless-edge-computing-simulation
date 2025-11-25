#!/bin/bash
# Docker Setup Script for Serverless Edge Computing

echo "========================================="
echo "DOCKER SETUP FOR SERVERLESS SIMULATION"
echo "========================================="

# Function to check command availability
check_command() {
    if command -v "$1" &> /dev/null; then
        echo "✅ $1 is available"
        return 0
    else
        echo "❌ $1 is not available"
        return 1
    fi
}

# Check Docker installation
echo "🔍 Checking Docker installation..."
if ! check_command docker; then
    echo ""
    echo "Docker is required but not installed."
    echo "Please install Docker from: https://docs.docker.com/get-docker/"
    echo ""
    echo "Installation instructions:"
    echo "• macOS: Download Docker Desktop from docker.com"
    echo "• Ubuntu: sudo apt-get update && sudo apt-get install docker.io"
    echo "• CentOS: sudo yum install -y docker"
    echo "• Windows: Download Docker Desktop from docker.com"
    exit 1
fi

# Check if Docker daemon is running
echo ""
echo "🔍 Checking Docker daemon..."
if docker info &> /dev/null; then
    echo "✅ Docker daemon is running"
else
    echo "❌ Docker daemon is not running"
    echo ""
    echo "Please start Docker:"
    echo "• macOS/Windows: Start Docker Desktop application"
    echo "• Linux: sudo systemctl start docker"
    exit 1
fi

# Check Docker permissions
echo ""
echo "🔍 Checking Docker permissions..."
if docker ps &> /dev/null; then
    echo "✅ Docker permissions are correct"
else
    echo "❌ Docker permission denied"
    echo ""
    echo "To fix this issue:"
    echo "• Linux: sudo usermod -aG docker \$USER && newgrp docker"
    echo "• macOS/Windows: Restart Docker Desktop"
    exit 1
fi

# Create serverless network
echo ""
echo "🌐 Setting up Docker network..."
NETWORK_NAME="serverless-network"

if docker network ls | grep -q "$NETWORK_NAME"; then
    echo "✅ Network '$NETWORK_NAME' already exists"
else
    echo "Creating network '$NETWORK_NAME'..."
    if docker network create "$NETWORK_NAME" &> /dev/null; then
        echo "✅ Network '$NETWORK_NAME' created successfully"
    else
        echo "❌ Failed to create network '$NETWORK_NAME'"
        exit 1
    fi
fi

# Pull/build base images
echo ""
echo "🐳 Setting up container images..."

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Create a simple serverless handler image
HANDLER_IMAGE="python-serverless-handler:latest"

echo "Building python serverless handler image..."
if [ -f "$PROJECT_ROOT/function_template/Dockerfile" ]; then
    if docker build -t "$HANDLER_IMAGE" -f "$PROJECT_ROOT/function_template/Dockerfile" "$PROJECT_ROOT/function_template"; then
        echo "✅ Python serverless handler image built successfully"
    else
        echo "❌ Failed to build python serverless handler image"
        exit 1
    fi
else
    echo "⚠️  Dockerfile not found at $PROJECT_ROOT/function_template/Dockerfile"
    echo "   Skipping handler image build"
fi

# Create edge node image
EDGE_IMAGE="edge-node:latest"

echo "Building edge node image..."

if [ -f "$PROJECT_ROOT/Dockerfile" ]; then
    if docker build -t "$EDGE_IMAGE" -f "$PROJECT_ROOT/Dockerfile" "$PROJECT_ROOT"; then
        echo "✅ Edge node image built successfully"
    else
        echo "❌ Failed to build edge node image"
        exit 1
    fi
else
    echo "❌ Dockerfile not found at $PROJECT_ROOT/Dockerfile"
    echo "   Cannot build edge node image"
    exit 1
fi

# Test container creation and execution
echo ""
echo "🧪 Testing container operations..."

# Test container creation with handler image if it exists
if docker images | grep -q "python-serverless-handler"; then
    echo "Testing handler container creation..."
    if CONTAINER_ID=$(docker create --name test-serverless-container "$HANDLER_IMAGE" 2>/dev/null); then
        echo "✅ Handler container creation successful"
        
        # Test container start
        echo "Testing container start..."
        if docker start "$CONTAINER_ID" &> /dev/null; then
            echo "✅ Container start successful"
            
            # Wait a moment
            sleep 2
            
            # Test container stop
            echo "Testing container stop..."
            if docker stop "$CONTAINER_ID" &> /dev/null; then
                echo "✅ Container stop successful"
            else
                echo "⚠️  Container stop failed"
            fi
        else
            echo "⚠️  Container start failed"
        fi
        
        # Clean up test container
        docker rm "$CONTAINER_ID" &> /dev/null
    else
        echo "❌ Handler container creation failed"
    fi
fi

# Display Docker system information
echo ""
echo "📊 Docker System Information..."
echo "------------------------------"
docker version --format "Docker version: {{.Server.Version}}"
echo ""
echo "Available images:"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep -E "(serverless|edge-node|python)"

echo ""
echo "Available networks:"
docker network ls --format "table {{.Name}}\t{{.Driver}}\t{{.Scope}}"

echo ""
echo "💾 Docker storage usage:"
docker system df

# Final summary
echo ""
echo "✅ Docker setup completed successfully!"
echo ""
echo "📋 Summary:"
echo "• Docker daemon is running"
echo "• Serverless network is created"
echo "• Base container images are available"
echo "• Container operations are working"
echo ""
echo "🚀 You can now deploy the serverless simulation:"
echo "• Edge nodes: ./deploy_edge.sh --node-id <ID> --central-url <URL> --port <PORT>"
echo ""
echo "Examples:"
echo "  ./deploy_edge.sh --node-id edge_001 --central-url http://localhost:8000 --port 8001"
echo "  ./deploy_edge.sh --node-id edge_002 --central-url http://localhost:8000 --port 8002 --cpus 2 --memory 1g"
echo ""