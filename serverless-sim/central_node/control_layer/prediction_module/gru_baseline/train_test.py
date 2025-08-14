#!/usr/bin/env python3
"""
Training script for GRU trajectory prediction model
"""

import numpy as np
import os
import sys
import matplotlib.pyplot as plt
from datetime import datetime

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from gru_model import GRUTrajectoryModel
from data.enhanced_data_loader import EnhancedDACTDataLoader

def main():
    """Main training function"""
    print("Starting GRU Trajectory Model Training")
    print("=" * 50)
    
    # Configuration
    config = {
        'sequence_length': 10,
        'input_features': 33,
        'output_features': 2,
        'gru_units': [64, 32],
        'dense_units': [32],
        'dropout_rate': 0.2,
        'recurrent_dropout': 0.1,
        'l2_regularization': 0.0005,
        'learning_rate': 0.001,
        'batch_size': 32,
        'epochs': 80,
        'validation_split': 0.2,
        'patience': 10,
    }
    
    try:
        # Load data
        print("Loading DACT dataset...")
        data_loader = EnhancedDACTDataLoader(
            csv_path=os.path.join(os.path.dirname(__file__), '..', '..', 'DACT Easy-Dataset.csv')
        )
        
        # Load and prepare data
        data_dict = data_loader.prepare_for_training(train_count=30, test_count=20)
        X_train = data_dict['X_train']
        y_train = data_dict['y_train']
        X_test = data_dict['X_test']
        y_test = data_dict['y_test']
        
        # Create validation split from training data
        from sklearn.model_selection import train_test_split
        X_train, X_val, y_train, y_val = train_test_split(
            X_train, y_train, test_size=0.2, random_state=42
        )
        
        print(f"[OK] Data loaded successfully!")
        print(f"   Training: {X_train.shape[0]} sequences")
        print(f"   Validation: {X_val.shape[0]} sequences") 
        print(f"   Test: {X_test.shape[0]} sequences")
        print(f"   Features: {X_train.shape[2]} features")
        
        # Create model
        print("\n[ARCH] Creating GRU model...")
        model = GRUTrajectoryModel(config)
        
        # Train model
        print("\n[TARGET] Training model...")
        start_time = datetime.now()
        
        training_results = model.train(
            X_train, y_train,
            X_val, y_val
        )
        
        training_time = datetime.now() - start_time
        print(f"[TIME] Training completed in: {training_time}")
        
        # Evaluate model
        print("\n[DATA] Evaluating model...")
        bounds = data_dict['bounds']
        
        evaluation_results = model.evaluate(X_test, y_test, bounds)
        
        # Save model
        model_path = os.path.join(os.path.dirname(__file__), 'gru_trajectory_model.keras')
        model.save_model(model_path)
        
        # Plot training history
        history_plot_path = os.path.join(os.path.dirname(__file__), 'gru_training_history.png')
        model.plot_training_history(history_plot_path)
        
        # Print summary
        print("\n" + "=" * 50)
        print("[CHART] TRAINING SUMMARY")
        print("=" * 50)
        
        print(f"[ARCH] Model Architecture: GRU")
        print(f"[DATA] Training samples: {X_train.shape[0]:,}")
        print(f"[MODEL] Total parameters: {training_results['total_params']:,}")
        print(f"[TIME] Training time: {training_time}")
        print(f"[GRAPH] Final training loss: {training_results['final_loss']:.6f}")
        print(f"[DATA] Final validation loss: {training_results['final_val_loss']:.6f}")
        print(f"[TARGET] Coordinate accuracy: {training_results['final_accuracy']:.6f}")
        print(f"[PIXEL] Pixel accuracy (50px): {training_results['final_pixel_accuracy']:.4f}")
        
        print(f"\n[BOUNDS] TEST RESULTS")
        print(f"[TARGET] Mean error: {evaluation_results['mean_error_meters']:.1f} meters")
        print(f"[DATA] Median error: {evaluation_results['median_error_meters']:.1f} meters")
        print(f"[STD] Std error: {evaluation_results['std_error_meters']:.1f} meters")
        print(f"[PIXELS] Mean error (pixels): {evaluation_results['mean_error_pixels']:.1f} px")
        
        # Save results
        results_path = os.path.join(os.path.dirname(__file__), 'gru_experiment_results.txt')
        with open(results_path, 'w') as f:
            f.write("GRU Trajectory Model - Experiment Results\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Configuration:\n")
            for key, value in config.items():
                f.write(f"  {key}: {value}\n")
            f.write(f"\nTraining Results:\n")
            for key, value in training_results.items():
                f.write(f"  {key}: {value}\n")
            f.write(f"\nEvaluation Results:\n")
            for key, value in evaluation_results.items():
                f.write(f"  {key}: {value}\n")
            f.write(f"\nTraining Time: {training_time}\n")
        
        print(f"\n[DISK] Results saved to: {results_path}")
        print("[OK] Training completed successfully!")
        
    except Exception as e:
        print(f"[ERROR] Error during training: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
