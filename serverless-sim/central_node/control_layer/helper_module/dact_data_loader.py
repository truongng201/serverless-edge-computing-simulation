import os
import csv
import logging
from collections import defaultdict
from typing import Dict, Any, List, Optional

class DactDataLoader:
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
