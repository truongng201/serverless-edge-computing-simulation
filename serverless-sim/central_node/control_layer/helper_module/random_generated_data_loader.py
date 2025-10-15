import random
import json
import os
import math


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
    
    def _random_location_around_central(self, central_node_location, min_distance=100, max_distance=700):
        angle = random.uniform(0, 2 * math.pi)
        
        min_radius_squared = min_distance * min_distance
        max_radius_squared = max_distance * max_distance
        
        radius_squared = random.uniform(min_radius_squared, max_radius_squared)
        radius = math.sqrt(radius_squared)

        x = central_node_location.get('x', 0) + radius * math.cos(angle)
        y = central_node_location.get('y', 0) + radius * math.sin(angle)
        
        return {'x': x, 'y': y}
    
    def random_velocity(self, min_speed=0, max_speed=3):
        speed = random.uniform(min_speed, max_speed)  # m/s, typical city driving
        direction = random.uniform(0, 2 * math.pi)
        
        vx = speed * math.cos(direction)
        vy = speed * math.sin(direction)
        
        return vx, vy, speed, direction
    
    def generate_car_user(self, i, radius=600):
        """
        Generate a car user with realistic car-like movement
        
        Args:
            i: User ID
            radius: Maximum radius around central node (default: 1000m)
            
        Returns:
            dict: User data with car-like movement properties
        """
        # Randomly place car around central node
        r = math.sqrt(random.uniform(0, 1)) * radius
        theta = random.uniform(0, 2 * math.pi)
        x = self.central_node_location.get('x', 0) + r * math.cos(theta)
        y = self.central_node_location.get('y', 0) + r * math.sin(theta)

        # Generate car-like velocity
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
        """
        Load complete simulation data from file if it exists, otherwise generate new data
        """
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
        """
        Save complete simulation data to the file
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.data_file_path), exist_ok=True)
            
            with open(self.data_file_path, 'w') as f:
                json.dump(simulation_data, f, indent=2)
            print(f"Successfully saved simulation data to {self.data_file_path}")
        except Exception as e:
            print(f"Error saving data to file: {e}")
    
    def _save_step_to_file(self, step: int, step_data):
        """
        Save a specific timestep data to the file
        """
        try:
            self.simulation_data['step_history'][str(step)] = step_data
            self._save_simulation_data(self.simulation_data)
        except Exception as e:
            print(f"Error saving step {step} to file: {e}")
    
    def get_data_by_step(self, step: int):
        """
        Get user data for a specific timestep, updating positions based on movement
        
        Args:
            step: The current simulation timestep
            
        Returns:
            List of user data with updated positions
        """
        # Check if we already have this step cached
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
            
            # Add some randomness to car movement (slight direction and speed variations)
            if "speed" in user and "direction" in user:
                # Slight variations in speed and direction for realistic car movement
                speed_variation = random.uniform(-1, 1)  # ±1 m/s variation
                direction_variation = random.uniform(-0.1, 0.1)  # ±0.1 rad variation (~6 degrees)
                
                user["speed"] = max(5, min(25, user["speed"] + speed_variation))  # Keep within 5-25 m/s
                user["direction"] += direction_variation
                
                # Update velocity based on new speed and direction
                user["velocity_x"] = user["speed"] * math.cos(user["direction"])
                user["velocity_y"] = user["speed"] * math.sin(user["direction"])
            else:
                # Fallback to old behavior for users without speed/direction
                user["velocity_x"] += random.uniform(-0.5, 0.5)
                user["velocity_y"] += random.uniform(-0.5, 0.5)
                
                # Clamp velocity to reasonable bounds
                user["velocity_x"] = max(-25, min(25, user["velocity_x"]))
                user["velocity_y"] = max(-25, min(25, user["velocity_y"]))
            
            
    def get_cached_steps(self):
        """
        Get list of all cached timesteps
        
        Returns:
            List of integers representing cached timesteps
        """
        return sorted([int(step) for step in self.step_history.keys()])
    
    def get_max_cached_step(self):
        """
        Get the maximum cached timestep
        
        Returns:
            Integer representing the maximum cached timestep, or -1 if no steps cached
        """
        cached_steps = self.get_cached_steps()
        return max(cached_steps) if cached_steps else -1
    
    def clear_cache_after_step(self, step: int):
        """
        Clear cached data after a specific step (useful for restarting simulation from a point)
        
        Args:
            step: The step after which to clear cache
        """
        steps_to_remove = [s for s in self.step_history.keys() if int(s) > step]
        for step_key in steps_to_remove:
            del self.step_history[step_key]
        
        # Save updated data
        self._save_simulation_data(self.simulation_data)
        print(f"Cleared cached data after step {step}")
    
    def __len__(self):
        return self.num_items