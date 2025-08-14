"""
Central Node Control Layer - Prediction Module
Handles workload prediction and performance forecasting
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import pickle
import os

@dataclass
class PredictionInput:
    timestamp: datetime
    node_id: str
    features: Dict[str, float]  # CPU, memory, network, etc.

@dataclass
class PredictionOutput:
    predicted_load: float
    confidence_interval: tuple
    prediction_horizon: int  # minutes
    model_accuracy: float

class WorkloadPredictor:
    def __init__(self, model_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.models = {}  # One model per node or global model
        self.historical_data = {}
        self.model_path = model_path
        
        # Load pre-trained models if available
        if model_path and os.path.exists(model_path):
            self._load_models()
            
    def _load_models(self):
        """Load pre-trained prediction models"""
        try:
            with open(self.model_path, 'rb') as f:
                self.models = pickle.load(f)
            self.logger.info("Loaded pre-trained prediction models")
        except Exception as e:
            self.logger.error(f"Failed to load models: {e}")
            
    def _save_models(self):
        """Save trained models to disk"""
        if self.model_path:
            try:
                os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
                with open(self.model_path, 'wb') as f:
                    pickle.dump(self.models, f)
                self.logger.info("Saved prediction models")
            except Exception as e:
                self.logger.error(f"Failed to save models: {e}")
                
    def add_historical_data(self, node_id: str, data: List[PredictionInput]):
        """Add historical data for model training"""
        if node_id not in self.historical_data:
            self.historical_data[node_id] = []
        self.historical_data[node_id].extend(data)
        
    def predict_workload(self, node_id: str, horizon_minutes: int = 30) -> Optional[PredictionOutput]:
        """Predict workload for a specific node"""
        try:
            if node_id not in self.models:
                # Use global model or return simple prediction
                return self._simple_prediction(node_id, horizon_minutes)
                
            model = self.models[node_id]
            
            # Get recent data for prediction
            recent_data = self._get_recent_features(node_id)
            if not recent_data:
                return self._simple_prediction(node_id, horizon_minutes)
                
            # Make prediction
            predicted_load = model.predict(recent_data.reshape(1, -1))[0]
            
            # Calculate confidence interval (simplified)
            confidence_lower = max(0, predicted_load - 0.1)
            confidence_upper = min(1.0, predicted_load + 0.1)
            
            return PredictionOutput(
                predicted_load=predicted_load,
                confidence_interval=(confidence_lower, confidence_upper),
                prediction_horizon=horizon_minutes,
                model_accuracy=0.85  # TODO: Calculate actual accuracy
            )
            
        except Exception as e:
            self.logger.error(f"Prediction failed for node {node_id}: {e}")
            return self._simple_prediction(node_id, horizon_minutes)
            
    def _simple_prediction(self, node_id: str, horizon_minutes: int) -> PredictionOutput:
        """Simple prediction when no trained model is available"""
        # Use historical average or current load
        if node_id in self.historical_data and self.historical_data[node_id]:
            recent_loads = [data.features.get('cpu_usage', 0.5) 
                          for data in self.historical_data[node_id][-10:]]
            predicted_load = np.mean(recent_loads)
        else:
            predicted_load = 0.5  # Default prediction
            
        return PredictionOutput(
            predicted_load=predicted_load,
            confidence_interval=(predicted_load - 0.2, predicted_load + 0.2),
            prediction_horizon=horizon_minutes,
            model_accuracy=0.6
        )
        
    def _get_recent_features(self, node_id: str, lookback_minutes: int = 60) -> Optional[np.ndarray]:
        """Get recent feature data for prediction"""
        if node_id not in self.historical_data:
            return None
            
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(minutes=lookback_minutes)
        
        recent_data = [
            data for data in self.historical_data[node_id]
            if data.timestamp >= cutoff_time
        ]
        
        if not recent_data:
            return None
            
        # Extract features (simplified - using only CPU usage for now)
        features = [data.features.get('cpu_usage', 0.0) for data in recent_data]
        return np.array(features)
        
    def train_model(self, node_id: str):
        """Train prediction model for a specific node"""
        if node_id not in self.historical_data or len(self.historical_data[node_id]) < 100:
            self.logger.warning(f"Insufficient data to train model for node {node_id}")
            return
            
        try:
            from sklearn.linear_model import LinearRegression
            from sklearn.preprocessing import StandardScaler
            
            # Prepare training data
            data = self.historical_data[node_id]
            X, y = self._prepare_training_data(data)
            
            if len(X) < 10:
                return
                
            # Train model
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            model = LinearRegression()
            model.fit(X_scaled, y)
            
            # Store model and scaler
            self.models[node_id] = {
                'model': model,
                'scaler': scaler
            }
            
            self.logger.info(f"Trained prediction model for node {node_id}")
            self._save_models()
            
        except Exception as e:
            self.logger.error(f"Failed to train model for node {node_id}: {e}")
            
    def _prepare_training_data(self, data: List[PredictionInput]):
        """Prepare training data from historical data"""
        # Simple time series approach - use past values to predict future
        features = []
        targets = []
        
        # Sort by timestamp
        sorted_data = sorted(data, key=lambda x: x.timestamp)
        
        window_size = 5  # Use last 5 data points to predict next one
        
        for i in range(window_size, len(sorted_data)):
            # Features: past window of CPU usage
            feature_window = [
                sorted_data[j].features.get('cpu_usage', 0.0)
                for j in range(i - window_size, i)
            ]
            features.append(feature_window)
            
            # Target: current CPU usage
            targets.append(sorted_data[i].features.get('cpu_usage', 0.0))
            
        return np.array(features), np.array(targets)
        
    def get_prediction_accuracy(self, node_id: str) -> float:
        """Get prediction accuracy for a node"""
        if node_id not in self.models:
            return 0.0
            
        # TODO: Implement actual accuracy calculation
        return 0.85
        
    def update_model(self, node_id: str, actual_data: List[PredictionInput]):
        """Update model with new actual data"""
        self.add_historical_data(node_id, actual_data)
        
        # Retrain if we have enough new data
        if len(actual_data) >= 50:
            self.train_model(node_id)
