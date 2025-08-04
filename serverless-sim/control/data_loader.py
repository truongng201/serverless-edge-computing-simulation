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

    def get_data_by_step(self, step_id: int):
        """
        Retrieve data by item_id (sequential ID).
        """
        if not self._data:
            return None

        items = []
        
        for item in self._data:
            for step in item['steps']:
                if step['timestep'] == step_id:
                    items.append({
                        "item_id": item['item_id'],
                        "location": step['location'],
                        "speed": step['speed'],
                        "acceleration": step['acceleration'],
                        "heading": step['heading'],
                        "heading_change": step['heading_change']
                    })
                    break
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
