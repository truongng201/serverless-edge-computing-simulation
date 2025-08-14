#!/usr/bin/env python3
"""
Enhanced LSTM Model for Trajectory Prediction
Features: Deeper architecture, custom loss function, attention mechanism, advanced regularization
"""

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras import backend as K
from typing import Tuple, Dict, Optional
import matplotlib.pyplot as plt

# Import utility functions for error calculation
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.error_calculator import calculate_meter_errors, calculate_pixel_errors

class AttentionLayer(layers.Layer):
    """Custom attention layer for sequence modeling"""
    
    def __init__(self, units=64, **kwargs):
        super(AttentionLayer, self).__init__(**kwargs)
        self.units = units
        self.attention = layers.Dense(units, activation='tanh')
        self.context = layers.Dense(1, activation='softmax')
        
    def call(self, inputs):
        # inputs shape: (batch_size, timesteps, features)
        attention_weights = self.attention(inputs)  # (batch_size, timesteps, units)
        attention_weights = self.context(attention_weights)  # (batch_size, timesteps, 1)
        attention_weights = tf.nn.softmax(attention_weights, axis=1)  # Normalize across timesteps
        
        # Apply attention weights
        weighted_input = inputs * attention_weights  # (batch_size, timesteps, features)
        attended_output = tf.reduce_sum(weighted_input, axis=1)  # (batch_size, features)
        
        return attended_output, attention_weights
    
    def get_config(self):
        config = super().get_config()
        config.update({"units": self.units})
        return config

def custom_distance_loss(y_true, y_pred):
    """
    Custom loss function that focuses on coordinate distance accuracy
    Combines MSE with geographic distance penalty
    """
    # Standard MSE loss
    mse_loss = tf.reduce_mean(tf.square(y_true - y_pred))
    
    # Euclidean distance loss in normalized space
    distance_loss = tf.reduce_mean(tf.sqrt(tf.reduce_sum(tf.square(y_true - y_pred), axis=1)))
    
    # Weighted combination: 60% MSE + 40% distance
    combined_loss = 0.6 * mse_loss + 0.4 * distance_loss
    
    return combined_loss

def coordinate_accuracy(y_true, y_pred):
    """Custom metric for coordinate accuracy"""
    distances = tf.sqrt(tf.reduce_sum(tf.square(y_true - y_pred), axis=1))
    return tf.reduce_mean(distances)

def pixel_accuracy_50(y_true, y_pred):
    """Custom metric: percentage of predictions within 50 pixels (in normalized space)"""
    # Assuming normalized coordinates, 50 pixels ≈ 0.04 in normalized space (50/1200)
    distances = tf.sqrt(tf.reduce_sum(tf.square(y_true - y_pred), axis=1))
    threshold = 0.04  # Approximately 50 pixels
    accurate_predictions = tf.cast(distances < threshold, tf.float32)
    return tf.reduce_mean(accurate_predictions)

class EnhancedLSTMTrajectoryModel:
    """Enhanced LSTM model with advanced architecture and training strategies"""
    
    def __init__(self, config: Dict = None):
        """
        Initialize enhanced LSTM model with configuration
        
        Args:
            config: Model configuration dictionary
        """
        self.config = {
            'sequence_length': 10,
            'input_features': 33,  # Enhanced features count
            'output_features': 2,   # lat, lng coordinates
            'lstm_units': [128, 64, 32],  # Deeper architecture
            'dense_units': [64, 32],       # Dense layers
            'dropout_rate': 0.3,
            'recurrent_dropout': 0.2,
            'l2_regularization': 0.001,
            'learning_rate': 0.001,
            'batch_size': 64,  # Larger batch size
            'epochs': 100,     # More epochs
            'validation_split': 0.2,
            'patience': 15,    # Increased patience
            'use_attention': True,
            'use_batch_norm': True,
            'use_layer_norm': False,
            'gradient_clip_norm': 1.0
        }
        
        if config:
            self.config.update(config)
        
        self.model = None
        self.history = None
        self.attention_weights = None
        
    def build_model(self) -> keras.Model:
        """Build enhanced LSTM architecture"""
        print("[MODEL] Building Enhanced LSTM model architecture...")
        
        # Input layer
        inputs = keras.Input(
            shape=(self.config['sequence_length'], self.config['input_features']),
            name='enhanced_trajectory_input'
        )
        
        # LSTM layers with enhanced architecture
        x = inputs
        
        # First LSTM layer
        x = layers.LSTM(
            units=self.config['lstm_units'][0],
            return_sequences=True,
            dropout=self.config['dropout_rate'],
            recurrent_dropout=self.config['recurrent_dropout'],
            kernel_regularizer=keras.regularizers.l2(self.config['l2_regularization']),
            name='lstm_1'
        )(x)
        
        if self.config['use_batch_norm']:
            x = layers.BatchNormalization(name='batch_norm_1')(x)
        
        # Second LSTM layer
        x = layers.LSTM(
            units=self.config['lstm_units'][1],
            return_sequences=True,
            dropout=self.config['dropout_rate'],
            recurrent_dropout=self.config['recurrent_dropout'],
            kernel_regularizer=keras.regularizers.l2(self.config['l2_regularization']),
            name='lstm_2'
        )(x)
        
        if self.config['use_batch_norm']:
            x = layers.BatchNormalization(name='batch_norm_2')(x)
        
        # Third LSTM layer  
        x = layers.LSTM(
            units=self.config['lstm_units'][2],
            return_sequences=self.config['use_attention'],  # Keep sequences for attention
            dropout=self.config['dropout_rate'],
            recurrent_dropout=self.config['recurrent_dropout'],
            kernel_regularizer=keras.regularizers.l2(self.config['l2_regularization']),
            name='lstm_3'
        )(x)
        
        if self.config['use_batch_norm']:
            x = layers.BatchNormalization(name='batch_norm_3')(x)
        
        # Attention mechanism (optional)
        if self.config['use_attention']:
            x, attention_weights = AttentionLayer(units=64, name='attention')(x)
            # Store attention for visualization
            self.attention_model = keras.Model(inputs=inputs, outputs=attention_weights)
        
        # Dense layers for coordinate prediction
        for i, units in enumerate(self.config['dense_units']):
            x = layers.Dense(
                units=units,
                activation='relu',
                kernel_regularizer=keras.regularizers.l2(self.config['l2_regularization']),
                name=f'dense_{i+1}'
            )(x)
            
            if self.config['use_batch_norm']:
                x = layers.BatchNormalization(name=f'dense_batch_norm_{i+1}')(x)
            
            x = layers.Dropout(self.config['dropout_rate'], name=f'dropout_dense_{i+1}')(x)
        
        # Output layer: predicted coordinates (normalized 0-1)
        outputs = layers.Dense(
            units=self.config['output_features'],
            activation='sigmoid',
            name='coordinate_output'
        )(x)
        
        # Create model
        self.model = keras.Model(inputs=inputs, outputs=outputs, name='enhanced_lstm_trajectory_predictor')
        
        # Advanced optimizer with gradient clipping
        optimizer = keras.optimizers.Adam(
            learning_rate=self.config['learning_rate'],
            clipnorm=self.config['gradient_clip_norm']
        )
        
        # Compile model with custom loss and metrics
        self.model.compile(
            optimizer=optimizer,
            loss=custom_distance_loss,
            metrics=[
                'mae', 'mse',
                coordinate_accuracy,
                pixel_accuracy_50
            ]
        )
        
        print("[OK] Enhanced model architecture:")
        self.model.summary()
        
        return self.model
    
    def create_advanced_callbacks(self, validation_data=None):
        """Create advanced training callbacks"""
        callbacks = []
        
        # Early stopping with restore best weights
        callbacks.append(
            keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=self.config['patience'],
                restore_best_weights=True,
                verbose=0,  # Reduced verbosity
                mode='min'
            )
        )
        
        # Learning rate scheduling
        callbacks.append(
            keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=5,
                min_lr=1e-7,
                verbose=0,  # Reduced verbosity
                mode='min'
            )
        )
        
        # Learning rate warmup and cosine decay
        def lr_schedule(epoch, lr):
            if epoch < 5:  # Warmup
                return self.config['learning_rate'] * (epoch + 1) / 5
            else:  # Cosine decay
                return self.config['learning_rate'] * 0.5 * (1 + np.cos(np.pi * (epoch - 5) / (self.config['epochs'] - 5)))
        
        callbacks.append(
            keras.callbacks.LearningRateScheduler(lr_schedule, verbose=0)
        )
        
        # Model checkpointing
        callbacks.append(
            keras.callbacks.ModelCheckpoint(
                'enhanced_lstm_best_model.keras',
                monitor='val_loss',
                save_best_only=True,
                save_weights_only=False,
                verbose=0
            )
        )
        
        return callbacks
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray, 
              X_val: Optional[np.ndarray] = None, y_val: Optional[np.ndarray] = None,
              verbose: int = 1) -> keras.callbacks.History:
        """
        Train the enhanced LSTM model
        """
        if self.model is None:
            self.build_model()
        
        print(f"[TRAINING] Training Enhanced LSTM model...")
        print(f"   Training data: {X_train.shape[0]:,} sequences")
        print(f"   Input shape: {X_train.shape}")
        print(f"   Output shape: {y_train.shape}")
        print(f"   Features per timestep: {X_train.shape[2]}")
        
        # Prepare validation data
        validation_data = None
        if X_val is not None and y_val is not None:
            validation_data = (X_val, y_val)
            validation_split = 0.0
        else:
            validation_split = self.config['validation_split']
        
        # Create advanced callbacks
        callbacks = self.create_advanced_callbacks(validation_data)
        
        # Train model (verbose=2 for clean one-line-per-epoch output)
        self.history = self.model.fit(
            X_train, y_train,
            batch_size=self.config['batch_size'],
            epochs=self.config['epochs'],
            validation_split=validation_split,
            validation_data=validation_data,
            callbacks=callbacks,
            verbose=2  # Clean one-line per epoch
        )
        
        print("[OK] Enhanced training completed!")
        return self.history
    
    def predict(self, X: np.ndarray, return_attention: bool = False) -> np.ndarray:
        """
        Predict coordinates for input sequences
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        predictions = self.model.predict(X, verbose=0)
        
        if return_attention and self.config['use_attention'] and hasattr(self, 'attention_model'):
            attention_weights = self.attention_model.predict(X, verbose=0)
            return predictions, attention_weights
        
        return predictions
    
    def evaluate_enhanced(self, X_test: np.ndarray, y_test: np.ndarray, bounds: Dict) -> Dict:
        """
        Enhanced evaluation with detailed metrics
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        print(f"[DATA] Enhanced evaluation on {X_test.shape[0]:,} test sequences...")
        
        # Get predictions
        if self.config['use_attention']:
            y_pred, attention_weights = self.predict(X_test, return_attention=True)
        else:
            y_pred = self.predict(X_test)
            attention_weights = None
        
        # Standard metrics
        test_metrics = self.model.evaluate(X_test, y_test, verbose=0)
        
        # Custom metrics calculations
        mse = np.mean((y_test - y_pred) ** 2)
        mae = np.mean(np.abs(y_test - y_pred))
        rmse = np.sqrt(mse)
        
        # Coordinate-wise errors
        lat_mae = np.mean(np.abs(y_test[:, 0] - y_pred[:, 0]))
        lng_mae = np.mean(np.abs(y_test[:, 1] - y_pred[:, 1]))
        
        # Distance errors in normalized space
        distances = np.sqrt(np.sum((y_test - y_pred) ** 2, axis=1))
        mean_distance_error = np.mean(distances)
        
        # Calculate meter errors (primary metric)
        meter_stats = calculate_meter_errors(y_test, y_pred, bounds)
        
        # Calculate pixel errors (for comparison)
        pixel_stats = calculate_pixel_errors(y_test, y_pred, bounds)
        
        # Compile results
        enhanced_metrics = {
            'model_metrics': dict(zip(self.model.metrics_names, test_metrics)),
            'mse': float(mse),
            'mae': float(mae),
            'rmse': float(rmse),
            'lat_mae': float(lat_mae),
            'lng_mae': float(lng_mae),
            'mean_distance_error': float(mean_distance_error),
            'meter_stats': meter_stats,  # Primary metric
            'pixel_stats': pixel_stats,  # For comparison
            'predictions': y_pred,
            'actual': y_test,
            'attention_weights': attention_weights
        }
        
        # Print results
        print(f"[CHART] Enhanced Evaluation Results:")
        print(f"   Custom Loss: {enhanced_metrics['model_metrics']['loss']:.6f}")
        
        # Debug metric names
        print(f"   Available metrics: {list(enhanced_metrics['model_metrics'].keys())}")
        
        # Safer access to metrics
        coord_acc = enhanced_metrics['model_metrics'].get('coordinate_accuracy', 
                   enhanced_metrics['model_metrics'].get('coordinate_accuracy_1', 0))
        pixel_acc = enhanced_metrics['model_metrics'].get('pixel_accuracy_50', 
                   enhanced_metrics['model_metrics'].get('pixel_accuracy_50_1', 0))
        
        print(f"   Coordinate Accuracy: {coord_acc:.6f}")
        print(f"   Pixel Accuracy (50px): {pixel_acc:.3f}")
        print(f"   Mean Meter Error: {enhanced_metrics['meter_stats']['mean_error']:.1f} meters")
        print(f"   Median Meter Error: {enhanced_metrics['meter_stats']['median_error']:.1f} meters")
        print(f"   Mean Pixel Error: {enhanced_metrics['pixel_stats']['mean_error']:.1f} pixels")
        
        return enhanced_metrics
    
    def plot_enhanced_training_history(self, save_path: str = None):
        """Plot enhanced training history with all metrics"""
        if self.history is None:
            print("No training history available")
            return
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        
        # Loss
        axes[0, 0].plot(self.history.history['loss'], label='Training Loss')
        axes[0, 0].plot(self.history.history['val_loss'], label='Validation Loss')
        axes[0, 0].set_title('Custom Distance Loss')
        axes[0, 0].set_xlabel('Epoch')
        axes[0, 0].set_ylabel('Loss')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # MAE
        axes[0, 1].plot(self.history.history['mae'], label='Training MAE')
        axes[0, 1].plot(self.history.history['val_mae'], label='Validation MAE')
        axes[0, 1].set_title('Mean Absolute Error')
        axes[0, 1].set_xlabel('Epoch')
        axes[0, 1].set_ylabel('MAE')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # Coordinate Accuracy
        axes[0, 2].plot(self.history.history['coordinate_accuracy'], label='Training')
        axes[0, 2].plot(self.history.history['val_coordinate_accuracy'], label='Validation')
        axes[0, 2].set_title('Coordinate Accuracy')
        axes[0, 2].set_xlabel('Epoch')
        axes[0, 2].set_ylabel('Distance Error')
        axes[0, 2].legend()
        axes[0, 2].grid(True, alpha=0.3)
        
        # Pixel Accuracy
        axes[1, 0].plot(self.history.history['pixel_accuracy_50'], label='Training')
        axes[1, 0].plot(self.history.history['val_pixel_accuracy_50'], label='Validation')
        axes[1, 0].set_title('Pixel Accuracy (<50px)')
        axes[1, 0].set_xlabel('Epoch')
        axes[1, 0].set_ylabel('Accuracy Rate')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # Learning Rate
        if 'lr' in self.history.history:
            axes[1, 1].plot(self.history.history['lr'])
            axes[1, 1].set_title('Learning Rate Schedule')
            axes[1, 1].set_xlabel('Epoch')
            axes[1, 1].set_ylabel('Learning Rate')
            axes[1, 1].set_yscale('log')
            axes[1, 1].grid(True, alpha=0.3)
        
        # MSE
        axes[1, 2].plot(self.history.history['mse'], label='Training MSE')
        axes[1, 2].plot(self.history.history['val_mse'], label='Validation MSE')
        axes[1, 2].set_title('Mean Squared Error')
        axes[1, 2].set_xlabel('Epoch')
        axes[1, 2].set_ylabel('MSE')
        axes[1, 2].legend()
        axes[1, 2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[DISK] Saved enhanced training history: {save_path}")
        
        plt.show()
    
    def save_model(self, filepath: str):
        """Save enhanced trained model"""
        if self.model is None:
            raise ValueError("No model to save")
        
        # Ensure .keras extension
        if not filepath.endswith('.keras'):
            filepath = filepath.replace('.h5', '.keras')
        
        self.model.save(filepath)
        print(f"[DISK] Enhanced model saved: {filepath}")
    
    def load_model(self, filepath: str):
        """Load pre-trained enhanced model"""
        # Register custom objects
        custom_objects = {
            'custom_distance_loss': custom_distance_loss,
            'coordinate_accuracy': coordinate_accuracy,
            'pixel_accuracy_50': pixel_accuracy_50,
            'AttentionLayer': AttentionLayer
        }
        
        self.model = keras.models.load_model(filepath, custom_objects=custom_objects)
        print(f"📥 Enhanced model loaded: {filepath}")
    
    def get_model_info(self) -> Dict:
        """Get enhanced model information"""
        if self.model is None:
            return {'status': 'not_built'}
        
        return {
            'status': 'ready',
            'config': self.config,
            'total_params': self.model.count_params(),
            'trainable_params': sum([tf.keras.utils.get_value(w).size for w in self.model.trainable_weights]),
            'layers': len(self.model.layers),
            'input_shape': self.model.input_shape,
            'output_shape': self.model.output_shape,
            'architecture': 'Enhanced LSTM with Attention',
            'features': {
                'attention_mechanism': self.config['use_attention'],
                'custom_loss': 'Distance-based loss',
                'regularization': f"L2={self.config['l2_regularization']}, Dropout={self.config['dropout_rate']}",
                'lstm_layers': len(self.config['lstm_units']),
                'total_features': self.config['input_features']
            }
        }

# Convenience function
def create_enhanced_lstm_model(config: Dict = None) -> EnhancedLSTMTrajectoryModel:
    """Create and return enhanced LSTM model with optional configuration"""
    return EnhancedLSTMTrajectoryModel(config) 