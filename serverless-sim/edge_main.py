#!/usr/bin/env python3
"""
Edge Node Entry Point
Runs the edge node with API layer and resource layer
Can be deployed on a separate computer within the network
"""

import sys
import argparse
import logging
import os
import time
import socket
from flask import Flask
from flask_cors import CORS

# Add the parent directory to sys.path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from edge_node.api_layer.edge_route import register_edge_route, initialize_edge_route
from config import Config

def create_edge_node_app(node_id: str, central_node_url: str, node_port: int, edge_node_url: str):
    """Create Flask app for edge node"""
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Initialize and register edge node API
    initialize_edge_route(node_id, central_node_url, node_port, edge_node_url)
    register_edge_route(app)

    return app

def setup_logging(log_level: str = "INFO", node_id: str = "edge"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'{node_id}.log')
        ]
    )

def get_local_ip():
    """Get the local IP address of this machine"""
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        return local_ip
    except Exception:
        return "127.0.0.1"

def validate_central_node_connection(central_url: str, timeout: int = 10):
    """Validate connection to central node"""
    import requests
    try:
        health_url = f"{central_url}/api/v1/central/health"
        response = requests.get(health_url, timeout=timeout)
        if response.status_code == 200:
            return True, "Connected successfully"
        else:
            return False, f"Central node returned status {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to central node"
    except requests.exceptions.Timeout:
        return False, "Connection timeout"
    except Exception as e:
        return False, f"Connection error: {str(e)}"

def auto_detect_port(preferred_port: int, max_attempts: int = 20):
    """Auto-detect available port starting from preferred port"""
    for i in range(max_attempts):
        port = preferred_port + i
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    return None

def main():
    parser = argparse.ArgumentParser(description='Serverless Edge Node (Cloudlet)')
    parser.add_argument('--node-id', type=str, required=True,
                       help='Unique edge node identifier (required)')
    parser.add_argument('--central-url', type=str, required=True,
                       help='Central node URL (required, e.g., http://192.168.1.100:5001)')
    parser.add_argument('--port', type=int, default=None,
                       help='Port to run on (auto-detect if not specified)')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--debug', action='store_true', default=False,
                       help='Enable debug mode')
    parser.add_argument('--log-level', type=str, default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    parser.add_argument('--auto-register', action='store_true', default=True,
                       help='Automatically register with central node (default: True)')
    parser.add_argument('--retry-connection', type=int, default=3,
                       help='Number of connection retry attempts (default: 3)')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.node_id)
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("STARTING SERVERLESS EDGE NODE (CLOUDLET)")
    logger.info("=" * 60)
    logger.info(f"Node ID: {args.node_id}")
    logger.info(f"Central Node URL: {args.central_url}")
    logger.info(f"Host: {args.host}")
    
    # Auto-detect port if not specified
    if args.port is None:
        args.port = auto_detect_port(Config.EDGE_NODE_PORT_RANGE[0])
        if args.port is None:
            logger.error("Could not find an available port")
            sys.exit(1)
        logger.info(f"Auto-detected port: {args.port}")
    else:
        logger.info(f"Port: {args.port}")
    
    logger.info(f"Debug Mode: {args.debug}")
    logger.info(f"Log Level: {args.log_level}")
    
    # Get local IP for registration
    local_ip = get_local_ip()
    logger.info(f"Local IP: {local_ip}")
    
    # Validate central node connection
    logger.info("Validating connection to central node...")
    for attempt in range(args.retry_connection):
        is_connected, message = validate_central_node_connection(args.central_url)
        if is_connected:
            logger.info(f"✓ Central node connection: {message}")
            break
        else:
            logger.warning(f"✗ Attempt {attempt + 1}/{args.retry_connection}: {message}")
            if attempt < args.retry_connection - 1:
                logger.info("Retrying in 5 seconds...")
                time.sleep(5)
    else:
        logger.error("Failed to connect to central node after all attempts")
        logger.error("Please ensure:")
        logger.error("  1. Central node is running")
        logger.error("  2. Central node URL is correct")
        logger.error("  3. Network connectivity exists")
        sys.exit(1)
    
    # Create edge node app
    logger.info("Initializing edge node...")
    app = create_edge_node_app(args.node_id, args.central_url, args.port, local_ip)

    logger.info("Edge Node components:")
    logger.info("  ✓ API Layer (Container execution, request handling)")
    logger.info("  ✓ Resource Layer (Docker management, system metrics)")
    logger.info("  ✓ Metrics reporting (every 10 seconds)")
    logger.info("  ✓ Automatic registration with central node")
    
    logger.info("-" * 60)
    logger.info("Edge Node endpoints:")
    logger.info("  • Execute Function: http://{}:{}/api/v1/edge/execute".format(local_ip, args.port))
    logger.info("  • Node Status: http://{}:{}/api/v1/edge/status".format(local_ip, args.port))
    logger.info("  • Health Check: http://{}:{}/api/v1/edge/health".format(local_ip, args.port))
    logger.info("  • Container List: http://{}:{}/api/v1/edge/containers".format(local_ip, args.port))
    logger.info("-" * 60)
    from edge_node.api_layer.edge_route import edge_node_api_agent
    # Start metrics reporting
    if args.auto_register:
        logger.info("Starting metrics reporting and registration...")
        if edge_node_api_agent:
            edge_node_api_agent.start_metrics_reporting()
            logger.info("✓ Metrics reporting started")
        else:
            logger.warning("Failed to start metrics reporting")
    
    # Start the Flask application
    try:
        logger.info("Starting Edge Node server...")
        logger.info(f"Edge Node {args.node_id} is ready to accept requests!")

        if edge_node_api_agent:
            edge_node_api_agent.start_cleanup_containers()
            logger.info("✓ Cleanup started")
        else:
            logger.warning("Failed to start cleanup")

        app.run(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        logger.info("Edge Node shutting down...")
        # Stop metrics reporting
        if edge_node_api_agent:
            edge_node_api_agent.stop_metrics_reporting()
            logger.info("Metrics reporting stopped")
            edge_node_api_agent.stop_cleanup_containers()
            logger.info("Cleanup stopped")
    except Exception as e:
        logger.error(f"Failed to start Edge Node: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
