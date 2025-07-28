#!/usr/bin/env python3
"""
Attention-based Models for Trajectory Prediction
Includes LSTM/GRU with Attention Mechanism
"""

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras import backend as K
from typing import Tuple, Dict, Optional
import matplotlib.pyplot as plt
import os

# Import utility functions for error calculation
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.error_calculator import calculate_meter_errors, calculate_pixel_errors

def coordinate_accuracy(y_true, y_pred):
    """Custom metric for coordinate accuracy"""
    distances = tf.sqrt(tf.reduce_sum(tf.square(y_true - y_pred), axis=1))
    return tf.reduce_mean(distances)

def pixel_accuracy_50(y_true, y_pred):
    """Custom metric: percentage of predictions within 50 pixels (in normalized space)"""
    distances = tf.sqrt(tf.reduce_sum(tf.square(y_true - y_pred), axis=1))
    threshold = 0.04  # Approximately 50 pixels in normalized space
    accurate_predictions = tf.cast(distances < threshold, tf.float32)
    return tf.reduce_mean(accurate_predictions)

class AttentionLayer(layers.Layer):
    """Custom attention layer for sequence modeling"""
    
    def __init__(self, units=64, **kwargs):
        super(AttentionLayer, self).__init__(**kwargs)
        self.units = units
        self.attention = layers.Dense(units, activation='tanh')
        self.context = layers.Dense(1)
        
    def call(self, inputs):
        # inputs shape: (batch_size, timesteps, features)
        # Apply attention mechanism
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

class SelfAttentionLayer(layers.Layer):
    """Self-attention layer for sequence modeling"""
    
    def __init__(self, d_model, num_heads=8, **kwargs):
        super(SelfAttentionLayer, self).__init__(**kwargs)
        self.d_model = d_model
        self.num_heads = num_heads
        
        assert d_model % num_heads == 0
        
        self.depth = d_model // num_heads
        
        self.wq = layers.Dense(d_model)
        self.wk = layers.Dense(d_model)
        self.wv = layers.Dense(d_model)
        
        self.dense = layers.Dense(d_model)
        
    def split_heads(self, x, batch_size):
        """Split the last dimension into (num_heads, depth)."""
        x = tf.reshape(x, (batch_size, -1, self.num_heads, self.depth))
        return tf.transpose(x, perm=[0, 2, 1, 3])
    
    def call(self, inputs):
        batch_size = tf.shape(inputs)[0]
        
        q = self.wq(inputs)  # (batch_size, seq_len, d_model)
        k = self.wk(inputs)  # (batch_size, seq_len, d_model)
        v = self.wv(inputs)  # (batch_size, seq_len, d_model)
        
        q = self.split_heads(q, batch_size)  # (batch_size, num_heads, seq_len, depth)
        k = self.split_heads(k, batch_size)  # (batch_size, num_heads, seq_len, depth)
        v = self.split_heads(v, batch_size)  # (batch_size, num_heads, seq_len, depth)
        
        # Scaled dot-product attention
        matmul_qk = tf.matmul(q, k, transpose_b=True)  # (..., seq_len, seq_len)
        
        # Scale matmul_qk
        dk = tf.cast(tf.shape(k)[-1], tf.float32)
        scaled_attention_logits = matmul_qk / tf.math.sqrt(dk)
        
        # Softmax
        attention_weights = tf.nn.softmax(scaled_attention_logits, axis=-1)
        
        output = tf.matmul(attention_weights, v)  # (..., seq_len, depth)
        
        output = tf.transpose(output, perm=[0, 2, 1, 3])  # (batch_size, seq_len, num_heads, depth)
        
        concat_attention = tf.reshape(output, 
                                    (batch_size, -1, self.d_model))  # (batch_size, seq_len, d_model)
        
        output = self.dense(concat_attention)  # (batch_size, seq_len, d_model)
        
        return output, attention_weights
    
    def get_config(self):
        config = super().get_config()
        config.update({
            "d_model": self.d_model,
            "num_heads": self.num_heads
        })
        return config

class AttentionTrajectoryModel:
    """RNN model with attention mechanism for trajectory prediction"""
    
    def __init__(self, config: Dict = None):
        """
        Initialize Attention-based RNN model with configuration
        
        Args:
            config: Model configuration dictionary
        """
        self.config = {
            'sequence_length': 10,
            'input_features': 33,
            'output_features': 2,   # lat, lng coordinates
            'rnn_type': 'LSTM',     # 'LSTM' or 'GRU'
            'rnn_units': [128, 64], # RNN layers
            'attention_units': 64,  # Attention layer units
            'attention_type': 'basic',  # 'basic' or 'self'
            'num_heads': 8,         # For self-attention
            'dense_units': [64, 32], # Dense layers after attention
            'dropout_rate': 0.3,
            'recurrent_dropout': 0.2,
            'l2_regularization': 0.001,
            'learning_rate': 0.001,
            'batch_size': 32,
            'epochs': 100,
            'validation_split': 0.2,
            'patience': 15,
        }
        
        # Update with provided config
        if config:
            self.config.update(config)
        
        self.model = None
        self.history = None
        self.is_trained = False
        
    def build_model(self) -> keras.Model:
        """Build Attention-based RNN model architecture"""
        # Input layer
        inputs = layers.Input(
            shape=(self.config['sequence_length'], self.config['input_features']),
            name='trajectory_input'
        )
        
        x = inputs
        
        # RNN layers (all return sequences for attention)
        for i, units in enumerate(self.config['rnn_units']):
            if self.config['rnn_type'] == 'LSTM':
                x = layers.LSTM(
                    units,
                    return_sequences=True,  # Always True for attention
                    dropout=self.config['dropout_rate'],
                    recurrent_dropout=self.config['recurrent_dropout'],
                    kernel_regularizer=keras.regularizers.l2(self.config['l2_regularization']),
                    name=f'lstm_{i+1}'
                )(x)
            else:  # GRU
                x = layers.GRU(
                    units,
                    return_sequences=True,  # Always True for attention
                    dropout=self.config['dropout_rate'],
                    recurrent_dropout=self.config['recurrent_dropout'],
                    kernel_regularizer=keras.regularizers.l2(self.config['l2_regularization']),
                    name=f'gru_{i+1}'
                )(x)
            
            x = layers.BatchNormalization(name=f'bn_rnn_{i+1}')(x)
        
        # Attention mechanism
        if self.config['attention_type'] == 'self':
            # Self-attention
            attended_output, attention_weights = SelfAttentionLayer(
                d_model=self.config['rnn_units'][-1],
                num_heads=self.config['num_heads'],
                name='self_attention'
            )(x)
            # Global average pooling to reduce sequence dimension
            x = layers.GlobalAveragePooling1D()(attended_output)
        else:
            # Basic attention
            attended_output, attention_weights = AttentionLayer(
                units=self.config['attention_units'],
                name='attention'
            )(x)
            x = attended_output
        
        # Dense layers
        for i, units in enumerate(self.config['dense_units']):
            x = layers.Dense(
                units,
                activation='relu',
                kernel_regularizer=keras.regularizers.l2(self.config['l2_regularization']),
                name=f'dense_{i+1}'
            )(x)
            x = layers.Dropout(self.config['dropout_rate'], name=f'dropout_dense_{i+1}')(x)
            x = layers.BatchNormalization(name=f'bn_dense_{i+1}')(x)
        
        # Output layer (no activation for regression)
        outputs = layers.Dense(
            self.config['output_features'],
            activation='linear',
            name='coordinate_output'
        )(x)
        
        # Create model
        model_name = f'{self.config["rnn_type"]}_with_{self.config["attention_type"]}_attention'
        model = keras.Model(
            inputs=inputs,
            outputs=outputs,
            name=model_name
        )
        
        # Compile model
        optimizer = keras.optimizers.Adam(
            learning_rate=self.config['learning_rate'],
            clipnorm=1.0  # Gradient clipping
        )
        
        model.compile(
            optimizer=optimizer,
            loss='mse',
            metrics=[coordinate_accuracy, pixel_accuracy_50, 'mae']
        )
        
        return model
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray, 
              X_val: np.ndarray = None, y_val: np.ndarray = None) -> Dict:
        """
        Train the Attention-based RNN model
        
        Args:
            X_train: Training sequences
            y_train: Training targets
            X_val: Validation sequences (optional)
            y_val: Validation targets (optional)
        
        Returns:
            Training history dictionary
        """
        print(f"[TRAINING] Training {self.config['rnn_type']} with {self.config['attention_type']} attention...")
        print(f"[DATA] Training data shape: {X_train.shape}")
        print(f"[TARGET] Target data shape: {y_train.shape}")
        
        # Build model
        self.model = self.build_model()
        
        # Print model summary
        print(f"\n[ARCH] Model Architecture:")
        self.model.summary()
        
        # Callbacks
        callbacks = [
            keras.callbacks.EarlyStopping(
                monitor='val_loss' if X_val is not None else 'loss',
                patience=self.config['patience'],
                restore_best_weights=True,
                verbose=1
            ),
            keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss' if X_val is not None else 'loss',
                factor=0.5,
                patience=self.config['patience'] // 2,
                min_lr=1e-6,
                verbose=1
            )
        ]
        
        # Prepare validation data
        validation_data = None
        if X_val is not None and y_val is not None:
            validation_data = (X_val, y_val)
        elif self.config['validation_split'] > 0:
            # Use internal validation split
            pass
        
        # Train model (verbose=2 for clean one-line-per-epoch output)
        self.history = self.model.fit(
            X_train, y_train,
            validation_data=validation_data,
            validation_split=self.config['validation_split'] if validation_data is None else 0,
            epochs=self.config['epochs'],
            batch_size=self.config['batch_size'],
            callbacks=callbacks,
            verbose=2  # Clean one-line per epoch
        )
        
        self.is_trained = True
        
        # Training results
        results = {
            'final_loss': self.history.history['loss'][-1],
            'final_val_loss': self.history.history['val_loss'][-1] if 'val_loss' in self.history.history else None,
            'final_accuracy': self.history.history['coordinate_accuracy'][-1],
            'final_pixel_accuracy': self.history.history['pixel_accuracy_50'][-1],
            'epochs_trained': len(self.history.history['loss']),
            'total_params': self.model.count_params(),
            'rnn_type': self.config['rnn_type'],
            'attention_type': self.config['attention_type']
        }
        
        print(f"\n[OK] Training completed!")
        print(f"[CHART] Final loss: {results['final_loss']:.6f}")
        if results['final_val_loss']:
            print(f"[GRAPH] Final val loss: {results['final_val_loss']:.6f}")
        print(f"[TARGET] Final coordinate accuracy: {results['final_accuracy']:.6f}")
        print(f"📐 Final pixel accuracy (50px): {results['final_pixel_accuracy']:.4f}")
        print(f"[SYMBOL] Total parameters: {results['total_params']:,}")
        
        return results
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions"""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        return self.model.predict(X, verbose=0)
    
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray, 
                 bounds: Dict = None) -> Dict:
        """
        Evaluate model performance
        
        Args:
            X_test: Test sequences
            y_test: Test targets  
            bounds: Geographic bounds for meter calculation
        
        Returns:
            Evaluation metrics dictionary
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before evaluation")
        
        print(f"[DATA] Evaluating {self.config['rnn_type']} with {self.config['attention_type']} attention...")
        
        # Make predictions
        y_pred = self.predict(X_test)
        
        # Basic metrics
        test_metrics = self.model.evaluate(X_test, y_test, verbose=0)
        metric_names = self.model.metrics_names
        
        results = dict(zip(metric_names, test_metrics))
        results.update({
            'rnn_type': self.config['rnn_type'],
            'attention_type': self.config['attention_type']
        })
        
        # Calculate error statistics if bounds provided
        if bounds:
            # Meter errors
            meter_stats = calculate_meter_errors(y_test, y_pred, bounds)
            results.update({
                'mean_error_meters': meter_stats['mean_error'],
                'median_error_meters': meter_stats['median_error'],
                'std_error_meters': meter_stats['std_error']
            })
            
            # Pixel errors
            pixel_stats = calculate_pixel_errors(y_test, y_pred, bounds)
            results.update({
                'mean_error_pixels': pixel_stats['mean_error'],
                'median_error_pixels': pixel_stats['median_error'],
                'std_error_pixels': pixel_stats['std_error']
            })
            
            print(f"[TARGET] Mean error: {meter_stats['mean_error']:.1f} meters ({pixel_stats['mean_error']:.1f} pixels)")
            print(f"[DATA] Median error: {meter_stats['median_error']:.1f} meters ({pixel_stats['median_error']:.1f} pixels)")
        
        return results
    
    def save_model(self, filepath: str):
        """Save trained model"""
        if not self.is_trained:
            raise ValueError("Model must be trained before saving")
        
        self.model.save(filepath)
        print(f"[DISK] Model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """Load trained model"""
        self.model = keras.models.load_model(
            filepath,
            custom_objects={
                'coordinate_accuracy': coordinate_accuracy,
                'pixel_accuracy_50': pixel_accuracy_50,
                'AttentionLayer': AttentionLayer,
                'SelfAttentionLayer': SelfAttentionLayer
            }
        )
        self.is_trained = True
        print(f"[FOLDER] Model loaded from {filepath}")
    
    def plot_training_history(self, save_path: str = None):
        """Plot training history"""
        if not self.history:
            raise ValueError("No training history available")
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Add title with model info
        fig.suptitle(f'{self.config["rnn_type"]} with {self.config["attention_type"].title()} Attention Training History', 
                     fontsize=16)
        
        # Loss
        axes[0, 0].plot(self.history.history['loss'], label='Training Loss')
        if 'val_loss' in self.history.history:
            axes[0, 0].plot(self.history.history['val_loss'], label='Validation Loss')
        axes[0, 0].set_title('Model Loss')
        axes[0, 0].set_xlabel('Epoch')
        axes[0, 0].set_ylabel('Loss')
        axes[0, 0].legend()
        axes[0, 0].grid(True)
        
        # Coordinate Accuracy
        axes[0, 1].plot(self.history.history['coordinate_accuracy'], label='Training Accuracy')
        if 'val_coordinate_accuracy' in self.history.history:
            axes[0, 1].plot(self.history.history['val_coordinate_accuracy'], label='Validation Accuracy')
        axes[0, 1].set_title('Coordinate Accuracy')
        axes[0, 1].set_xlabel('Epoch')
        axes[0, 1].set_ylabel('Accuracy')
        axes[0, 1].legend()
        axes[0, 1].grid(True)
        
        # Pixel Accuracy
        axes[1, 0].plot(self.history.history['pixel_accuracy_50'], label='Training Pixel Acc')
        if 'val_pixel_accuracy_50' in self.history.history:
            axes[1, 0].plot(self.history.history['val_pixel_accuracy_50'], label='Validation Pixel Acc')
        axes[1, 0].set_title('Pixel Accuracy (50px threshold)')
        axes[1, 0].set_xlabel('Epoch')
        axes[1, 0].set_ylabel('Accuracy')
        axes[1, 0].legend()
        axes[1, 0].grid(True)
        
        # MAE
        axes[1, 1].plot(self.history.history['mae'], label='Training MAE')
        if 'val_mae' in self.history.history:
            axes[1, 1].plot(self.history.history['val_mae'], label='Validation MAE')
        axes[1, 1].set_title('Mean Absolute Error')
        axes[1, 1].set_xlabel('Epoch')
        axes[1, 1].set_ylabel('MAE')
        axes[1, 1].legend()
        axes[1, 1].grid(True)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[DATA] Training history plot saved to {save_path}")
        
        plt.show()
