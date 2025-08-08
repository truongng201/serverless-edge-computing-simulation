#!/usr/bin/env python3
"""
Spatial-Temporal Graph Neural Network for Trajectory Prediction
Models the trajectory problem as a graph with spatial relationships
"""

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from typing import Tuple, Dict, Optional, List
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

class GraphConvolution(layers.Layer):
    """Graph Convolution Layer for processing spatial relationships"""
    
    def __init__(self, units, activation='relu', **kwargs):
        super(GraphConvolution, self).__init__(**kwargs)
        self.units = units
        self.activation = keras.activations.get(activation)
        self.dense = layers.Dense(units)
        
    def call(self, inputs):
        # inputs: [node_features, adjacency_matrix]
        node_features, adjacency = inputs
        
        # Apply dense transformation
        transformed = self.dense(node_features)
        
        # Graph convolution: A * X * W
        # adjacency: (batch_size, num_nodes, num_nodes)
        # transformed: (batch_size, num_nodes, units)
        output = tf.matmul(adjacency, transformed)
        
        return self.activation(output)
    
    def get_config(self):
        config = super().get_config()
        config.update({
            "units": self.units,
            "activation": keras.activations.serialize(self.activation)
        })
        return config

class TemporalAttention(layers.Layer):
    """Temporal attention for focusing on important time steps"""
    
    def __init__(self, units, **kwargs):
        super(TemporalAttention, self).__init__(**kwargs)
        self.units = units
        self.attention = layers.Dense(units, activation='tanh')
        self.context = layers.Dense(1)
        
    def call(self, inputs):
        # inputs: (batch_size, timesteps, features)
        attention_weights = self.attention(inputs)
        attention_weights = self.context(attention_weights)
        attention_weights = tf.nn.softmax(attention_weights, axis=1)
        
        # Apply attention
        weighted_input = inputs * attention_weights
        attended_output = tf.reduce_sum(weighted_input, axis=1)
        
        return attended_output, attention_weights
    
    def get_config(self):
        config = super().get_config()
        config.update({"units": self.units})
        return config

class SpatialTemporalGNNModel:
    """Spatial-Temporal GNN model for trajectory prediction"""
    
    def __init__(self, config: Dict = None):
        """
        Initialize ST-GNN model with configuration
        
        Args:
            config: Model configuration dictionary
        """
        self.config = {
            'sequence_length': 10,
            'input_features': 33,
            'output_features': 2,   # lat, lng coordinates
            'num_spatial_nodes': 16,  # Number of spatial regions/nodes
            'gcn_units': [64, 32],    # Graph convolution layers
            'lstm_units': [64, 32],   # Temporal LSTM layers
            'attention_units': 64,    # Temporal attention
            'dense_units': [64, 32],  # Final dense layers
            'dropout_rate': 0.3,
            'recurrent_dropout': 0.2,
            'l2_regularization': 0.001,
            'learning_rate': 0.001,
            'batch_size': 32,
            'epochs': 120,
            'validation_split': 0.2,
            'patience': 20,
            'use_temporal_attention': True,
        }
        
        # Update with provided config
        if config:
            self.config.update(config)
        
        self.model = None
        self.history = None
        self.is_trained = False
        
    def create_spatial_adjacency_matrix(self, batch_size: int) -> tf.Tensor:
        """
        Create adjacency matrix for spatial relationships
        For simplicity, we use a grid-based approach where nodes are connected to neighbors
        """
        num_nodes = self.config['num_spatial_nodes']
        grid_size = int(np.sqrt(num_nodes))  # Assume square grid
        
        # Create adjacency matrix (grid topology)
        adj = np.zeros((num_nodes, num_nodes), dtype=np.float32)
        
        for i in range(grid_size):
            for j in range(grid_size):
                node_id = i * grid_size + j
                
                # Connect to neighbors (4-connectivity)
                neighbors = []
                if i > 0: neighbors.append((i-1) * grid_size + j)  # Up
                if i < grid_size-1: neighbors.append((i+1) * grid_size + j)  # Down
                if j > 0: neighbors.append(i * grid_size + (j-1))  # Left
                if j < grid_size-1: neighbors.append(i * grid_size + (j+1))  # Right
                
                for neighbor in neighbors:
                    adj[node_id, neighbor] = 1.0
                
                # Self-connection
                adj[node_id, node_id] = 1.0
        
        # Normalize adjacency matrix (add self-loops and normalize)
        degree = np.sum(adj, axis=1)
        degree_inv_sqrt = np.power(degree, -0.5)
        degree_inv_sqrt[np.isinf(degree_inv_sqrt)] = 0.0
        
        # D^(-1/2) * A * D^(-1/2)
        adj_normalized = degree_inv_sqrt[:, None] * adj * degree_inv_sqrt[None, :]
        
        # Broadcast to batch size
        adj_batch = np.tile(adj_normalized[None, :, :], (batch_size, 1, 1))
        
        return tf.constant(adj_batch, dtype=tf.float32)
    
    def trajectory_to_spatial_features(self, trajectory_data):
        """
        Convert trajectory sequences to spatial node features
        This is a simplified approach - in practice, you'd use more sophisticated methods
        """
        batch_size = tf.shape(trajectory_data)[0]
        seq_len = tf.shape(trajectory_data)[1]
        
        # Project trajectory to spatial nodes using learned projection
        spatial_projection = layers.Dense(
            self.config['num_spatial_nodes'] * self.config['input_features'],
            name='spatial_projection'
        )(trajectory_data)
        
        # Reshape to spatial node format - using Lambda to handle dynamic batch size
        spatial_features = layers.Lambda(
            lambda x: tf.reshape(x, 
                (tf.shape(x)[0], tf.shape(x)[1], self.config['num_spatial_nodes'], self.config['input_features'])),
            name='spatial_reshape_lambda'
        )(spatial_projection)
        
        return spatial_features
    
    def build_model(self) -> keras.Model:
        """Build Spatial-Temporal GNN model architecture"""
        # Input layer
        inputs = layers.Input(
            shape=(self.config['sequence_length'], self.config['input_features']),
            name='trajectory_input'
        )
        
        # Convert trajectory to spatial features
        x = inputs
        
        # Spatial-Temporal processing for each time step
        processed_timesteps = []
        
        for t in range(self.config['sequence_length']):
            # Extract features for time step t
            timestep_data = x[:, t, :]  # (batch_size, features)
            
            # Project to spatial nodes
            spatial_features = layers.Dense(
                self.config['num_spatial_nodes'] * 32,
                activation='relu',
                name=f'spatial_proj_t{t}'
            )(timestep_data)
            
            spatial_features = layers.Reshape(
                (self.config['num_spatial_nodes'], 32),
                name=f'spatial_reshape_t{t}'
            )(spatial_features)
            
            # Create adjacency matrix using Lambda layer
            adjacency = layers.Lambda(
                lambda x: tf.tile(
                    self.create_spatial_adjacency_matrix(1), 
                    [tf.shape(x)[0], 1, 1]
                ),
                name=f'adjacency_tile_t{t}'
            )(spatial_features)
            
            # Apply Graph Convolution layers
            gcn_output = spatial_features
            for i, units in enumerate(self.config['gcn_units']):
                gcn_output = GraphConvolution(
                    units=units,
                    name=f'gcn_{i+1}_t{t}'
                )([gcn_output, adjacency])
                gcn_output = layers.Dropout(
                    self.config['dropout_rate'],
                    name=f'gcn_dropout_{i+1}_t{t}'
                )(gcn_output)
            
            # Global pooling to get single representation for this timestep
            timestep_repr = layers.GlobalAveragePooling1D(
                name=f'global_pool_t{t}'
            )(gcn_output)
            
            processed_timesteps.append(timestep_repr)
        
        # Stack processed timesteps - using Concatenate and Reshape
        # Each timestep_repr has shape (batch_size, features)
        # We want (batch_size, sequence_length, features)
        if len(processed_timesteps) == 1:
            temporal_sequence = layers.Reshape((1, -1))(processed_timesteps[0])
        else:
            # Stack manually using concatenate and reshape
            stacked_features = layers.Concatenate(axis=1)(
                [layers.Reshape((1, -1))(t) for t in processed_timesteps]
            )
            temporal_sequence = stacked_features
        
        # Temporal modeling with LSTM
        lstm_output = temporal_sequence
        for i, units in enumerate(self.config['lstm_units']):
            return_sequences = i < len(self.config['lstm_units']) - 1
            
            lstm_output = layers.LSTM(
                units,
                return_sequences=return_sequences,
                dropout=self.config['dropout_rate'],
                recurrent_dropout=self.config['recurrent_dropout'],
                kernel_regularizer=keras.regularizers.l2(self.config['l2_regularization']),
                name=f'lstm_{i+1}'
            )(lstm_output)
            
            if return_sequences:
                lstm_output = layers.BatchNormalization(name=f'bn_lstm_{i+1}')(lstm_output)
        
        # Temporal attention (optional)
        if self.config['use_temporal_attention'] and len(self.config['lstm_units']) > 1:
            # Apply attention to LSTM sequence output
            temp_seq = temporal_sequence
            for i in range(len(self.config['lstm_units']) - 1):
                temp_seq = layers.LSTM(
                    self.config['lstm_units'][i],
                    return_sequences=True,
                    dropout=self.config['dropout_rate'],
                    recurrent_dropout=self.config['recurrent_dropout'],
                    name=f'lstm_att_{i+1}'
                )(temp_seq)
            
            attended_output, attention_weights = TemporalAttention(
                units=self.config['attention_units'],
                name='temporal_attention'
            )(temp_seq)
            
            # Combine LSTM output with attention
            x = layers.Concatenate(name='combine_lstm_attention')([lstm_output, attended_output])
        else:
            x = lstm_output
        
        # Final dense layers
        for i, units in enumerate(self.config['dense_units']):
            x = layers.Dense(
                units,
                activation='relu',
                kernel_regularizer=keras.regularizers.l2(self.config['l2_regularization']),
                name=f'dense_{i+1}'
            )(x)
            x = layers.Dropout(self.config['dropout_rate'], name=f'dropout_dense_{i+1}')(x)
            x = layers.BatchNormalization(name=f'bn_dense_{i+1}')(x)
        
        # Output layer
        outputs = layers.Dense(
            self.config['output_features'],
            activation='linear',
            name='coordinate_output'
        )(x)
        
        # Create model
        model = keras.Model(
            inputs=inputs,
            outputs=outputs,
            name='SpatialTemporal_GNN_Model'
        )
        
        # Compile model
        optimizer = keras.optimizers.Adam(
            learning_rate=self.config['learning_rate'],
            clipnorm=1.0
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
        Train the ST-GNN model
        
        Args:
            X_train: Training sequences
            y_train: Training targets
            X_val: Validation sequences (optional)
            y_val: Validation targets (optional)
        
        Returns:
            Training history dictionary
        """
        print(f"[TRAINING] Training Spatial-Temporal GNN model...")
        print(f"[DATA] Training data shape: {X_train.shape}")
        print(f"[TARGET] Target data shape: {y_train.shape}")
        print(f"[SPATIAL] Spatial nodes: {self.config['num_spatial_nodes']}")
        print(f"⏰ Temporal attention: {self.config['use_temporal_attention']}")
        
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
                patience=self.config['patience'] // 3,
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
            'num_spatial_nodes': self.config['num_spatial_nodes'],
            'use_temporal_attention': self.config['use_temporal_attention']
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
        
        print(f"[DATA] Evaluating Spatial-Temporal GNN model...")
        
        # Make predictions
        y_pred = self.predict(X_test)
        
        # Basic metrics
        test_metrics = self.model.evaluate(X_test, y_test, verbose=0)
        metric_names = self.model.metrics_names
        
        results = dict(zip(metric_names, test_metrics))
        results.update({
            'num_spatial_nodes': self.config['num_spatial_nodes'],
            'use_temporal_attention': self.config['use_temporal_attention']
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
                'GraphConvolution': GraphConvolution,
                'TemporalAttention': TemporalAttention
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
        fig.suptitle(f'ST-GNN Training History (Nodes={self.config["num_spatial_nodes"]}, Attention={self.config["use_temporal_attention"]})', 
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
