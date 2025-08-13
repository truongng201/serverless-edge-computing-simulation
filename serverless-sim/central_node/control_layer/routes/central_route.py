import logging
import time
from typing import Optional
from flask import Blueprint, request, jsonify, Flask

from config import Config

from central_node.api_layer.central_controller import CentralNodeAPIController

central_route = Blueprint('central_route', __name__, url_prefix=Config.CENTRAL_ROUTE_PREFIX)

# Global instance (will be initialized by the central node app)
central_node_api_controller: Optional[CentralNodeAPIController] = None

def initialize_central_route():
    """Initialize the central node API"""
    global central_node_api_controller
    central_node_api_controller = CentralNodeAPIController()
    return central_node_api_controller

def register_central_route(app: Flask):
    """Register the central API blueprint with the Flask app"""
    app.register_blueprint(central_route)
    logging.getLogger(__name__).info("Central API routes registered successfully")

# API Routes
@central_route.route('/schedule', methods=['POST'])
def schedule_request():
    """Schedule a request to an edge node"""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400

    result = central_node_api_controller.schedule_request(data)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@central_route.route('/nodes/register', methods=['POST'])
def register_node():
    """Register a new edge node"""
    data = request.get_json()
    if not data or "node_id" not in data:
        return jsonify({"success": False, "error": "Invalid node data"}), 400
        
    result = central_node_api_controller.register_edge_node(data)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@central_route.route('/nodes/<node_id>/metrics', methods=['POST'])
def update_metrics(node_id):
    """Update metrics for an edge node"""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No metrics data provided"}), 400
        
    result = central_node_api_controller.update_node_metrics(node_id, data)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@central_route.route('/cluster/status', methods=['GET'])
def get_cluster_status():
    """Get cluster status"""
    result = central_node_api_controller.get_cluster_status()
    status_code = 200 if result["success"] else 500
    return jsonify(result), status_code

@central_route.route('/predict/<node_id>', methods=['GET'])
def predict_workload(node_id):
    """Get workload prediction for a node"""
    horizon = request.args.get('horizon', default=30, type=int)
    result = central_node_api_controller.predict_workload(node_id, horizon)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@central_route.route('/metrics/export', methods=['GET'])
def export_metrics():
    """Export metrics data"""
    duration = request.args.get('duration_hours', default=1, type=int)
    format_type = request.args.get('format', default='json', type=str)
    
    try:
        exported_data = central_node_api_controller.metrics_collector.export_metrics(format_type, duration)
        return exported_data, 200, {'Content-Type': 'application/json'}
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@central_route.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "components": {
            "scheduler": "running",
            "predictor": "running",
            "migration_manager": "running",
            "metrics_collector": "running"
        }
    })

@central_route.route('/nodes/cleanup', methods=['POST'])
def cleanup_dead_nodes():
    """Manually trigger cleanup of dead/disconnected nodes"""
    result = central_node_api_controller.cleanup_dead_nodes()
    status_code = 200 if result["success"] else 500
    return jsonify(result), status_code