"""
Data Manager for Central Node Control Layer
Handles data loading and simulation data management for the UI
"""

import os
import csv
import logging
import math
from collections import defaultdict
from typing import Dict, Any, List, Optional

class DataManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.vehicle_loader = None
        self.dact_loader = None
        self.highd_loader = None
    
    def _load_vehicle_data(self, data_path: str = None):
        self.vehicle_loader = VehicleDataLoader(data_path)
        self.logger.info(f"Vehicle data loaded with {len(self.vehicle_loader)} records")
        
    def _load_dact_data(self, data_path: str = None):
        self.dact_loader = DactDataLoader(data_path)
        self.logger.info(f"DACT data loaded with {len(self.dact_loader)} trips")
        
    def _load_highd_data(self, data_path: str = None):
        self.highd_loader = HighDDataLoader(data_path)
        self.logger.info(f"HighD data loaded with {len(self.highd_loader)} vehicles")
        
    def get_vehicle_data_by_timestep(self, timestep: float) -> Optional[Dict[str, Any]]:
        if self.vehicle_loader is None:
            self._load_vehicle_data()
        return self.vehicle_loader.get_data_by_timestep(timestep)
        
    def get_dact_data_by_step(self, step_id: int) -> Optional[Dict[str, Any]]:
        if self.dact_loader is None:
            self._load_dact_data()
        return self.dact_loader.get_data_by_step(step_id)
        
    def get_highd_data_by_frame(self, frame: int) -> Optional[Dict[str, Any]]:
        if self.highd_loader is None:
            self._load_highd_data()
        return self.highd_loader.get_data_by_frame(frame)


class DactDataLoader:
    """Loads and manages DACT dataset for simulation"""
    
    def __init__(self, data_path: str = None):
        self.logger = logging.getLogger(__name__)
        # Look for data in the project data directory
        if data_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            data_path = os.path.join(project_root, 'mock_data', 'DACT-Easy-Dataset.csv')
        
        self._data_path = data_path
        self._data = None
        self._load_data()

    def _load_data(self):
        """
        Load data from the specified CSV file and organize it by trip_id.
        """
        if not os.path.isfile(self._data_path):
            self.logger.warning(f"DACT data file not found: {self._data_path}")
            self._data = []
            return

        trip_dict = defaultdict(list)
        try:
            with open(self._data_path, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    try:
                        trip_id = row['TripID']
                        step = {
                            "timestep": int(row['TimeStep']),
                            "location": {
                                "lat": float(row['Latitude']),
                                "lon": float(row['Longitude']),
                            },
                            "speed": float(row['Speed']),
                            "acceleration": float(row['Acceleration']),
                            "heading": float(row['Heading']),
                            "heading_change": float(row['HeadingChange']),
                        }
                        trip_dict[trip_id].append(step)
                    except (KeyError, ValueError) as e:
                        self.logger.warning(f"Skipping row due to invalid data: {e}")

            # Convert to list format with item_id
            self._data = [
                {
                    "item_id": idx,
                    "trip_id": trip_id,
                    "steps": steps
                }
                for idx, (trip_id, steps) in enumerate(trip_dict.items(), start=1)
            ]
            
            self.logger.info(f"Loaded {len(self._data)} trips from DACT dataset")

        except Exception as e:
            self.logger.error(f"Failed to load DACT data: {e}")
            self._data = []

    def _normalize_coordinates(self, items: List[Dict]) -> List[Dict]:
        """
        Scale coordinates for UI visibility while preserving relative positioning.
        Uses global min/max from entire dataset to maintain consistency across timesteps.
        """
        if not items or not self._data:
            return items

        # Get global min/max from entire dataset to preserve movement continuity
        if not hasattr(self, '_global_bounds'):
            all_lats = []
            all_lons = []
            for trip in self._data:
                for step in trip['steps']:
                    all_lats.append(step['location']['lat'])
                    all_lons.append(step['location']['lon'])
            
            self._global_bounds = {
                'min_lat': min(all_lats) if all_lats else 0,
                'max_lat': max(all_lats) if all_lats else 1,
                'min_lon': min(all_lons) if all_lons else 0,
                'max_lon': max(all_lons) if all_lons else 1
            }

        # Scale factor for UI visibility with larger distances between items
        scale_x = 2000  # Much larger scale for better separation
        scale_y = 1500  # Much larger scale for better separation
        offset_x = 200  # Larger offset from edge
        offset_y = 150  # Larger offset from edge

        for item in items:
            # Normalize using global bounds to preserve relative positioning
            lat_range = self._global_bounds['max_lat'] - self._global_bounds['min_lat']
            lon_range = self._global_bounds['max_lon'] - self._global_bounds['min_lon']
            
            if lat_range > 0:
                normalized_lat = (item['x'] - self._global_bounds['min_lat']) / lat_range
            else:
                normalized_lat = 0.5
                
            if lon_range > 0:
                normalized_lon = (item['y'] - self._global_bounds['min_lon']) / lon_range
            else:
                normalized_lon = 0.5
            
            # Apply scaling and offset for UI
            item['x'] = normalized_lat * scale_x + offset_x
            item['y'] = normalized_lon * scale_y + offset_y

        return items

    def get_data_by_step(self, step_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve data by step_id (timestep) from the DACT dataset.
        """
        if not self._data:
            return None
        items = []
        for item in self._data:
            for step in item['steps']:
                if step['timestep'] == step_id:
                    items.append({
                        "id": item['item_id'],
                        "x": step['location']['lat'],
                        "y": step['location']['lon'],
                        "speed": step['speed'],
                        "acceleration": step['acceleration'],
                        "heading": step['heading'],
                        "heading_change": step['heading_change'],
                        "size": 8,  # Default size
                    })
                    break
        
        items = self._normalize_coordinates(items)
        return {
            "step_id": step_id,
            "items": items
        }

    def get_all_data(self) -> List[Dict[str, Any]]:
        """Get the full dataset."""
        return self._data or []

    def __len__(self) -> int:
        """Get the number of trip items loaded."""
        return len(self._data or [])


class VehicleDataLoader:
    """Loads and manages vehicle dataset for simulation"""
    
    def __init__(self, data_path: str = None):
        self.logger = logging.getLogger(__name__)
        # Look for data in the project data directory
        if data_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            data_path = os.path.join(project_root, 'mock_data', 'vehicles_data_5min.csv')
        
        self._data_path = data_path
        self._data = None
        self._load_data()
    
    def _load_data(self):
        """
        Load and preprocess vehicle data from the specified CSV file.
        Converts fields to appropriate types for later use.
        """
        if not os.path.isfile(self._data_path):
            self.logger.warning(f"Vehicle data file not found: {self._data_path}")
            self._data = []
            return

        self._data = []
        try:
            with open(self._data_path, 'r', newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    try:
                        self._data.append({
                            "time": float(row["time"]),
                            "vehicle_id": row["vehicle_id"].strip(),
                            "x": float(row["x"]),
                            "y": float(row["y"]),
                            "lon": float(row["lon"]),
                            "lat": float(row["lat"]),
                            "speed": float(row["speed"]),
                            "angle": float(row["angle"])
                        })
                    except (ValueError, KeyError) as e:
                        self.logger.warning(f"Skipping malformed row: {row} - Error: {e}")
                        
            if not self._data:
                self.logger.warning(f"Loaded file but found no valid vehicle data in: {self._data_path}")
            else:
                self.logger.info(f"Loaded {len(self._data)} vehicle records")
                
        except Exception as e:
            self.logger.error(f"Failed to read vehicle data file {self._data_path}: {e}")
            self._data = []
            
    def _normalize_coordinates(self, items: List[Dict]) -> List[Dict]:
        """
        Scale coordinates for UI visibility while preserving relative positioning.
        Uses global min/max from entire dataset to maintain consistency across timesteps.
        """
        if not items or not self._data:
            return items

        # Get global min/max from entire dataset to preserve movement continuity
        if not hasattr(self, '_global_bounds'):
            all_lats = [row['lat'] for row in self._data]
            all_lons = [row['lon'] for row in self._data]
            self._global_bounds = {
                'min_lat': min(all_lats),
                'max_lat': max(all_lats),
                'min_lon': min(all_lons),
                'max_lon': max(all_lons)
            }

        # Scale factor for UI visibility with larger distances between items
        scale_x = 2000  # Much larger scale for better separation
        scale_y = 1500  # Much larger scale for better separation
        offset_x = 200  # Larger offset from edge
        offset_y = 200  # Larger offset from edge

        for item in items:
            # Normalize using global bounds to preserve relative positioning
            lat_range = self._global_bounds['max_lat'] - self._global_bounds['min_lat']
            lon_range = self._global_bounds['max_lon'] - self._global_bounds['min_lon']
            
            if lat_range > 0:
                normalized_lat = (item['x'] - self._global_bounds['min_lat']) / lat_range
            else:
                normalized_lat = 0.5
                
            if lon_range > 0:
                normalized_lon = (item['y'] - self._global_bounds['min_lon']) / lon_range
            else:
                normalized_lon = 0.5
            
            # Apply scaling and offset for UI
            item['x'] = normalized_lat * scale_x + offset_x
            item['y'] = normalized_lon * scale_y + offset_y

        return items
            
    def get_data_by_timestep(self, timestep: float) -> Optional[Dict[str, Any]]:
        """
        Retrieve vehicle data by timestep and normalize coordinates.
        Expected output format:
        {
            "step_id": timestep,
            "items": [
                {
                    "id": vehicle_id,
                    "x": lat,
                    "y": lon,
                    "speed": speed,
                    "acceleration": 0.0,  # default
                    "heading": angle,
                    "heading_change": 0.0,  # default
                    "size": 8  # default
                },
                ...
            ]
        }
        """
        if not self._data:
            return None
            
        items = []
        for row in self._data:
            if float(row["time"]) == float(timestep):
                items.append({
                    "id": row["vehicle_id"],
                    "x": float(row["lat"]),
                    "y": float(row["lon"]),
                    "speed": float(row["speed"]),
                    "acceleration": 0.0,
                    "heading": float(row["angle"]),
                    "heading_change": 0.0,
                    "size": 8
                })

        items = self._normalize_coordinates(items)

        return {
            "step_id": timestep,
            "items": items
        }


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

