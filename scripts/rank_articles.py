"""
Rank articles using trained LightGBM model
"""
# Fix for numpy_core error in pickle
import numpy as np
import sys
# Ensure numpy is properly initialized before pickle
np.random.seed(42)

import pandas as pd
import os
import pickle
import glob
import lightgbm as lgb
from sentence_transformers import SentenceTransformer

# Configuration
RAW_DATA_DIR = "data/articles_raw"
LABELS_FILE = "data/labels/labels_master.csv"
MODEL_DIR = "model"
MODEL_PATH = os.path.join(MODEL_DIR, "lgbm_model.txt")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.pkl")

def get_days_since(date_str):
    from datetime import datetime
    try:
        if pd.isna(date_str): return 0
        date_obj = pd.to_datetime(date_str)
        today = datetime.now()
        return (today - date_obj).days
    except:
        return 0

def rank_articles():
    """Rank articles using LightGBM model"""
    print("="*70)
    print(">>> Ranking Articles with LightGBM Model...")
    print("="*70)
    
    try:
        # Step 1: Find latest article file
        print("\n[Step 1/6] Finding article files...")
        csv_files = glob.glob(os.path.join(RAW_DATA_DIR, "articles_*.csv"))
        csv_files = [f for f in csv_files if "ranked" not in os.path.basename(f)]
        
        if not csv_files:
            print("[ERROR] No article CSVs found.")
            return
        
        import re
        def extract_date_from_filename(filepath):
            basename = os.path.basename(filepath)
            match = re.search(r'_(\d{8})\.csv$', basename)
            if match:
                return match.group(1)
            return "00000000"
        
        latest_file = max(csv_files, key=extract_date_from_filename)
        print(f"[OK] Found: {os.path.basename(latest_file)}")
        
        # Step 2: Load articles
        print("\n[Step 2/6] Loading article data...")
        try:
            df = pd.read_csv(latest_file, encoding='utf-8')
            print(f"[OK] Loaded {len(df)} articles (UTF-8)")
        except UnicodeDecodeError:
            print("[INFO] UTF-8 failed, trying CP949...")
            df = pd.read_csv(latest_file, encoding='cp949')
            print(f"[OK] Loaded {len(df)} articles (CP949)")
        
        if df.empty:
            print("[ERROR] File is empty.")
            return
        
        # Step 3: Check model files
        print("\n[Step 3/6] Checking model files...")
        if not os.path.exists(MODEL_PATH):
            print(f"[ERROR] Model not found: {MODEL_PATH}")
            return
        if not os.path.exists(SCALER_PATH):
            print(f"[ERROR] Scaler not found: {SCALER_PATH}")
            return
        print("[OK] Model files exist")
        
        # Step 4: Load model & scaler
        print("\n[Step 4/6] Loading model & scaler...")
        model = lgb.Booster(model_file=MODEL_PATH)
        with open(SCALER_PATH, 'rb') as f:
            scaler = pickle.load(f)
        print("[OK] Model & scaler loaded")
        
        # Step 5: Feature extraction
        print("\n[Step 5/6] Extracting features...")
        print("  - Loading SentenceTransformer...")
        sys.stdout.flush()
        model_st = SentenceTransformer('all-MiniLM-L6-v2')
        
        print(f"  - Encoding {len(df)} articles...")
        sys.stdout.flush()
        text_features = model_st.encode(
            (df['title'] + " " + df['summary'].fillna('')).tolist(),
            show_progress_bar=True
        )
        
        # PCA: Encode 384 -> 64 dimensions (Load trained PCA)
        PCA_PATH = os.path.join(MODEL_DIR, "pca.pkl")
        if not os.path.exists(PCA_PATH):
            print(f"[ERROR] PCA model not found at {PCA_PATH}")
            print("Please retrain the model first: python scripts/train_lgbm_model.py")
            sys.exit(1)
            
        with open(PCA_PATH, 'rb') as f:
            pca = pickle.load(f)
        
        print("  - Reducing dimensions (PCA 384 -> 64)...")
        text_features = pca.transform(text_features)
        
        print("  - Extracting metadata features...")
        df['score_ag'] = pd.to_numeric(df['score_ag'], errors='coerce').fillna(0)
        
        # Category encoding (one-hot) - must match training
        category_dummies = pd.get_dummies(df['category'], prefix='cat')
        
        # Removed days_old to reduce temporal bias
        
        meta_features = pd.concat([
            df[['score_ag']],
            category_dummies
        ], axis=1).fillna(0).values
        
        X = np.hstack([text_features, meta_features])
        X_scaled = scaler.transform(X)
        print("[OK] Feature extraction complete")
        
        # Step 6: Prediction
        print("\n[Step 6/6] Running LightGBM prediction...")
        scores = model.predict(X_scaled)
        print(f"[OK] Predicted scores for {len(scores)} articles")
        
        df['lgbm_score'] = scores
        
        # Load labels if available
        if os.path.exists(LABELS_FILE):
            try:
                labels_df = pd.read_csv(LABELS_FILE, encoding='utf-8')
                print("  - Loaded labels (UTF-8)")
            except UnicodeDecodeError:
                labels_df = pd.read_csv(LABELS_FILE, encoding='cp949')
                print("  - Loaded labels (CP949)")
            except Exception as e:
                print(f"  - Warning: Could not load labels: {str(e)}")
                labels_df = None
            
            if labels_df is not None:
                labels_df['url'] = labels_df['url'].astype(str)
                df['url'] = df['url'].astype(str)
                
                # Handle reward column naming
                reward_col = None
                for col in ['reward', 'reward_label', 'reward_raw']:
                    if col in labels_df.columns:
                        reward_col = col
                        break
                
                if reward_col:
                    df = pd.merge(df, labels_df[['url', reward_col]].rename(columns={reward_col: 'reward'}), 
                                  on='url', how='left')
                    print(f"  - Merged {len(labels_df)} labels")
        
        # Normalize scores
        print("  - Calculating final scores...")
        
        # Use absolute scores instead of normalization to avoid time bias
        # final_score = weighted combination of LGBM prediction and original score
        # Adjusted: Model performance is low (AUC 0.55), so rely more on rules
        LGBM_WEIGHT = 0.3      # Reduced from 0.7 (low confidence in model)
        SCOREAG_WEIGHT = 0.7    # Increased from 0.3 (rely on rules)
        
        # Normalize each score to 0-1 range separately (not relative to dataset)
        # For score_ag: it's already in a reasonable range, just clip
        df['score_ag_norm'] = df['score_ag'].clip(0, 10) / 10  # Assume max 10
        
        # For lgbm_score: it's already a probability (0-1), use as-is
        df['lgbm_score_norm'] = df['lgbm_score'].clip(0, 1)
        
        df['final_score'] = LGBM_WEIGHT * df['lgbm_score_norm'] + SCOREAG_WEIGHT * df['score_ag_norm']
        
        # Category-balanced selection for top results
        print("  - Applying category balancing...")
        df_sorted = df.sort_values(by='final_score', ascending=False)
        
        # Strategy: Pick top articles from each category proportionally
        # Target: ~20 articles with diverse categories
        balanced_selection = []
        categories = df['category'].unique()
        
        # First pass: Top 2-3 from each major category
        for cat in ['Distribution', 'Client', 'BD', 'Zuellig']:
            if cat in categories:
                cat_articles = df_sorted[df_sorted['category'] == cat].head(3)
                balanced_selection.append(cat_articles)
        
        # Second pass: Top 1-2 from other categories
        for cat in categories:
            if cat not in ['Distribution', 'Client', 'BD', 'Zuellig']:
                cat_articles = df_sorted[df_sorted['category'] == cat].head(2)
                balanced_selection.append(cat_articles)
        
        # Combine and re-sort by score
        if balanced_selection:
            df_balanced = pd.concat(balanced_selection, ignore_index=True)
            df_balanced = df_balanced.drop_duplicates(subset=['url'])
            df_balanced = df_balanced.sort_values(by='final_score', ascending=False)
            
            # Fill remaining slots with highest scores (if less than 20)
            if len(df_balanced) < 20:
                remaining = df_sorted[~df_sorted['url'].isin(df_balanced['url'])].head(20 - len(df_balanced))
                df_balanced = pd.concat([df_balanced, remaining], ignore_index=True)
            
            # Use balanced top 20 for display, but save full sorted list
            df_top20_display = df_balanced.head(20)
        else:
            df_top20_display = df_sorted.head(20)
        
        # Save results
        print("  - Saving results...")
        date_str = os.path.basename(latest_file).replace("articles_", "").replace(".csv", "")
        output_file = os.path.join(RAW_DATA_DIR, f"articles_ranked_{date_str}.csv")
        
        df_sorted.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n[SUCCESS] Saved ranked articles to:")
        print(f"  {output_file}")
        
        # Display top results (category-balanced)
        print(f"\n{'='*70}")
        print(f"Top 20 Recommended Articles (Category-Balanced):")
        print(f"{'='*70}")
        for idx, row in enumerate(df_top20_display.head(20).itertuples(), 1):
            print(f"{idx}. [{row.category}] {row.title[:60]}...")
            print(f"   Score: {row.final_score:.4f} (LGBM: {row.lgbm_score:.4f})")
        print(f"{'='*70}")
        
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Process stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n[CRITICAL ERROR] An unexpected error occurred:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("\nStack trace:")
        import traceback
        traceback.print_exc()
        print("\n[FAILED] Ranking process terminated due to error")
        sys.exit(1)

if __name__ == "__main__":
    rank_articles()
