"""
Data Manager for Central Node Control Layer
Handles data loading and simulation data management for the UI
"""

import os
import csv
import logging
from collections import defaultdict
from typing import Dict, Any, List, Optional

class DataManager:
    """
    Manages simulation data for the central node UI.
    Provides data loading capabilities for DACT and vehicle datasets.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.dact_loader = DactDataLoader()
        self.vehicle_loader = VehicleDataLoader()
        
    def get_vehicle_data_by_timestep(self, timestep: float) -> Optional[Dict[str, Any]]:
        """Get vehicle data for a specific timestep"""
        return self.vehicle_loader.get_data_by_timestep(timestep)
        
    def get_dact_data_by_step(self, step_id: int) -> Optional[Dict[str, Any]]:
        """Get DACT data for a specific step"""
        return self.dact_loader.get_data_by_step(step_id)


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
        Normalize the x (latitude) and y (longitude) coordinates to a range of 0 to 1 and apply a new scaling factor.
        """
        if not items:
            return items

        min_lat = min(item['x'] for item in items)
        max_lat = max(item['x'] for item in items)
        min_lon = min(item['y'] for item in items)
        max_lon = max(item['y'] for item in items)

        for item in items:
            item['x'] = (item['x'] - min_lat) / (max_lat - min_lat) if max_lat > min_lat else 0.5
            item['x'] *= 1000  # Adjusted scale for better visibility
            item['y'] = (item['y'] - min_lon) / (max_lon - min_lon) if max_lon > min_lon else 0.5
            item['y'] *= 1000

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
        Normalize the x (latitude) and y (longitude) coordinates to a range of 0 to 1 and apply a new scaling factor.
        """
        if not items:
            return items

        min_lat = min(item['x'] for item in items)
        max_lat = max(item['x'] for item in items)
        min_lon = min(item['y'] for item in items)
        max_lon = max(item['y'] for item in items)

        for item in items:
            item['x'] = (item['x'] - min_lat) / (max_lat - min_lat) if max_lat > min_lat else 0.5
            item['x'] *= 1000  # Adjusted scale for better visibility
            item['y'] = (item['y'] - min_lon) / (max_lon - min_lon) if max_lon > min_lon else 0.5
            item['y'] *= 1000

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
