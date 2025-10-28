import os
import csv
import logging
import math
from typing import Dict, Any, List, Optional

class HighDDataLoader:
    """Loads and manages HighD dataset for simulation"""
    
    def __init__(self, data_path: str = None):
        self.logger = logging.getLogger(__name__)
        # Look for data in the project data directory
        if data_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            data_path = os.path.join(project_root, 'mock_data', 'highD-dataset-v1.0', 'data', '01_tracks.csv')
        
        self._data_path = data_path
        self._meta_path = data_path.replace('_tracks.csv', '_tracksMeta.csv')
        self._data = None
        self._meta_data = None
        self._load_data()
    
    def _load_data(self):
        """
        Load and preprocess HighD tracks data from the specified CSV file.
        """
        if not os.path.isfile(self._data_path):
            self.logger.warning(f"HighD tracks data file not found: {self._data_path}")
            self._data = []
            return

        # Load metadata first
        self._load_metadata()

        self._data = []
        try:
            with open(self._data_path, 'r', newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    try:
                        # Convert velocity from m/s to km/h for consistency with other loaders
                        x_velocity = float(row["xVelocity"]) * 3.6
                        y_velocity = float(row["yVelocity"]) * 3.6
                        speed = (x_velocity**2 + y_velocity**2)**0.5
                        
                        # Calculate heading angle from velocity components
                        heading = math.atan2(float(row["yVelocity"]), float(row["xVelocity"])) * 180 / math.pi
                        
                        self._data.append({
                            "frame": int(row["frame"]),
                            "id": int(row["id"]),
                            "x": float(row["x"]),
                            "y": float(row["y"]),
                            "width": float(row["width"]),
                            "height": float(row["height"]),
                            "xVelocity": float(row["xVelocity"]),
                            "yVelocity": float(row["yVelocity"]),
                            "xAcceleration": float(row["xAcceleration"]),
                            "yAcceleration": float(row["yAcceleration"]),
                            "speed": speed,
                            "heading": heading,
                            "laneId": int(row["laneId"])
                        })
                    except (ValueError, KeyError) as e:
                        self.logger.warning(f"Skipping malformed row: {row} - Error: {e}")
                        
            if not self._data:
                self.logger.warning(f"Loaded file but found no valid HighD data in: {self._data_path}")
            else:
                self.logger.info(f"Loaded {len(self._data)} HighD track records")
                
        except Exception as e:
            self.logger.error(f"Failed to read HighD data file {self._data_path}: {e}")
            self._data = []

    def _load_metadata(self):
        """Load metadata about vehicles from tracksMeta.csv"""
        if not os.path.isfile(self._meta_path):
            self.logger.warning(f"HighD metadata file not found: {self._meta_path}")
            self._meta_data = {}
            return
        
        self._meta_data = {}
        try:
            with open(self._meta_path, 'r', newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    try:
                        vehicle_id = int(row["id"])
                        self._meta_data[vehicle_id] = {
                            "class": row["class"],
                            "width": float(row["width"]),
                            "height": float(row["height"]),
                            "initialFrame": int(row["initialFrame"]),
                            "finalFrame": int(row["finalFrame"]),
                            "numFrames": int(row["numFrames"]),
                            "drivingDirection": int(row["drivingDirection"]),
                            "traveledDistance": float(row["traveledDistance"]),
                            "meanXVelocity": float(row["meanXVelocity"]),
                            "numLaneChanges": int(row["numLaneChanges"])
                        }
                    except (ValueError, KeyError) as e:
                        self.logger.warning(f"Skipping metadata row: {row} - Error: {e}")
                        
            self.logger.info(f"Loaded metadata for {len(self._meta_data)} vehicles")
            
        except Exception as e:
            self.logger.error(f"Failed to read HighD metadata file {self._meta_path}: {e}")
            self._meta_data = {}
            
    def _normalize_coordinates(self, items: List[Dict]) -> List[Dict]:
        """
        Scale coordinates for UI visibility while preserving relative positioning.
        HighD coordinates are in meters, so we need to scale appropriately.
        """
        if not items or not self._data:
            return items

        # Get global min/max from entire dataset to preserve movement continuity
        if not hasattr(self, '_global_bounds'):
            all_x = [row['x'] for row in self._data]
            all_y = [row['y'] for row in self._data]
            self._global_bounds = {
                'min_x': min(all_x),
                'max_x': max(all_x),
                'min_y': min(all_y),
                'max_y': max(all_y)
            }

        # Scale factor for UI visibility - HighD uses highway coordinates
        scale_x = 1500  # Scale for highway length
        scale_y = 300   # Scale for highway width (lanes)
        offset_x = 200  # Offset from edge
        offset_y = 200  # Offset from edge

        for item in items:
            # Normalize using global bounds to preserve relative positioning
            x_range = self._global_bounds['max_x'] - self._global_bounds['min_x']
            y_range = self._global_bounds['max_y'] - self._global_bounds['min_y']
            
            if x_range > 0:
                normalized_x = (item['x'] - self._global_bounds['min_x']) / x_range
            else:
                normalized_x = 0.5
                
            if y_range > 0:
                normalized_y = (item['y'] - self._global_bounds['min_y']) / y_range
            else:
                normalized_y = 0.5
            
            # Apply scaling and offset for UI
            item['x'] = normalized_x * scale_x + offset_x
            item['y'] = normalized_y * scale_y + offset_y

        return items
            
    def get_data_by_frame(self, frame: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve vehicle data by frame (timestep) and normalize coordinates.
        Expected output format:
        {
            "step_id": frame,
            "items": [
                {
                    "id": vehicle_id,
                    "x": x_position,
                    "y": y_position,
                    "speed": speed,
                    "acceleration": acceleration_magnitude,
                    "heading": heading_angle,
                    "heading_change": 0.0,  # would need previous frame to calculate
                    "size": vehicle_size
                },
                ...
            ]
        }
        """
        if not self._data:
            return None
            
        items = []
        for row in self._data:
            if row["frame"] == frame:
                # Calculate acceleration magnitude
                acceleration = (row["xAcceleration"]**2 + row["yAcceleration"]**2)**0.5
                
                # Get vehicle class for size determination
                vehicle_class = "Car"  # default
                size = 8  # default size
                if self._meta_data and row["id"] in self._meta_data:
                    vehicle_class = self._meta_data[row["id"]]["class"]
                    # Adjust size based on vehicle class
                    if vehicle_class == "Truck":
                        size = 12
                    elif vehicle_class == "Car":
                        size = 8
                    else:
                        size = 10
                
                items.append({
                    "id": str(row["id"]),
                    "x": row["x"],
                    "y": row["y"],
                    "speed": row["speed"],
                    "acceleration": acceleration,
                    "heading": row["heading"],
                    "heading_change": 0.0,  # Would need previous frame data to calculate
                    "size": size,
                    "vehicle_class": vehicle_class,
                    "lane_id": row["laneId"]
                })

        items = self._normalize_coordinates(items)

        return {
            "step_id": frame,
            "items": items
        }
    
    def get_all_data(self) -> List[Dict[str, Any]]:
        """Get the full dataset."""
        return self._data or []
    
    def get_metadata(self) -> Dict[int, Dict[str, Any]]:
        """Get vehicle metadata."""
        return self._meta_data or {}
    
    def get_frame_range(self) -> tuple:
        """Get the range of available frames."""
        if not self._data:
            return (0, 0)
        frames = [row["frame"] for row in self._data]
        return (min(frames), max(frames))
    
    def get_vehicle_ids(self) -> List[int]:
        """Get list of all vehicle IDs in the dataset."""
        if not self._data:
            return []
        return list(set(row["id"] for row in self._data))

    def __len__(self) -> int:
        """Get the number of track records loaded."""
        return len(self._data or [])

