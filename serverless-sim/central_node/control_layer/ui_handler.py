"""
UI Handler for Central Node Control Layer
Manages simulation UI interactions and legacy compatibility
"""

import logging
import threading
from typing import Dict, Any, Optional

from central_node.control_layer.data_manager import DataManager

# Create blueprint for UI endpoints - only import Flask when needed
ui_blueprint = None

def _get_blueprint():
    """Lazy import of Flask blueprint"""
    global ui_blueprint
    if ui_blueprint is None:
        try:
            from flask import Blueprint
            ui_blueprint = Blueprint('ui', __name__)
        except ImportError:
            raise ImportError("Flask is required for UI functionality")
    return ui_blueprint

class UIHandler:
    """
    Handles UI-related requests for the simulation interface.
    Provides legacy compatibility while integrating with the control layer.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data_manager = DataManager()
        
        # Global variables to manage simulation state
        self.simulation_running = False
        self.step_lock = threading.Lock()
        
        self.logger.info("UI Handler initialized in control layer")
        
    def get_sample_data(self, timestep: float) -> Optional[Dict[str, Any]]:
        """
        Get sample data for a specific timestep from vehicle dataset.
        """
        try:
            self.logger.info(f"Requesting vehicle data for timestep: {timestep}")
            return self.data_manager.get_vehicle_data_by_timestep(timestep)
        except Exception as e:
            self.logger.error(f"Error getting sample data: {e}")
            return None

    def get_dact_sample_data(self, step_id: int) -> Optional[Dict[str, Any]]:
        """
        Get sample data for a specific step from DACT dataset.
        """
        try:
            self.logger.info(f"Requesting DACT data for step: {step_id}")
            return self.data_manager.get_dact_data_by_step(step_id)
        except Exception as e:
            self.logger.error(f"Error getting DACT sample data: {e}")
            return None

# Global UI handler instance
ui_handler = UIHandler()

# Route definitions
def home():
    """Home endpoint for simulation UI"""
    return "Welcome to the Serverless Edge Computing Simulation!", 200

def get_sample_data():
    """
    Endpoint to receive sample vehicle data by step_id.
    Legacy endpoint for simulation UI compatibility.
    """
    from flask import request, jsonify
    
    step_id = request.args.get('step_id', 28800, type=float)
    sample_data = ui_handler.get_sample_data(step_id)
    if sample_data:
        return jsonify({"status": "success", "data": sample_data}), 200
    else:
        return jsonify({"status": "error", "message": "No data available"}), 404

def get_dact_sample_data():
    """
    Endpoint to receive sample DACT data by step ID.
    """
    from flask import request, jsonify
    
    step_id = request.args.get('step_id', 659, type=int)
    sample_data = ui_handler.get_dact_sample_data(step_id)
    
    if sample_data:
        return jsonify({"status": "success", "data": sample_data}), 200
    else:
        return jsonify({"status": "error", "message": "No DACT data available"}), 404

def get_simulation_status():
    """
    Get current simulation status.
    """
    from flask import jsonify
    
    return jsonify({
        "status": "success",
        "simulation_running": ui_handler.simulation_running,
        "data_loaded": {
            "vehicle_data": len(ui_handler.data_manager.vehicle_loader._data or []),
            "dact_data": len(ui_handler.data_manager.dact_loader._data or [])
        }
    }), 200

def start_simulation():
    """
    Start the simulation.
    """
    from flask import jsonify
    
    with ui_handler.step_lock:
        if ui_handler.simulation_running:
            return jsonify({"status": "error", "message": "Simulation already running"}), 400
            
        ui_handler.simulation_running = True
        ui_handler.logger.info("Simulation started")
        
    return jsonify({"status": "success", "message": "Simulation started"}), 200

def stop_simulation():
    """
    Stop the simulation.
    """
    from flask import jsonify
    
    with ui_handler.step_lock:
        if not ui_handler.simulation_running:
            return jsonify({"status": "error", "message": "Simulation not running"}), 400
            
        ui_handler.simulation_running = False
        ui_handler.logger.info("Simulation stopped")
        
    return jsonify({"status": "success", "message": "Simulation stopped"}), 200

def register_ui_handler(app):
    """
    Register the UI handler routes with the Flask app.
    """
    # Register routes directly with the app
    app.add_url_rule("/", "home", home, methods=["GET"])
    app.add_url_rule("/get_sample", "get_sample_data", get_sample_data, methods=["GET"])
    app.add_url_rule("/get_dact_sample", "get_dact_sample_data", get_dact_sample_data, methods=["GET"])
    app.add_url_rule("/simulation/status", "get_simulation_status", get_simulation_status, methods=["GET"])
    app.add_url_rule("/simulation/start", "start_simulation", start_simulation, methods=["POST"])
    app.add_url_rule("/simulation/stop", "stop_simulation", stop_simulation, methods=["POST"])
    
    logging.getLogger(__name__).info("UI Handler registered with Flask app")
