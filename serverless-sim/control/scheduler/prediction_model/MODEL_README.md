# Trajectory Prediction Models - Comprehensive Comparison

This directory contains implementations of various machine learning models for trajectory prediction, ranging from basic RNN architectures to advanced Graph Neural Networks.

## 📁 Project Structure

```
ml_model/
├── lstm_baseline/          # Basic LSTM implementation
├── lstm_enhanced/          # Enhanced LSTM with advanced features
├── gru_baseline/           # GRU implementation
├── bidirectional_rnn/      # Bidirectional LSTM and GRU variants
├── attention_models/       # Attention-based models
├── transformer/            # Pure Transformer architecture
├── spatial_temporal_gnn/   # Graph Neural Network approach
├── data/                   # Data loading and preprocessing
├── utils/                  # Utility functions
├── comparison/             # Model comparison tools
└── master_comparison.py    # Main comparison script
```

## 🎯 Model Categories

### 1. **Basic RNN Variants** (Moderate Complexity)
#### GRU (Gated Recurrent Unit)
- **File**: `gru_baseline/gru_model.py`
- **Description**: Simplified LSTM variant with fewer parameters
- **When to use**: Faster training, similar performance to LSTM
- **Advantages**: Lower computational cost, less overfitting
- **Disadvantages**: May underperform on very complex sequences

#### Bidirectional RNN
- **File**: `bidirectional_rnn/bidirectional_model.py`
- **Description**: Processes sequences in both forward and backward directions
- **Variants**: Bidirectional LSTM/GRU with different merge modes
- **When to use**: When future context is important for prediction
- **Advantages**: Better sequence understanding, higher accuracy
- **Disadvantages**: Double the parameters, slower training

### 2. **Attention-Based Models** (Advanced)
#### LSTM/GRU with Attention
- **File**: `attention_models/attention_model.py`
- **Description**: RNN with attention mechanism to focus on important timesteps
- **Types**: Basic attention and Self-attention variants
- **When to use**: Long sequences where only some steps are crucial
- **Advantages**: Interpretable, improved accuracy on long sequences
- **Disadvantages**: Increased model complexity

#### Transformer
- **File**: `transformer/transformer_model.py`
- **Description**: Pure attention-based architecture without RNN
- **Features**: Multi-head attention, positional encoding
- **When to use**: Large datasets, state-of-the-art performance needed
- **Advantages**: Excellent performance, parallelizable training
- **Disadvantages**: Requires more data, careful hyperparameter tuning

### 3. **Graph-Based Approach** (Novel)
#### Spatial-Temporal GNN
- **File**: `spatial_temporal_gnn/st_gnn_model.py`
- **Description**: Models trajectories as graph with spatial relationships
- **Features**: Graph convolution + LSTM + temporal attention
- **When to use**: Modeling spatial dependencies in trajectory data
- **Advantages**: Captures spatial relationships, global context
- **Disadvantages**: Most complex to implement and tune

## 🚀 Quick Start

### Train Individual Models

```bash
# Train GRU model
cd gru_baseline
python train_test.py

# Train Bidirectional models
cd ../bidirectional_rnn
python train_test.py

# Train Attention models
cd ../attention_models
python train_test.py

# Train Transformer models
cd ../transformer
python train_test.py

# Train ST-GNN models
cd ../spatial_temporal_gnn
python train_test.py
```

### Run Complete Comparison

```bash
# From ml_model directory
python master_comparison.py
```

This will:
1. Train all model variants
2. Collect results from each model
3. Create comprehensive comparison plots
4. Generate detailed performance report

## 📊 Model Configurations

### GRU Baseline
```python
config = {
    'gru_units': [64, 32],
    'dense_units': [32],
    'dropout_rate': 0.2,
    'epochs': 80,
    'batch_size': 32
}
```

### Bidirectional RNN
```python
config = {
    'rnn_type': 'LSTM',  # or 'GRU'
    'rnn_units': [64, 32],
    'merge_mode': 'concat',  # 'sum', 'ave', 'mul'
    'epochs': 100
}
```

### Attention Models
```python
config = {
    'rnn_type': 'LSTM',
    'attention_type': 'basic',  # or 'self'
    'rnn_units': [128, 64],
    'attention_units': 64,
    'num_heads': 8  # for self-attention
}
```

### Transformer
```python
config = {
    'd_model': 128,
    'num_heads': 8,
    'num_blocks': 4,
    'dff': 512,
    'epochs': 100
}
```

### Spatial-Temporal GNN
```python
config = {
    'num_spatial_nodes': 16,
    'gcn_units': [64, 32],
    'lstm_units': [64, 32],
    'use_temporal_attention': True,
    'epochs': 120
}
```

## 📈 Performance Metrics

All models are evaluated on:
- **Mean Error (meters)**: Average prediction error in real-world distance
- **Median Error (meters)**: Robust error metric
- **Pixel Accuracy**: Percentage of predictions within 50 pixels
- **Parameter Count**: Model complexity measure
- **Training Time**: Computational efficiency

## 🔬 Research Insights

### Expected Performance Ranking (Hypothesis)
1. **Transformer** - Best accuracy for large datasets
2. **ST-GNN** - Best for spatial relationship modeling
3. **Attention Models** - Good balance of performance and interpretability
4. **Bidirectional RNN** - Solid improvement over basic RNN
5. **GRU** - Best efficiency/performance trade-off
6. **LSTM Baseline** - Reference baseline

### Model Selection Guidelines

| Use Case | Recommended Model | Reason |
|----------|------------------|--------|
| Production App | GRU Baseline | Fast, efficient, good performance |
| Research | Transformer or ST-GNN | State-of-the-art accuracy |
| Interpretability | Attention Models | Attention weights show focus |
| Limited Data | Bidirectional RNN | Better generalization |
| Real-time | GRU Baseline | Lowest latency |
| Spatial Context | ST-GNN | Models spatial relationships |

## 🛠️ Implementation Details

### Data Pipeline
- **Input**: Sequences of trajectory features (33 features)
- **Output**: Next position coordinates (lat, lng)
- **Preprocessing**: Normalization, sequence windowing
- **Splits**: 60% train, 20% validation, 20% test

### Training Process
- **Loss Function**: Mean Squared Error (MSE)
- **Optimizer**: Adam with gradient clipping
- **Callbacks**: Early stopping, learning rate reduction
- **Metrics**: Custom coordinate accuracy, pixel accuracy

### Evaluation
- **Geographic Bounds**: Columbus, Ohio area
- **Error Calculation**: Haversine distance for real-world metrics
- **Visualization**: Training curves, error distributions

## 📋 Requirements

```bash
# Core dependencies
tensorflow>=2.8.0
numpy>=1.21.0
pandas>=1.3.0
matplotlib>=3.5.0
scikit-learn>=1.0.0

# Optional for enhanced features
seaborn>=0.11.0
tqdm>=4.64.0
```

## 🎯 Future Extensions

### Planned Improvements
1. **Ensemble Methods**: Combine multiple models
2. **Neural Architecture Search**: Auto-optimize architectures
3. **Multi-Task Learning**: Predict multiple trajectory properties
4. **Domain Adaptation**: Transfer between different cities
5. **Uncertainty Quantification**: Prediction confidence estimation

### Advanced Variants
1. **ConvLSTM**: Spatial-temporal convolutions
2. **Memory Networks**: External memory for long-term dependencies
3. **Meta-Learning**: Few-shot adaptation to new users
4. **Physics-Informed**: Incorporate movement constraints

## 📊 Results Summary

After running all models, check:
- `master_comparison_report.txt` - Detailed performance analysis
- `master_model_comparison.png` - Visual comparison charts
- Individual model folders for specific results

## 🤝 Contributing

To add new models:
1. Create new folder under `ml_model/`
2. Implement model class with standard interface
3. Add training script with evaluation
4. Update `master_comparison.py` to include your model

## 📚 References

1. **GRU**: Cho et al. "Learning Phrase Representations using RNN Encoder-Decoder"
2. **Bidirectional RNN**: Schuster & Paliwal "Bidirectional Recurrent Neural Networks"
3. **Attention**: Bahdanau et al. "Neural Machine Translation by Jointly Learning to Align and Translate"
4. **Transformer**: Vaswani et al. "Attention Is All You Need"
5. **ST-GNN**: Yu et al. "Spatio-Temporal Graph Convolutional Networks"

---

🎯 **Goal**: Find the optimal balance between accuracy, efficiency, and interpretability for trajectory prediction in digital twin simulations.
