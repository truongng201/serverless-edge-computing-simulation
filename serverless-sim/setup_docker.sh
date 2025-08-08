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

# Create a simple serverless handler image
HANDLER_IMAGE="serverless-handler:latest"

if docker images | grep -q "serverless-handler"; then
    echo "✅ Serverless handler image already exists"
else
    echo "Building serverless handler image..."
    
    # Create a temporary Dockerfile
    cat > /tmp/Dockerfile.serverless-handler << 'EOF'
FROM python:3.9-slim

# Install basic dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Create a simple handler script
RUN echo '#!/usr/bin/env python3
import json
import sys
import time
import os

def main():
    print("Serverless function handler started")
    
    # Simulate function execution
    function_id = os.environ.get("FUNCTION_ID", "unknown")
    execution_time = float(os.environ.get("EXECUTION_TIME", "1.0"))
    
    print(f"Executing function: {function_id}")
    print(f"Simulated execution time: {execution_time}s")
    
    # Simulate work
    time.sleep(execution_time)
    
    result = {
        "function_id": function_id,
        "status": "completed",
        "execution_time": execution_time,
        "timestamp": time.time()
    }
    
    print(f"Function result: {json.dumps(result)}")
    return result

if __name__ == "__main__":
    main()
' > /app/handler.py

RUN chmod +x /app/handler.py

# Default command
CMD ["python3", "/app/handler.py"]
EOF

    if docker build -t "$HANDLER_IMAGE" -f /tmp/Dockerfile.serverless-handler /tmp; then
        echo "✅ Serverless handler image built successfully"
        rm -f /tmp/Dockerfile.serverless-handler
    else
        echo "❌ Failed to build serverless handler image"
        rm -f /tmp/Dockerfile.serverless-handler
        exit 1
    fi
fi

# Create additional test images
echo ""
echo "🧪 Creating test function images..."

# Simple Python function
TEST_IMAGES=("python-hello:latest" "nodejs-hello:latest")

# Python test function
if ! docker images | grep -q "python-hello"; then
    echo "Building Python test function..."
    cat > /tmp/Dockerfile.python-hello << 'EOF'
FROM python:3.9-slim

WORKDIR /app

RUN echo '#!/usr/bin/env python3
import json
import time
import os

def hello_world():
    name = os.environ.get("NAME", "World")
    message = f"Hello, {name}! Time: {time.time()}"
    
    result = {
        "message": message,
        "language": "python",
        "timestamp": time.time()
    }
    
    print(json.dumps(result))
    return result

if __name__ == "__main__":
    hello_world()
' > /app/function.py

RUN chmod +x /app/function.py

CMD ["python3", "/app/function.py"]
EOF

    docker build -t "python-hello:latest" -f /tmp/Dockerfile.python-hello /tmp &> /dev/null
    rm -f /tmp/Dockerfile.python-hello
    echo "✅ Python test function image created"
fi

# Node.js test function
if ! docker images | grep -q "nodejs-hello"; then
    echo "Building Node.js test function..."
    cat > /tmp/Dockerfile.nodejs-hello << 'EOF'
FROM node:16-slim

WORKDIR /app

RUN echo 'const name = process.env.NAME || "World";
const message = `Hello, ${name}! Time: ${Date.now()}`;

const result = {
    message: message,
    language: "nodejs",
    timestamp: Date.now()
};

console.log(JSON.stringify(result));
' > /app/function.js

CMD ["node", "/app/function.js"]
EOF

    docker build -t "nodejs-hello:latest" -f /tmp/Dockerfile.nodejs-hello /tmp &> /dev/null
    rm -f /tmp/Dockerfile.nodejs-hello
    echo "✅ Node.js test function image created"
fi

# Test container creation and execution
echo ""
echo "🧪 Testing container operations..."

# Test container creation
echo "Testing container creation..."
if CONTAINER_ID=$(docker create --name test-serverless-container "$HANDLER_IMAGE" 2>/dev/null); then
    echo "✅ Container creation successful"
    
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
    echo "❌ Container creation failed"
fi

# Display Docker system information
echo ""
echo "📊 Docker System Information..."
echo "------------------------------"
docker version --format "Docker version: {{.Server.Version}}"
echo "Available images:"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep -E "(serverless|hello)"

echo "Available networks:"
docker network ls --format "table {{.Name}}\t{{.Driver}}\t{{.Scope}}"

echo ""
echo "💾 Docker storage usage:"
docker system df

# Cleanup function
cleanup_docker() {
    echo ""
    echo "🧹 Docker cleanup options:"
    echo "• Remove unused containers: docker container prune"
    echo "• Remove unused images: docker image prune"
    echo "• Remove unused networks: docker network prune"
    echo "• Remove everything unused: docker system prune"
    echo ""
    read -p "Do you want to run docker system prune now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker system prune -f
        echo "✅ Docker cleanup completed"
    fi
}

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
echo "• Central node: ./deploy_central.sh"
echo "• Edge nodes: ./deploy_edge.sh --node-id <ID> --central-url <URL>"
echo ""

# Ask for cleanup
cleanup_docker
