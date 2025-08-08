#!/usr/bin/env python3
"""
LSTM Training and Testing Script
Train on 30 trips, test on 20 trips, measure coordinate accuracy
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import time
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from data.data_loader import DACTDataLoader
from lstm_baseline.lstm_model import LSTMTrajectoryModel

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    
    Args:
        lat1, lon1: Latitude and longitude of first point
        lat2, lon2: Latitude and longitude of second point
        
    Returns:
        Distance in meters
    """
    from math import radians, cos, sin, asin, sqrt
    
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in meters
    r = 6371000
    
    return c * r

def calculate_meter_errors(y_true: np.ndarray, y_pred: np.ndarray, 
                          bounds: Dict) -> Dict:
    """
    Calculate prediction errors in meters using Haversine distance
    
    Args:
        y_true: True normalized coordinates [N, 2]
        y_pred: Predicted normalized coordinates [N, 2]
        bounds: Geographical bounds for denormalization
        
    Returns:
        Dictionary with meter error statistics
    """
    # Denormalize coordinates to lat/lng
    lat_span = bounds['lat_max'] - bounds['lat_min']
    lng_span = bounds['lng_max'] - bounds['lng_min']
    
    true_coords = np.zeros_like(y_true)
    pred_coords = np.zeros_like(y_pred)
    
    true_coords[:, 0] = y_true[:, 0] * lat_span + bounds['lat_min']  # lat
    true_coords[:, 1] = y_true[:, 1] * lng_span + bounds['lng_min']  # lng
    pred_coords[:, 0] = y_pred[:, 0] * lat_span + bounds['lat_min']  # lat
    pred_coords[:, 1] = y_pred[:, 1] * lng_span + bounds['lng_min']  # lng
    
    # Calculate meter distances using Haversine
    meter_errors = np.array([
        haversine_distance(
            true_coords[i, 0], true_coords[i, 1],
            pred_coords[i, 0], pred_coords[i, 1]
        ) for i in range(len(true_coords))
    ])
    
    # Calculate statistics
    error_stats = {
        'mean_error': np.mean(meter_errors),
        'median_error': np.median(meter_errors),
        'min_error': np.min(meter_errors),
        'max_error': np.max(meter_errors),
        'std_error': np.std(meter_errors),
        'meter_errors': meter_errors,
        'true_coords': true_coords,
        'pred_coords': pred_coords
    }
    
    # Error distribution in meters
    error_ranges = [
        (0, 100, '0-100m'),
        (100, 500, '100-500m'),
        (500, 1000, '500m-1km'),
        (1000, 5000, '1-5km'),
        (5000, float('inf'), '>5km')
    ]
    
    error_distribution = {}
    for min_err, max_err, label in error_ranges:
        count = np.sum((meter_errors >= min_err) & (meter_errors < max_err))
        percentage = count / len(meter_errors) * 100
        error_distribution[label] = {'count': int(count), 'percentage': float(percentage)}
    
    error_stats['distribution'] = error_distribution
    
    return error_stats

def calculate_pixel_errors(y_true: np.ndarray, y_pred: np.ndarray, 
                          bounds: Dict, canvas_size: Tuple[int, int] = (1200, 800)) -> Dict:
    """
    Calculate prediction errors in pixels (legacy function for comparison)
    
    Args:
        y_true: True normalized coordinates [N, 2]
        y_pred: Predicted normalized coordinates [N, 2]
        bounds: Geographical bounds for denormalization
        canvas_size: Canvas size for pixel conversion
        
    Returns:
        Dictionary with pixel error statistics
    """
    # Denormalize coordinates
    lat_span = bounds['lat_max'] - bounds['lat_min']
    lng_span = bounds['lng_max'] - bounds['lng_min']
    
    true_coords = np.zeros_like(y_true)
    pred_coords = np.zeros_like(y_pred)
    
    true_coords[:, 0] = y_true[:, 0] * lat_span + bounds['lat_min']  # lat
    true_coords[:, 1] = y_true[:, 1] * lng_span + bounds['lng_min']  # lng
    pred_coords[:, 0] = y_pred[:, 0] * lat_span + bounds['lat_min']  # lat
    pred_coords[:, 1] = y_pred[:, 1] * lng_span + bounds['lng_min']  # lng
    
    # Convert to pixels
    margin = 50
    true_pixels = np.zeros_like(true_coords)
    pred_pixels = np.zeros_like(pred_coords)
    
    # Lat to Y (inverted)
    true_pixels[:, 1] = ((true_coords[:, 0] - bounds['lat_min']) / lat_span) * (canvas_size[1] - 2 * margin) + margin
    pred_pixels[:, 1] = ((pred_coords[:, 0] - bounds['lat_min']) / lat_span) * (canvas_size[1] - 2 * margin) + margin
    
    # Lng to X
    true_pixels[:, 0] = ((true_coords[:, 1] - bounds['lng_min']) / lng_span) * (canvas_size[0] - 2 * margin) + margin
    pred_pixels[:, 0] = ((pred_coords[:, 1] - bounds['lng_min']) / lng_span) * (canvas_size[0] - 2 * margin) + margin
    
    # Calculate pixel distances
    pixel_errors = np.sqrt(np.sum((true_pixels - pred_pixels) ** 2, axis=1))
    
    # Calculate statistics
    error_stats = {
        'mean_error': np.mean(pixel_errors),
        'median_error': np.median(pixel_errors),
        'min_error': np.min(pixel_errors),
        'max_error': np.max(pixel_errors),
        'std_error': np.std(pixel_errors),
        'pixel_errors': pixel_errors,
        'true_pixels': true_pixels,
        'pred_pixels': pred_pixels
    }
    
    # Error distribution
    error_ranges = [
        (0, 10, '0-10px'),
        (10, 25, '10-25px'),
        (25, 50, '25-50px'),
        (50, 100, '50-100px'),
        (100, float('inf'), '>100px')
    ]
    
    error_distribution = {}
    for min_err, max_err, label in error_ranges:
        count = np.sum((pixel_errors >= min_err) & (pixel_errors < max_err))
        percentage = count / len(pixel_errors) * 100
        error_distribution[label] = {'count': int(count), 'percentage': float(percentage)}
    
    error_stats['distribution'] = error_distribution
    
    return error_stats

def run_lstm_experiment(train_trips: int = 30, test_trips: int = 20, 
                       sequence_length: int = 5, epochs: int = 50) -> Dict:
    """
    Run complete LSTM training and testing experiment
    
    Args:
        train_trips: Number of trips for training
        test_trips: Number of trips for testing
        sequence_length: Input sequence length
        epochs: Training epochs
        
    Returns:
        Complete results dictionary
    """
    print("[TRAIN] LSTM Trajectory Prediction Experiment")
    print("=" * 60)
    print(f"Configuration:")
    print(f"  Training trips: {train_trips}")
    print(f"  Testing trips: {test_trips}")
    print(f"  Sequence length: {sequence_length}")
    print(f"  Training epochs: {epochs}")
    
    # Step 1: Load and prepare data
    print(f"\n[STEP1] Step 1: Loading and preparing data...")
    start_time = time.time()
    
    loader = DACTDataLoader(sequence_length=sequence_length)
    data_dict = loader.prepare_for_training(train_trips, test_trips)
    
    data_load_time = time.time() - start_time
    print(f"[OK] Data preparation completed in {data_load_time:.1f}s")
    
    # Step 2: Create and configure model
    print(f"\n[MODEL] Step 2: Creating LSTM model...")
    
    model_config = {
        'sequence_length': sequence_length,
        'input_features': 5,
        'output_features': 2,
        'lstm_units': [64, 32],
        'dropout_rate': 0.2,
        'learning_rate': 0.001,
        'batch_size': 32,
        'epochs': epochs,
        'validation_split': 0.2,
        'patience': 10
    }
    
    model = LSTMTrajectoryModel(model_config)
    model.build_model()
    
    # Step 3: Train model
    print(f"\n[STEP3] Step 3: Training model...")
    train_start_time = time.time()
    
    history = model.train(
        data_dict['X_train'], 
        data_dict['y_train'],
        verbose=1
    )
    
    train_time = time.time() - train_start_time
    print(f"[OK] Training completed in {train_time:.1f}s")
    
    # Step 4: Evaluate model
    print(f"\n[STEP4] Step 4: Evaluating model...")
    test_start_time = time.time()
    
    # Get predictions
    y_pred = model.predict(data_dict['X_test'])
    y_true = data_dict['y_test']
    
    # Standard metrics (verbose=0 to avoid Unicode issues)
    metrics = model.evaluate(data_dict['X_test'], data_dict['y_test'])
    
    # Meter-based accuracy (primary)
    meter_stats = calculate_meter_errors(y_true, y_pred, data_dict['bounds'])
    
    # Pixel-based accuracy (for comparison)
    pixel_stats = calculate_pixel_errors(y_true, y_pred, data_dict['bounds'])
    
    test_time = time.time() - test_start_time
    print(f"[OK] Evaluation completed in {test_time:.1f}s")
    
    # Step 5: Display results
    print(f"\n[CHART] EXPERIMENT RESULTS")
    print("=" * 50)
    
    print(f"\n[SYMBOL] Dataset Statistics:")
    print(f"  Training sequences: {len(data_dict['X_train']):,}")
    print(f"  Testing sequences: {len(data_dict['X_test']):,}")
    print(f"  Sequence length: {sequence_length} timesteps")
    
    print(f"\n[MODEL] Model Performance:")
    print(f"  Normalized MSE: {metrics['mse']:.6f}")
    print(f"  Normalized MAE: {metrics['mae']:.6f}")
    print(f"  Normalized RMSE: {metrics['rmse']:.6f}")
    
    print(f"\n[BOUNDS] Coordinate Accuracy (Meters):")
    print(f"  Mean Error: {meter_stats['mean_error']:.1f} meters")
    print(f"  Median Error: {meter_stats['median_error']:.1f} meters")
    print(f"  Std Deviation: {meter_stats['std_error']:.1f} meters")
    print(f"  Min Error: {meter_stats['min_error']:.1f} meters")
    print(f"  Max Error: {meter_stats['max_error']:.1f} meters")
    
    print(f"\n[STATS] Error Distribution (Meters):")
    for range_label, stats in meter_stats['distribution'].items():
        print(f"  {range_label:<10}: {stats['count']:>6,} samples ({stats['percentage']:>5.1f}%)")
    
    # Success metrics (meters)
    excellent_predictions = meter_stats['distribution']['0-100m']['count']
    good_predictions = excellent_predictions + meter_stats['distribution']['100-500m']['count']
    acceptable_predictions = good_predictions + meter_stats['distribution']['500m-1km']['count']
    
    total_predictions = len(meter_stats['meter_errors'])
    
    print(f"\n[RATES] Success Rates (Meters):")
    print(f"  Excellent (<100m): {excellent_predictions:,} ({excellent_predictions/total_predictions*100:.1f}%)")
    print(f"  Good (<500m): {good_predictions:,} ({good_predictions/total_predictions*100:.1f}%)")
    print(f"  Acceptable (<1km): {acceptable_predictions:,} ({acceptable_predictions/total_predictions*100:.1f}%)")
    
    # Also show pixel results for comparison
    print(f"\n[BOUNDS] Coordinate Accuracy (Pixels - for comparison):")
    print(f"  Mean Error: {pixel_stats['mean_error']:.1f} pixels")
    print(f"  Median Error: {pixel_stats['median_error']:.1f} pixels")
    print(f"  Std Deviation: {pixel_stats['std_error']:.1f} pixels")
    
    # Performance timing
    print(f"\n[TIME] Performance Timing:")
    print(f"  Data loading: {data_load_time:.1f}s")
    print(f"  Model training: {train_time:.1f}s")
    print(f"  Model testing: {test_time:.1f}s")
    print(f"  Total time: {data_load_time + train_time + test_time:.1f}s")
    
    # Step 6: Create visualizations
    print(f"\n[VISUAL] Creating visualizations...")
    
    # Training history
    model.plot_training_history('lstm_training_history.png')
    
    # Error distribution plot
    plt.figure(figsize=(15, 10))
    
    # 1. Meter Error histogram
    plt.subplot(2, 3, 1)
    plt.hist(meter_stats['meter_errors'], bins=50, alpha=0.7, color='skyblue', edgecolor='black')
    plt.axvline(meter_stats['mean_error'], color='red', linestyle='--', 
                label=f'Mean: {meter_stats["mean_error"]:.1f}m')
    plt.axvline(meter_stats['median_error'], color='green', linestyle='--', 
                label=f'Median: {meter_stats["median_error"]:.1f}m')
    plt.title('Prediction Error Distribution (Meters)')
    plt.xlabel('Error (meters)')
    plt.ylabel('Frequency')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 2. Meter Error ranges bar chart
    plt.subplot(2, 3, 2)
    ranges = list(meter_stats['distribution'].keys())
    counts = [meter_stats['distribution'][r]['count'] for r in ranges]
    colors = ['green', 'lightgreen', 'yellow', 'orange', 'red']
    plt.bar(ranges, counts, color=colors[:len(ranges)], alpha=0.7)
    plt.title('Error Range Distribution (Meters)')
    plt.xlabel('Error Range')
    plt.ylabel('Count')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    
    # 3. Scatter plot of predictions vs actual (sample)
    plt.subplot(2, 3, 3)
    sample_size = min(1000, len(y_true))
    sample_idx = np.random.choice(len(y_true), sample_size, replace=False)
    
    plt.scatter(y_true[sample_idx, 0], y_pred[sample_idx, 0], alpha=0.5, s=10, label='Latitude')
    plt.scatter(y_true[sample_idx, 1], y_pred[sample_idx, 1], alpha=0.5, s=10, label='Longitude')
    plt.plot([0, 1], [0, 1], 'r--', label='Perfect Prediction')
    plt.title('Predicted vs Actual (Normalized)')
    plt.xlabel('Actual')
    plt.ylabel('Predicted')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 4. Geographical error plot (sample) - using meter errors
    plt.subplot(2, 3, 4)
    sample_true = pixel_stats['true_pixels'][sample_idx]
    sample_pred = pixel_stats['pred_pixels'][sample_idx]
    sample_errors = meter_stats['meter_errors'][sample_idx]
    
    scatter = plt.scatter(sample_true[:, 0], sample_true[:, 1], 
                         c=sample_errors, cmap='Reds', alpha=0.6, s=20)
    plt.colorbar(scatter, label='Error (meters)')
    plt.title('Geographical Distribution of Errors (Meters)')
    plt.xlabel('X (pixels)')
    plt.ylabel('Y (pixels)')
    plt.grid(True, alpha=0.3)
    
    # 5. Error vs distance from start
    plt.subplot(2, 3, 5)
    # Calculate distance from first position for each test sequence
    error_vs_seq = []
    for i, metadata in enumerate(data_dict['test_metadata']):
        if i < len(meter_stats['meter_errors']):
            error_vs_seq.append(meter_stats['meter_errors'][i])
    
    if len(error_vs_seq) > 100:
        plt.scatter(range(len(error_vs_seq)), error_vs_seq, alpha=0.5, s=2)
        plt.title('Error vs Sequence Order (Meters)')
        plt.xlabel('Test Sequence')
        plt.ylabel('Error (meters)')
        plt.grid(True, alpha=0.3)
    
    # 6. Model loss
    plt.subplot(2, 3, 6)
    if hasattr(model.history, 'history'):
        epochs_range = range(1, len(model.history.history['loss']) + 1)
        plt.plot(epochs_range, model.history.history['loss'], label='Training Loss')
        plt.plot(epochs_range, model.history.history['val_loss'], label='Validation Loss')
        plt.title('Training Progress')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.legend()
        plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('lstm_experiment_results.png', dpi=300, bbox_inches='tight')
    print("[DISK] Saved experiment results: lstm_experiment_results.png")
    plt.show()
    
    # Step 7: Save model
    model.save_model('lstm_trajectory_model.keras')
    
    # Compile final results
    results = {
        'experiment_config': {
            'train_trips': train_trips,
            'test_trips': test_trips,
            'sequence_length': sequence_length,
            'epochs': epochs
        },
        'data_stats': {
            'train_sequences': len(data_dict['X_train']),
            'test_sequences': len(data_dict['X_test']),
            'train_trips': data_dict['train_trips'],
            'test_trips': data_dict['test_trips']
        },
        'model_metrics': metrics,
        'meter_accuracy': meter_stats,
        'pixel_accuracy': pixel_stats,  # Keep for comparison
        'timing': {
            'data_load_time': data_load_time,
            'train_time': train_time,
            'test_time': test_time
        },
        'success_rates': {
            'excellent_100m': excellent_predictions/total_predictions*100,
            'good_500m': good_predictions/total_predictions*100,
            'acceptable_1km': acceptable_predictions/total_predictions*100
        }
    }
    
    print(f"\n[OK] EXPERIMENT COMPLETED!")
    print(f"[RESULT] Key Result: Mean coordinate error = {meter_stats['mean_error']:.1f} meters")
    print(f"🏆 Success rate (<500m) = {good_predictions/total_predictions*100:.1f}%")
    
    return results

def main():
    """Main function to run the experiment"""
    print("[TARGET] LSTM Trajectory Prediction - Complete Experiment")
    print("[TARGET] Train on 30 trips, test on 20 trips")
    print("[TARGET] Measure coordinate accuracy in meters")
    
    # Run experiment with default settings
    results = run_lstm_experiment(
        train_trips=30,
        test_trips=20,
        sequence_length=5,
        epochs=50
    )
    
    return results

if __name__ == "__main__":
    results = main() 