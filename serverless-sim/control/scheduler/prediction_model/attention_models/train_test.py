#!/usr/bin/env python3
"""
Training script for Attention-based trajectory prediction models
Tests various attention mechanisms with LSTM and GRU
"""

import numpy as np
import os
import sys
import matplotlib.pyplot as plt
from datetime import datetime

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from attention_model import AttentionTrajectoryModel
from data.enhanced_data_loader import EnhancedDACTDataLoader

def train_attention_model(config, model_name):
    """Train a single attention model"""
    print(f"\n[TRAIN] Training {model_name}")
    print("=" * 60)
    
    # Create model
    model = AttentionTrajectoryModel(config)
    
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
    """Main training function for all attention models"""
    print("[TRAINING] Starting Attention-based Trajectory Model Training")
    print("=" * 60)
    
    # Base configuration
    base_config = {
        'sequence_length': 10,
        'input_features': 33,
        'output_features': 2,
        'rnn_units': [128, 64],
        'attention_units': 64,
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
        # LSTM with Basic Attention
        {
            **base_config,
            'rnn_type': 'LSTM',
            'attention_type': 'basic',
            'attention_units': 64
        },
        # LSTM with Self-Attention
        {
            **base_config,
            'rnn_type': 'LSTM',
            'attention_type': 'self',
            'num_heads': 8
        },
        # LSTM with Self-Attention (different heads)
        {
            **base_config,
            'rnn_type': 'LSTM',
            'attention_type': 'self',
            'num_heads': 4
        },
        # GRU with Basic Attention
        {
            **base_config,
            'rnn_type': 'GRU',
            'attention_type': 'basic',
            'attention_units': 64
        },
        # GRU with Self-Attention
        {
            **base_config,
            'rnn_type': 'GRU',
            'attention_type': 'self',
            'num_heads': 8
        }
    ]
    
    # Model names
    model_names = [
        "LSTM with Basic Attention",
        "LSTM with Self-Attention (8 heads)",
        "LSTM with Self-Attention (4 heads)",
        "GRU with Basic Attention",
        "GRU with Self-Attention (8 heads)"
    ]
    
    all_results = []
    
    try:
        # Train each model
        for config, model_name in zip(model_configs, model_names):
            result = train_attention_model(config, model_name)
            all_results.append(result)
        
        # Compare results
        print("\n" + "=" * 80)
        print("[TARGET] ATTENTION MODELS COMPARISON")
        print("=" * 80)
        
        print(f"{'Model':<35} {'Parameters':<12} {'Train Loss':<12} {'Val Loss':<12} {'Mean Error (m)':<15} {'Pixel Acc':<12}")
        print("-" * 100)
        
        for result in all_results:
            tr = result['training_results']
            ev = result['evaluation_results']
            print(f"{result['model_name']:<35} "
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
        
        # Create comparison plot
        create_comparison_plot(all_results)
        
        # Save comprehensive results
        results_path = os.path.join(os.path.dirname(__file__), 'attention_models_comparison.txt')
        with open(results_path, 'w') as f:
            f.write("Attention-based Models - Comprehensive Comparison\n")
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
        print("[SUCCESS] All attention model training completed successfully!")
        
    except Exception as e:
        print(f"[ERROR] Error during training: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

def create_comparison_plot(all_results):
    """Create comparison plot for all attention models"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    model_names = [r['model_name'] for r in all_results]
    
    # Mean Error comparison
    mean_errors = [r['evaluation_results']['mean_error_meters'] for r in all_results]
    ax1.bar(range(len(model_names)), mean_errors, color='skyblue', alpha=0.7)
    ax1.set_title('Mean Error Comparison (meters)')
    ax1.set_xlabel('Models')
    ax1.set_ylabel('Mean Error (meters)')
    ax1.set_xticks(range(len(model_names)))
    ax1.set_xticklabels([name.replace(' ', '\n') for name in model_names], rotation=45, ha='right')
    
    # Add values on bars
    for i, v in enumerate(mean_errors):
        ax1.text(i, v + max(mean_errors)*0.01, f'{v:.1f}', ha='center', va='bottom')
    
    # Parameter count comparison
    param_counts = [r['training_results']['total_params'] for r in all_results]
    ax2.bar(range(len(model_names)), param_counts, color='lightcoral', alpha=0.7)
    ax2.set_title('Parameter Count Comparison')
    ax2.set_xlabel('Models')
    ax2.set_ylabel('Parameters')
    ax2.set_xticks(range(len(model_names)))
    ax2.set_xticklabels([name.replace(' ', '\n') for name in model_names], rotation=45, ha='right')
    
    # Add values on bars
    for i, v in enumerate(param_counts):
        ax2.text(i, v + max(param_counts)*0.01, f'{v/1000:.0f}K', ha='center', va='bottom')
    
    # Pixel Accuracy comparison
    pixel_accs = [r['training_results']['final_pixel_accuracy'] for r in all_results]
    ax3.bar(range(len(model_names)), pixel_accs, color='lightgreen', alpha=0.7)
    ax3.set_title('Pixel Accuracy Comparison (50px threshold)')
    ax3.set_xlabel('Models')
    ax3.set_ylabel('Pixel Accuracy')
    ax3.set_xticks(range(len(model_names)))
    ax3.set_xticklabels([name.replace(' ', '\n') for name in model_names], rotation=45, ha='right')
    
    # Add values on bars
    for i, v in enumerate(pixel_accs):
        ax3.text(i, v + max(pixel_accs)*0.01, f'{v:.3f}', ha='center', va='bottom')
    
    # Training Loss comparison
    train_losses = [r['training_results']['final_loss'] for r in all_results]
    val_losses = [r['training_results']['final_val_loss'] for r in all_results]
    
    x = np.arange(len(model_names))
    width = 0.35
    
    ax4.bar(x - width/2, train_losses, width, label='Training Loss', color='orange', alpha=0.7)
    ax4.bar(x + width/2, val_losses, width, label='Validation Loss', color='purple', alpha=0.7)
    ax4.set_title('Loss Comparison')
    ax4.set_xlabel('Models')
    ax4.set_ylabel('Loss')
    ax4.set_xticks(x)
    ax4.set_xticklabels([name.replace(' ', '\n') for name in model_names], rotation=45, ha='right')
    ax4.legend()
    
    plt.tight_layout()
    
    # Save plot
    plot_path = os.path.join(os.path.dirname(__file__), 'attention_models_comparison.png')
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"[PLOT] Comparison plot saved to: {plot_path}")
    
    plt.show()

if __name__ == "__main__":
    exit(main())
