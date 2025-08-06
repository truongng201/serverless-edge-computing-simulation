#!/usr/bin/env python3
"""
Model Comparison Script
Comprehensive analysis between baseline and enhanced LSTM models
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple
import json
from pathlib import Path

class ModelComparator:
    """Comprehensive model comparison and analysis"""
    
    def __init__(self):
        self.results = {}
        self.comparison_data = {}
        
    def add_model_results(self, model_name: str, results: Dict):
        """Add model results for comparison"""
        self.results[model_name] = results
        print(f"[OK] Added {model_name} results for comparison")
    
    def calculate_performance_metrics(self) -> Dict:
        """Calculate comprehensive performance metrics"""
        if len(self.results) < 2:
            print("[WARNING] Need at least 2 models for comparison")
            return {}
        
        comparison = {}
        
        for model_name, results in self.results.items():
            if model_name == 'baseline':
                pixel_stats = results['pixel_stats']
            else:  # enhanced
                pixel_stats = results['metrics']['pixel_stats']
            
            # Core metrics
            comparison[model_name] = {
                'mean_pixel_error': pixel_stats['mean_error'],
                'median_pixel_error': pixel_stats['median_error'],
                'std_pixel_error': pixel_stats['std_error'],
                'min_pixel_error': pixel_stats['min_error'],
                'max_pixel_error': pixel_stats['max_error'],
                'excellent_rate': pixel_stats['distribution']['0-10px']['percentage'],
                'good_rate': pixel_stats['distribution']['10-25px']['percentage'],
                'acceptable_rate': pixel_stats['distribution']['25-50px']['percentage'],
                'poor_rate': pixel_stats['distribution']['>100px']['percentage'],
                'success_rate_25px': pixel_stats['distribution']['0-10px']['percentage'] + 
                                   pixel_stats['distribution']['10-25px']['percentage'],
                'success_rate_50px': (pixel_stats['distribution']['0-10px']['percentage'] + 
                                    pixel_stats['distribution']['10-25px']['percentage'] + 
                                    pixel_stats['distribution']['25-50px']['percentage']),
                'train_time': results['train_time'],
                'test_time': results['test_time'],
                'feature_count': results['data_stats']['feature_count']
            }
        
        self.comparison_data = comparison
        return comparison
    
    def generate_improvement_report(self) -> Dict:
        """Generate detailed improvement report"""
        if 'baseline' not in self.comparison_data or 'enhanced' not in self.comparison_data:
            print("[WARNING] Need both baseline and enhanced results")
            return {}
        
        baseline = self.comparison_data['baseline']
        enhanced = self.comparison_data['enhanced']
        
        improvements = {}
        
        # Accuracy improvements
        improvements['pixel_error_reduction'] = {
            'absolute': baseline['mean_pixel_error'] - enhanced['mean_pixel_error'],
            'percentage': ((baseline['mean_pixel_error'] - enhanced['mean_pixel_error']) / 
                          baseline['mean_pixel_error']) * 100
        }
        
        improvements['median_error_reduction'] = {
            'absolute': baseline['median_pixel_error'] - enhanced['median_pixel_error'],
            'percentage': ((baseline['median_pixel_error'] - enhanced['median_pixel_error']) / 
                          baseline['median_pixel_error']) * 100
        }
        
        # Success rate improvements
        improvements['success_rate_25px_improvement'] = {
            'absolute': enhanced['success_rate_25px'] - baseline['success_rate_25px'],
            'percentage': ((enhanced['success_rate_25px'] - baseline['success_rate_25px']) / 
                          baseline['success_rate_25px']) * 100 if baseline['success_rate_25px'] > 0 else 0
        }
        
        improvements['success_rate_50px_improvement'] = {
            'absolute': enhanced['success_rate_50px'] - baseline['success_rate_50px'],
            'percentage': ((enhanced['success_rate_50px'] - baseline['success_rate_50px']) / 
                          baseline['success_rate_50px']) * 100 if baseline['success_rate_50px'] > 0 else 0
        }
        
        # Consistency improvements
        improvements['consistency_improvement'] = {
            'std_reduction': baseline['std_pixel_error'] - enhanced['std_pixel_error'],
            'std_reduction_percent': ((baseline['std_pixel_error'] - enhanced['std_pixel_error']) / 
                                    baseline['std_pixel_error']) * 100
        }
        
        # Quality improvements
        improvements['excellent_rate_improvement'] = {
            'absolute': enhanced['excellent_rate'] - baseline['excellent_rate'],
            'multiplier': enhanced['excellent_rate'] / baseline['excellent_rate'] if baseline['excellent_rate'] > 0 else float('inf')
        }
        
        improvements['poor_rate_reduction'] = {
            'absolute': baseline['poor_rate'] - enhanced['poor_rate'],
            'percentage': ((baseline['poor_rate'] - enhanced['poor_rate']) / 
                          baseline['poor_rate']) * 100 if baseline['poor_rate'] > 0 else 0
        }
        
        # Computational cost
        improvements['training_time_ratio'] = enhanced['train_time'] / baseline['train_time']
        improvements['feature_enhancement_ratio'] = enhanced['feature_count'] / baseline['feature_count']
        
        return improvements
    
    def create_detailed_comparison_plots(self, save_path: str = None):
        """Create comprehensive comparison visualizations"""
        if len(self.comparison_data) < 2:
            print("[WARNING] Need comparison data")
            return
        
        # Set up the plotting style
        plt.style.use('default')
        sns.set_palette("husl")
        
        fig = plt.figure(figsize=(20, 16))
        
        # 1. Overall Performance Comparison
        ax1 = plt.subplot(3, 4, 1)
        models = list(self.comparison_data.keys())
        mean_errors = [self.comparison_data[model]['mean_pixel_error'] for model in models]
        colors = ['lightcoral', 'lightgreen']
        
        bars = plt.bar(models, mean_errors, color=colors, alpha=0.8, edgecolor='black')
        plt.title('Mean Pixel Error Comparison', fontsize=14, fontweight='bold')
        plt.ylabel('Mean Error (pixels)', fontsize=12)
        
        for bar, error in zip(bars, mean_errors):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{error:.1f}px', ha='center', va='bottom', fontweight='bold')
        
        plt.grid(True, alpha=0.3)
        
        # 2. Success Rate Comparison
        ax2 = plt.subplot(3, 4, 2)
        success_rates_25 = [self.comparison_data[model]['success_rate_25px'] for model in models]
        success_rates_50 = [self.comparison_data[model]['success_rate_50px'] for model in models]
        
        x = np.arange(len(models))
        width = 0.35
        
        bars1 = plt.bar(x - width/2, success_rates_25, width, label='<25px', color='green', alpha=0.7)
        bars2 = plt.bar(x + width/2, success_rates_50, width, label='<50px', color='blue', alpha=0.7)
        
        plt.title('Success Rate Comparison', fontsize=14, fontweight='bold')
        plt.ylabel('Success Rate (%)', fontsize=12)
        plt.xticks(x, models)
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 3. Error Distribution Comparison
        ax3 = plt.subplot(3, 4, 3)
        
        if 'baseline' in self.comparison_data and 'enhanced' in self.comparison_data:
            baseline_dist = self.results['baseline']['pixel_stats']['distribution']
            enhanced_dist = self.results['enhanced']['metrics']['pixel_stats']['distribution']
            
            ranges = list(baseline_dist.keys())
            baseline_counts = [baseline_dist[r]['count'] for r in ranges]
            enhanced_counts = [enhanced_dist[r]['count'] for r in ranges]
            
            x = np.arange(len(ranges))
            width = 0.35
            
            plt.bar(x - width/2, baseline_counts, width, label='Baseline', color='lightcoral', alpha=0.7)
            plt.bar(x + width/2, enhanced_counts, width, label='Enhanced', color='lightgreen', alpha=0.7)
            
            plt.title('Error Distribution Comparison', fontsize=14, fontweight='bold')
            plt.xlabel('Error Range', fontsize=12)
            plt.ylabel('Count', fontsize=12)
            plt.xticks(x, ranges, rotation=45)
            plt.legend()
            plt.grid(True, alpha=0.3)
        
        # 4. Consistency Comparison (Standard Deviation)
        ax4 = plt.subplot(3, 4, 4)
        std_errors = [self.comparison_data[model]['std_pixel_error'] for model in models]
        
        bars = plt.bar(models, std_errors, color=colors, alpha=0.8, edgecolor='black')
        plt.title('Error Consistency Comparison', fontsize=14, fontweight='bold')
        plt.ylabel('Standard Deviation (pixels)', fontsize=12)
        
        for bar, std in zip(bars, std_errors):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{std:.1f}px', ha='center', va='bottom', fontweight='bold')
        
        plt.grid(True, alpha=0.3)
        
        # 5. Feature Count Comparison
        ax5 = plt.subplot(3, 4, 5)
        feature_counts = [self.comparison_data[model]['feature_count'] for model in models]
        
        bars = plt.bar(models, feature_counts, color=colors, alpha=0.8, edgecolor='black')
        plt.title('Feature Count Comparison', fontsize=14, fontweight='bold')
        plt.ylabel('Features per Timestep', fontsize=12)
        
        for bar, count in zip(bars, feature_counts):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f'{count}', ha='center', va='bottom', fontweight='bold')
        
        plt.grid(True, alpha=0.3)
        
        # 6. Training Time Comparison
        ax6 = plt.subplot(3, 4, 6)
        train_times = [self.comparison_data[model]['train_time'] for model in models]
        
        bars = plt.bar(models, train_times, color=colors, alpha=0.8, edgecolor='black')
        plt.title('Training Time Comparison', fontsize=14, fontweight='bold')
        plt.ylabel('Training Time (seconds)', fontsize=12)
        
        for bar, time_val in zip(bars, train_times):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                    f'{time_val:.1f}s', ha='center', va='bottom', fontweight='bold')
        
        plt.grid(True, alpha=0.3)
        
        # 7. Quality Breakdown (Stacked Bar)
        ax7 = plt.subplot(3, 4, 7)
        
        excellent_rates = [self.comparison_data[model]['excellent_rate'] for model in models]
        good_rates = [self.comparison_data[model]['good_rate'] for model in models]
        acceptable_rates = [self.comparison_data[model]['acceptable_rate'] for model in models]
        
        bottom = np.array(excellent_rates)
        middle = np.array(good_rates)
        
        p1 = plt.bar(models, excellent_rates, color='darkgreen', alpha=0.8, label='Excellent (0-10px)')
        p2 = plt.bar(models, good_rates, bottom=bottom, color='lightgreen', alpha=0.8, label='Good (10-25px)')
        p3 = plt.bar(models, acceptable_rates, bottom=bottom+middle, color='yellow', alpha=0.8, label='Acceptable (25-50px)')
        
        plt.title('Prediction Quality Breakdown', fontsize=14, fontweight='bold')
        plt.ylabel('Percentage', fontsize=12)
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 8. Min/Max Error Comparison
        ax8 = plt.subplot(3, 4, 8)
        min_errors = [self.comparison_data[model]['min_pixel_error'] for model in models]
        max_errors = [self.comparison_data[model]['max_pixel_error'] for model in models]
        
        x = np.arange(len(models))
        width = 0.35
        
        bars1 = plt.bar(x - width/2, min_errors, width, label='Min Error', color='blue', alpha=0.7)
        bars2 = plt.bar(x + width/2, max_errors, width, label='Max Error', color='red', alpha=0.7)
        
        plt.title('Error Range Comparison', fontsize=14, fontweight='bold')
        plt.ylabel('Error (pixels)', fontsize=12)
        plt.xticks(x, models)
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 9. Performance Radar Chart
        ax9 = plt.subplot(3, 4, 9, projection='polar')
        
        metrics_names = ['Accuracy', 'Consistency', 'Efficiency', 'Quality']
        
        # Normalize metrics for radar chart (0-1 scale)
        def normalize_metric(value, min_val, max_val, invert=False):
            if invert:  # For error metrics (lower is better)
                return 1 - (value - min_val) / (max_val - min_val) if max_val > min_val else 0.5
            else:  # For success metrics (higher is better)
                return (value - min_val) / (max_val - min_val) if max_val > min_val else 0.5
        
        angles = np.linspace(0, 2 * np.pi, len(metrics_names), endpoint=False).tolist()
        angles += angles[:1]
        
        for i, model in enumerate(models):
            data = self.comparison_data[model]
            
            scores = [
                normalize_metric(data['success_rate_25px'], 0, 100),  # Accuracy
                normalize_metric(data['std_pixel_error'], 0, 150, invert=True),  # Consistency (lower std = better)
                normalize_metric(data['train_time'], 0, 300, invert=True),  # Efficiency (faster = better)
                normalize_metric(data['excellent_rate'], 0, 50)  # Quality
            ]
            scores += scores[:1]
            
            color = colors[i]
            ax9.plot(angles, scores, 'o-', linewidth=2, label=model.title(), color=color)
            ax9.fill(angles, scores, alpha=0.25, color=color)
        
        ax9.set_xticks(angles[:-1])
        ax9.set_xticklabels(metrics_names)
        ax9.set_ylim(0, 1)
        ax9.set_title('Performance Radar Chart', fontsize=14, fontweight='bold')
        ax9.legend()
        
        # 10. Error Histogram Comparison
        ax10 = plt.subplot(3, 4, 10)
        
        if 'baseline' in self.results and 'enhanced' in self.results:
            baseline_errors = self.results['baseline']['pixel_stats']['pixel_errors']
            enhanced_errors = self.results['enhanced']['metrics']['pixel_stats']['pixel_errors']
            
            plt.hist(baseline_errors, bins=50, alpha=0.6, label='Baseline', color='red', density=True)
            plt.hist(enhanced_errors, bins=50, alpha=0.6, label='Enhanced', color='green', density=True)
            
            plt.title('Error Distribution Histogram', fontsize=14, fontweight='bold')
            plt.xlabel('Error (pixels)', fontsize=12)
            plt.ylabel('Density', fontsize=12)
            plt.legend()
            plt.grid(True, alpha=0.3)
        
        # 11. Improvement Summary
        ax11 = plt.subplot(3, 4, 11)
        ax11.axis('off')
        
        if 'baseline' in self.comparison_data and 'enhanced' in self.comparison_data:
            improvements = self.generate_improvement_report()
            
            summary_text = f"""
IMPROVEMENT SUMMARY

Accuracy:
• Error Reduction: {improvements['pixel_error_reduction']['percentage']:.1f}%
• Success Rate (+25px): +{improvements['success_rate_25px_improvement']['absolute']:.1f}pp

Consistency:
• Std Reduction: {improvements['consistency_improvement']['std_reduction_percent']:.1f}%

Quality:
• Excellent Rate: {improvements['excellent_rate_improvement']['multiplier']:.1f}x better
• Poor Rate: -{improvements['poor_rate_reduction']['percentage']:.1f}%

Features:
• {improvements['feature_enhancement_ratio']:.1f}x more features
• {improvements['training_time_ratio']:.1f}x training time
            """
            
            ax11.text(0.1, 0.9, summary_text, transform=ax11.transAxes, fontsize=11,
                     verticalalignment='top', fontfamily='monospace',
                     bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        
        # 12. Model Architecture Comparison
        ax12 = plt.subplot(3, 4, 12)
        
        # Create a simple architecture comparison
        architecture_data = {
            'Baseline': {'LSTM Layers': 2, 'Attention': 0, 'Features': 5, 'Regularization': 1},
            'Enhanced': {'LSTM Layers': 3, 'Attention': 1, 'Features': 33, 'Regularization': 3}
        }
        
        components = list(architecture_data['Baseline'].keys())
        baseline_values = list(architecture_data['Baseline'].values())
        enhanced_values = list(architecture_data['Enhanced'].values())
        
        x = np.arange(len(components))
        width = 0.35
        
        bars1 = plt.bar(x - width/2, baseline_values, width, label='Baseline', color='lightcoral', alpha=0.7)
        bars2 = plt.bar(x + width/2, enhanced_values, width, label='Enhanced', color='lightgreen', alpha=0.7)
        
        plt.title('Architecture Comparison', fontsize=14, fontweight='bold')
        plt.ylabel('Count/Score', fontsize=12)
        plt.xticks(x, components, rotation=45)
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[DISK] Saved detailed comparison plots: {save_path}")
        
        plt.show()
    
    def generate_comparison_report(self, save_path: str = None) -> str:
        """Generate a comprehensive text report"""
        if len(self.comparison_data) < 2:
            return "Insufficient data for comparison"
        
        improvements = self.generate_improvement_report()
        
        report = f"""
{'='*80}
                    LSTM TRAJECTORY PREDICTION MODEL COMPARISON
{'='*80}

BASELINE MODEL PERFORMANCE:
{'─'*40}
• Mean Pixel Error: {self.comparison_data['baseline']['mean_pixel_error']:.1f} pixels
• Median Pixel Error: {self.comparison_data['baseline']['median_pixel_error']:.1f} pixels
• Success Rate (<25px): {self.comparison_data['baseline']['success_rate_25px']:.1f}%
• Success Rate (<50px): {self.comparison_data['baseline']['success_rate_50px']:.1f}%
• Excellent Predictions (0-10px): {self.comparison_data['baseline']['excellent_rate']:.1f}%
• Poor Predictions (>100px): {self.comparison_data['baseline']['poor_rate']:.1f}%
• Error Consistency (Std): {self.comparison_data['baseline']['std_pixel_error']:.1f} pixels
• Training Time: {self.comparison_data['baseline']['train_time']:.1f} seconds
• Features per Timestep: {self.comparison_data['baseline']['feature_count']}

ENHANCED MODEL PERFORMANCE:
{'─'*40}
• Mean Pixel Error: {self.comparison_data['enhanced']['mean_pixel_error']:.1f} pixels
• Median Pixel Error: {self.comparison_data['enhanced']['median_pixel_error']:.1f} pixels
• Success Rate (<25px): {self.comparison_data['enhanced']['success_rate_25px']:.1f}%
• Success Rate (<50px): {self.comparison_data['enhanced']['success_rate_50px']:.1f}%
• Excellent Predictions (0-10px): {self.comparison_data['enhanced']['excellent_rate']:.1f}%
• Poor Predictions (>100px): {self.comparison_data['enhanced']['poor_rate']:.1f}%
• Error Consistency (Std): {self.comparison_data['enhanced']['std_pixel_error']:.1f} pixels
• Training Time: {self.comparison_data['enhanced']['train_time']:.1f} seconds
• Features per Timestep: {self.comparison_data['enhanced']['feature_count']}

IMPROVEMENTS ACHIEVED:
{'─'*40}
[TARGET] ACCURACY IMPROVEMENTS:
   • Pixel Error Reduction: {improvements['pixel_error_reduction']['absolute']:.1f} pixels ({improvements['pixel_error_reduction']['percentage']:.1f}%)
   • Median Error Reduction: {improvements['median_error_reduction']['absolute']:.1f} pixels ({improvements['median_error_reduction']['percentage']:.1f}%)
   • Success Rate Improvement (<25px): +{improvements['success_rate_25px_improvement']['absolute']:.1f} percentage points
   • Success Rate Improvement (<50px): +{improvements['success_rate_50px_improvement']['absolute']:.1f} percentage points

[TARGET] QUALITY IMPROVEMENTS:
   • Excellent Rate Enhancement: {improvements['excellent_rate_improvement']['multiplier']:.1f}x better
   • Poor Predictions Reduction: -{improvements['poor_rate_reduction']['percentage']:.1f}%
   • Consistency Improvement: {improvements['consistency_improvement']['std_reduction_percent']:.1f}% less variance

[TARGET] FEATURE ENGINEERING:
   • Feature Enhancement: {improvements['feature_enhancement_ratio']:.1f}x more features
   • Advanced Architecture: 3 LSTM layers + Attention mechanism
   • Custom Loss Function: Distance-based optimization
   • Data Augmentation: Noise injection and scaling

[TARGET] COMPUTATIONAL COST:
   • Training Time Ratio: {improvements['training_time_ratio']:.1f}x baseline time
   • Model Complexity: Significantly higher but manageable
   • Memory Usage: Increased due to more features and deeper architecture

CONCLUSION:
{'─'*40}
The Enhanced LSTM model demonstrates significant improvements over the baseline:

[OK] PRIMARY ACHIEVEMENTS:
   • {improvements['pixel_error_reduction']['percentage']:.1f}% reduction in prediction error
   • {improvements['success_rate_25px_improvement']['absolute']:.1f} percentage point increase in success rate
   • {improvements['excellent_rate_improvement']['multiplier']:.1f}x improvement in excellent predictions
   • {improvements['consistency_improvement']['std_reduction_percent']:.1f}% improvement in prediction consistency

[OK] TECHNICAL INNOVATIONS:
   • Advanced feature engineering with 33 features per timestep
   • Attention mechanism for better sequence modeling
   • Custom distance-based loss function
   • Deeper architecture with proper regularization
   • Data augmentation techniques

[WARNING] TRADE-OFFS:
   • {improvements['training_time_ratio']:.1f}x longer training time
   • Increased model complexity
   • Higher memory requirements

[TRAINING] RECOMMENDATION:
The Enhanced model is recommended for production use when accuracy is prioritized
over computational efficiency. The {improvements['pixel_error_reduction']['percentage']:.1f}% error reduction and 
{improvements['success_rate_25px_improvement']['absolute']:.1f}pp success rate improvement justify the increased complexity.

{'='*80}
        """
        
        if save_path:
            with open(save_path, 'w') as f:
                f.write(report)
            print(f"[DISK] Saved comparison report: {save_path}")
        
        return report
    
    def export_results_to_json(self, save_path: str):
        """Export all comparison results to JSON"""
        export_data = {
            'model_results': self.results,
            'comparison_metrics': self.comparison_data,
            'improvements': self.generate_improvement_report() if len(self.comparison_data) >= 2 else {}
        }
        
        with open(save_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"[DISK] Exported results to JSON: {save_path}")

def run_model_comparison(baseline_results: Dict, enhanced_results: Dict) -> ModelComparator:
    """Run comprehensive model comparison"""
    print("[DATA] Running comprehensive model comparison...")
    
    comparator = ModelComparator()
    comparator.add_model_results('baseline', baseline_results)
    comparator.add_model_results('enhanced', enhanced_results)
    
    # Calculate performance metrics
    comparison_metrics = comparator.calculate_performance_metrics()
    
    # Generate visualizations
    comparator.create_detailed_comparison_plots('model_comparison_detailed.png')
    
    # Generate text report
    report = comparator.generate_comparison_report('model_comparison_report.txt')
    print(report)
    
    # Export to JSON
    comparator.export_results_to_json('model_comparison_results.json')
    
    return comparator

if __name__ == "__main__":
    print("[DATA] Model Comparison Tool")
    print("This script is designed to be imported and used with actual model results")
    print("Example usage:")
    print("  from model_comparison import run_model_comparison")
    print("  comparator = run_model_comparison(baseline_results, enhanced_results)") 