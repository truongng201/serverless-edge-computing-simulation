import os
import csv
from collections import defaultdict

class DactDataLoader:
    def __init__(self, data_path: str = None):
        self._data_path = data_path or os.path.join(os.getcwd(), 'control/data/DACT-Easy-Dataset.csv')
        self._data = None
        self._load_data()

    def _load_data(self):
        """
        Load data from the specified CSV file and organize it by trip_id.
        """
        if not os.path.isfile(self._data_path):
            print(f"[ERROR] File not found: {self._data_path}")
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
                        print(f"[WARNING] Skipping row due to invalid data: {e}")

            # Convert to list format with item_id
            self._data = [
                {
                    "item_id": idx,
                    "trip_id": trip_id,
                    "steps": steps
                }
                for idx, (trip_id, steps) in enumerate(trip_dict.items(), start=1)
            ]

            if not self._data:
                print(f"[WARNING] Loaded file but found no valid trip data in: {self._data_path}")

        except Exception as e:
            print(f"[ERROR] Failed to read file {self._data_path}: {e}")
            self._data = []

    def get_data_by_trip_id(self, trip_id: str):
        """
        Retrieve data by trip_id.
        """
        if not self._data:
            return None
        return next((item for item in self._data if item['trip_id'] == trip_id), None)

    def _normalize_coordinates(self, items):
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
            item['x'] *= 5000  # Adjusted scale for better visibility
            item['y'] = (item['y'] - min_lon) / (max_lon - min_lon) if max_lon > min_lon else 0.5
            item['y'] *= 5000

        return items

    def get_data_by_step(self, step_id: int):
        """
        Retrieve data by item_id (sequential ID) and normalize coordinates.
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

        data = {
            "step_id": step_id,
            "items": items
        }
        return data

    def get_all_data(self):
        """
        Get the full dataset.
        """
        return self._data or []

    def __len__(self):
        """
        Get the number of trip items loaded.
        """
        return len(self._data or [])


class VehicleDataLoader:
    def __init__(self, data_path: str = None):
        self._data_path = data_path or os.path.join(os.getcwd(), 'control/data/vehicles_data_5min.csv')
        self._data = None
        self._load_data()
    
    def _load_data(self):
        """
        Load and preprocess vehicle data from the specified CSV file.
        Converts fields to appropriate types for later use.
        """
        if not os.path.isfile(self._data_path):
            print(f"[ERROR] File not found: {self._data_path}")
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
                        print(f"[WARN] Skipping malformed row: {row} - Error: {e}")
            if not self._data:
                print(f"[WARNING] Loaded file but found no valid vehicle data in: {self._data_path}")
        except Exception as e:
            print(f"[ERROR] Failed to read file {self._data_path}: {e}")
            self._data = []
            
    def _normalize_coordinates(self, items):
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
            
    def get_data_by_timestep(self, timestep: float):
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

            
            