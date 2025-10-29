import random
import json
import os
import math
from config import Config


class RandomGeneratedDataLoader:
    def __init__(self, num_items: int = 1000, central_node_location: dict = {"x": 730, "y": 1070}):
        if central_node_location is None:
            central_node_location = {'x': 0, 'y': 0}
        
        self.num_items = num_items
        self.central_node_location = central_node_location
        self.current_step = 0  # Add current_step tracking
        
        # Define the path to the data file
        self.data_file_path = os.path.join(
            os.path.dirname(__file__), 
            '..', '..', '..', 
            'mock_data', 
            'random_generated.txt'
        )
        
        # Load or generate initial data and simulation history
        self.simulation_data = self._load_or_generate_simulation_data()
        self.users = self.simulation_data['initial_users']  # For current state tracking
        self.step_history = self.simulation_data['step_history']  # All computed steps
    
    def _random_location_around_central(self, central_node_location, min_distance=None, max_distance=None):
        if min_distance is None:
            min_distance = Config.USER_MIN_SPAWN_DISTANCE
        if max_distance is None:
            max_distance = Config.USER_MAX_SPAWN_DISTANCE
            
        angle = random.uniform(0, 2 * math.pi)
        
        min_radius_squared = min_distance * min_distance
        max_radius_squared = max_distance * max_distance
        
        radius_squared = random.uniform(min_radius_squared, max_radius_squared)
        radius = math.sqrt(radius_squared)

        x = central_node_location.get('x', 0) + radius * math.cos(angle)
        y = central_node_location.get('y', 0) + radius * math.sin(angle)
        
        return {'x': x, 'y': y}
    
    def random_velocity(self, min_speed=None, max_speed=None):
        if min_speed is None:
            min_speed = Config.USER_MIN_SPEED
        if max_speed is None:
            max_speed = Config.USER_MAX_SPEED
            
        speed = random.uniform(min_speed, max_speed)  # m/s, slow pedestrian/vehicle speed
        direction = random.uniform(0, 2 * math.pi)
        
        vx = speed * math.cos(direction)
        vy = speed * math.sin(direction)
        
        return vx, vy, speed, direction
    
    def generate_car_user(self, i, radius=None):
        x, y = self._random_location_around_central(self.central_node_location).values()
        vx, vy, speed, direction = self.random_velocity()

        return {
            "user_id": i,
            "current_step": 0,
            "location_x": x,
            "location_y": y,
            "velocity_x": vx,
            "velocity_y": vy,
            "speed": speed,
            "direction": direction
        }
    
    def _load_or_generate_simulation_data(self):
        if os.path.exists(self.data_file_path):
            # Load existing data
            try:
                with open(self.data_file_path, 'r') as f:
                    data = json.load(f)
                    # Validate that the data matches our requirements
                    if (isinstance(data, dict) and 
                        'num_items' in data and 
                        'initial_users' in data and 
                        'step_history' in data and
                        data['num_items'] == self.num_items and
                        len(data['initial_users']) == self.num_items):
                        print(f"Loaded existing simulation data from {self.data_file_path}")
                        print(f"Found {len(data['step_history'])} cached timesteps")
                        return data
                    else:
                        print(f"Data file format mismatch, regenerating...")
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error loading data file: {e}, regenerating...")
        
        # Generate new simulation data
        print(f"Generating new simulation data and saving to {self.data_file_path}")
        users = []
        for i in range(1, self.num_items + 1):  # user range from 1 -> num_items
            user = self.generate_car_user(i)
            users.append(user)
        
        simulation_data = {
            'num_items': self.num_items,
            'central_node_location': self.central_node_location,
            'initial_users': users,
            'step_history': {}  # Will store all timestep data
        }
        
        # Save to file
        self._save_simulation_data(simulation_data)
        return simulation_data
    
    def _save_simulation_data(self, simulation_data):
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.data_file_path), exist_ok=True)
            
            with open(self.data_file_path, 'w') as f:
                json.dump(simulation_data, f, indent=2)
            print(f"Successfully saved simulation data to {self.data_file_path}")
        except Exception as e:
            print(f"Error saving data to file: {e}")
    
    def _save_step_to_file(self, step: int, step_data):
        try:
            self.simulation_data['step_history'][str(step)] = step_data
            self._save_simulation_data(self.simulation_data)
        except Exception as e:
            print(f"Error saving step {step} to file: {e}")
    
    def get_data_by_step(self, step: int):
        step_key = str(step)
        if step_key in self.step_history:
            print(f"Returning cached data for step {step}")
            return self.step_history[step_key]
        
        # Update positions if we've moved to a new step
        if step > self.current_step:
            self._update_user_positions(step - self.current_step)
            self.current_step = step
        
        # Create current user data with timestep
        data = []
        for user in self.users:
            user_data = {
                "timestep": step,
                "user_id": user["user_id"],
                "location_x": user["location_x"],
                "location_y": user["location_y"]
            }
            data.append(user_data)
        
        # Cache this step data
        self.step_history[step_key] = data
        
        # Save to file
        self._save_step_to_file(step, data)
        
        print(f"Generated and cached new data for step {step}")
        return data
    
    def _update_user_positions(self, steps_elapsed: int = 1):
        for user in self.users:
            # Update current step
            user["current_step"] += steps_elapsed
            # Update position based on velocity
            user["location_x"] += user["velocity_x"] * steps_elapsed
            user["location_y"] += user["velocity_y"] * steps_elapsed
            
            # Check if user is getting too far from central node and apply boundary constraints
            central_x = self.central_node_location.get('x', 0)
            central_y = self.central_node_location.get('y', 0)
            distance_from_center = math.sqrt((user["location_x"] - central_x)**2 + (user["location_y"] - central_y)**2)
            max_allowed_distance = Config.USER_MAX_DISTANCE_FROM_CENTER
            
            # Add some randomness to movement (slight direction and speed variations)
            if "speed" in user and "direction" in user:
                # If user is too far, redirect them back towards center
                if distance_from_center > max_allowed_distance:
                    # Calculate direction back to center
                    angle_to_center = math.atan2(central_y - user["location_y"], central_x - user["location_x"])
                    # Add some randomness to avoid straight-line movement
                    angle_variation = random.uniform(-0.5, 0.5)  # ±30 degrees variation
                    user["direction"] = angle_to_center + angle_variation
                else:
                    # Normal movement with slight variations
                    direction_variation = random.uniform(-0.2, 0.2)  # ±0.2 rad variation (~11 degrees)
                    user["direction"] += direction_variation
                
                # Slight speed variations for realistic movement
                speed_variation = random.uniform(-0.3, 0.3)  # ±0.3 m/s variation
                user["speed"] = max(Config.USER_MIN_SPEED, min(Config.USER_MAX_SPEED, user["speed"] + speed_variation))
                
                # Update velocity based on new speed and direction
                user["velocity_x"] = user["speed"] * math.cos(user["direction"])
                user["velocity_y"] = user["speed"] * math.sin(user["direction"])
            else:
                # Fallback to old behavior for users without speed/direction
                user["velocity_x"] += random.uniform(-0.2, 0.2)
                user["velocity_y"] += random.uniform(-0.2, 0.2)
                
                # Clamp velocity to reasonable bounds (much slower)
                max_vel = Config.USER_MAX_SPEED
                user["velocity_x"] = max(-max_vel, min(max_vel, user["velocity_x"]))
                user["velocity_y"] = max(-max_vel, min(max_vel, user["velocity_y"]))
                
                # Apply boundary constraint for users without direction
                if distance_from_center > max_allowed_distance:
                    # Reduce velocity towards center
                    direction_to_center_x = (central_x - user["location_x"]) / distance_from_center
                    direction_to_center_y = (central_y - user["location_y"]) / distance_from_center
                    user["velocity_x"] = direction_to_center_x * abs(user["velocity_x"])
                    user["velocity_y"] = direction_to_center_y * abs(user["velocity_y"])
            
    def __len__(self):
        return self.num_items