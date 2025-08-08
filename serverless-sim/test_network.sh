#!/bin/bash
# Network Testing Script for Serverless Edge Computing Simulation

echo "========================================"
echo "SERVERLESS NETWORK CONNECTIVITY TESTER"
echo "========================================"

# Function to test HTTP connectivity
test_http_connection() {
    local url=$1
    local description=$2
    
    echo -n "Testing $description... "
    
    if command -v curl &> /dev/null; then
        if curl -s --connect-timeout 5 --max-time 10 "$url" > /dev/null 2>&1; then
            echo "✅ SUCCESS"
            return 0
        else
            echo "❌ FAILED"
            return 1
        fi
    else
        echo "⚠️  curl not found"
        return 1
    fi
}

# Function to test port connectivity
test_port_connection() {
    local host=$1
    local port=$2
    local description=$3
    
    echo -n "Testing $description ($host:$port)... "
    
    if command -v nc &> /dev/null; then
        if nc -z -w5 "$host" "$port" 2>/dev/null; then
            echo "✅ SUCCESS"
            return 0
        else
            echo "❌ FAILED"
            return 1
        fi
    elif command -v telnet &> /dev/null; then
        if timeout 5 telnet "$host" "$port" 2>/dev/null | grep -q "Connected"; then
            echo "✅ SUCCESS"
            return 0
        else
            echo "❌ FAILED"
            return 1
        fi
    else
        echo "⚠️  nc/telnet not found"
        return 1
    fi
}

# Parse command line arguments
CENTRAL_IP=""
CENTRAL_PORT="5001"
EDGE_IPS=()

usage() {
    echo "Usage: $0 --central-ip <IP> [--central-port <PORT>] [--edge-ip <IP1>] [--edge-ip <IP2>] ..."
    echo ""
    echo "Options:"
    echo "  --central-ip <IP>     Central node IP address (required)"
    echo "  --central-port <PORT> Central node port (default: 5001)"
    echo "  --edge-ip <IP>        Edge node IP address (can be specified multiple times)"
    echo "  --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --central-ip 192.168.1.100"
    echo "  $0 --central-ip 192.168.1.100 --edge-ip 192.168.1.101 --edge-ip 192.168.1.102"
    echo "  $0 --central-ip 10.0.0.50 --central-port 8001 --edge-ip 10.0.0.51"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --central-ip)
            CENTRAL_IP="$2"
            shift 2
            ;;
        --central-port)
            CENTRAL_PORT="$2"
            shift 2
            ;;
        --edge-ip)
            EDGE_IPS+=("$2")
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

if [[ -z "$CENTRAL_IP" ]]; then
    echo "❌ Error: --central-ip is required"
    echo ""
    usage
    exit 1
fi

echo "Configuration:"
echo "  Central Node: $CENTRAL_IP:$CENTRAL_PORT"
if [[ ${#EDGE_IPS[@]} -gt 0 ]]; then
    echo "  Edge Nodes: ${EDGE_IPS[*]}"
else
    echo "  Edge Nodes: None specified"
fi
echo ""

# Test central node
echo "🔍 Testing Central Node Connectivity..."
echo "----------------------------------------"

# Test basic port connectivity
test_port_connection "$CENTRAL_IP" "$CENTRAL_PORT" "Central node port"

# Test HTTP health endpoint
test_http_connection "http://$CENTRAL_IP:$CENTRAL_PORT/api/v1/central/health" "Central node health endpoint"

# Test simulation UI
test_http_connection "http://$CENTRAL_IP:$CENTRAL_PORT/" "Simulation UI"

echo ""

# Test edge nodes if specified
if [[ ${#EDGE_IPS[@]} -gt 0 ]]; then
    echo "🔍 Testing Edge Node Connectivity..."
    echo "------------------------------------"
    
    for edge_ip in "${EDGE_IPS[@]}"; do
        echo "Testing edge node: $edge_ip"
        
        # Try common edge node ports
        edge_ports=(5002 5003 5004 5005 5006 5007 5008 5009 5010)
        found_port=false
        
        for port in "${edge_ports[@]}"; do
            if test_port_connection "$edge_ip" "$port" "Edge port $port" >/dev/null 2>&1; then
                echo "  ✅ Found edge node on port $port"
                test_http_connection "http://$edge_ip:$port/api/v1/edge/health" "  Edge health endpoint"
                found_port=true
                break
            fi
        done
        
        if [[ "$found_port" == false ]]; then
            echo "  ❌ No edge node found on common ports"
        fi
        
        echo ""
    done
fi

# Test Docker connectivity
echo "🐳 Testing Docker..."
echo "-------------------"
if command -v docker &> /dev/null; then
    if docker info &> /dev/null; then
        echo "✅ Docker is running and accessible"
        
        # Test Docker network
        if docker network ls | grep -q "serverless-network"; then
            echo "✅ Serverless network exists"
        else
            echo "⚠️  Serverless network not found (will be created automatically)"
        fi
    else
        echo "❌ Docker is installed but not running"
    fi
else
    echo "❌ Docker is not installed"
fi

echo ""

# Network information
echo "🌐 Network Information..."
echo "------------------------"

# Get local IP
if command -v hostname &> /dev/null; then
    LOCAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null)
    if [[ -n "$LOCAL_IP" ]]; then
        echo "Local IP: $LOCAL_IP"
    fi
fi

# Test internet connectivity
echo -n "Internet connectivity... "
if ping -c 1 8.8.8.8 &> /dev/null; then
    echo "✅ Available"
else
    echo "❌ Not available"
fi

# DNS resolution
echo -n "DNS resolution... "
if nslookup google.com &> /dev/null; then
    echo "✅ Working"
else
    echo "❌ Not working"
fi

echo ""

# Summary and recommendations
echo "📋 Summary and Recommendations..."
echo "--------------------------------"

echo "✅ Successfully completed network connectivity test"
echo ""

echo "Next steps:"
echo "1. Deploy central node: ./deploy_central.sh"
echo "2. Deploy edge nodes: ./deploy_edge.sh --node-id <ID> --central-url http://$CENTRAL_IP:$CENTRAL_PORT"
echo "3. Verify deployment: curl http://$CENTRAL_IP:$CENTRAL_PORT/api/v1/central/cluster/status"
echo ""

echo "Troubleshooting tips:"
echo "• If connections fail, check firewall settings"
echo "• Ensure all machines are on the same network"
echo "• Verify IP addresses are correct"
echo "• Check that required ports are not blocked"
