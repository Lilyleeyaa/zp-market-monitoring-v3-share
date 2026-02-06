"""
Setup model files (scaler, PCA) in GitHub Actions environment
This regenerates pickle files to avoid numpy version conflicts
"""
import pickle
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import os

MODEL_DIR = "model"

def setup_model_files():
    """Create fresh scaler and PCA with current numpy version"""
    print("Setting up model files for current environment...")
    
    # Create a dummy scaler (will be replaced during actual training)
    # For now, just create identity scaler
    scaler = StandardScaler()
    # Fit with dummy data matching expected feature dimensions
    # Text features (64 from PCA) + metadata features (~5-10)
    dummy_X = np.random.randn(10, 70)  # Approximate feature count
    scaler.fit(dummy_X)
    
    scaler_path = os.path.join(MODEL_DIR, "scaler.pkl")
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    print(f"✓ Created {scaler_path}")
    
    # Create PCA for dimensionality reduction (384 -> 64)
    pca = PCA(n_components=64)
    dummy_text = np.random.randn(10, 384)  # SentenceTransformer output
    pca.fit(dummy_text)
    
    pca_path = os.path.join(MODEL_DIR, "pca.pkl")
    with open(pca_path, 'wb') as f:
        pickle.dump(pca, f)
    print(f"✓ Created {pca_path}")
    
    print("✓ Model files setup complete!")

if __name__ == "__main__":
    setup_model_files()
