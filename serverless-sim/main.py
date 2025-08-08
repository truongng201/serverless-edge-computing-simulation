import sys
import argparse
import logging
from flask import Flask
from flask_cors import CORS

from central_node.api_layer.central_api import register_central_api
from edge_node.api_layer.edge_api import register_edge_api, initialize_edge_api
from config import Config, NodeType

def create_central_node_app():
    """Create Flask app for central node"""
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Register existing UI handler (for simulation UI)
    app.register_blueprint(ui_app)
    
    # Register central node API
    register_central_api(app)
    
    return app

def create_edge_node_app(node_id: str, central_node_url: str):
    """Create Flask app for edge node"""
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Initialize and register edge node API
    initialize_edge_api(node_id, central_node_url)
    register_edge_api(app)
    
    return app

def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('serverless_sim.log')
        ]
    )

def main():
    parser = argparse.ArgumentParser(description='Serverless Edge Computing Simulation')
    parser.add_argument('--mode', choices=['central', 'edge'], default='central',
                       help='Node mode: central or edge')
    parser.add_argument('--node-id', type=str, default='edge_001',
                       help='Edge node ID (only for edge mode)')
    parser.add_argument('--central-url', type=str, default='http://localhost:5001',
                       help='Central node URL (only for edge mode)')
    parser.add_argument('--port', type=int, default=None,
                       help='Port to run on (default: 5001 for central, 5002+ for edge)')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='Host to bind to')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode')
    parser.add_argument('--log-level', type=str, default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Determine port
    if args.port is None:
        if args.mode == 'central':
            port = Config.CENTRAL_NODE_PORT
        else:
            port = Config.EDGE_NODE_PORT_RANGE[0]  # Default to first edge port
    else:
        port = args.port
    
    # Create appropriate app
    if args.mode == 'central':
        logger.info("Starting Central Node...")
        app = create_central_node_app()
        logger.info(f"Central Node starting on {args.host}:{port}")
        
    elif args.mode == 'edge':
        logger.info(f"Starting Edge Node: {args.node_id}")
        app = create_edge_node_app(args.node_id, args.central_url)
        logger.info(f"Edge Node {args.node_id} starting on {args.host}:{port}")
        logger.info(f"Will connect to Central Node at: {args.central_url}")
        
        # Start metrics reporting for edge node
        from edge_node.api_layer.edge_api import edge_node_api
        if edge_node_api:
            edge_node_api.start_metrics_reporting()
    
    else:
        logger.error(f"Unknown mode: {args.mode}")
        sys.exit(1)
    
    # Start the Flask application
    try:
        app.run(host=args.host, port=port, debug=args.debug)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        if args.mode == 'edge':
            from edge_node.api_layer.edge_api import edge_node_api
            if edge_node_api:
                edge_node_api.stop_metrics_reporting()
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()