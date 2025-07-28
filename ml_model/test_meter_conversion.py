#!/usr/bin/env python3
"""
Test script to verify meter conversion functionality
"""

import numpy as np
import sys
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.error_calculator import calculate_meter_errors, calculate_pixel_errors, haversine_distance

def test_haversine_distance():
    """Test Haversine distance calculation"""
    print("🧪 Testing Haversine distance calculation...")
    
    # Test case 1: Same point
    lat1, lon1 = 40.0, -83.0
    lat2, lon2 = 40.0, -83.0
    distance = haversine_distance(lat1, lon1, lat2, lon2)
    print(f"   Same point distance: {distance:.2f} meters (expected: ~0)")
    
    # Test case 2: Known distance (Columbus to Cleveland ~200km)
    lat1, lon1 = 39.9612, -82.9988  # Columbus
    lat2, lon2 = 41.4993, -81.6944  # Cleveland
    distance = haversine_distance(lat1, lon1, lat2, lon2)
    print(f"   Columbus to Cleveland: {distance/1000:.1f} km (expected: ~200km)")
    
    # Test case 3: Small distance (1 degree lat ≈ 111km)
    lat1, lon1 = 40.0, -83.0
    lat2, lon2 = 41.0, -83.0
    distance = haversine_distance(lat1, lon1, lat2, lon2)
    print(f"   1 degree latitude: {distance/1000:.1f} km (expected: ~111km)")

def test_meter_errors():
    """Test meter error calculation"""
    print("\n🧪 Testing meter error calculation...")
    
    # Create sample data
    np.random.seed(42)
    n_samples = 1000
    
    # Normalized coordinates (0-1)
    y_true = np.random.random((n_samples, 2))
    y_pred = y_true + np.random.normal(0, 0.01, (n_samples, 2))  # Add small noise
    
    # DACT dataset bounds (Columbus area)
    bounds = {
        'lat_min': 39.8,
        'lat_max': 40.2,
        'lng_min': -83.2,
        'lng_max': -82.8
    }
    
    # Calculate meter errors
    meter_stats = calculate_meter_errors(y_true, y_pred, bounds)
    
    print(f"   Mean error: {meter_stats['mean_error']:.1f} meters")
    print(f"   Median error: {meter_stats['median_error']:.1f} meters")
    print(f"   Std error: {meter_stats['std_error']:.1f} meters")
    print(f"   Min error: {meter_stats['min_error']:.1f} meters")
    print(f"   Max error: {meter_stats['max_error']:.1f} meters")
    
    # Check distribution
    print(f"\n   Error distribution:")
    for range_label, stats in meter_stats['distribution'].items():
        print(f"     {range_label}: {stats['count']} samples ({stats['percentage']:.1f}%)")

def test_pixel_errors():
    """Test pixel error calculation"""
    print("\n🧪 Testing pixel error calculation...")
    
    # Create sample data
    np.random.seed(42)
    n_samples = 1000
    
    # Normalized coordinates (0-1)
    y_true = np.random.random((n_samples, 2))
    y_pred = y_true + np.random.normal(0, 0.01, (n_samples, 2))  # Add small noise
    
    # DACT dataset bounds (Columbus area)
    bounds = {
        'lat_min': 39.8,
        'lat_max': 40.2,
        'lng_min': -83.2,
        'lng_max': -82.8
    }
    
    # Calculate pixel errors
    pixel_stats = calculate_pixel_errors(y_true, y_pred, bounds)
    
    print(f"   Mean error: {pixel_stats['mean_error']:.1f} pixels")
    print(f"   Median error: {pixel_stats['median_error']:.1f} pixels")
    print(f"   Std error: {pixel_stats['std_error']:.1f} pixels")
    print(f"   Min error: {pixel_stats['min_error']:.1f} pixels")
    print(f"   Max error: {pixel_stats['max_error']:.1f} pixels")
    
    # Check distribution
    print(f"\n   Error distribution:")
    for range_label, stats in pixel_stats['distribution'].items():
        print(f"     {range_label}: {stats['count']} samples ({stats['percentage']:.1f}%)")

def test_conversion_consistency():
    """Test consistency between meter and pixel conversions"""
    print("\n🧪 Testing conversion consistency...")
    
    # Create sample data with known errors
    np.random.seed(42)
    n_samples = 100
    
    # Normalized coordinates (0-1)
    y_true = np.random.random((n_samples, 2))
    y_pred = y_true + np.random.normal(0, 0.01, (n_samples, 2))
    
    # DACT dataset bounds (Columbus area)
    bounds = {
        'lat_min': 39.8,
        'lat_max': 40.2,
        'lng_min': -83.2,
        'lng_max': -82.8
    }
    
    # Calculate both types of errors
    meter_stats = calculate_meter_errors(y_true, y_pred, bounds)
    pixel_stats = calculate_pixel_errors(y_true, y_pred, bounds)
    
    # Check if both calculations use the same coordinate conversion
    true_coords_meter = meter_stats['true_coords']
    true_coords_pixel = pixel_stats['true_pixels']
    
    # Convert pixel coordinates back to lat/lng for comparison
    lat_span = bounds['lat_max'] - bounds['lat_min']
    lng_span = bounds['lng_max'] - bounds['lng_min']
    margin = 50
    canvas_size = (1200, 800)
    
    # Convert pixel coordinates back to lat/lng
    pixel_to_lat = (true_coords_pixel[:, 1] - margin) / (canvas_size[1] - 2 * margin) * lat_span + bounds['lat_min']
    pixel_to_lng = (true_coords_pixel[:, 0] - margin) / (canvas_size[0] - 2 * margin) * lng_span + bounds['lng_min']
    
    # Check if conversions are consistent
    lat_diff = np.abs(true_coords_meter[:, 0] - pixel_to_lat)
    lng_diff = np.abs(true_coords_meter[:, 1] - pixel_to_lng)
    
    print(f"   Max latitude conversion difference: {np.max(lat_diff):.6f} degrees")
    print(f"   Max longitude conversion difference: {np.max(lng_diff):.6f} degrees")
    print(f"   Conversion consistency: {'[OK] PASS' if np.max(lat_diff) < 1e-6 and np.max(lng_diff) < 1e-6 else '[ERROR] FAIL'}")

def main():
    """Run all tests"""
    print("[TRAINING] Testing Meter Conversion Functionality")
    print("=" * 50)
    
    test_haversine_distance()
    test_meter_errors()
    test_pixel_errors()
    test_conversion_consistency()
    
    print("\n[OK] All tests completed!")

if __name__ == "__main__":
    main() 