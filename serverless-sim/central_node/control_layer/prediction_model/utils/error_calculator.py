#!/usr/bin/env python3
"""
Error Calculator Utilities
Common functions for calculating prediction errors in meters and pixels
"""

import numpy as np
from typing import Dict, Tuple
from math import radians, cos, sin, asin, sqrt

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

def print_meter_results(meter_stats: Dict, pixel_stats: Dict = None):
    """
    Print formatted meter error results
    
    Args:
        meter_stats: Meter error statistics
        pixel_stats: Pixel error statistics (optional, for comparison)
    """
    print(f"\n[BOUNDS] Coordinate Accuracy (Meters):")
    print(f"  Mean Error: {meter_stats['mean_error']:.1f} meters")
    print(f"  Median Error: {meter_stats['median_error']:.1f} meters")
    print(f"  Std Deviation: {meter_stats['std_error']:.1f} meters")
    print(f"  Min Error: {meter_stats['min_error']:.1f} meters")
    print(f"  Max Error: {meter_stats['max_error']:.1f} meters")
    
    print(f"\n[DATA] Error Distribution (Meters):")
    for range_label, stats in meter_stats['distribution'].items():
        print(f"  {range_label:<10}: {stats['count']:>6,} samples ({stats['percentage']:>5.1f}%)")
    
    # Success metrics (meters)
    excellent_predictions = meter_stats['distribution']['0-100m']['count']
    good_predictions = excellent_predictions + meter_stats['distribution']['100-500m']['count']
    acceptable_predictions = good_predictions + meter_stats['distribution']['500m-1km']['count']
    
    total_predictions = len(meter_stats['meter_errors'])
    
    print(f"\n[TARGET] Success Rates (Meters):")
    print(f"  Excellent (<100m): {excellent_predictions:,} ({excellent_predictions/total_predictions*100:.1f}%)")
    print(f"  Good (<500m): {good_predictions:,} ({good_predictions/total_predictions*100:.1f}%)")
    print(f"  Acceptable (<1km): {acceptable_predictions:,} ({acceptable_predictions/total_predictions*100:.1f}%)")
    
    # Also show pixel results for comparison if provided
    if pixel_stats:
        print(f"\n[BOUNDS] Coordinate Accuracy (Pixels - for comparison):")
        print(f"  Mean Error: {pixel_stats['mean_error']:.1f} pixels")
        print(f"  Median Error: {pixel_stats['median_error']:.1f} pixels")
        print(f"  Std Deviation: {pixel_stats['std_error']:.1f} pixels") 