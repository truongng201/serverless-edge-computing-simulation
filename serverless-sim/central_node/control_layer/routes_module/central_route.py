import logging
import time
from typing import Optional
from flask import Blueprint, request, jsonify, Flask

from config import Config

from central_node.control_layer.controller_module.CentralCoreController import CentralCoreController
from shared.standard_response import standard_response

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


@central_route.route('/nodes/register', methods=['POST'])
@standard_response
def register_node():
    request_data = request.get_json()
    result = central_core_controller.register_edge_node(request_data)
    return result


@central_route.route('/nodes/<node_id>/metrics', methods=['POST'])
def update_metrics(node_id):
    request_data = request.get_json()
    result = central_core_controller.update_node_metrics(node_id, request_data)
    return result


@central_route.route('/cluster/status', methods=['GET'])
@standard_response
def get_cluster_status():
    result = central_core_controller.get_cluster_status()
    return result


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


@central_route.route("/update_user_node", methods=["POST"])
def update_user_node():
    """Update user node location and recalculate assigned node"""
    user_data = request.get_json()
    if not user_data:
        return jsonify({"status": "error", "message": "No user data provided"}), 400
    
    result = central_core_controller.update_user_node(user_data)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code


@central_route.route("/get_all_users", methods=["GET"])
def get_all_users():
    """Get all user nodes"""
    result = central_core_controller.get_all_users()
    status_code = 200 if result["success"] else 500
    return jsonify(result), status_code

@central_route.route("/delete_all_users", methods=["DELETE"])
def delete_all_users():
    result = central_core_controller.delete_all_users()
    status_code = 200 if result["success"] else 500
    return jsonify(result), status_code

@central_route.route('/delete_user/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    result = central_core_controller.delete_user(user_id)
    status_code = 200 if result["success"] else 500
    return jsonify(result), status_code

@central_route.route('/execute', methods=['POST'])
def execute_function():
    if not central_core_controller:
        return jsonify({"success": False, "error": "Central node not initialized"}), 500
        
    data = request.get_json()
    result = central_core_controller.execute_function(data)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@central_route.route('/get_dact_sample', methods=['GET'])
def get_dact_sample():
    if not central_core_controller:
        return jsonify({"success": False, "error": "Central node not initialized"}), 500
    result = central_core_controller.get_dact_sample()
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@central_route.route('/get_vehicles_sample', methods=['GET'])
def get_vehicles_sample():
    if not central_core_controller:
        return jsonify({"success": False, "error": "Central node not initialized"}), 500
    result = central_core_controller.get_vehicles_sample()
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@central_route.route('/start_simulation', methods=['POST'])
def start_simulation():
    if not central_core_controller:
        return jsonify({"success": False, "error": "Central node not initialized"}), 500
    result = central_core_controller.start_simulation()
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@central_route.route('/stop_simulation', methods=['POST'])
def stop_simulation():
    if not central_core_controller:
        return jsonify({"success": False, "error": "Central node not initialized"}), 500
    result = central_core_controller.stop_simulation()
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@central_route.route('/set_scheduling_strategy', methods=['POST'])
def set_scheduling_strategy():
    """Set the scheduling strategy"""
    if not central_core_controller:
        return jsonify({"success": False, "error": "Central node not initialized"}), 500
    
    data = request.get_json()
    strategy = data.get('strategy', 'round_robin')
    
    result = central_core_controller.set_scheduling_strategy(strategy)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code

@central_route.route('/get_scheduling_strategy', methods=['GET'])
def get_scheduling_strategy():
    """Get current scheduling strategy"""
    if not central_core_controller:
        return jsonify({"success": False, "error": "Central node not initialized"}), 500
    
    result = central_core_controller.get_scheduling_strategy()
    return jsonify(result), 200

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