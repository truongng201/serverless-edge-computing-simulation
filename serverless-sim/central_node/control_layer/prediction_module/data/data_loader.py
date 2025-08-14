#!/usr/bin/env python3
"""
DACT Data Loader for LSTM Training
Handles data loading, preprocessing, and sequence generation
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
from typing import Tuple, List, Dict
import warnings
warnings.filterwarnings('ignore')

class DACTDataLoader:
    """Load and preprocess DACT dataset for LSTM training"""
    
    def __init__(self, csv_path: str = None, sequence_length: int = 5):
        """
        Initialize data loader
        
        Args:
            csv_path: Path to DACT CSV file
            sequence_length: Length of input sequences for LSTM
        """
        self.csv_path = csv_path or Path(__file__).parent.parent.parent / "DACT Easy-Dataset.csv"
        self.sequence_length = sequence_length
        self.data = None
        self.scalers = {}
        self.bounds = {}
        
    def load_data(self) -> pd.DataFrame:
        """Load DACT dataset"""
        print(f"[DATA] Loading DACT dataset from: {self.csv_path}")
        
        if not Path(self.csv_path).exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")
        
        self.data = pd.read_csv(self.csv_path)
        
        # Convert numeric columns
        numeric_cols = ['TimeStep', 'Speed', 'Acceleration', 'Heading', 
                       'HeadingChange', 'Latitude', 'Longitude']
        
        for col in numeric_cols:
            if col in self.data.columns:
                self.data[col] = pd.to_numeric(self.data[col], errors='coerce')
        
        print(f"[OK] Loaded {len(self.data):,} records with {self.data['TripID'].nunique()} trips")
        return self.data
    
    def calculate_bounds(self) -> Dict:
        """Calculate geographical bounds for normalization"""
        self.bounds = {
            'lat_min': self.data['Latitude'].min(),
            'lat_max': self.data['Latitude'].max(),
            'lng_min': self.data['Longitude'].min(),
            'lng_max': self.data['Longitude'].max(),
            'speed_min': self.data['Speed'].min(),
            'speed_max': self.data['Speed'].max(),
            'heading_min': 0.0,
            'heading_max': 360.0,
            'accel_min': self.data['Acceleration'].min(),
            'accel_max': self.data['Acceleration'].max()
        }
        
        print(f"[BOUNDS] Geographical bounds:")
        print(f"  Lat: {self.bounds['lat_min']:.6f} to {self.bounds['lat_max']:.6f}")
        print(f"  Lng: {self.bounds['lng_min']:.6f} to {self.bounds['lng_max']:.6f}")
        print(f"  Speed: {self.bounds['speed_min']:.1f} to {self.bounds['speed_max']:.1f} mph")
        
        return self.bounds
    
    def normalize_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Normalize features to 0-1 range"""
        normalized_data = data.copy()
        
        # Normalize coordinates
        normalized_data['lat_norm'] = (data['Latitude'] - self.bounds['lat_min']) / \
                                     (self.bounds['lat_max'] - self.bounds['lat_min'])
        normalized_data['lng_norm'] = (data['Longitude'] - self.bounds['lng_min']) / \
                                     (self.bounds['lng_max'] - self.bounds['lng_min'])
        
        # Normalize speed (0-1)
        normalized_data['speed_norm'] = (data['Speed'] - self.bounds['speed_min']) / \
                                       (self.bounds['speed_max'] - self.bounds['speed_min'])
        
        # Normalize heading (0-1)
        normalized_data['heading_norm'] = data['Heading'] / 360.0
        
        # Normalize acceleration (center around 0, scale by max abs value)
        max_abs_accel = max(abs(self.bounds['accel_min']), abs(self.bounds['accel_max']))
        normalized_data['accel_norm'] = (data['Acceleration'] + max_abs_accel) / (2 * max_abs_accel)
        
        return normalized_data
    
    def denormalize_coordinates(self, lat_norm: float, lng_norm: float) -> Tuple[float, float]:
        """Convert normalized coordinates back to actual lat/lng"""
        lat = lat_norm * (self.bounds['lat_max'] - self.bounds['lat_min']) + self.bounds['lat_min']
        lng = lng_norm * (self.bounds['lng_max'] - self.bounds['lng_min']) + self.bounds['lng_min']
        return lat, lng
    
    def coord_to_pixels(self, lat: float, lng: float, canvas_size: Tuple[int, int] = (1200, 800)) -> Tuple[float, float]:
        """Convert lat/lng to pixel coordinates"""
        # Normalize coordinates first
        lat_norm = (lat - self.bounds['lat_min']) / (self.bounds['lat_max'] - self.bounds['lat_min'])
        lng_norm = (lng - self.bounds['lng_min']) / (self.bounds['lng_max'] - self.bounds['lng_min'])
        
        # Convert to pixels with margin
        margin = 50
        x = lng_norm * (canvas_size[0] - 2 * margin) + margin
        y = lat_norm * (canvas_size[1] - 2 * margin) + margin
        
        return x, y
    
    def create_sequences(self, trip_ids: List[str]) -> Tuple[np.ndarray, np.ndarray, List[Dict]]:
        """
        Create LSTM training sequences from specified trips
        
        Args:
            trip_ids: List of trip IDs to process
            
        Returns:
            X: Input sequences [samples, timesteps, features]
            y: Target coordinates [samples, 2]
            metadata: List of metadata for each sequence
        """
        if self.data is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        # Normalize features
        normalized_data = self.normalize_features(self.data)
        
        X_sequences = []
        y_sequences = []
        metadata = []
        
        for trip_id in trip_ids:
            trip_data = normalized_data[normalized_data['TripID'] == trip_id].copy()
            trip_data = trip_data.sort_values('TimeStep').reset_index(drop=True)
            
            if len(trip_data) <= self.sequence_length:
                continue
            
            # Create sequences for this trip
            for i in range(self.sequence_length, len(trip_data)):
                # Input sequence: last N timesteps
                input_sequence = []
                for j in range(i - self.sequence_length, i):
                    row = trip_data.iloc[j]
                    features = [
                        row['lat_norm'],
                        row['lng_norm'], 
                        row['speed_norm'],
                        row['heading_norm'],
                        row['accel_norm']
                    ]
                    input_sequence.append(features)
                
                # Target: next position (normalized)
                target_row = trip_data.iloc[i]
                target = [target_row['lat_norm'], target_row['lng_norm']]
                
                X_sequences.append(input_sequence)
                y_sequences.append(target)
                
                # Metadata for tracking
                metadata.append({
                    'trip_id': trip_id,
                    'timestep': target_row['TimeStep'],
                    'actual_lat': target_row['Latitude'],
                    'actual_lng': target_row['Longitude'],
                    'speed': target_row['Speed'],
                    'sequence_index': i
                })
        
        X = np.array(X_sequences, dtype=np.float32)
        y = np.array(y_sequences, dtype=np.float32)
        
        print(f"[DATA] Created {len(X):,} sequences from {len(trip_ids)} trips")
        print(f"   Input shape: {X.shape}")
        print(f"   Output shape: {y.shape}")
        
        return X, y, metadata
    
    def split_trips(self, train_count: int = 30, test_count: int = 20) -> Tuple[List[str], List[str]]:
        """
        Split trips into train and test sets
        
        Args:
            train_count: Number of trips for training
            test_count: Number of trips for testing
            
        Returns:
            train_trips: List of training trip IDs
            test_trips: List of testing trip IDs
        """
        if self.data is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        all_trips = sorted(self.data['TripID'].unique(), 
                          key=lambda x: int(x.split('-')[1]))  # Extract number from T-X
        
        if len(all_trips) < train_count + test_count:
            raise ValueError(f"Not enough trips. Available: {len(all_trips)}, "
                           f"Requested: {train_count + test_count}")
        
        train_trips = all_trips[:train_count]
        test_trips = all_trips[train_count:train_count + test_count]
        
        print(f"[DATA] Dataset Split:")
        print(f"   Training trips: {len(train_trips)} ({train_trips[0]} to {train_trips[-1]})")
        print(f"   Testing trips: {len(test_trips)} ({test_trips[0]} to {test_trips[-1]})")
        
        return train_trips, test_trips
    
    def get_trip_stats(self, trip_ids: List[str]) -> Dict:
        """Get statistics for specified trips"""
        trip_data = self.data[self.data['TripID'].isin(trip_ids)]
        
        trip_lengths = trip_data.groupby('TripID').size()
        
        stats = {
            'trip_count': len(trip_ids),
            'total_timesteps': len(trip_data),
            'avg_trip_length': trip_lengths.mean(),
            'min_trip_length': trip_lengths.min(),
            'max_trip_length': trip_lengths.max(),
            'potential_sequences': sum(max(0, length - self.sequence_length) 
                                     for length in trip_lengths)
        }
        
        return stats
    
    def prepare_for_training(self, train_count: int = 30, test_count: int = 20) -> Dict:
        """
        Complete data preparation pipeline
        
        Returns:
            Dictionary with all prepared data and metadata
        """
        print("[PREP] Preparing DACT data for LSTM training...")
        
        # Load and process data
        self.load_data()
        self.calculate_bounds()
        
        # Split trips
        train_trips, test_trips = self.split_trips(train_count, test_count)
        
        # Create sequences
        print(f"\nCreating training sequences...")
        X_train, y_train, train_metadata = self.create_sequences(train_trips)
        
        print(f"\nCreating testing sequences...")
        X_test, y_test, test_metadata = self.create_sequences(test_trips)
        
        # Get statistics
        train_stats = self.get_trip_stats(train_trips)
        test_stats = self.get_trip_stats(test_trips)
        
        print(f"\n[DATA] Final Statistics:")
        print(f"   Training: {train_stats['potential_sequences']:,} sequences from {train_stats['trip_count']} trips")
        print(f"   Testing: {test_stats['potential_sequences']:,} sequences from {test_stats['trip_count']} trips")
        
        return {
            'X_train': X_train,
            'y_train': y_train,
            'X_test': X_test,
            'y_test': y_test,
            'train_metadata': train_metadata,
            'test_metadata': test_metadata,
            'train_trips': train_trips,
            'test_trips': test_trips,
            'bounds': self.bounds,
            'sequence_length': self.sequence_length,
            'train_stats': train_stats,
            'test_stats': test_stats
        }

# Convenience function
def load_dact_data(sequence_length: int = 5, train_count: int = 30, test_count: int = 20) -> Dict:
    """Convenience function to load and prepare DACT data"""
    loader = DACTDataLoader(sequence_length=sequence_length)
    return loader.prepare_for_training(train_count, test_count) 