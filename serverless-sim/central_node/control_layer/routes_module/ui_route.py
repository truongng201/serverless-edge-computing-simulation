import logging

from typing import Optional
from flask import Blueprint, Flask, request, jsonify

from central_node.control_layer.controller_module.ui_controller import UIController

ui_route = Blueprint('ui_route', __name__)

# Global instance (will be initialized by the central node app)
ui_controller: Optional[UIController] = None

def initialize_ui_route():
    """Initialize the UI API"""
    global ui_controller
    ui_controller = UIController()
    return ui_controller

def register_ui_route(app: Flask):
    """Register the UI route blueprint with the Flask app"""
    app.register_blueprint(ui_route)
    logging.getLogger(__name__).info("UI routes registered successfully")

# UI Route definitions
@ui_route.route("/", methods=["GET"])
def home():
    """Home endpoint for simulation UI"""
    return "Welcome to the Serverless Edge Computing Simulation!", 200

@ui_route.route("/sample_data", methods=["GET"])
def get_sample_data():
    """
    Endpoint to receive sample vehicle data by step_id.
    Legacy endpoint for simulation UI compatibility.
    """
    
    step_id = request.args.get('step_id', 28800, type=float)
    sample_data = ui_controller.get_sample_data(step_id)
    if sample_data:
        return jsonify({"status": "success", "data": sample_data}), 200
    else:
        return jsonify({"status": "error", "message": "No data available"}), 404

@ui_route.route("/dact_sample_data", methods=["GET"])
def get_dact_sample_data():
    """
    Endpoint to receive sample DACT data by step ID.
    """
    step_id = request.args.get('step_id', 659, type=int)
    sample_data = ui_controller.get_dact_sample_data(step_id)
    
    if sample_data:
        return jsonify({"status": "success", "data": sample_data}), 200
    else:
        return jsonify({"status": "error", "message": "No DACT data available"}), 404

@ui_route.route("/create_user", methods=["POST"])
def create_user():
    user_data = request.get_json()
    result = None
    if result:
        return jsonify({"status": "success", "data": result}), 201
    else:
        return jsonify({"status": "error", "message": "User creation failed"}), 400

@ui_route.route("/update_user", methods=["POST"])
def update_user():
    user_data = request.get_json()
    result = None
    if result:
        return jsonify({"status": "success", "data": result}), 200
    else:
        return jsonify({"status": "error", "message": "User update failed"}), 400
    
@ui_route.route("/delete_user", methods=["POST"])
def delete_user():
    user_id = request.get_json().get("user_id")
    result = None
    if result:
        return jsonify({"status": "success", "data": result}), 200
    else:
        return jsonify({"status": "error", "message": "User deletion failed"}), 400

@ui_route.route("/update_node", methods=["POST"])
def update_node():
    node_data = request.get_json()
    result = None
    if result:
        return jsonify({"status": "success", "data": result}), 200
    else:
        return jsonify({"status": "error", "message": "Node update failed"}), 400

@ui_route.route("/get_node_user_assignment", methods=["GET"])
def get_node_user_assignment():
    node_id = request.args.get("node_id")
    result = None
    if result:
        return jsonify({"status": "success", "data": result}), 200
    else:
        return jsonify({"status": "error", "message": "Node user assignment retrieval failed"}), 400