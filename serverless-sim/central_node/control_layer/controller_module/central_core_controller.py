from central_node.api_layer import CentralNodeAPIController, CentralNodeAPIAgent

from central_node.control_layer.controller_module import *
from central_node.control_layer.scheduler_module.scheduler import Scheduler
from central_node.control_layer.agents_module.scheduler_agent import SchedulerAgent
from central_node.control_layer.agents_module.users_agent import UsersAgent
from central_node.control_layer.prediction_module.prediction import WorkloadPredictor
from central_node.control_layer.prediction_module.trajectory_predictor import TrajectoryPredictor
from central_node.control_layer.helper_module.data_manager import DataManager

class CentralCoreController:
    def __init__(self):
        self.scheduler = Scheduler()
        self.predictor = WorkloadPredictor()
        # Attach trajectory predictor (optional GNN)
        try:
            import os
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            # model file path relative to prediction_module
            model_path = os.path.join(
                base,
                'prediction_module',
                'spatial_temporal_gnn',
                'st-gnn_small_9_nodes_model.keras'
            )
            self.trajectory_predictor = TrajectoryPredictor(model_path=model_path, sequence_length=5)
        except Exception:
            self.trajectory_predictor = TrajectoryPredictor(model_path=None)
        # Share with scheduler
        self.scheduler.trajectory_predictor = self.trajectory_predictor
        self.data_manager = DataManager()
        self.central_node_api_controller = CentralNodeAPIController()
        
        CentralNodeAPIAgent(self.central_node_api_controller).start_all_tasks()
        SchedulerAgent(self.scheduler).start_all_tasks()
        UsersAgent(self.scheduler).start_all_tasks()

    def register_edge_node(self, request_data):
        controller = RegisterEdgeNodeController(self.scheduler, request_data)
        controller.execute()
        return f"Node {request_data.get('node_id')} registered successfully"

    def update_node_metrics(self, node_id, request_data):
        controller = UpdateNodeMetricsController(self.scheduler, node_id, request_data)
        controller.execute()
        return f"Update metrics for node {node_id} updated successfully"
            
    def get_cluster_status(self):
        controller = GetClusterStatusController(self.scheduler, self.central_node_api_controller)
        return controller.execute()
    
    def start_simulation(self):
        controller = StartSimulationController(self.scheduler)
        controller.execute()
        return "Simulation started successfully"

    def stop_simulation(self):
        controller = StopSimulationController(self.scheduler)
        controller.execute()
        return "Simulation stopped successfully"
    
    def reset_simulation(self):
        controller = ResetSimulationController(self.scheduler)
        controller.execute()
        return "Simulation reset successfully"
            
    def update_edge_node(self, request_data):
        controller = UpdateEdgeNodeController(self.scheduler, request_data)
        controller.execute()
        return f"Edge node {request_data.get('node_id')} updated successfully"

    def update_central_node(self, request_data):
        controller = UpdateCentralNodeController(self.scheduler, request_data)
        return controller.execute()
    
    def create_user_node(self, request_data):
        controller = CreateUserNodeController(self.scheduler, request_data)
        controller.execute()
        return f"User node {request_data.get('user_id')} created successfully"
    
    def update_user_node(self, request_data):
        controller = UpdateUserNodeController(self.scheduler, request_data)
        controller.execute()
        return f"User node {request_data.get('user_id')} updated successfully"

    def get_all_users(self):
        controller = GetAllUsersController(self.scheduler, self.data_manager)
        return controller.execute()

    def delete_all_users(self):
        controller = DeleteAllUsersController(self.scheduler)
        controller.execute()
        return "Delete all users executed successfully"
    
    def delete_user(self, user_id: str):
        controller = DeleteUserController(self.scheduler, user_id)
        controller.execute()
        return f"User {user_id} deleted successfully"

    def execute_function(self, request_data):
        controller = ExecuteFunctionController(self.central_node_api_controller, request_data)
        response = controller.execute()
        return response

    # Assignment strategy/config APIs
    def set_assignment_strategy(self, request_data):
        strategy = request_data.get('strategy', 'round_robin')
        self.scheduler.set_scheduling_strategy(strategy)
        return f"Assignment strategy set to {self.scheduler.get_scheduling_strategy()}"

    def update_assignment_config(self, request_data):
        cfg = {}
        for key in ['handoff_min_dwell_seconds', 'handoff_improvement_threshold', 'assignment_scan_interval', 'load_aware_alpha']:
            if key in request_data:
                cfg[key] = request_data[key]
        self.scheduler.set_assignment_config(**cfg)
        return self.scheduler.get_assignment_status()

    def get_assignment_status(self):
        return self.scheduler.get_assignment_status()

    def start_dact_sample(self):
        controller = StartDactSampleController(self.data_manager, self.scheduler)
        controller.execute()
        return "Start using dact sample"
    
    def start_vehicles_sample(self):
        controller = StartVehiclesSampleController(self.data_manager, self.scheduler)
        controller.execute()
        return "Start using vehicles sample"
