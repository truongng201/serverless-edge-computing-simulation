import logging
import time
from typing import Optional
from flask import Blueprint, request, jsonify, Flask

from config import Config

from central_node.control_layer.controller_module.central_core_controller import CentralCoreController
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

@central_route.route('/health', methods=['GET'])
@standard_response
def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "components": {
            "scheduler": "running",
            "predictor": "running",
            "migration_manager": "running",
            "metrics_collector": "running"
        }
    }

@central_route.route('/nodes/register', methods=['POST'])
@standard_response
def register_node():
    request_data = request.get_json()
    result = central_core_controller.register_edge_node(request_data)
    return result


@central_route.route('/nodes/<node_id>/metrics', methods=['POST'])
@standard_response
def update_metrics(node_id):
    request_data = request.get_json()
    result = central_core_controller.update_node_metrics(node_id, request_data)
    return result


@central_route.route('/cluster/status', methods=['GET'])
@standard_response
def get_cluster_status():
    result = central_core_controller.get_cluster_status()
    return result

@central_route.route('/start_simulation', methods=['POST'])
@standard_response
def start_simulation():
    result = central_core_controller.start_simulation()
    return result

@central_route.route('/stop_simulation', methods=['POST'])
@standard_response
def stop_simulation():
    result = central_core_controller.stop_simulation()
    return result

@central_route.route("/reset_simulation", methods=["POST"])
@standard_response
def reset_simulation():
    result = central_core_controller.reset_simulation()
    return result

@central_route.route("/update_edge_node", methods=["POST"])
@standard_response
def update_edge_node():
    request_data = request.get_json()
    result = central_core_controller.update_edge_node(request_data)
    return result

@central_route.route("/create_user_node", methods=["POST"])
@standard_response
def create_user_node():
    request_data = request.get_json()
    result = central_core_controller.create_user_node(request_data)
    return result

@central_route.route("/update_user_node", methods=["POST"])
@standard_response
def update_user_node():
    request_data = request.get_json()
    result = central_core_controller.update_user_node(request_data)
    return result 

@central_route.route("/update_central_node", methods=["POST"])
@standard_response
def update_central_node():
    request_data = request.get_json()
    result = central_core_controller.update_central_node(request_data)
    return result

@central_route.route("/get_all_users", methods=["GET"])
@standard_response
def get_all_users():
    result = central_core_controller.get_all_users()
    return result

@central_route.route("/delete_all_users", methods=["DELETE"])
@standard_response
def delete_all_users():
    result = central_core_controller.delete_all_users()
    return result

@central_route.route('/delete_user/<user_id>', methods=['DELETE'])
@standard_response
def delete_user(user_id):
    result = central_core_controller.delete_user(user_id)
    return result

@central_route.route('/start_dact_sample', methods=['POST'])
@standard_response
def start_dact_sample():
    result = central_core_controller.start_dact_sample()
    return result

@central_route.route('/start_vehicles_sample', methods=['POST'])
@standard_response
def start_vehicles_sample():
    result = central_core_controller.start_vehicles_sample()
    return result

@central_route.route('/execute', methods=['POST'])
@standard_response
def execute_function():
    request_data = request.get_json()
    result = central_core_controller.execute_function(request_data)
    return result

# Assignment strategy/config endpoints
@central_route.route('/assignment/strategy', methods=['POST'])
@standard_response
def set_assignment_strategy():
    request_data = request.get_json() or {}
    result = central_core_controller.set_assignment_strategy(request_data)
    return result

@central_route.route('/assignment/config', methods=['POST'])
@standard_response
def set_assignment_config():
    request_data = request.get_json() or {}
    result = central_core_controller.update_assignment_config(request_data)
    return result