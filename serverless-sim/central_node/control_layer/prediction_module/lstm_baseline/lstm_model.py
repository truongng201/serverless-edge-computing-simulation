#!/usr/bin/env python3
"""
LSTM Model for Trajectory Prediction
Using TensorFlow/Keras for position prediction based on sequence of movements
"""

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from typing import Tuple, Dict, Optional
import matplotlib.pyplot as plt

class LSTMTrajectoryModel:
    """LSTM model for predicting next position based on movement history"""
    
    def __init__(self, config: Dict = None):
        """
        Initialize LSTM model with configuration
        
        Args:
            config: Model configuration dictionary
        """
        self.config = {
            'sequence_length': 5,
            'input_features': 5,  # lat, lng, speed, heading, acceleration
            'output_features': 2,  # predicted lat, lng
            'lstm_units': [64, 32],  # LSTM layer sizes
            'dropout_rate': 0.2,
            'learning_rate': 0.001,
            'batch_size': 32,
            'epochs': 50,
            'validation_split': 0.2,
            'patience': 10  # Early stopping patience
        }
        
        if config:
            self.config.update(config)
        
        self.model = None
        self.history = None
        
    def build_model(self) -> keras.Model:
        """Build LSTM architecture"""
        print("[MODEL] Building LSTM model architecture...")
        
        # Input layer
        inputs = keras.Input(
            shape=(self.config['sequence_length'], self.config['input_features']),
            name='trajectory_input'
        )
        
        # LSTM layers
        x = inputs
        for i, units in enumerate(self.config['lstm_units']):
            return_sequences = i < len(self.config['lstm_units']) - 1
            
            x = layers.LSTM(
                units=units,
                return_sequences=return_sequences,
                dropout=self.config['dropout_rate'],
                recurrent_dropout=self.config['dropout_rate'],
                name=f'lstm_{i+1}'
            )(x)
            
            # Batch normalization
            x = layers.BatchNormalization(name=f'batch_norm_{i+1}')(x)
        
        # Dense layers for coordinate prediction
        x = layers.Dense(
            units=32,
            activation='relu',
            name='dense_1'
        )(x)
        
        x = layers.Dropout(self.config['dropout_rate'], name='dropout_dense')(x)
        
        # Output layer: predicted coordinates (normalized 0-1)
        outputs = layers.Dense(
            units=self.config['output_features'],
            activation='sigmoid',  # Sigmoid for normalized coordinates
            name='coordinate_output'
        )(x)
        
        # Create model
        self.model = keras.Model(inputs=inputs, outputs=outputs, name='lstm_trajectory_predictor')
        
        # Compile model
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=self.config['learning_rate']),
            loss='mse',
            metrics=['mae', 'mse']
        )
        
        print("[OK] Model architecture:")
        self.model.summary()
        
        return self.model
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray, 
              X_val: Optional[np.ndarray] = None, y_val: Optional[np.ndarray] = None,
              verbose: int = 1) -> keras.callbacks.History:
        """
        Train the LSTM model
        
        Args:
            X_train: Training input sequences
            y_train: Training target coordinates
            X_val: Validation input sequences (optional)
            y_val: Validation target coordinates (optional)
            verbose: Training verbosity
            
        Returns:
            Training history
        """
        if self.model is None:
            self.build_model()
        
        print(f"[TRAINING] Training LSTM model...")
        print(f"   Training data: {X_train.shape[0]:,} sequences")
        print(f"   Input shape: {X_train.shape}")
        print(f"   Output shape: {y_train.shape}")
        
        # Callbacks
        callbacks = [
            keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=self.config['patience'],
                restore_best_weights=True,
                verbose=1
            ),
            keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=5,
                min_lr=1e-6,
                verbose=1
            )
        ]
        
        # Prepare validation data
        validation_data = None
        if X_val is not None and y_val is not None:
            validation_data = (X_val, y_val)
            validation_split = 0.0
        else:
            validation_split = self.config['validation_split']
        
        # Train model
        self.history = self.model.fit(
            X_train, y_train,
            batch_size=self.config['batch_size'],
            epochs=self.config['epochs'],
            validation_split=validation_split,
            validation_data=validation_data,
            callbacks=callbacks,
            verbose=verbose
        )
        
        print("[OK] Training completed!")
        return self.history
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict coordinates for input sequences
        
        Args:
            X: Input sequences [samples, timesteps, features]
            
        Returns:
            Predicted coordinates [samples, 2]
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        predictions = self.model.predict(X, verbose=0)
        return predictions
    
    def predict_single(self, sequence: np.ndarray) -> Tuple[float, float]:
        """
        Predict next position for a single sequence
        
        Args:
            sequence: Single input sequence [timesteps, features]
            
        Returns:
            Predicted (lat, lng) coordinates (normalized)
        """
        # Add batch dimension
        X = np.expand_dims(sequence, axis=0)
        prediction = self.predict(X)
        return prediction[0][0], prediction[0][1]
    
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict:
        """
        Evaluate model performance
        
        Args:
            X_test: Test input sequences
            y_test: Test target coordinates
            
        Returns:
            Evaluation metrics
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        print(f"[DATA] Evaluating model on {X_test.shape[0]:,} test sequences...")
        
        # Get predictions
        y_pred = self.predict(X_test)
        
        # Calculate metrics
        mse = np.mean((y_test - y_pred) ** 2)
        mae = np.mean(np.abs(y_test - y_pred))
        rmse = np.sqrt(mse)
        
        # Calculate coordinate-wise errors
        lat_mae = np.mean(np.abs(y_test[:, 0] - y_pred[:, 0]))
        lng_mae = np.mean(np.abs(y_test[:, 1] - y_pred[:, 1]))
        
        # Calculate distance errors in normalized space
        distances = np.sqrt(np.sum((y_test - y_pred) ** 2, axis=1))
        mean_distance_error = np.mean(distances)
        
        metrics = {
            'mse': float(mse),
            'mae': float(mae),
            'rmse': float(rmse),
            'lat_mae': float(lat_mae),
            'lng_mae': float(lng_mae),
            'mean_distance_error': float(mean_distance_error),
            'predictions': y_pred,
            'actual': y_test
        }
        
        print(f"[CHART] Evaluation Results:")
        print(f"   MSE: {mse:.6f}")
        print(f"   MAE: {mae:.6f}")
        print(f"   RMSE: {rmse:.6f}")
        print(f"   Lat MAE: {lat_mae:.6f}")
        print(f"   Lng MAE: {lng_mae:.6f}")
        print(f"   Mean Distance Error: {mean_distance_error:.6f}")
        
        return metrics
    
    def plot_training_history(self, save_path: str = None):
        """Plot training history"""
        if self.history is None:
            print("No training history available")
            return
        
        plt.figure(figsize=(12, 4))
        
        # Loss plot
        plt.subplot(1, 2, 1)
        plt.plot(self.history.history['loss'], label='Training Loss')
        plt.plot(self.history.history['val_loss'], label='Validation Loss')
        plt.title('Model Loss')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # MAE plot
        plt.subplot(1, 2, 2)
        plt.plot(self.history.history['mae'], label='Training MAE')
        plt.plot(self.history.history['val_mae'], label='Validation MAE')
        plt.title('Model MAE')
        plt.xlabel('Epoch')
        plt.ylabel('MAE')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[DISK] Saved training history: {save_path}")
        
        plt.show()
    
    def save_model(self, filepath: str):
        """Save trained model"""
        if self.model is None:
            raise ValueError("No model to save")
        
        # Ensure .keras extension for newer TensorFlow versions
        if not filepath.endswith('.keras'):
            filepath = filepath.replace('.h5', '.keras')
        
        self.model.save(filepath)
        print(f"[DISK] Model saved: {filepath}")
    
    def load_model(self, filepath: str):
        """Load pre-trained model"""
        self.model = keras.models.load_model(filepath)
        print(f"📥 Model loaded: {filepath}")
    
    def get_model_info(self) -> Dict:
        """Get model information"""
        if self.model is None:
            return {'status': 'not_built'}
        
        return {
            'status': 'ready',
            'config': self.config,
            'total_params': self.model.count_params(),
            'trainable_params': sum([tf.keras.utils.get_value(w).size for w in self.model.trainable_weights]),
            'layers': len(self.model.layers),
            'input_shape': self.model.input_shape,
            'output_shape': self.model.output_shape
        }

# Convenience function
def create_lstm_model(config: Dict = None) -> LSTMTrajectoryModel:
    """Create and return LSTM model with optional configuration"""
    return LSTMTrajectoryModel(config) 