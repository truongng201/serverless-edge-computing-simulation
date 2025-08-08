#!/usr/bin/env python3
"""
Pre-training check script
Kiểm tra tất cả dependencies và files trước khi training
"""

import os
import sys
from pathlib import Path

def check_python_version():
    """Kiểm tra Python version"""
    version = sys.version_info
    print(f"[PYTHON] Python version: {version.major}.{version.minor}.{version.micro}")
    if version.major >= 3 and version.minor >= 8:
        print("[OK] Python version OK")
        return True
    else:
        print("[ERROR] Cần Python 3.8+")
        return False

def check_tensorflow():
    """Kiểm tra TensorFlow"""
    try:
        import tensorflow as tf
        print(f"[TF] TensorFlow version: {tf.__version__}")
        
        # Kiểm tra GPU
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            print(f"[TRAINING] GPU found: {len(gpus)} GPU(s)")
            for i, gpu in enumerate(gpus):
                print(f"   GPU {i}: {gpu.name}")
        else:
            print("[WARNING]  No GPU found, sẽ dùng CPU")
        
        print("[OK] TensorFlow OK")
        return True
    except ImportError:
        print("[ERROR] TensorFlow chưa cài đặt")
        print("   Chạy: pip install tensorflow>=2.8.0")
        return False

def check_other_libraries():
    """Kiểm tra các thư viện khác"""
    libraries = [
        ('numpy', 'numpy'),
        ('pandas', 'pandas'), 
        ('sklearn', 'scikit-learn'),
        ('matplotlib', 'matplotlib'),
        ('seaborn', 'seaborn')
    ]
    
    all_ok = True
    for lib_name, import_name in libraries:
        try:
            module = __import__(import_name)
            version = getattr(module, '__version__', 'unknown')
            print(f"[OK] {lib_name}: {version}")
        except ImportError:
            print(f"[ERROR] {lib_name} chưa cài đặt")
            all_ok = False
    
    return all_ok

def check_datasets():
    """Kiểm tra dataset files"""
    base_dir = Path(__file__).parent.parent
    datasets = [
        base_dir / "DACT Easy-Dataset.csv",
        base_dir / "DACT Strict-Dataset.csv"
    ]
    
    all_found = True
    for dataset in datasets:
        if dataset.exists():
            size_mb = dataset.stat().st_size / (1024 * 1024)
            print(f"[OK] {dataset.name}: Found ({size_mb:.1f} MB)")
        else:
            print(f"[ERROR] {dataset.name}: Không tìm thấy")
            all_found = False
    
    return all_found

def check_model_scripts():
    """Kiểm tra training scripts của các models"""
    base_dir = Path(__file__).parent
    scripts_to_check = [
        ("LSTM Baseline", base_dir / "lstm_baseline" / "train_test.py"),
        ("GRU Baseline", base_dir / "gru_baseline" / "train_test.py"),
        ("Enhanced LSTM", base_dir / "lstm_enhanced" / "enhanced_train_test.py"),
        ("Bidirectional RNN", base_dir / "bidirectional_rnn" / "train_test.py"),
        ("Attention Models", base_dir / "attention_models" / "train_test.py"),
        ("Transformer", base_dir / "transformer" / "train_test.py"),
        ("ST-GNN", base_dir / "spatial_temporal_gnn" / "train_test.py")
    ]
    
    all_found = True
    for model_name, script_path in scripts_to_check:
        if script_path.exists():
            print(f"[OK] {model_name}: Script tìm thấy")
        else:
            print(f"[ERROR] {model_name}: Script không tìm thấy tại {script_path}")
            all_found = False
    
    return all_found

def check_disk_space():
    """Kiểm tra disk space"""
    import shutil
    current_dir = Path(__file__).parent
    
    try:
        # Get free space in bytes, works on Windows and Unix
        total, used, free = shutil.disk_usage(current_dir)
        free_gb = free / (1024**3)
        
        print(f"[DISK] Free disk space: {free_gb:.1f} GB")
        
        if free_gb > 5:  # Cần ít nhất 5GB
            print("[OK] Disk space OK")
            return True
        else:
            print("[ERROR] Cần ít nhất 5GB free space")
            return False
    except Exception as e:
        print(f"[WARNING]  Không thể kiểm tra disk space: {e}")
        print("[OK] Bỏ qua check này")
        return True

def main():
    """Main check function"""
    print("[CHECK] PRE-TRAINING CHECK")
    print("=" * 50)
    
    checks = []
    
    print("\n1. Kiểm tra Python version:")
    checks.append(check_python_version())
    
    print("\n2. Kiểm tra TensorFlow:")
    checks.append(check_tensorflow())
    
    print("\n3. Kiểm tra các thư viện khác:")
    checks.append(check_other_libraries())
    
    print("\n4. Kiểm tra dataset files:")
    checks.append(check_datasets())
    
    print("\n5. Kiểm tra training scripts:")
    checks.append(check_model_scripts())
    
    print("\n6. Kiểm tra disk space:")
    checks.append(check_disk_space())
    
    # Tổng kết
    print("\n" + "=" * 50)
    print("[DATA] TỔNG KẾT:")
    print("=" * 50)
    
    passed = sum(checks)
    total = len(checks)
    
    if passed == total:
        print(f"[SUCCESS] Tất cả checks passed ({passed}/{total})!")
        print("[OK] Sẵn sàng để training!")
        print("\nBước tiếp theo:")
        print("  python run_individual_training.py --single")
        print("  hoặc")
        print("  python run_individual_training.py --all")
        return True
    else:
        print(f"[WARNING]  {passed}/{total} checks passed")
        print("[ERROR] Cần fix các issues trước khi training")
        print("\nCác bước khắc phục:")
        
        if not checks[1]:  # TensorFlow
            print("1. Cài TensorFlow: pip install tensorflow>=2.8.0")
        if not checks[2]:  # Other libs
            print("2. Cài dependencies: pip install -r requirements.txt")
        if not checks[3]:  # Datasets
            print("3. Download datasets và đặt trong thư mục gốc")
        
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 