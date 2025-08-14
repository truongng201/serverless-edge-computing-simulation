#!/usr/bin/env python3
"""
Enhanced DACT Data Loader with Advanced Feature Engineering
Includes velocity vectors, acceleration patterns, distance features, and time-based features
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from typing import Tuple, List, Dict, Optional
import warnings
warnings.filterwarnings('ignore')

class EnhancedDACTDataLoader:
    """Enhanced data loader with advanced feature engineering for LSTM training"""
    
    def __init__(self, csv_path: str = None, sequence_length: int = 10):
        """
        Initialize enhanced data loader
        
        Args:
            csv_path: Path to DACT CSV file
            sequence_length: Length of input sequences for LSTM (increased to 10)
        """
        self.csv_path = csv_path or Path(__file__).parent.parent.parent / "DACT Easy-Dataset.csv"
        self.sequence_length = sequence_length
        self.data = None
        self.enhanced_data = None
        self.scalers = {}
        self.bounds = {}
        self.feature_names = []
        
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
    
    def calculate_velocity_features(self, trip_data: pd.DataFrame) -> pd.DataFrame:
        """Calculate velocity and movement-based features"""
        enhanced = trip_data.copy()
        
        # Sort by timestep to ensure correct order
        enhanced = enhanced.sort_values('TimeStep').reset_index(drop=True)
        
        # Calculate time differences (assuming 1 second per timestep)
        enhanced['dt'] = 1.0  # seconds per timestep
        
        # Calculate position differences
        enhanced['dlat'] = enhanced['Latitude'].diff().fillna(0)
        enhanced['dlng'] = enhanced['Longitude'].diff().fillna(0)
        
        # Calculate velocity vectors (degrees per second)
        enhanced['velocity_lat'] = enhanced['dlat'] / enhanced['dt']
        enhanced['velocity_lng'] = enhanced['dlng'] / enhanced['dt']
        
        # Calculate velocity magnitude and direction
        enhanced['velocity_magnitude'] = np.sqrt(enhanced['velocity_lat']**2 + enhanced['velocity_lng']**2)
        enhanced['velocity_direction'] = np.arctan2(enhanced['velocity_lat'], enhanced['velocity_lng']) * 180 / np.pi
        enhanced['velocity_direction'] = (enhanced['velocity_direction'] + 360) % 360  # 0-360 degrees
        
        # Calculate acceleration vectors
        enhanced['accel_lat'] = enhanced['velocity_lat'].diff().fillna(0) / enhanced['dt']
        enhanced['accel_lng'] = enhanced['velocity_lng'].diff().fillna(0) / enhanced['dt']
        enhanced['accel_magnitude'] = np.sqrt(enhanced['accel_lat']**2 + enhanced['accel_lng']**2)
        
        # Speed change rate (mph/s)
        enhanced['speed_change_rate'] = enhanced['Speed'].diff().fillna(0) / enhanced['dt']
        
        # Heading change rate (degrees/s)  
        enhanced['heading_change_rate'] = enhanced['HeadingChange'].fillna(0) / enhanced['dt']
        
        # Jerk (rate of acceleration change)
        enhanced['jerk_lat'] = enhanced['accel_lat'].diff().fillna(0) / enhanced['dt']
        enhanced['jerk_lng'] = enhanced['accel_lng'].diff().fillna(0) / enhanced['dt']
        enhanced['jerk_magnitude'] = np.sqrt(enhanced['jerk_lat']**2 + enhanced['jerk_lng']**2)
        
        return enhanced
    
    def calculate_distance_features(self, trip_data: pd.DataFrame) -> pd.DataFrame:
        """Calculate distance-based features"""
        enhanced = trip_data.copy()
        
        # Distance from trip start
        start_lat, start_lng = enhanced.iloc[0]['Latitude'], enhanced.iloc[0]['Longitude']
        enhanced['dist_from_start'] = np.sqrt(
            (enhanced['Latitude'] - start_lat)**2 + 
            (enhanced['Longitude'] - start_lng)**2
        )
        
        # Distance from trip end
        end_lat, end_lng = enhanced.iloc[-1]['Latitude'], enhanced.iloc[-1]['Longitude']
        enhanced['dist_from_end'] = np.sqrt(
            (enhanced['Latitude'] - end_lat)**2 + 
            (enhanced['Longitude'] - end_lng)**2
        )
        
        # Cumulative distance traveled
        distances = np.sqrt(enhanced['dlat']**2 + enhanced['dlng']**2)
        enhanced['cumulative_distance'] = distances.cumsum()
        
        # Distance to trip centroid
        centroid_lat, centroid_lng = enhanced['Latitude'].mean(), enhanced['Longitude'].mean()
        enhanced['dist_from_centroid'] = np.sqrt(
            (enhanced['Latitude'] - centroid_lat)**2 + 
            (enhanced['Longitude'] - centroid_lng)**2
        )
        
        # Relative position in trip (0 to 1)
        enhanced['trip_progress'] = np.linspace(0, 1, len(enhanced))
        
        return enhanced
    
    def calculate_temporal_features(self, trip_data: pd.DataFrame) -> pd.DataFrame:
        """Calculate time-based features"""
        enhanced = trip_data.copy()
        
        # Time since trip start (normalized)
        enhanced['time_since_start'] = (enhanced['TimeStep'] - enhanced['TimeStep'].min()) / enhanced['TimeStep'].max()
        
        # Time until trip end (normalized)
        enhanced['time_until_end'] = (enhanced['TimeStep'].max() - enhanced['TimeStep']) / enhanced['TimeStep'].max()
        
        # Trip duration feature
        trip_duration = enhanced['TimeStep'].max() - enhanced['TimeStep'].min()
        enhanced['trip_duration'] = trip_duration
        
        # Rolling statistics (last 3 timesteps)
        window_size = min(3, len(enhanced))
        enhanced['speed_rolling_mean'] = enhanced['Speed'].rolling(window=window_size, min_periods=1).mean()
        enhanced['speed_rolling_std'] = enhanced['Speed'].rolling(window=window_size, min_periods=1).std().fillna(0)
        
        enhanced['heading_rolling_mean'] = enhanced['Heading'].rolling(window=window_size, min_periods=1).mean()
        enhanced['heading_rolling_std'] = enhanced['Heading'].rolling(window=window_size, min_periods=1).std().fillna(0)
        
        return enhanced
    
    def calculate_behavior_features(self, trip_data: pd.DataFrame) -> pd.DataFrame:
        """Calculate behavior and pattern-based features"""
        enhanced = trip_data.copy()
        
        # Turn detection (based on heading change)
        enhanced['is_turning'] = (np.abs(enhanced['HeadingChange'].fillna(0)) > 15).astype(float)
        enhanced['turn_intensity'] = np.abs(enhanced['HeadingChange'].fillna(0)) / 180.0  # Normalized
        
        # Speed behavior
        speed_mean = enhanced['Speed'].mean()
        enhanced['speed_relative'] = enhanced['Speed'] / (speed_mean + 1e-6)  # Relative to trip average
        enhanced['is_accelerating'] = (enhanced['Acceleration'] > 0.5).astype(float)
        enhanced['is_decelerating'] = (enhanced['Acceleration'] < -0.5).astype(float)
        enhanced['is_constant_speed'] = (np.abs(enhanced['Acceleration']) <= 0.5).astype(float)
        
        # Movement patterns
        enhanced['is_high_speed'] = (enhanced['Speed'] > enhanced['Speed'].quantile(0.75)).astype(float)
        enhanced['is_low_speed'] = (enhanced['Speed'] < enhanced['Speed'].quantile(0.25)).astype(float)
        
        # Consistency features
        enhanced['speed_consistency'] = 1.0 / (1.0 + np.abs(enhanced['speed_change_rate']))
        enhanced['heading_consistency'] = 1.0 / (1.0 + np.abs(enhanced['heading_change_rate']))
        
        return enhanced
    
    def create_enhanced_features(self) -> pd.DataFrame:
        """Create all enhanced features for the dataset"""
        if self.data is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        print(f"[FIX] Creating enhanced features...")
        
        enhanced_trips = []
        
        for trip_id in sorted(self.data['TripID'].unique()):
            trip_data = self.data[self.data['TripID'] == trip_id].copy()
            
            if len(trip_data) < 3:  # Skip very short trips
                continue
            
            # Apply all feature engineering steps
            trip_data = self.calculate_velocity_features(trip_data)
            trip_data = self.calculate_distance_features(trip_data)
            trip_data = self.calculate_temporal_features(trip_data)
            trip_data = self.calculate_behavior_features(trip_data)
            
            enhanced_trips.append(trip_data)
        
        self.enhanced_data = pd.concat(enhanced_trips, ignore_index=True)
        
        # Define feature columns for ML
        self.feature_names = [
            # Original coordinates and movement
            'lat_norm', 'lng_norm', 'speed_norm', 'heading_norm', 'acceleration_norm',
            
            # Velocity features
            'velocity_lat_norm', 'velocity_lng_norm', 'velocity_magnitude_norm', 'velocity_direction_norm',
            
            # Acceleration features  
            'accel_lat_norm', 'accel_lng_norm', 'accel_magnitude_norm',
            
            # Movement rates
            'speed_change_rate_norm', 'heading_change_rate_norm',
            
            # Distance features
            'dist_from_start_norm', 'dist_from_end_norm', 'cumulative_distance_norm', 'dist_from_centroid_norm',
            
            # Temporal features
            'trip_progress', 'time_since_start', 'time_until_end',
            'speed_rolling_mean_norm', 'speed_rolling_std_norm',
            
            # Behavior features
            'is_turning', 'turn_intensity', 'speed_relative_norm',
            'is_accelerating', 'is_decelerating', 'is_constant_speed',
            'is_high_speed', 'is_low_speed',
            'speed_consistency', 'heading_consistency'
        ]
        
        print(f"[OK] Created enhanced features: {len(self.feature_names)} features per timestep")
        print(f"   Total enhanced records: {len(self.enhanced_data):,}")
        
        return self.enhanced_data
    
    def calculate_bounds(self) -> Dict:
        """Calculate bounds for all features"""
        if self.enhanced_data is None:
            raise ValueError("Enhanced data not created. Call create_enhanced_features() first.")
        
        print(f"[DATA] Calculating feature bounds...")
        
        # Original bounds
        self.bounds = {
            'lat_min': self.enhanced_data['Latitude'].min(),
            'lat_max': self.enhanced_data['Latitude'].max(),
            'lng_min': self.enhanced_data['Longitude'].min(),
            'lng_max': self.enhanced_data['Longitude'].max(),
            'speed_min': self.enhanced_data['Speed'].min(),
            'speed_max': self.enhanced_data['Speed'].max(),
            'heading_min': 0.0,
            'heading_max': 360.0,
            'accel_min': self.enhanced_data['Acceleration'].min(),
            'accel_max': self.enhanced_data['Acceleration'].max()
        }
        
        # Enhanced feature bounds
        feature_columns = [
            'velocity_lat', 'velocity_lng', 'velocity_magnitude', 'velocity_direction',
            'accel_lat', 'accel_lng', 'accel_magnitude',
            'speed_change_rate', 'heading_change_rate',
            'dist_from_start', 'dist_from_end', 'cumulative_distance', 'dist_from_centroid',
            'speed_rolling_mean', 'speed_rolling_std', 'speed_relative'
        ]
        
        for col in feature_columns:
            if col in self.enhanced_data.columns:
                self.bounds[f'{col}_min'] = self.enhanced_data[col].min()
                self.bounds[f'{col}_max'] = self.enhanced_data[col].max()
        
        print(f"[OK] Calculated bounds for {len(self.bounds)} features")
        return self.bounds
    
    def normalize_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Normalize all features to appropriate ranges"""
        normalized_data = data.copy()
        
        # Basic coordinate normalization
        lat_span = self.bounds['lat_max'] - self.bounds['lat_min']
        lng_span = self.bounds['lng_max'] - self.bounds['lng_min']
        
        normalized_data['lat_norm'] = (data['Latitude'] - self.bounds['lat_min']) / lat_span
        normalized_data['lng_norm'] = (data['Longitude'] - self.bounds['lng_min']) / lng_span
        normalized_data['speed_norm'] = data['Speed'] / (self.bounds['speed_max'] + 1e-6)
        normalized_data['heading_norm'] = data['Heading'] / 360.0
        
        # Acceleration (center around 0)
        max_abs_accel = max(abs(self.bounds['accel_min']), abs(self.bounds['accel_max']))
        normalized_data['acceleration_norm'] = (data['Acceleration'] + max_abs_accel) / (2 * max_abs_accel + 1e-6)
        
        # Velocity features
        velocity_features = ['velocity_lat', 'velocity_lng', 'velocity_magnitude']
        for feat in velocity_features:
            if feat in data.columns and f'{feat}_max' in self.bounds:
                feat_span = self.bounds[f'{feat}_max'] - self.bounds[f'{feat}_min']
                if feat_span > 1e-6:
                    normalized_data[f'{feat}_norm'] = (data[feat] - self.bounds[f'{feat}_min']) / feat_span
                else:
                    normalized_data[f'{feat}_norm'] = 0.0
        
        # Velocity direction (0-1)
        if 'velocity_direction' in data.columns:
            normalized_data['velocity_direction_norm'] = data['velocity_direction'] / 360.0
        
        # Acceleration features (center around 0)
        accel_features = ['accel_lat', 'accel_lng', 'accel_magnitude']
        for feat in accel_features:
            if feat in data.columns and f'{feat}_max' in self.bounds:
                max_abs = max(abs(self.bounds[f'{feat}_min']), abs(self.bounds[f'{feat}_max']))
                if max_abs > 1e-6:
                    normalized_data[f'{feat}_norm'] = (data[feat] + max_abs) / (2 * max_abs)
                else:
                    normalized_data[f'{feat}_norm'] = 0.5
        
        # Rate features (center around 0)
        rate_features = ['speed_change_rate', 'heading_change_rate']
        for feat in rate_features:
            if feat in data.columns and f'{feat}_max' in self.bounds:
                max_abs = max(abs(self.bounds[f'{feat}_min']), abs(self.bounds[f'{feat}_max']))
                if max_abs > 1e-6:
                    normalized_data[f'{feat}_norm'] = (data[feat] + max_abs) / (2 * max_abs)
                else:
                    normalized_data[f'{feat}_norm'] = 0.5
        
        # Distance features (0-1)
        distance_features = ['dist_from_start', 'dist_from_end', 'cumulative_distance', 'dist_from_centroid']
        for feat in distance_features:
            if feat in data.columns and f'{feat}_max' in self.bounds:
                feat_span = self.bounds[f'{feat}_max'] - self.bounds[f'{feat}_min']
                if feat_span > 1e-6:
                    normalized_data[f'{feat}_norm'] = (data[feat] - self.bounds[f'{feat}_min']) / feat_span
                else:
                    normalized_data[f'{feat}_norm'] = 0.0
        
        # Rolling statistics
        rolling_features = ['speed_rolling_mean', 'speed_rolling_std']
        for feat in rolling_features:
            if feat in data.columns and f'{feat}_max' in self.bounds:
                if feat == 'speed_rolling_mean':
                    normalized_data[f'{feat}_norm'] = data[feat] / (self.bounds['speed_max'] + 1e-6)
                else:  # std features
                    normalized_data[f'{feat}_norm'] = data[feat] / (self.bounds[f'{feat}_max'] + 1e-6)
        
        # Speed relative (already relative)
        if 'speed_relative' in data.columns:
            max_rel = self.bounds.get('speed_relative_max', 1.0)
            normalized_data['speed_relative_norm'] = np.clip(data['speed_relative'] / (max_rel + 1e-6), 0, 1)
        
        return normalized_data
    
    def create_sequences(self, trip_ids: List[str]) -> Tuple[np.ndarray, np.ndarray, List[Dict]]:
        """Create enhanced LSTM training sequences from specified trips"""
        if self.enhanced_data is None:
            raise ValueError("Enhanced data not created. Call create_enhanced_features() first.")
        
        # Normalize features
        normalized_data = self.normalize_features(self.enhanced_data)
        
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
                # Input sequence: last N timesteps with enhanced features
                input_sequence = []
                for j in range(i - self.sequence_length, i):
                    row = trip_data.iloc[j]
                    features = [row[feat] for feat in self.feature_names if feat in row]
                    input_sequence.append(features)
                
                # Target: next position (normalized coordinates only)
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
        
        print(f"[DATA] Created {len(X):,} enhanced sequences from {len(trip_ids)} trips")
        print(f"   Input shape: {X.shape}")
        print(f"   Output shape: {y.shape}")
        print(f"   Features per timestep: {len(self.feature_names)}")
        
        return X, y, metadata
    
    def prepare_for_training(self, train_count: int = 30, test_count: int = 20) -> Dict:
        """Complete enhanced data preparation pipeline"""
        print("[TRAINING] Preparing Enhanced DACT data for LSTM training...")
        
        # Load and process data
        self.load_data()
        self.create_enhanced_features()
        self.calculate_bounds()
        
        # Split trips (sort numerically, not alphabetically)
        all_trips = sorted(self.enhanced_data['TripID'].unique(), 
                          key=lambda x: int(x.split('-')[1]))  # Extract number from T-X
        train_trips = all_trips[:train_count]
        test_trips = all_trips[train_count:train_count + test_count]
        
        print(f"\n[DATA] Dataset Split:")
        print(f"   Training trips: {len(train_trips)} ({train_trips[0]} to {train_trips[-1]})")
        print(f"   Testing trips: {len(test_trips)} ({test_trips[0]} to {test_trips[-1]})")
        
        # Create sequences
        print(f"\n📚 Creating enhanced training sequences...")
        X_train, y_train, train_metadata = self.create_sequences(train_trips)
        
        print(f"\n🧪 Creating enhanced testing sequences...")
        X_test, y_test, test_metadata = self.create_sequences(test_trips)
        
        print(f"\n[DATA] Enhanced Data Statistics:")
        print(f"   Training: {len(X_train):,} sequences from {len(train_trips)} trips")
        print(f"   Testing: {len(X_test):,} sequences from {len(test_trips)} trips")
        print(f"   Feature count: {len(self.feature_names)} enhanced features")
        print(f"   Sequence length: {self.sequence_length} timesteps")
        
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
            'feature_names': self.feature_names,
            'feature_count': len(self.feature_names)
        }

# Convenience function
def load_enhanced_dact_data(sequence_length: int = 10, train_count: int = 30, test_count: int = 20) -> Dict:
    """Convenience function to load and prepare enhanced DACT data"""
    loader = EnhancedDACTDataLoader(sequence_length=sequence_length)
    return loader.prepare_for_training(train_count, test_count) 