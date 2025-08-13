import logging
import time
from typing import Optional
from flask import Flask, request, jsonify, Blueprint

from edge_node.api_layer.edge_controller import EdgeNodeAPIController
from config import Config

edge_route = Blueprint('edge_route', __name__, url_prefix=Config.EDGE_ROUTE_PREFIX)

# Global instance (will be initialized by the edge node app)
edge_node_api_controller: Optional[EdgeNodeAPIController] = None

def initialize_edge_route(node_id: str, central_node_url: str):
    """Initialize the edge node API"""
    global edge_node_api_controller
    edge_node_api_controller = EdgeNodeAPIController(node_id, central_node_url)
    return edge_node_api_controller

def register_edge_route(app: Flask):
    """Register the edge API blueprint with the Flask app"""
    app.register_blueprint(edge_route)
    logging.getLogger(__name__).info("Edge API routes registered successfully")

# API Routes
@edge_route.route('/execute', methods=['POST'])
def execute_function():
    """Execute a serverless function"""
    if not edge_node_api_controller:
        return jsonify({"success": False, "error": "Edge node not initialized"}), 500
        
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No function data provided"}), 400
        
    result = edge_node_api_controller.execute_function(data)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@edge_route.route('/status', methods=['GET'])
def get_status():
    """Get edge node status"""
    if not edge_node_api_controller:
        return jsonify({"success": False, "error": "Edge node not initialized"}), 500
        
    status = edge_node_api_controller.get_node_status()
    return jsonify(status)

@edge_route.route('/containers', methods=['GET'])
def list_containers():
    """List containers on this edge node"""
    if not edge_node_api_controller:
        return jsonify({"success": False, "error": "Edge node not initialized"}), 500
        
    containers = edge_node_api_controller.container_manager.list_containers()
    container_list = [
        {
            "container_id": c.container_id,
            "name": c.name,
            "state": c.state.value,
            "created_at": c.created_at,
            "image": c.image
        }
        for c in containers
    ]
    
    return jsonify({"containers": container_list})

@edge_route.route('/containers/<container_id>/stats', methods=['GET'])
def get_container_stats(container_id):
    """Get container statistics"""
    if not edge_node_api_controller:
        return jsonify({"success": False, "error": "Edge node not initialized"}), 500
        
    stats = edge_node_api_controller.container_manager.get_container_stats(container_id)
    if stats:
        return jsonify(stats)
    else:
        return jsonify({"success": False, "error": "Container not found or stats unavailable"}), 404

@edge_route.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "node_id": edge_node_api_controller.node_id if edge_node_api_controller else "unknown"
    })