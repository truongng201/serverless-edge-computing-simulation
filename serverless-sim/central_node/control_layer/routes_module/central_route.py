import logging
import time
from typing import Optional
from flask import Blueprint, request, jsonify, Flask

from config import Config

from central_node.control_layer.controller_module.central_core_controller import CentralCoreController

central_route = Blueprint('central_route', __name__, url_prefix=Config.CENTRAL_ROUTE_PREFIX)

# Global instance (will be initialized by the central node app)
central_core_controller: Optional[CentralCoreController] = None

def initialize_central_route():
    """Initialize the central node API"""
    global central_core_controller
    central_core_controller = CentralCoreController()
    return central_core_controller

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

    result = central_core_controller.schedule_request(data)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@central_route.route('/nodes/register', methods=['POST'])
def register_node():
    data = request.get_json()
    if not data or "node_id" not in data:
        return jsonify({"success": False, "error": "Invalid node data"}), 400
        
    result = central_core_controller.register_edge_node(data)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@central_route.route('/nodes/<node_id>/metrics', methods=['POST'])
def update_metrics(node_id):
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No metrics data provided"}), 400
        
    result = central_core_controller.update_node_metrics(node_id, data)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@central_route.route('/cluster/status', methods=['GET'])
def get_cluster_status():
    result = central_core_controller.get_cluster_status()
    status_code = 200 if result["success"] else 500
    return jsonify(result), status_code

@central_route.route('/predict/<node_id>', methods=['GET'])
def predict_workload(node_id):
    horizon = request.args.get('horizon', default=30, type=int)
    result = central_core_controller.predict_workload(node_id, horizon)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@central_route.route("/update_edge_node", methods=["POST"])
def update_edge_node():
    node_data = request.get_json()
    result = central_core_controller.update_edge_node(node_data)
    if result:
        return jsonify({"status": "success", "message": "Update edge node success"}), 200
    else:
        return jsonify({"status": "error", "message": "Edge node update failed"}), 400
    
@central_route.route("/create_user_node", methods=["POST"])
def create_user_node():
    user_data = request.get_json()
    result = central_core_controller.create_user_node(user_data)
    if result:
        return jsonify({"status": "success", "message": "Node user creation success"}), 201
    else:
        return jsonify({"status": "error", "message": "Node User creation failed"}), 400

@central_route.route("/get_all_users", methods=["GET"])
def get_all_users():
    """Get all user nodes"""
    result = central_core_controller.get_all_users()
    status_code = 200 if result["success"] else 500
    return jsonify(result), status_code

@central_route.route('/health', methods=['GET'])
def health_check():
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