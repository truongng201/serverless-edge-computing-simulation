import os
import csv
import logging
from collections import defaultdict
from typing import Dict, Any, List, Optional

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