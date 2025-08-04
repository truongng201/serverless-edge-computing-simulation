from flask import Flask, jsonify
from flask_socketio import SocketIO, emit
from control.data_loader import DactDataLoader  # Assuming DataLoader is defined in data_loader.py
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")



# Global variables to manage simulation state
data_loader = DactDataLoader()
simulation_running = False
step_lock = threading.Lock()

@app.route("/", methods=["GET"])
def home():
    return "Welcome to the Flask HTTP Server with Socket.IO!", 200

@app.route("/get_first_sample", methods=["GET"])
def receive_data():
    """
    Endpoint to receive the first sample of data.
    """
    first_sample = data_loader.get_data_by_step(step_id=659)
    if first_sample:
        return jsonify({"status": "success", "data": first_sample}), 200
    else:
        return jsonify({"status": "error", "message": "No data available"}), 404

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connection_response', {'status': 'Connected', 'message': 'Connected to the server'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')
@socketio.on('request_next_step')
def handle_next_step_request(current_step):
    print(f'Received request_next_step for step {current_step}')
    current_step = int(current_step)
    with step_lock:
        # Get data for current step
        step_data = data_loader.get_data_by_step(step_id=current_step)
        print(step_data)
        if step_data.get("items"):
            # Send the data back to client
            emit('step_data', {
                'status': 'success',
                'data': step_data,
                'current_step': current_step
            })
        else:
            print(f'No data available for step {current_step}')
            # No more data available, reset or handle end of simulation
            emit('step_data', {
                'status': 'error',
                'message': f'No data available for step {current_step}',
                'current_step': current_step
            })

