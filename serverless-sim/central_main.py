#!/usr/bin/env python3
"""
Central Node Entry Point
Runs the central node with control layer, API layer, and resource layer
"""

import sys
import argparse
import logging
import os
from flask import Flask
from flask_cors import CORS

# Add the parent directory to sys.path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from central_node.api_layer.central_api import register_central_api
from config import Config

def create_central_node_app():
    """Create Flask app for central node"""
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Register central node API (includes UI handler)
    register_central_api(app)
    
    return app

def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('central_node.log')
        ]
    )

def main():
    parser = argparse.ArgumentParser(description='Serverless Central Node')
    parser.add_argument('--port', type=int, default=Config.CENTRAL_NODE_PORT,
                       help='Port to run on (default: 5001)')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode')
    parser.add_argument('--log-level', type=str, default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    parser.add_argument('--config', type=str, default=None,
                       help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("STARTING SERVERLESS CENTRAL NODE")
    logger.info("=" * 60)
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Debug Mode: {args.debug}")
    logger.info(f"Log Level: {args.log_level}")
    
    # Create central node app
    app = create_central_node_app()
    
    logger.info("Central Node components:")
    logger.info("  ✓ Control Layer (Scheduler, Prediction, Migration, Metrics, Graph, UI, Data)")
    logger.info("  ✓ API Layer (REST endpoints)")
    logger.info("  ✓ Resource Layer (Docker management)")
    logger.info("  ✓ Legacy UI Compatibility (Integrated)")
    
    logger.info("-" * 60)
    logger.info("Available endpoints:")
    logger.info("  • Simulation UI: http://{}:{}".format(args.host, args.port))
    logger.info("  • Central API: http://{}:{}/api/v1/central".format(args.host, args.port))
    logger.info("  • Legacy UI Data: http://{}:{}/get_sample".format(args.host, args.port))
    logger.info("  • Health Check: http://{}:{}/api/v1/central/health".format(args.host, args.port))
    logger.info("  • Cluster Status: http://{}:{}/api/v1/central/cluster/status".format(args.host, args.port))
    logger.info("-" * 60)
    
    # Start the Flask application
    try:
        logger.info("Starting Central Node server...")
        app.run(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        logger.info("Central Node shutting down...")
    except Exception as e:
        logger.error(f"Failed to start Central Node: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
