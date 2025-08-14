#!/usr/bin/env python3
"""
Training script for Transformer trajectory prediction models
Tests different Transformer configurations
"""

import numpy as np
import os
import sys
import matplotlib.pyplot as plt
from datetime import datetime

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from transformer_model import TransformerTrajectoryModel
from data.enhanced_data_loader import EnhancedDACTDataLoader

def train_transformer_model(config, model_name):
    """Train a single transformer model"""
    print(f"\n[TRAIN] Training {model_name}")
    print("=" * 60)
    
    # Create model
    model = TransformerTrajectoryModel(config)
    
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
    """Main training function for all transformer models"""
    print("[TRAINING] Starting Transformer Trajectory Model Training")
    print("=" * 60)
    
    # Base configuration
    base_config = {
        'sequence_length': 10,
        'input_features': 33,
        'output_features': 2,
        'dense_units': [64, 32],
        'dropout_rate': 0.1,
        'l2_regularization': 0.001,
        'learning_rate': 0.001,
        'batch_size': 32,
        'epochs': 100,
        'validation_split': 0.2,
        'patience': 15,
        'warmup_steps': 4000,
    }
    
    # Model configurations to test
    model_configs = [
        # Small Transformer
        {
            **base_config,
            'd_model': 64,
            'num_heads': 4,
            'num_blocks': 2,
            'dff': 256
        },
        # Medium Transformer
        {
            **base_config,
            'd_model': 128,
            'num_heads': 8,
            'num_blocks': 4,
            'dff': 512
        },
        # Large Transformer
        {
            **base_config,
            'd_model': 256,
            'num_heads': 16,
            'num_blocks': 6,
            'dff': 1024
        },
        # Wide Transformer (more heads, fewer blocks)
        {
            **base_config,
            'd_model': 128,
            'num_heads': 16,
            'num_blocks': 2,
            'dff': 512
        },
        # Deep Transformer (fewer heads, more blocks)
        {
            **base_config,
            'd_model': 128,
            'num_heads': 4,
            'num_blocks': 8,
            'dff': 512
        }
    ]
    
    # Model names
    model_names = [
        "Small Transformer (d64-h4-b2)",
        "Medium Transformer (d128-h8-b4)",
        "Large Transformer (d256-h16-b6)",
        "Wide Transformer (d128-h16-b2)",
        "Deep Transformer (d128-h4-b8)"
    ]
    
    all_results = []
    
    try:
        # Train each model
        for config, model_name in zip(model_configs, model_names):
            result = train_transformer_model(config, model_name)
            all_results.append(result)
        
        # Compare results
        print("\n" + "=" * 90)
        print("[TF] TRANSFORMER MODELS COMPARISON")
        print("=" * 90)
        
        print(f"{'Model':<30} {'Parameters':<12} {'Train Loss':<12} {'Val Loss':<12} {'Mean Error (m)':<15} {'Pixel Acc':<12} {'Time':<10}")
        print("-" * 105)
        
        for result in all_results:
            tr = result['training_results']
            ev = result['evaluation_results']
            time_str = str(result['training_time']).split('.')[0]  # Remove microseconds
            print(f"{result['model_name']:<30} "
                  f"{tr['total_params']:<12,} "
                  f"{tr['final_loss']:<12.6f} "
                  f"{tr['final_val_loss']:<12.6f} "
                  f"{ev['mean_error_meters']:<15.1f} "
                  f"{tr['final_pixel_accuracy']:<12.4f} "
                  f"{time_str:<10}")
        
        # Find best model
        best_model = min(all_results, key=lambda x: x['evaluation_results']['mean_error_meters'])
        print(f"\n🏆 Best Model: {best_model['model_name']}")
        print(f"   Mean Error: {best_model['evaluation_results']['mean_error_meters']:.1f} meters")
        print(f"   Parameters: {best_model['training_results']['total_params']:,}")
        print(f"   Training Time: {best_model['training_time']}")
        
        # Create comparison plot
        create_comparison_plot(all_results)
        
        # Performance vs Parameters analysis
        create_performance_analysis(all_results)
        
        # Save comprehensive results
        results_path = os.path.join(os.path.dirname(__file__), 'transformer_models_comparison.txt')
        with open(results_path, 'w') as f:
            f.write("Transformer Models - Comprehensive Comparison\n")
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
        print("[SUCCESS] All transformer model training completed successfully!")
        
    except Exception as e:
        print(f"[ERROR] Error during training: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

def create_comparison_plot(all_results):
    """Create comparison plot for all transformer models"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    model_names = [r['model_name'] for r in all_results]
    short_names = [name.split('(')[0].strip() for name in model_names]
    
    # Mean Error comparison
    mean_errors = [r['evaluation_results']['mean_error_meters'] for r in all_results]
    bars1 = ax1.bar(range(len(short_names)), mean_errors, color='skyblue', alpha=0.7)
    ax1.set_title('Mean Error Comparison (meters)')
    ax1.set_xlabel('Models')
    ax1.set_ylabel('Mean Error (meters)')
    ax1.set_xticks(range(len(short_names)))
    ax1.set_xticklabels(short_names, rotation=45, ha='right')
    
    # Add values on bars
    for i, v in enumerate(mean_errors):
        ax1.text(i, v + max(mean_errors)*0.01, f'{v:.1f}', ha='center', va='bottom')
    
    # Parameter count comparison
    param_counts = [r['training_results']['total_params'] for r in all_results]
    bars2 = ax2.bar(range(len(short_names)), param_counts, color='lightcoral', alpha=0.7)
    ax2.set_title('Parameter Count Comparison')
    ax2.set_xlabel('Models')
    ax2.set_ylabel('Parameters')
    ax2.set_xticks(range(len(short_names)))
    ax2.set_xticklabels(short_names, rotation=45, ha='right')
    
    # Add values on bars
    for i, v in enumerate(param_counts):
        if v >= 1000000:
            label = f'{v/1000000:.1f}M'
        else:
            label = f'{v/1000:.0f}K'
        ax2.text(i, v + max(param_counts)*0.01, label, ha='center', va='bottom')
    
    # Training time comparison
    training_times = [r['training_time'].total_seconds() / 60 for r in all_results]  # Convert to minutes
    bars3 = ax3.bar(range(len(short_names)), training_times, color='lightgreen', alpha=0.7)
    ax3.set_title('Training Time Comparison')
    ax3.set_xlabel('Models')
    ax3.set_ylabel('Training Time (minutes)')
    ax3.set_xticks(range(len(short_names)))
    ax3.set_xticklabels(short_names, rotation=45, ha='right')
    
    # Add values on bars
    for i, v in enumerate(training_times):
        ax3.text(i, v + max(training_times)*0.01, f'{v:.1f}', ha='center', va='bottom')
    
    # Training vs Validation Loss
    train_losses = [r['training_results']['final_loss'] for r in all_results]
    val_losses = [r['training_results']['final_val_loss'] for r in all_results]
    
    x = np.arange(len(short_names))
    width = 0.35
    
    ax4.bar(x - width/2, train_losses, width, label='Training Loss', color='orange', alpha=0.7)
    ax4.bar(x + width/2, val_losses, width, label='Validation Loss', color='purple', alpha=0.7)
    ax4.set_title('Loss Comparison')
    ax4.set_xlabel('Models')
    ax4.set_ylabel('Loss')
    ax4.set_xticks(x)
    ax4.set_xticklabels(short_names, rotation=45, ha='right')
    ax4.legend()
    
    plt.tight_layout()
    
    # Save plot
    plot_path = os.path.join(os.path.dirname(__file__), 'transformer_models_comparison.png')
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"[PLOT] Comparison plot saved to: {plot_path}")
    
    plt.show()

def create_performance_analysis(all_results):
    """Create performance vs parameters analysis"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    param_counts = [r['training_results']['total_params'] for r in all_results]
    mean_errors = [r['evaluation_results']['mean_error_meters'] for r in all_results]
    training_times = [r['training_time'].total_seconds() / 60 for r in all_results]
    model_names = [r['model_name'].split('(')[0].strip() for r in all_results]
    
    # Performance vs Parameters
    scatter1 = ax1.scatter(param_counts, mean_errors, s=100, alpha=0.7, c='blue')
    ax1.set_xlabel('Number of Parameters')
    ax1.set_ylabel('Mean Error (meters)')
    ax1.set_title('Performance vs Model Size')
    ax1.grid(True, alpha=0.3)
    
    # Add labels
    for i, name in enumerate(model_names):
        ax1.annotate(name, (param_counts[i], mean_errors[i]), 
                    xytext=(5, 5), textcoords='offset points', fontsize=9)
    
    # Training Time vs Parameters
    scatter2 = ax2.scatter(param_counts, training_times, s=100, alpha=0.7, c='red')
    ax2.set_xlabel('Number of Parameters')
    ax2.set_ylabel('Training Time (minutes)')
    ax2.set_title('Training Time vs Model Size')
    ax2.grid(True, alpha=0.3)
    
    # Add labels
    for i, name in enumerate(model_names):
        ax2.annotate(name, (param_counts[i], training_times[i]), 
                    xytext=(5, 5), textcoords='offset points', fontsize=9)
    
    plt.tight_layout()
    
    # Save plot
    analysis_path = os.path.join(os.path.dirname(__file__), 'transformer_performance_analysis.png')
    plt.savefig(analysis_path, dpi=300, bbox_inches='tight')
    print(f"[ANALYSIS] Performance analysis saved to: {analysis_path}")
    
    plt.show()

if __name__ == "__main__":
    exit(main())
