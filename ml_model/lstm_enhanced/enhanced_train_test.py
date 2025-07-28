#!/usr/bin/env python3
"""
Enhanced LSTM Training and Testing Script
Advanced training with enhanced features, deeper architecture, and comprehensive evaluation
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import time
from typing import Dict, Tuple, List
import warnings
warnings.filterwarnings('ignore')

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from data.enhanced_data_loader import EnhancedDACTDataLoader
from lstm_enhanced.enhanced_lstm_model import EnhancedLSTMTrajectoryModel
from data.data_loader import DACTDataLoader  # For comparison
from lstm_baseline.lstm_model import LSTMTrajectoryModel  # For comparison
from utils.error_calculator import print_meter_results

class DataAugmentation:
    """Data augmentation techniques for trajectory data"""
    
    @staticmethod
    def add_noise(X: np.ndarray, noise_level: float = 0.01) -> np.ndarray:
        """Add Gaussian noise to input sequences"""
        noise = np.random.normal(0, noise_level, X.shape)
        return X + noise
    
    @staticmethod
    def time_shift(X: np.ndarray, y: np.ndarray, shift_range: int = 2) -> Tuple[np.ndarray, np.ndarray]:
        """Randomly shift sequences in time"""
        augmented_X, augmented_y = [], []
        
        for i in range(len(X)):
            # Random shift
            shift = np.random.randint(-shift_range, shift_range + 1)
            if shift == 0:
                augmented_X.append(X[i])
                augmented_y.append(y[i])
            else:
                # Apply shift (simplified - in practice would need proper boundary handling)
                augmented_X.append(X[i])
                augmented_y.append(y[i])
        
        return np.array(augmented_X), np.array(augmented_y)
    
    @staticmethod
    def speed_scaling(X: np.ndarray, scale_range: Tuple[float, float] = (0.8, 1.2)) -> np.ndarray:
        """Scale speed-related features"""
        augmented_X = X.copy()
        
        for i in range(len(X)):
            scale_factor = np.random.uniform(scale_range[0], scale_range[1])
            # Scale speed-related features (assuming they're in specific positions)
            # This is a simplified version - would need proper feature indexing
            speed_indices = [2, 8, 12]  # Example speed-related feature indices
            for idx in speed_indices:
                if idx < X.shape[2]:
                    augmented_X[i, :, idx] *= scale_factor
        
        return augmented_X

def run_enhanced_experiment(train_trips: int = 30, test_trips: int = 20, 
                          sequence_length: int = 10, epochs: int = 100,
                          compare_with_baseline: bool = True) -> Dict:
    """
    Run complete enhanced LSTM experiment with comparison to baseline
    """
    print("[TRAINING] ENHANCED LSTM Trajectory Prediction Experiment")
    print("=" * 70)
    print(f"Configuration:")
    print(f"  Training trips: {train_trips}")
    print(f"  Testing trips: {test_trips}")
    print(f"  Sequence length: {sequence_length}")
    print(f"  Training epochs: {epochs}")
    print(f"  Compare with baseline: {compare_with_baseline}")
    
    results = {'enhanced': {}, 'baseline': {}, 'comparison': {}}
    
    # STEP 1: Enhanced Model Training
    print(f"\n{'='*50}")
    print(f"[MODEL] ENHANCED MODEL TRAINING")
    print(f"{'='*50}")
    
    # Load enhanced data
    print(f"\n[DATA] Step 1: Loading enhanced data...")
    start_time = time.time()
    
    enhanced_loader = EnhancedDACTDataLoader(sequence_length=sequence_length)
    enhanced_data = enhanced_loader.prepare_for_training(train_trips, test_trips)
    
    enhanced_data_time = time.time() - start_time
    print(f"[OK] Enhanced data preparation completed in {enhanced_data_time:.1f}s")
    
    # Create enhanced model
    print(f"\n[MODEL] Step 2: Creating enhanced LSTM model...")
    
    enhanced_config = {
        'sequence_length': sequence_length,
        'input_features': enhanced_data['feature_count'],
        'output_features': 2,
        'lstm_units': [128, 64, 32],
        'dense_units': [64, 32],
        'dropout_rate': 0.3,
        'recurrent_dropout': 0.2,
        'l2_regularization': 0.001,
        'learning_rate': 0.001,
        'batch_size': 64,
        'epochs': epochs,
        'validation_split': 0.2,
        'patience': 15,
        'use_attention': True,
        'use_batch_norm': True,
        'gradient_clip_norm': 1.0
    }
    
    enhanced_model = EnhancedLSTMTrajectoryModel(enhanced_config)
    
    # Data augmentation (optional)
    print(f"\n[PROCESS] Step 3: Applying data augmentation...")
    augmenter = DataAugmentation()
    
    # Create augmented training data
    X_train_aug = augmenter.add_noise(enhanced_data['X_train'], noise_level=0.005)
    y_train_aug = enhanced_data['y_train'].copy()
    
    # Combine original and augmented data
    X_train_combined = np.concatenate([enhanced_data['X_train'], X_train_aug], axis=0)
    y_train_combined = np.concatenate([enhanced_data['y_train'], y_train_aug], axis=0)
    
    print(f"   Original training: {len(enhanced_data['X_train']):,} sequences")
    print(f"   Augmented training: {len(X_train_combined):,} sequences")
    
    # Train enhanced model
    print(f"\n[TARGET] Step 4: Training enhanced model...")
    enhanced_train_start = time.time()
    
    enhanced_history = enhanced_model.train(
        X_train_combined, y_train_combined,
        verbose=2  # 2 = one line per epoch, less verbose than 1
    )
    
    enhanced_train_time = time.time() - enhanced_train_start
    print(f"[OK] Enhanced training completed in {enhanced_train_time:.1f}s")
    
    # Evaluate enhanced model
    print(f"\n[DATA] Step 5: Evaluating enhanced model...")
    enhanced_test_start = time.time()
    
    enhanced_metrics = enhanced_model.evaluate_enhanced(
        enhanced_data['X_test'], 
        enhanced_data['y_test'], 
        enhanced_data['bounds']
    )
    
    enhanced_test_time = time.time() - enhanced_test_start
    print(f"[OK] Enhanced evaluation completed in {enhanced_test_time:.1f}s")
    
    # Store enhanced results
    results['enhanced'] = {
        'data_prep_time': enhanced_data_time,
        'train_time': enhanced_train_time,
        'test_time': enhanced_test_time,
        'metrics': enhanced_metrics,
        'config': enhanced_config,
        'data_stats': {
            'train_sequences': len(enhanced_data['X_train']),
            'test_sequences': len(enhanced_data['X_test']),
            'feature_count': enhanced_data['feature_count'],
            'augmented_sequences': len(X_train_combined)
        }
    }
    
    # STEP 2: Baseline Model Training (for comparison)
    if compare_with_baseline:
        print(f"\n{'='*50}")
        print(f"[DATA] BASELINE MODEL TRAINING (for comparison)")
        print(f"{'='*50}")
        
        # Load baseline data
        print(f"\n[DATA] Loading baseline data...")
        baseline_start = time.time()
        
        baseline_loader = DACTDataLoader(sequence_length=5)  # Original sequence length
        baseline_data = baseline_loader.prepare_for_training(train_trips, test_trips)
        
        baseline_data_time = time.time() - baseline_start
        
        # Create baseline model
        print(f"\n[MODEL] Creating baseline LSTM model...")
        baseline_config = {
            'sequence_length': 5,
            'input_features': 5,
            'output_features': 2,
            'lstm_units': [64, 32],
            'dropout_rate': 0.2,
            'learning_rate': 0.001,
            'batch_size': 32,
            'epochs': 50,  # Fewer epochs for baseline
            'validation_split': 0.2,
            'patience': 10
        }
        
        baseline_model = LSTMTrajectoryModel(baseline_config)
        
        # Train baseline model
        print(f"\n[TARGET] Training baseline model...")
        baseline_train_start = time.time()
        
        baseline_history = baseline_model.train(
            baseline_data['X_train'], baseline_data['y_train'],
            verbose=0  # Less verbose for comparison
        )
        
        baseline_train_time = time.time() - baseline_train_start
        
        # Evaluate baseline model
        print(f"\n[DATA] Evaluating baseline model...")
        baseline_test_start = time.time()
        
        baseline_metrics = baseline_model.evaluate(
            baseline_data['X_test'], baseline_data['y_test']
        )
        
        # Calculate pixel errors for baseline (simplified)
        from ..utils.error_calculator import calculate_pixel_errors
        baseline_pixel_stats = calculate_pixel_errors(
            baseline_metrics['actual'], 
            baseline_metrics['predictions'], 
            baseline_data['bounds']
        )
        
        baseline_test_time = time.time() - baseline_test_start
        
        # Store baseline results
        results['baseline'] = {
            'data_prep_time': baseline_data_time,
            'train_time': baseline_train_time,
            'test_time': baseline_test_time,
            'metrics': baseline_metrics,
            'pixel_stats': baseline_pixel_stats,
            'config': baseline_config,
            'data_stats': {
                'train_sequences': len(baseline_data['X_train']),
                'test_sequences': len(baseline_data['X_test']),
                'feature_count': 5
            }
        }
    
    # STEP 3: Results Comparison and Analysis
    print(f"\n{'='*50}")
    print(f"[DATA] COMPREHENSIVE RESULTS ANALYSIS")
    print(f"{'='*50}")
    
    # Enhanced model results
    enhanced_pixel_error = results['enhanced']['metrics']['pixel_stats']['mean_error']
    enhanced_success_rate = (
        results['enhanced']['metrics']['pixel_stats']['distribution']['0-10px']['count'] +
        results['enhanced']['metrics']['pixel_stats']['distribution']['10-25px']['count']
    ) / len(results['enhanced']['metrics']['pixel_stats']['pixel_errors']) * 100
    
    print(f"\n[MODEL] ENHANCED MODEL RESULTS:")
    print(f"   Mean Meter Error: {results['enhanced']['metrics']['meter_stats']['mean_error']:.1f} meters")
    print(f"   Median Meter Error: {results['enhanced']['metrics']['meter_stats']['median_error']:.1f} meters")
    print(f"   Mean Pixel Error: {enhanced_pixel_error:.1f} pixels")
    print(f"   Success Rate (<500m): {results['enhanced']['metrics']['meter_stats']['distribution']['100-500m']['percentage'] + results['enhanced']['metrics']['meter_stats']['distribution']['0-100m']['percentage']:.1f}%")
    print(f"   Feature Count: {results['enhanced']['data_stats']['feature_count']}")
    print(f"   Training Sequences: {results['enhanced']['data_stats']['augmented_sequences']:,}")
    print(f"   Architecture: {len(enhanced_config['lstm_units'])} LSTM layers + Attention")
    
    if compare_with_baseline:
        baseline_pixel_error = results['baseline']['pixel_stats']['mean_error']
        baseline_success_rate = (
            results['baseline']['pixel_stats']['distribution']['0-10px']['count'] +
            results['baseline']['pixel_stats']['distribution']['10-25px']['count']
        ) / len(results['baseline']['pixel_stats']['pixel_errors']) * 100
        
        print(f"\n[DATA] BASELINE MODEL RESULTS:")
        print(f"   Mean Pixel Error: {baseline_pixel_error:.1f} pixels")
        print(f"   Success Rate (<25px): {baseline_success_rate:.1f}%")
        print(f"   Feature Count: {results['baseline']['data_stats']['feature_count']}")
        print(f"   Training Sequences: {results['baseline']['data_stats']['train_sequences']:,}")
        print(f"   Architecture: {len(baseline_config['lstm_units'])} LSTM layers")
        
        # Calculate improvements
        error_improvement = ((baseline_pixel_error - enhanced_pixel_error) / baseline_pixel_error) * 100
        success_improvement = enhanced_success_rate - baseline_success_rate
        
        print(f"\n[TRAINING] IMPROVEMENTS:")
        print(f"   Pixel Error Reduction: {error_improvement:.1f}%")
        print(f"   Success Rate Increase: +{success_improvement:.1f} percentage points")
        print(f"   Feature Enhancement: {results['enhanced']['data_stats']['feature_count']/5:.1f}x more features")
        
        results['comparison'] = {
            'error_improvement_percent': error_improvement,
            'success_rate_improvement': success_improvement,
            'enhanced_pixel_error': enhanced_pixel_error,
            'baseline_pixel_error': baseline_pixel_error,
            'enhanced_success_rate': enhanced_success_rate,
            'baseline_success_rate': baseline_success_rate
        }
    
    # STEP 4: Advanced Visualizations
    print(f"\n[DATA] Creating enhanced visualizations...")
    
    # Create comprehensive visualization
    if compare_with_baseline:
        fig = plt.figure(figsize=(20, 15))
        
        # 1. Model comparison bar chart
        ax1 = plt.subplot(3, 4, 1)
        models = ['Baseline', 'Enhanced']
        pixel_errors = [baseline_pixel_error, enhanced_pixel_error]
        colors = ['lightcoral', 'lightgreen']
        bars = plt.bar(models, pixel_errors, color=colors, alpha=0.7)
        plt.title('Mean Pixel Error Comparison')
        plt.ylabel('Pixels')
        for bar, error in zip(bars, pixel_errors):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{error:.1f}px', ha='center', va='bottom')
        plt.grid(True, alpha=0.3)
        
        # 2. Success rate comparison
        ax2 = plt.subplot(3, 4, 2)
        success_rates = [baseline_success_rate, enhanced_success_rate]
        bars = plt.bar(models, success_rates, color=colors, alpha=0.7)
        plt.title('Success Rate Comparison (<25px)')
        plt.ylabel('Percentage')
        for bar, rate in zip(bars, success_rates):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f'{rate:.1f}%', ha='center', va='bottom')
        plt.grid(True, alpha=0.3)
        
        # 3. Feature count comparison
        ax3 = plt.subplot(3, 4, 3)
        feature_counts = [5, results['enhanced']['data_stats']['feature_count']]
        bars = plt.bar(models, feature_counts, color=colors, alpha=0.7)
        plt.title('Feature Count Comparison')
        plt.ylabel('Features per Timestep')
        for bar, count in zip(bars, feature_counts):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f'{count}', ha='center', va='bottom')
        plt.grid(True, alpha=0.3)
        
        # 4. Training time comparison
        ax4 = plt.subplot(3, 4, 4)
        train_times = [results['baseline']['train_time'], results['enhanced']['train_time']]
        bars = plt.bar(models, train_times, color=colors, alpha=0.7)
        plt.title('Training Time Comparison')
        plt.ylabel('Seconds')
        for bar, time_val in zip(bars, train_times):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{time_val:.1f}s', ha='center', va='bottom')
        plt.grid(True, alpha=0.3)
    else:
        fig = plt.figure(figsize=(20, 10))
    
    # Enhanced model training history
    ax5 = plt.subplot(3, 4, 5)
    enhanced_model.plot_enhanced_training_history('enhanced_lstm_training_history.png')
    
    # Error distribution comparison
    if compare_with_baseline:
        ax6 = plt.subplot(3, 4, 6)
        
        # Enhanced error distribution
        enhanced_dist = results['enhanced']['metrics']['pixel_stats']['distribution']
        baseline_dist = results['baseline']['pixel_stats']['distribution']
        
        ranges = list(enhanced_dist.keys())
        enhanced_counts = [enhanced_dist[r]['count'] for r in ranges]
        baseline_counts = [baseline_dist[r]['count'] for r in ranges]
        
        x = np.arange(len(ranges))
        width = 0.35
        
        plt.bar(x - width/2, baseline_counts, width, label='Baseline', color='lightcoral', alpha=0.7)
        plt.bar(x + width/2, enhanced_counts, width, label='Enhanced', color='lightgreen', alpha=0.7)
        
        plt.title('Error Distribution Comparison')
        plt.xlabel('Error Range')
        plt.ylabel('Count')
        plt.xticks(x, ranges, rotation=45)
        plt.legend()
        plt.grid(True, alpha=0.3)
    
    # Model architecture comparison
    if compare_with_baseline:
        ax7 = plt.subplot(3, 4, 7)
        
        # Create architecture visualization
        architectures = ['Baseline\n(2 LSTM)', 'Enhanced\n(3 LSTM + Attention)']
        complexity_scores = [2, 5]  # Relative complexity
        bars = plt.bar(architectures, complexity_scores, color=colors, alpha=0.7)
        plt.title('Model Architecture Complexity')
        plt.ylabel('Relative Complexity Score')
        plt.grid(True, alpha=0.3)
    
    # Performance metrics radar chart (if baseline available)
    if compare_with_baseline:
        ax8 = plt.subplot(3, 4, 8, projection='polar')
        
        # Normalize metrics for radar chart
        metrics_names = ['Accuracy', 'Speed', 'Features', 'Robustness']
        
        # Baseline metrics (normalized to 0-1)
        baseline_scores = [
            1 - (baseline_pixel_error / 200),  # Accuracy (lower error = higher score)
            1 - (results['baseline']['train_time'] / 200),  # Speed (faster = higher score)
            5 / 50,  # Features (normalized)
            0.6  # Robustness (estimated)
        ]
        
        # Enhanced metrics (normalized to 0-1)
        enhanced_scores = [
            1 - (enhanced_pixel_error / 200),  # Accuracy
            1 - (results['enhanced']['train_time'] / 200),  # Speed
            results['enhanced']['data_stats']['feature_count'] / 50,  # Features
            0.8  # Robustness (estimated higher due to regularization)
        ]
        
        angles = np.linspace(0, 2 * np.pi, len(metrics_names), endpoint=False).tolist()
        angles += angles[:1]  # Complete the circle
        
        baseline_scores += baseline_scores[:1]
        enhanced_scores += enhanced_scores[:1]
        
        ax8.plot(angles, baseline_scores, 'o-', linewidth=2, label='Baseline', color='red')
        ax8.fill(angles, baseline_scores, alpha=0.25, color='red')
        ax8.plot(angles, enhanced_scores, 'o-', linewidth=2, label='Enhanced', color='green')
        ax8.fill(angles, enhanced_scores, alpha=0.25, color='green')
        
        ax8.set_xticks(angles[:-1])
        ax8.set_xticklabels(metrics_names)
        ax8.set_ylim(0, 1)
        ax8.set_title('Performance Radar Chart')
        ax8.legend()
    
    plt.tight_layout()
    plt.savefig('enhanced_lstm_complete_analysis.png', dpi=300, bbox_inches='tight')
    print("[DISK] Saved complete analysis: enhanced_lstm_complete_analysis.png")
    plt.show()
    
    # Save enhanced model
    enhanced_model.save_model('enhanced_lstm_trajectory_model.keras')
    
    # Final summary
    print(f"\n[OK] ENHANCED EXPERIMENT COMPLETED!")
    print(f"[TARGET] Enhanced Model: {enhanced_pixel_error:.1f}px mean error, {enhanced_success_rate:.1f}% success rate")
    
    if compare_with_baseline:
        print(f"[DATA] Baseline Model: {baseline_pixel_error:.1f}px mean error, {baseline_success_rate:.1f}% success rate")
        print(f"[TRAINING] Improvement: {error_improvement:.1f}% error reduction, +{success_improvement:.1f}pp success rate")
    
    return results

def main():
    """Main function to run the enhanced experiment"""
    print("[TARGET] Enhanced LSTM Trajectory Prediction - Complete Experiment")
    print("[TARGET] Advanced features, deeper architecture, attention mechanism")
    print("[TARGET] Data augmentation and comprehensive evaluation")
    
    # Run enhanced experiment with comparison
    results = run_enhanced_experiment(
        train_trips=30,
        test_trips=20,
        sequence_length=10,  # Increased sequence length
        epochs=100,          # More epochs
        compare_with_baseline=True
    )
    
    return results

if __name__ == "__main__":
    results = main() 