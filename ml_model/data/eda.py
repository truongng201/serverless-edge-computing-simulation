#!/usr/bin/env python3
"""
Simple DACT Dataset EDA - No formatting issues
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def simple_eda():
    """Simple but comprehensive DACT EDA"""
    print("[DATA] DACT Dataset - Simple EDA Analysis")
    print("=" * 50)
    
    # Load dataset
    csv_path = Path(__file__).parent.parent / "DACT Easy-Dataset.csv"
    print(f"Loading: {csv_path}")
    
    data = pd.read_csv(csv_path)
    print(f"[OK] Dataset loaded: {data.shape}")
    print(f"Columns: {list(data.columns)}")
    
    # 1. BASIC INFO
    print(f"\n[MENU] DATASET OVERVIEW")
    print(f"Total Records: {len(data):,}")
    print(f"Total Columns: {len(data.columns)}")
    
    # Column info without formatting issues
    print(f"\nColumn Details:")
    for col in data.columns:
        non_null = data[col].count()
        dtype = str(data[col].dtype)
        print(f"  {col}: {dtype} - {non_null:,} non-null values")
    
    # 2. TRAJECTORY ANALYSIS
    print(f"\n[SPATIAL] TRAJECTORY ANALYSIS")
    print(f"Unique TripIDs: {data['TripID'].nunique()}")
    print(f"TripID samples: {data['TripID'].unique()[:10].tolist()}")
    
    # Group by TripID
    traj_lengths = data.groupby('TripID').size()
    print(f"\nTrajectory Length Statistics:")
    print(f"  Count: {len(traj_lengths)} trajectories")
    print(f"  Mean: {traj_lengths.mean():.1f} timesteps")
    print(f"  Median: {traj_lengths.median():.1f} timesteps")
    print(f"  Min: {traj_lengths.min()} timesteps")
    print(f"  Max: {traj_lengths.max()} timesteps")
    print(f"  Std: {traj_lengths.std():.1f} timesteps")
    
    # Sample trajectories
    print(f"\nSample Trajectories:")
    for trip_id in data['TripID'].unique()[:10]:
        trip_data = data[data['TripID'] == trip_id]
        avg_speed = trip_data['Speed'].mean()
        print(f"  {trip_id}: {len(trip_data)} steps, avg speed: {avg_speed:.1f} mph")
    
    # 3. GEOGRAPHICAL BOUNDS
    print(f"\n🌍 GEOGRAPHICAL ANALYSIS")
    print(f"Latitude range: {data['Latitude'].min():.6f} to {data['Latitude'].max():.6f}")
    print(f"Longitude range: {data['Longitude'].min():.6f} to {data['Longitude'].max():.6f}")
    
    lat_span = data['Latitude'].max() - data['Latitude'].min()
    lng_span = data['Longitude'].max() - data['Longitude'].min()
    print(f"Geographical span: {lat_span:.6f}[SYMBOL] x {lng_span:.6f}[SYMBOL]")
    
    # 4. MOVEMENT PATTERNS
    print(f"\n🚗 MOVEMENT ANALYSIS")
    print(f"Speed (mph):")
    print(f"  Mean: {data['Speed'].mean():.2f}")
    print(f"  Median: {data['Speed'].median():.2f}")
    print(f"  Range: {data['Speed'].min():.2f} - {data['Speed'].max():.2f}")
    
    print(f"Acceleration (m/s²):")
    print(f"  Mean: {data['Acceleration'].mean():.3f}")
    print(f"  Range: {data['Acceleration'].min():.3f} - {data['Acceleration'].max():.3f}")
    
    print(f"Heading (degrees):")
    print(f"  Range: {data['Heading'].min():.1f} - {data['Heading'].max():.1f}")
    
    # 5. SEGMENT TYPES
    print(f"\n[TARGET] SEGMENT TYPES")
    segment_counts = data['SegmentType'].value_counts().head(10)
    print("Top segment types:")
    for segment, count in segment_counts.items():
        if pd.notna(segment) and segment != 'NULL':
            pct = count / len(data) * 100
            print(f"  {segment}: {count:,} ({pct:.2f}%)")
    
    # 6. LSTM RECOMMENDATIONS
    print(f"\n[MODEL] LSTM TRAINING PLAN")
    print(f"Total trajectories: {data['TripID'].nunique()}")
    
    # Calculate sequences for LSTM (5 timesteps -> 1 prediction)
    sequence_length = 5
    total_sequences = 0
    for trip_id in data['TripID'].unique():
        trip_length = len(data[data['TripID'] == trip_id])
        trip_sequences = max(0, trip_length - sequence_length)
        total_sequences += trip_sequences
    
    print(f"Potential training sequences: {total_sequences:,}")
    print(f"Average sequences per trajectory: {total_sequences / data['TripID'].nunique():.1f}")
    
    # Train/test split as requested
    train_trips = 30
    test_trips = 20
    
    print(f"\nProposed Split (as requested):")
    print(f"  Training: First {train_trips} trips")
    print(f"  Testing: Next {test_trips} trips")
    
    # Calculate sequences for train/test
    train_sequences = 0
    test_sequences = 0
    
    trip_ids = data['TripID'].unique()
    for i, trip_id in enumerate(trip_ids):
        trip_length = len(data[data['TripID'] == trip_id])
        trip_seqs = max(0, trip_length - sequence_length)
        
        if i < train_trips:
            train_sequences += trip_seqs
        elif i < train_trips + test_trips:
            test_sequences += trip_seqs
    
    print(f"  Training sequences: ~{train_sequences:,}")
    print(f"  Test sequences: ~{test_sequences:,}")
    
    print(f"\nModel Architecture:")
    print(f"  Input: 5 timesteps x 5 features (lat, lng, speed, heading, accel)")
    print(f"  Output: 2 coordinates (next lat, lng)")
    print(f"  Target: <50 pixel coordinate error")
    
    # 7. SIMPLE VISUALIZATION
    print(f"\n[DATA] CREATING PLOTS")
    
    plt.figure(figsize=(15, 10))
    
    # Plot 1: Trajectory lengths
    plt.subplot(2, 3, 1)
    traj_lengths.hist(bins=20, alpha=0.7, color='skyblue', edgecolor='black')
    plt.title('Trajectory Length Distribution')
    plt.xlabel('Length (timesteps)')
    plt.ylabel('Frequency')
    plt.axvline(traj_lengths.mean(), color='red', linestyle='--', label=f'Mean: {traj_lengths.mean():.0f}')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Plot 2: Speed distribution
    plt.subplot(2, 3, 2)
    data['Speed'].hist(bins=30, alpha=0.7, color='lightgreen', edgecolor='black')
    plt.title('Speed Distribution')
    plt.xlabel('Speed (mph)')
    plt.ylabel('Frequency')
    plt.axvline(data['Speed'].mean(), color='red', linestyle='--', label=f'Mean: {data["Speed"].mean():.1f}')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Plot 3: Geographical scatter
    plt.subplot(2, 3, 3)
    sample_data = data.sample(min(5000, len(data)))
    plt.scatter(sample_data['Longitude'], sample_data['Latitude'], 
               c=sample_data['Speed'], cmap='viridis', alpha=0.6, s=2)
    plt.title('Geographical Distribution')
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.colorbar(label='Speed (mph)')
    plt.grid(True, alpha=0.3)
    
    # Plot 4: Speed vs Acceleration
    plt.subplot(2, 3, 4)
    sample_data = data.sample(min(3000, len(data)))
    plt.scatter(sample_data['Speed'], sample_data['Acceleration'], alpha=0.5, s=3)
    plt.title('Speed vs Acceleration')
    plt.xlabel('Speed (mph)')
    plt.ylabel('Acceleration (m/s²)')
    plt.axhline(0, color='red', linestyle='--', alpha=0.5)
    plt.grid(True, alpha=0.3)
    
    # Plot 5: Heading distribution
    plt.subplot(2, 3, 5)
    data['Heading'].hist(bins=36, alpha=0.7, color='purple', edgecolor='black')
    plt.title('Heading Distribution')
    plt.xlabel('Heading (degrees)')
    plt.ylabel('Frequency')
    plt.grid(True, alpha=0.3)
    
    # Plot 6: Segment types
    plt.subplot(2, 3, 6)
    top_segments = data['SegmentType'].value_counts().head(8)
    top_segments = top_segments[top_segments.index.notna()]
    top_segments = top_segments[top_segments.index != 'NULL']
    if len(top_segments) > 0:
        top_segments.plot(kind='bar', color='orange', alpha=0.7)
        plt.title('Top Segment Types')
        plt.xlabel('Segment Type')
        plt.ylabel('Count')
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('dact_simple_eda.png', dpi=300, bbox_inches='tight')
    print("[DISK] Saved plots: dact_simple_eda.png")
    plt.show()
    
    print(f"\n[OK] EDA COMPLETE!")
    print(f"[TRAINING] Dataset is ready for LSTM training!")
    print(f"[CHART] Recommendation: Train on first 30 trips, test on next 20 trips")
    
    return data, traj_lengths

if __name__ == "__main__":
    data, traj_lengths = simple_eda() 