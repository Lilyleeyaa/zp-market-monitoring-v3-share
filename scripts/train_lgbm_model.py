"""
Article Ranking Model - LightGBM Version
Optimized for small datasets and production use
"""
import pandas as pd
import numpy as np
import os
import pickle
import lightgbm as lgb
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score
from datetime import datetime

# Configuration
LABELS_FILE = "data/labels/labels_master.csv"
RAW_DATA_DIR = "data/articles_raw"
MODEL_DIR = "model"
LOG_DIR = "data/logs"

MODEL_PATH = os.path.join(MODEL_DIR, "lgbm_model.txt")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.pkl")

# LightGBM Hyperparameters (optimized for small data)
LGBM_PARAMS = {
    'objective': 'binary',
    'metric': 'auc',
    'boosting_type': 'gbdt',
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'verbose': -1,
    'min_data_in_leaf': 5,
    'max_depth': 5
}

# Ensure directories
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

def get_days_since(date_str):
    try:
        if pd.isna(date_str): return 0
        date_obj = pd.to_datetime(date_str)
        today = datetime.now()
        return (today - date_obj).days
    except:
        return 0


def load_data():
    """Load and merge labeled data with raw features"""
    print("\n>>> Loading Data...")
    
    # Load labels
    try:
        labels_df = pd.read_csv(LABELS_FILE, encoding='utf-8')
    except UnicodeDecodeError:
        labels_df = pd.read_csv(LABELS_FILE, encoding='cp949')
    
    labels_df['url'] = labels_df['url'].astype(str)
    
    # Load all raw CSVs
    import glob
    all_files = glob.glob(os.path.join(RAW_DATA_DIR, "articles_*.csv"))
    all_files.sort()
    
    raw_df_list = []
    for f in all_files:
        try:
            raw_df_list.append(pd.read_csv(f, encoding='utf-8'))
        except UnicodeDecodeError:
            raw_df_list.append(pd.read_csv(f, encoding='cp949'))
    
    if not raw_df_list:
        print("No raw articles found.")
        return None
        
    raw_df = pd.concat(raw_df_list, ignore_index=True)
    raw_df['url'] = raw_df['url'].astype(str)
    raw_df = raw_df.drop_duplicates(subset=['url'], keep='last')
    
    # Merge
    df = pd.merge(labels_df, raw_df, on='url', how='inner', suffixes=('_label', '_raw'))
    
    # Use raw columns
    for col in ['title', 'summary', 'published_date', 'category', 'score_ag']:
        if f'{col}_raw' in df.columns:
            df[col] = df[f'{col}_raw']
    
    print(f"[OK] Loaded {len(df)} labeled articles")
    return df


def extract_features(df):
    """Extract features for LightGBM"""
    print("\n>>> Extracting Features...")
    
    # Load sentence transformer
    model_st = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Text embeddings
    print("  - Encoding text features...")
    text_embeddings = model_st.encode(
        (df['title'] + " " + df['summary'].fillna('')).tolist(),
        show_progress_bar=True
    )
    
    # PCA: Encode 384 -> 128 dimensions (Increased capacity for better semantic separation)
    from sklearn.decomposition import PCA
    print("  - Reducing dimensions (PCA 384 -> 128)...")
    pca = PCA(n_components=128, random_state=42)
    text_features = pca.fit_transform(text_embeddings)
    
    # Save PCA model
    PCA_PATH = os.path.join(MODEL_DIR, "pca.pkl")
    with open(PCA_PATH, 'wb') as f:
        pickle.dump(pca, f)
    print(f"[OK] PCA model saved to {PCA_PATH}")

    
    # Metadata features
    print("  - Extracting metadata features...")
    df['score_ag'] = pd.to_numeric(df['score_ag'], errors='coerce').fillna(0)
    
    # Category encoding (one-hot)
    category_dummies = pd.get_dummies(df['category'], prefix='cat')
    
    # Removed days_old - it was causing temporal bias
    
    meta_features = pd.concat([
        df[['score_ag']],
        category_dummies
    ], axis=1).fillna(0).values
    
    # Combine
    X = np.hstack([text_features, meta_features])
    
    # Get reward labels (handle suffix from merge)
    if 'reward' in df.columns:
        y = df['reward'].values
    elif 'reward_label' in df.columns:
        y = df['reward_label'].values
    elif 'reward_raw' in df.columns:
        y = df['reward_raw'].values
    else:
        raise KeyError("No reward column found in dataset!")
        
    # Create sample weights based on score_ag (Higher score = More important to learn)
    weights = df['score_ag'].values
    weights = np.clip(weights, 1, 10) # Clip 1~10
    
    print(f"[OK] Feature extraction complete: {X.shape}")
    print(f"[OK] Text features: 128 dims (PCA) + Metadata: {meta_features.shape[1]} features")
    return X, y, weights, df


def train_model():
    """Train LightGBM model"""
    print("="*70)
    print(">>> Starting LightGBM Training...")
    print("="*70)
    
    # Load data
    df = load_data()
    if df is None or len(df) == 0:
        print("No data available for training.")
        return
    
    # Extract features
    X, y, weights, df = extract_features(df)
    
    # Stratified split (Splitting X, y, AND weights)
    print("\n>>> Splitting Data...")
    X_train, X_test, y_train, y_test, w_train, w_test = train_test_split(
        X, y, weights,
        test_size=0.3,
        stratify=y,
        random_state=42
    )
    
    print(f"Train samples: {len(X_train)} | Test samples: {len(X_test)}")
    print(f"Train positive rate: {y_train.mean():.1%}")
    print(f"Test positive rate: {y_test.mean():.1%}")
    
    # Scale features
    print("\n>>> Scaling Features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Save scaler
    with open(SCALER_PATH, 'wb') as f:
        pickle.dump(scaler, f)
    print(f"[OK] Scaler saved to {SCALER_PATH}")
    
    # Create LightGBM datasets WITH WEIGHTS
    print("\n>>> Training LightGBM Model (Weighted by score_ag)...")
    train_data = lgb.Dataset(X_train_scaled, label=y_train, weight=w_train)
    test_data = lgb.Dataset(X_test_scaled, label=y_test, weight=w_test, reference=train_data)

    
    # Train
    model = lgb.train(
        LGBM_PARAMS,
        train_data,
        num_boost_round=100,
        valid_sets=[train_data, test_data],
        valid_names=['train', 'test'],
        callbacks=[
            lgb.early_stopping(stopping_rounds=10),
            lgb.log_evaluation(period=10)
        ]
    )
    
    # Save model
    model.save_model(MODEL_PATH)
    print(f"\n[OK] Model saved to {MODEL_PATH}")
    
    # Evaluate
    print("\n>>> Evaluating on Test Set...")
    y_pred_proba = model.predict(X_test_scaled)
    y_pred = (y_pred_proba >= 0.5).astype(int)
    
    auc = roc_auc_score(y_test, y_pred_proba)
    acc = accuracy_score(y_test, y_pred)
    
    print(f"Test AUC: {auc:.4f}")
    print(f"Test Accuracy: {acc:.4f}")
    
    # Top-K metric
    top_k = 5
    top_indices = np.argsort(-y_pred_proba)[:top_k]
    top_k_reward = y_test[top_indices].mean()
    print(f"Test Avg Reward @ Top-{top_k}: {top_k_reward:.4f}")
    
    # Feature importance
    print("\n>>> Top 10 Feature Importances:")
    importance = model.feature_importance(importance_type='gain')
    
    # Reconstruct feature names (removed days_old)
    category_cols = pd.get_dummies(df['category'], prefix='cat').columns.tolist()
    feature_names = [f"pca_{i}" for i in range(128)] + ['score_ag'] + category_cols
    
    importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': importance
    }).sort_values('importance', ascending=False)
    
    print(importance_df.head(10).to_string(index=False))
    
    print("\n" + "="*70)
    print("Training Complete!")
    print("="*70)


if __name__ == "__main__":
    # Auto-install LightGBM if needed
    try:
        import lightgbm
    except ImportError:
        print("📦 Installing LightGBM...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "lightgbm", "-q"])
        print("✅ LightGBM installed")
    
    train_model()
