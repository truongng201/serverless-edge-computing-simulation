#!/usr/bin/env python3
"""
Training script for Bidirectional RNN trajectory prediction models
Tests both Bidirectional LSTM and Bidirectional GRU
"""

import numpy as np
import os
import sys
import matplotlib.pyplot as plt
from datetime import datetime

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from bidirectional_model import BidirectionalRNNTrajectoryModel
from data.enhanced_data_loader import EnhancedDACTDataLoader

def train_bidirectional_model(config, model_name):
    """Train a single bidirectional model"""
    print(f"\n[TRAIN] Training {model_name}")
    print("=" * 60)
    
    # Create model
    model = BidirectionalRNNTrajectoryModel(config)
    
    # Load data (shared across models)
    print("[DATA] Loading DACT dataset...")
    data_loader = EnhancedDACTDataLoader(
        csv_path=os.path.join(os.path.dirname(__file__), '..', '..', 'DACT Easy-Dataset.csv'),
        sequence_length=config['sequence_length']
    )
    
    # Load and prepare data
    data_dict = data_loader.prepare_for_training(train_count=30, test_count=20)
    
    # Extract data from dictionary
    X_train = data_dict['X_train']
    y_train = data_dict['y_train']
    X_test = data_dict['X_test']
    y_test = data_dict['y_test']
    
    # Create validation split from training data
    val_split = int(0.2 * len(X_train))
    X_val = X_train[-val_split:]
    y_val = y_train[-val_split:]
    X_train = X_train[:-val_split]
    y_train = y_train[:-val_split]
    
    print(f"[SUCCESS] Data loaded successfully!")
    print(f"   Training: {X_train.shape[0]} sequences")
    print(f"   Validation: {X_val.shape[0]} sequences") 
    print(f"   Test: {X_test.shape[0]} sequences")
    
    # Train model
    start_time = datetime.now()
    training_results = model.train(X_train, y_train, X_val, y_val)
    training_time = datetime.now() - start_time
    
    # Evaluate model
    print(f"\n[EVAL] Evaluating {model_name}...")
    bounds = data_dict['bounds']
    evaluation_results = model.evaluate(X_test, y_test, bounds)
    
    # Save model
    model_filename = f"{model_name.lower().replace(' ', '_').replace('(', '').replace(')', '')}_model.keras"
    model_path = os.path.join(os.path.dirname(__file__), model_filename)
    model.save_model(model_path)
    
    # Plot training history
    plot_filename = f"{model_name.lower().replace(' ', '_').replace('(', '').replace(')', '')}_training_history.png"
    history_plot_path = os.path.join(os.path.dirname(__file__), plot_filename)
    model.plot_training_history(history_plot_path)
    
    return {
        'model_name': model_name,
        'training_results': training_results,
        'evaluation_results': evaluation_results,
        'training_time': training_time,
        'config': config
    }

def main():
    """Main training function for all bidirectional models"""
    print("[TRAINING] Starting Bidirectional RNN Trajectory Model Training")
    print("=" * 60)
    
    # Base configuration
    base_config = {
        'sequence_length': 10,
        'input_features': 33,
        'output_features': 2,
        'rnn_units': [64, 32],
        'dense_units': [64, 32],
        'dropout_rate': 0.3,
        'recurrent_dropout': 0.2,
        'l2_regularization': 0.001,
        'learning_rate': 0.001,
        'batch_size': 32,
        'epochs': 100,
        'validation_split': 0.2,
        'patience': 15,
    }
    
    # Model configurations to test
    model_configs = [
        # Bidirectional LSTM variants
        {
            **base_config,
            'rnn_type': 'LSTM',
            'merge_mode': 'concat'
        },
        {
            **base_config,
            'rnn_type': 'LSTM',
            'merge_mode': 'sum'
        },
        {
            **base_config,
            'rnn_type': 'LSTM',
            'merge_mode': 'ave'
        },
        # Bidirectional GRU variants
        {
            **base_config,
            'rnn_type': 'GRU',
            'merge_mode': 'concat'
        },
        {
            **base_config,
            'rnn_type': 'GRU',
            'merge_mode': 'sum'
        }
    ]
    
    # Model names
    model_names = [
        "Bidirectional LSTM (Concat)",
        "Bidirectional LSTM (Sum)", 
        "Bidirectional LSTM (Average)",
        "Bidirectional GRU (Concat)",
        "Bidirectional GRU (Sum)"
    ]
    
    all_results = []
    
    try:
        # Train each model
        for config, model_name in zip(model_configs, model_names):
            result = train_bidirectional_model(config, model_name)
            all_results.append(result)
        
        # Compare results
        print("\n" + "=" * 80)
        print("[COMPARE] BIDIRECTIONAL MODELS COMPARISON")
        print("=" * 80)
        
        print(f"{'Model':<30} {'Parameters':<12} {'Train Loss':<12} {'Val Loss':<12} {'Mean Error (m)':<15} {'Pixel Acc':<12}")
        print("-" * 95)
        
        for result in all_results:
            tr = result['training_results']
            ev = result['evaluation_results']
            print(f"{result['model_name']:<30} "
                  f"{tr['total_params']:<12,} "
                  f"{tr['final_loss']:<12.6f} "
                  f"{tr['final_val_loss']:<12.6f} "
                  f"{ev['mean_error_meters']:<15.1f} "
                  f"{tr['final_pixel_accuracy']:<12.4f}")
        
        # Find best model
        best_model = min(all_results, key=lambda x: x['evaluation_results']['mean_error_meters'])
        print(f"\n🏆 Best Model: {best_model['model_name']}")
        print(f"   Mean Error: {best_model['evaluation_results']['mean_error_meters']:.1f} meters")
        print(f"   Parameters: {best_model['training_results']['total_params']:,}")
        
        # Save comprehensive results
        results_path = os.path.join(os.path.dirname(__file__), 'bidirectional_models_comparison.txt')
        with open(results_path, 'w') as f:
            f.write("Bidirectional RNN Models - Comprehensive Comparison\n")
            f.write("=" * 60 + "\n\n")
            
            for result in all_results:
                f.write(f"Model: {result['model_name']}\n")
                f.write("-" * 40 + "\n")
                f.write(f"Configuration:\n")
                for key, value in result['config'].items():
                    f.write(f"  {key}: {value}\n")
                f.write(f"\nTraining Results:\n")
                for key, value in result['training_results'].items():
                    f.write(f"  {key}: {value}\n")
                f.write(f"\nEvaluation Results:\n")
                for key, value in result['evaluation_results'].items():
                    f.write(f"  {key}: {value}\n")
                f.write(f"\nTraining Time: {result['training_time']}\n")
                f.write("\n" + "=" * 60 + "\n\n")
            
            f.write(f"Best Model: {best_model['model_name']}\n")
            f.write(f"Best Mean Error: {best_model['evaluation_results']['mean_error_meters']:.1f} meters\n")
        
        print(f"\n[DISK] Comprehensive results saved to: {results_path}")
        print("[SUCCESS] All bidirectional model training completed successfully!")
        
    except Exception as e:
        print(f"[ERROR] Error during training: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
