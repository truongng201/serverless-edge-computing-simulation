#!/bin/bash

# Experiment Runner for Serverless Edge Computing Simulation
# Usage: ./run_experiment.sh [options]

set -e  # Exit on any error

# Default values
CENTRAL_URL="http://localhost:8000"
EXPERIMENT_TYPE="quick"
USERS="100 500 1000"
EDGES="10 25 50 100"
PYTHON_CMD="python3"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Help function
show_help() {
    cat << EOF
Serverless Edge Computing Experiment Runner

Usage: $0 [OPTIONS]

OPTIONS:
    -h, --help              Show this help message
    -u, --url URL          Central node URL (default: http://localhost:8000)
    -t, --type TYPE        Experiment type: quick|full|custom (default: quick)
    --users "LIST"         Space-separated list of user counts (default: "100 500 1000")
    --edges "LIST"         Space-separated list of edge counts (default: "10 25 50 100") 
    --python CMD           Python command to use (default: python3)

EXPERIMENT TYPES:
    quick                  Run quick comparison (3 configs, both algorithms)
    full                   Run comprehensive experiments with all combinations
    custom                 Use custom user/edge ranges

EXAMPLES:
    # Quick test with default settings
    $0

    # Quick test with different central node URL
    $0 --url http://192.168.1.100:8000

    # Full comprehensive test
    $0 --type full

    # Custom ranges
    $0 --type custom --users "50 100 200" --edges "5 10 20"

PREREQUISITES:
    1. Central node must be running at the specified URL
    2. Python 3 with required packages (requests, etc.)
    3. Proper permissions to write result files

EOF
}

# Check if python is available
check_python() {
    if ! command -v "$PYTHON_CMD" &> /dev/null; then
        echo -e "${RED}Error: $PYTHON_CMD not found${NC}"
        echo "Please install Python 3 or specify different command with --python"
        exit 1
    fi
    
    echo -e "${GREEN}✓${NC} Python check passed: $($PYTHON_CMD --version)"
}

# Check if central node is reachable
check_central_node() {
    echo -e "${BLUE}Checking central node at $CENTRAL_URL...${NC}"
    
    if curl -f -s "$CENTRAL_URL/api/v1/central/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Central node is reachable and healthy"
        return 0
    else
        echo -e "${RED}✗${NC} Central node not reachable at $CENTRAL_URL"
        echo "Please ensure the central node is running:"
        echo "  cd /path/to/serverless-sim"
        echo "  ./deploy_central.sh"
        return 1
    fi
}

# Check required Python packages
check_dependencies() {
    echo -e "${BLUE}Checking Python dependencies...${NC}"
    
    if $PYTHON_CMD -c "import requests" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} requests package available"
    else
        echo -e "${YELLOW}⚠${NC}  requests package not found, installing..."
        pip3 install requests
    fi
}

# Run the experiment
run_experiment() {
    local script_name="simple_experiment_runner.py"
    
    if [[ ! -f "$script_name" ]]; then
        echo -e "${RED}Error: $script_name not found${NC}"
        echo "Please run this script from the serverless-sim directory"
        exit 1
    fi
    
    echo -e "${BLUE}Starting experiment runner...${NC}"
    echo "Type: $EXPERIMENT_TYPE"
    echo "Central URL: $CENTRAL_URL"
    
    case "$EXPERIMENT_TYPE" in
        "quick")
            echo -e "${GREEN}Running quick comparison experiment...${NC}"
            $PYTHON_CMD "$script_name" --central-url "$CENTRAL_URL" --quick
            ;;
        "full") 
            echo -e "${GREEN}Running comprehensive experiments...${NC}"
            $PYTHON_CMD "$script_name" --central-url "$CENTRAL_URL" \
                --users 100 200 300 500 750 1000 \
                --edges 10 20 30 50 75 100
            ;;
        "custom")
            echo -e "${GREEN}Running custom experiments...${NC}"
            echo "Users: $USERS"
            echo "Edges: $EDGES"
            $PYTHON_CMD "$script_name" --central-url "$CENTRAL_URL" \
                --users $USERS --edges $EDGES
            ;;
        *)
            echo -e "${RED}Error: Invalid experiment type: $EXPERIMENT_TYPE${NC}"
            exit 1
            ;;
    esac
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -u|--url)
            CENTRAL_URL="$2"
            shift 2
            ;;
        -t|--type)
            EXPERIMENT_TYPE="$2"
            shift 2
            ;;
        --users)
            USERS="$2"
            shift 2
            ;;
        --edges)
            EDGES="$2"
            shift 2
            ;;
        --python)
            PYTHON_CMD="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Main execution
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Serverless Edge Computing Experiment Runner${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
    
    # Perform checks
    check_python
    check_dependencies
    
    if ! check_central_node; then
        echo
        echo -e "${YELLOW}To start the central node:${NC}"
        echo "  cd $(pwd)"
        echo "  ./deploy_central.sh"
        echo
        echo "Then run this experiment script again."
        exit 1
    fi
    
    echo
    
    # Run experiment
    run_experiment
    
    echo
    echo -e "${GREEN}✓ Experiments completed!${NC}"
    echo "Results saved to CSV files in current directory"
    echo "Check the log output above for detailed results"
}

# Handle interrupts
trap 'echo -e "\n${YELLOW}Experiment interrupted by user${NC}"; exit 1' INT

# Run main function
main