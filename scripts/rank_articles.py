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
import pickle
import glob
try:
    import lightgbm as lgb
    HAS_LGBM = True
except ImportError:
    HAS_LGBM = False
    print("[WARNING] LightGBM not found. Skipping model-based ranking.")

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
        try:
            import joblib
            if not HAS_LGBM:
                 raise ImportError("LightGBM module not loaded")
            
            model = lgb.Booster(model_file=MODEL_PATH)
            # Use joblib instead of pickle for better numpy compatibility
            scaler = joblib.load(SCALER_PATH)
            print("[OK] Model & scaler loaded")
            use_model = True
        except Exception as e:
            print(f"[WARNING] Could not load model/scaler: {str(e)}")
            print("[INFO] Falling back to score_ag ranking only")
            use_model = False
        
        # Step 5: Feature extraction (skip if model not available)
        if use_model:
            print("\n[Step 5/6] Extracting features...")
            print("  - Loading SentenceTransformer...")
            sys.stdout.flush()
            
            print("  - Encoding text features (jhgan/ko-sroberta-multitask)...")
            # Using Korean-Specific Model
            model_st = SentenceTransformer('jhgan/ko-sroberta-multitask')
            text_features = model_st.encode(
                (df['title'] + " " + df['summary'].fillna('')).tolist(),
                show_progress_bar=False
            )
            
            # PCA: Encode 768 -> 128 dimensions (Load trained PCA)
            PCA_PATH = os.path.join(MODEL_DIR, "pca.pkl")
            if not os.path.exists(PCA_PATH):
                print(f"[ERROR] PCA model not found at {PCA_PATH}")
                print("Please retrain the model first: python scripts/train_lgbm_model.py")
                sys.exit(1)
            
            pca = joblib.load(PCA_PATH)
            
            print("  - Reducing dimensions (PCA 768 -> 128)...")
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
        else:
            print("\n[Step 5/6] Skipping feature extraction (no model)")
            print("\n[Step 6/6] Using score_ag only for ranking...")
            df['score_ag'] = pd.to_numeric(df['score_ag'], errors='coerce').fillna(0)
            df['lgbm_score'] = 0  # Placeholder
        
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
        
        if use_model:
            # Use weighted combination of LGBM prediction and original score
            LGBM_WEIGHT = 0.3      # Reduced from 0.7 (low confidence in model)
            SCOREAG_WEIGHT = 0.7    # Increased from 0.3 (rely on rules)
            
            # Normalize each score to 0-1 range separately
            df['score_ag_norm'] = df['score_ag'].clip(0, 10) / 10  # Assume max 10
            df['lgbm_score_norm'] = df['lgbm_score'].clip(0, 1)
            
            df['final_score'] = LGBM_WEIGHT * df['lgbm_score_norm'] + SCOREAG_WEIGHT * df['score_ag_norm']
        else:
            # Use score_ag only
            df['final_score'] = df['score_ag'].clip(0, 10) / 10


        # --- Strategic Scoring (Rule-Based Enhancement) ---
        # User Feedback:
        # - High Priority: MNC (Global Pharma), Major Distributors (Zuellig, Geo-Young), Key Topics (Patent Expiry, Price Cut, Reimbursement, Co-promotion)
        # - Low Priority: Domestic Pharma Earnings (unless Major Distributor), Minor Clinical Trials (Phase 1/2) without MNC context
        
        # --- New Strategic Scoring (Business Value Based) ---
        def calculate_bd_strategic_score(row):
            # 1. Base Score by Category
            category_map = {
                'Distribution': 10.0, 
                'Zuellig': 10.0,
                'Reimbursement': 9.0, 
                'Client': 8.0,
                'BD': 7.0, 
                'Product Approval': 7.0,
                'Supply Issues': 5.0, 
                'Therapeutic Areas': 5.0,
                'Regulation': 5.0
            }
            base_score = category_map.get(row.get('category'), 2.0)
            
            # Text Extraction (Title + Summary + Keywords)
            text = (str(row.get('title', '')) + " " + str(row.get('summary', '')) + " " + str(row.get('keywords', ''))).lower()
            
            # 2. Commercial Boost Keywords (+3.0)
            commercial_keywords = [
                "출시", "판권", "유통", "계약", "파트너", "공동판매", "코프로모션", "허가완료", "급여", "도입",
                "launch", "license", "distribution", "contract", "partner", "co-promotion", "approval", "reimbursement"
            ]
            has_commercial = any(k in text for k in commercial_keywords)
            
            # 3. Market Dynamic Keywords (+2.0)
            market_keywords = [
                "지오영", "백제", "m&a", "인수", "철수", "한국 법인", "점유율",
                "geo-young", "market share"
            ]
            has_market = any(k in text for k in market_keywords)
            
            # 4. Clinical Penalty Keywords (-8.0 ~ -10.0)
            clinical_keywords = [
                "임상", "1상", "2상", "3상", "진입", "시험 중", "파이프라인", "전임상", "후보물질", "연구 결과",
                "clinical", "phase 1", "phase 2", "phase 3", "trial", "preclinical", "pipeline"
            ]
            has_clinical = any(k in text for k in clinical_keywords)
            
            # 5. Calculate Strategic Score
            strategic_score = base_score
            
            if has_commercial:
                strategic_score += 3.0
            
            if has_market:
                strategic_score += 2.0
                
            if has_clinical:
                if has_commercial:
                    strategic_score -= 2.0  # Commercial context (e.g. "Phase 3 complete, Launch imminent") -> Mild Penalty
                else:
                    strategic_score -= 10.0 # Pure Clinical -> Severe Penalty (Remove from Top 20)
            
            # 6. Specific Exclusion (User Request)
            exclusion_keywords = ["동아쏘시오", "donga socio", "이뮨온시아", "immuneoncia", "에스바이오메딕스", "s-biomedics"]
            if any(k in text for k in exclusion_keywords):
                strategic_score -= 20.0 # Force remove
                
            # 7. Conditional Exclusion: Distribution + (Hospital & Bidding)
            if row.get('category') == 'Distribution':
                if '병원' in text and '입찰' in text:
                    strategic_score -= 20.0 # Force remove (User Request)
            
            return max(0, strategic_score)

        df['strategic_score'] = df.apply(calculate_bd_strategic_score, axis=1)
        
        # Combine Scores: Final = (LGBM_Component * 0.4) + (Strategic_Score * 0.6)
        # LGBM_Component needs to be on 0-10 scale.
        
        if use_model:
            # lgbm_score is 0-1. Scaling to 10.
            # We also mix in score_ag for robustness (0-10).
            # let's assume 'LGBM_Score' in user's formula represents the "AI/Quality" Score.
            # We'll use a mix: 50% LGBM (scaled) + 50% ScoreAG.
            df['lgbm_component'] = (df['lgbm_score'] * 10 * 0.5) + (df['score_ag'] * 0.5)
        else:
            df['lgbm_component'] = df['score_ag'] # Fallback
            
        # Apply Formula
        # Final_Score = (LGBM_Component * 0.4) + (Strategic_Score * 0.6)
        
        df['final_score'] = (df['lgbm_component'] * 0.4) + (df['strategic_score'] * 0.6)
        
        # Removed boost_zuellig as it caps score at 10.0, which is lower than the new max score (~14.2).
        # Zuellig articles now naturally score high via Base(10) + Keywords.
        
        # Category-balanced selection for top results
        print("  - Applying category balancing...")
        df_sorted = df.sort_values(by='final_score', ascending=False)
        
        # Strategy: Pick top articles from each category proportionally
        # Target: ~20 articles with diverse categories
        balanced_selection = []
        categories = df['category'].unique()
        
        # First pass: Top 4 from each major category (Reverted to 4 as per user request - Safety Net)
        for cat in ['Distribution', 'Client', 'BD', 'Zuellig']:
            if cat in categories:
                cat_articles = df_sorted[df_sorted['category'] == cat].head(4)
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
        
        # Step 7: Gemini Deduplication & Strategic Scoring
        # ── Gemini 필터 주석처리 (API quota 절약) ────────────────────────────
        # Gemini quota가 복구되면 아래 주석을 해제하세요.
        # Daily crawl에서 매일 ~6회 API 호출로 quota 소진 → 번역까지 영향
        #
        # gemini_key = os.getenv('GENAI_API_KEY')
        # if not gemini_key:
        #     print("  [WARNING] GENAI_API_KEY not found. Skipping Gemini filter.")
        # else:
        #     try:
        #         from gemini_filter import gemini_batch_deduplicate_and_score
        #         top_candidates = df_sorted.head(30).copy()
        #         print(f"  - Sending {len(top_candidates)} articles to Gemini for scoring...")
        #         filtered_candidates = gemini_batch_deduplicate_and_score(top_candidates)
        #         if filtered_candidates is not None and not filtered_candidates.empty:
        #             def apply_gemini_impact(row):
        #                 g_score = row.get('gemini_score', 0)
        #                 current_score = row.get('final_score', 0)
        #                 if g_score >= 8:
        #                     return min(current_score * 1.5, 1.0)
        #                 elif g_score >= 6:
        #                     return min(current_score * 1.2, 1.0)
        #                 elif g_score <= 2:
        #                     return 0.0
        #                 else:
        #                     return current_score
        #             filtered_candidates['final_score'] = filtered_candidates.apply(apply_gemini_impact, axis=1)
        #             filtered_candidates = filtered_candidates[filtered_candidates['final_score'] > 0]
        #             remaining = df_sorted.iloc[30:]
        #             df_final = pd.concat([filtered_candidates, remaining], ignore_index=True)
        #             df_sorted = df_final.sort_values(by='final_score', ascending=False)
        #             print(f"  [OK] Gemini filtering complete. Top score: {df_sorted['final_score'].max():.2f}")
        #     except ImportError:
        #         print("  [ERROR] Could not import gemini_filter.")
        #     except Exception as e:
        #         print(f"  [ERROR] Gemini filter failed: {str(e)}")
        # ── Gemini 끝 ─────────────────────────────────────────────────────────
        print("\n[Step 7/7] Gemini filter skipped (quota 절약 모드) - LightGBM scores used")
        
        # Update display list with new sorted top 20
        df_top20_display = df_sorted.head(20) # WARNING: This was unwinding the balance!
        
        # CORRECT LOGIC: Re-apply balance if needed or use the balanced list if it was created
        if balanced_selection:
             # df_balanced is already sorted by final_score and contains the balanced set
             df_top20_balanced = df_balanced.head(20)
             
             # Mark these as Top 20 in the full list
             df_sorted['is_top20'] = df_sorted['url'].isin(df_top20_balanced['url'])
             
             # Use balanced list for display
             df_top20_display = df_top20_balanced
        else:
             df_sorted['is_top20'] = False
             df_sorted.loc[df_sorted.index[:20], 'is_top20'] = True
             df_top20_display = df_sorted.head(20)
        
        # Step 8: Save results
        print("\n[Step 8/8] Saving results...")
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
