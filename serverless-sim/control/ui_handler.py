from flask import Flask, jsonify, request
from control.data_loader import DactDataLoader, VehicleDataLoader  # Assuming DataLoader is defined in data_loader.py
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'



# Global variables to manage simulation state
data_loader = VehicleDataLoader()
simulation_running = False
step_lock = threading.Lock()

@app.route("/", methods=["GET"])
def home():
    return "Welcome to the Flask HTTP Server with Socket.IO!", 200

@app.route("/get_sample", methods=["GET"])
def receive_data():
    """
    Endpoint to receive the first sample of data.
    """
    timestep = request.args.get('timestep', 28800.00, type=float)
    print(f"Requesting data for timestep: {timestep}")
    first_sample = data_loader.get_data_by_timestep(timestep=timestep)
    if first_sample:
        return jsonify({"status": "success", "data": first_sample}), 200
    else:
        return jsonify({"status": "error", "message": "No data available"}), 404