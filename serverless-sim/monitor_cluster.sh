#!/bin/bash
# Cluster Monitoring Script

echo "========================================="
echo "SERVERLESS CLUSTER MONITORING DASHBOARD"
echo "========================================="

# Default configuration
CENTRAL_URL=""
REFRESH_INTERVAL=5
CONTINUOUS_MODE=false

# Parse command line arguments
usage() {
    echo "Usage: $0 --central-url <URL> [OPTIONS]"
    echo ""
    echo "Required:"
    echo "  --central-url <URL>   Central node URL"
    echo ""
    echo "Options:"
    echo "  --interval <SEC>      Refresh interval in seconds (default: 5)"
    echo "  --continuous          Continuous monitoring mode"
    echo "  --help               Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 --central-url http://192.168.1.100:5001"
    echo "  $0 --central-url http://localhost:5001 --continuous"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --central-url)
            CENTRAL_URL="$2"
            shift 2
            ;;
        --interval)
            REFRESH_INTERVAL="$2"
            shift 2
            ;;
        --continuous)
            CONTINUOUS_MODE=true
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

if [[ -z "$CENTRAL_URL" ]]; then
    echo "Error: --central-url is required"
    usage
    exit 1
fi

# Function to fetch cluster status
get_cluster_status() {
    curl -s "$CENTRAL_URL/api/v1/central/cluster/status" 2>/dev/null
}

# Function to format and display status
display_status() {
    local status_json="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Clear screen in continuous mode
    if [[ "$CONTINUOUS_MODE" == true ]]; then
        clear
    fi
    
    echo "========================================="
    echo "CLUSTER STATUS - $timestamp"
    echo "========================================="
    
    if [[ -z "$status_json" ]]; then
        echo "❌ Failed to connect to central node"
        echo "   URL: $CENTRAL_URL"
        echo "   Please check:"
        echo "   • Central node is running"
        echo "   • URL is correct"
        echo "   • Network connectivity"
        return 1
    fi
    
    # Parse JSON (basic parsing without jq dependency)
    echo "📊 CLUSTER OVERVIEW"
    echo "-------------------"
    
    # Extract basic info using grep and sed
    if echo "$status_json" | grep -q '"success".*true'; then
        echo "✅ Central node: Online"
        
        # Extract node counts
        total_nodes=$(echo "$status_json" | jq -r '.cluster_info.total_nodes // 0')
        healthy_nodes=$(echo "$status_json" | jq -r '.cluster_info.healthy_nodes // 0')

        echo "🖥️  Total nodes: $total_nodes"
        echo "✅ Healthy nodes: $healthy_nodes"
        
        # Calculate unhealthy nodes
        if [[ -n "$total_nodes" && -n "$healthy_nodes" ]]; then
            unhealthy=$((total_nodes - healthy_nodes))
            if [[ $unhealthy -gt 0 ]]; then
                echo "⚠️  Unhealthy nodes: $unhealthy"
            fi
        fi
        
        # Extract container info
        total_containers=$(echo "$status_json" | jq -r '.health.total_containers // 0')
        echo "📦 Total containers: ${total_containers}"
        
        # Extract load info
        echo ""
        echo "📈 PERFORMANCE METRICS"
        echo "---------------------"
        
        # Try to extract CPU usage
        cpu_usage=$(echo "$status_json" | jq -r '.metrics.total_cpu_usage // 0')
        echo "💻 Average CPU usage: ${cpu_usage}%"

        # Try to extract memory usage
        memory_usage=$(echo "$status_json" | jq -r '.metrics.total_memory_usage // 0')
        echo "💾 Average memory usage: ${memory_usage}%"

        # Try to extract energy consumption
        energy=$(echo "$status_json" | jq -r '.metrics.total_energy // 0')
        echo "⚡ Total energy: ${energy} kWh"

        
    else
        echo "❌ Central node: Error"
        echo "Response: $status_json"
    fi
}

# Function to display node details if available
display_node_details() {
    local status_json="$1"
    
    echo ""
    echo "🏢 EDGE NODES"
    echo "-------------"
    
    # This is a simplified display - in a real implementation,
    # you'd parse the JSON properly to show individual node status
    if echo "$status_json" | grep -q '"node_details"'; then
        echo "Individual node details available in full JSON response"
        echo "Use: curl $CENTRAL_URL/api/v1/central/cluster/status | jq"
    else
        echo "No detailed node information available"
    fi
}

# Main monitoring loop
monitor_cluster() {
    local count=0
    
    while true; do
        status_json=$(get_cluster_status)
        display_status "$status_json"
        
        if [[ -n "$status_json" ]]; then
            display_node_details "$status_json"
        fi
        
        echo ""
        echo "🔄 MONITORING INFO"
        echo "------------------"
        echo "Refresh interval: ${REFRESH_INTERVAL}s"
        echo "Updates: $((++count))"
        
        if [[ "$CONTINUOUS_MODE" == true ]]; then
            echo "Press Ctrl+C to stop monitoring"
            echo ""
            sleep "$REFRESH_INTERVAL"
        else
            break
        fi
    done
}

# Test connectivity first
echo "🔍 Testing connection to central node..."
if ! curl -s --connect-timeout 5 "$CENTRAL_URL/api/v1/central/health" >/dev/null; then
    echo "❌ Cannot connect to central node at: $CENTRAL_URL"
    echo ""
    echo "Please ensure:"
    echo "• Central node is running"
    echo "• URL is correct"
    echo "• Network connectivity exists"
    exit 1
fi

echo "✅ Connected to central node"
echo ""

# Start monitoring
monitor_cluster

echo ""
echo "📋 ADDITIONAL COMMANDS"
echo "----------------------"
echo "• Health check: curl $CENTRAL_URL/api/v1/central/health"
echo "• Full status: curl $CENTRAL_URL/api/v1/central/cluster/status | jq"
echo "• Export metrics: curl \"$CENTRAL_URL/api/v1/central/metrics/export?duration_hours=1\""
echo "• Simulation UI: $CENTRAL_URL"
