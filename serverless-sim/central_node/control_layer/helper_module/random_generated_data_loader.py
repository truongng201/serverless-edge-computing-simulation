import random


class RandomGeneratedDataLoader:
    """Generates and manages random data for simulation with moving users around a central node"""
    
    def __init__(self, num_items: int = 100, central_node_location: dict = None):
        """
        Initialize the data loader with users positioned around a central node
        
        Args:
            num_items: Number of users to generate
            central_node_location: Dict with 'x' and 'y' keys for central node position
        """
        if central_node_location is None:
            central_node_location = {'x': 0, 'y': 0}
        
        self.num_items = num_items
        self.central_node_location = central_node_location
        self.current_step = 0
        
        # Initialize users with random positions around central node
        self.users = []
        for i in range(1, num_items + 1):  # user range from 1 -> num_items
            user = {
                "user_id": i,
                "location_x": central_node_location.get('x', 0) + random.uniform(100, 500) * random.choice([-1, 1]),
                "location_y": central_node_location.get('y', 0) + random.uniform(100, 500) * random.choice([-1, 1]),
                "velocity_x": random.uniform(-2, 2),  # Small random velocity
                "velocity_y": random.uniform(-2, 2)   # Small random velocity
            }
            self.users.append(user)
    
    def get_data_by_step(self, step: int):
        """
        Get user data for a specific timestep, updating positions based on movement
        
        Args:
            step: The current simulation timestep
            
        Returns:
            List of user data with updated positions
        """
        # Update positions if we've moved to a new step
        if step > self.current_step:
            self._update_user_positions(step - self.current_step)
            self.current_step = step
        
        # Return current user data with timestep
        data = []
        for user in self.users:
            user_data = {
                "timestep": step,
                "user_id": user["user_id"],
                "location_x": user["location_x"],
                "location_y": user["location_y"]
            }
            data.append(user_data)
        
        return data
    
    def _update_user_positions(self, steps_elapsed: int = 1):
        """
        Update user positions based on their velocities
        
        Args:
            steps_elapsed: Number of timesteps that have passed
        """
        for user in self.users:
            # Update position based on velocity
            user["location_x"] += user["velocity_x"] * steps_elapsed
            user["location_y"] += user["velocity_y"] * steps_elapsed
            
            # Add some randomness to velocity for more realistic movement
            user["velocity_x"] += random.uniform(-0.5, 0.5)
            user["velocity_y"] += random.uniform(-0.5, 0.5)
            
            # Clamp velocity to reasonable bounds
            user["velocity_x"] = max(-5, min(5, user["velocity_x"]))
            user["velocity_y"] = max(-5, min(5, user["velocity_y"]))
    
    def get_user_count(self):
        """Get the number of users in the simulation"""
        return self.num_items
    
    def reset_simulation(self, central_node_location: dict = None):
        """
        Reset the simulation with new random positions around central node
        
        Args:
            central_node_location: Optional new central node location
        """
        if central_node_location:
            self.central_node_location = central_node_location
        
        self.current_step = 0
        
        # Regenerate user positions
        for i, user in enumerate(self.users, 1):
            user["user_id"] = i
            user["location_x"] = self.central_node_location.get('x', 0) + random.uniform(100, 500) * random.choice([-1, 1])
            user["location_y"] = self.central_node_location.get('y', 0) + random.uniform(100, 500) * random.choice([-1, 1])
            user["velocity_x"] = random.uniform(-2, 2)
            user["velocity_y"] = random.uniform(-2, 2)