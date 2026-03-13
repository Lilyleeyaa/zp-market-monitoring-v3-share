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
import glob
import re
import joblib
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
            
            # Reindex to match training categories
            CAT_COLS_PATH = os.path.join(MODEL_DIR, "category_cols.pkl")
            if os.path.exists(CAT_COLS_PATH):
                training_cat_cols = joblib.load(CAT_COLS_PATH)
                category_dummies = category_dummies.reindex(columns=training_cat_cols, fill_value=0)
            else:
                # Fallback to known 8 categories if file doesn't exist
                known_cats = ['cat_BD', 'cat_Client', 'cat_Distribution', 'cat_Product Approval', 'cat_Reimbursement', 'cat_Supply Issues', 'cat_Therapeutic Areas', 'cat_Zuellig']
                category_dummies = category_dummies.reindex(columns=known_cats, fill_value=0)
            
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
            # LGBM weight increased to 0.6 - feedback data is being reflected well
            LGBM_WEIGHT = 0.6      # Increased from 0.3 (model now learning from thumbs-up)
            SCOREAG_WEIGHT = 0.4    # Decreased from 0.7
            
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
                'Reimbursement': 6.0,  # Lowered from 9: was inflating low-LGBM articles via strategic stacking
                'Client': 7.0,        # Restored to 7.0 so important Client news isn't lost
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
            
            # 2-1. Co-promotion MUST appear — extra strong boost
            COPROM_TERMS = ["코프로모션", "공동판매", "co-promotion", "코프로"]
            has_coprom = any(k in text for k in COPROM_TERMS)
            
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
            
            if has_coprom:
                strategic_score += 6.0  # Co-promotion: strongest commercial boost (must-see)
            elif has_commercial:
                strategic_score += 3.0
            
            if has_market:
                strategic_score += 2.0
                
            if has_clinical:
                if has_commercial:
                    strategic_score -= 2.0  # Commercial context (e.g. "Phase 3 complete, Launch imminent") -> Mild Penalty
                else:
                    strategic_score -= 10.0 # Pure Clinical -> Severe Penalty (Remove from Top 20)
            
            # 6. General Corporate Penalty (Softened based on user feedback)
            # Remove "흑자전환", "재편" as user considers major pharma restructuring/earnings as important Client news
            corporate_keywords_minor = [
                "주주총회", "배당", "적자", "단순 실적"
            ]
            if str(row.get('category')) == 'Client':
                if any(k in text for k in corporate_keywords_minor):
                    strategic_score -= 5.0  # Milder penalty for very generic IR news
            
            # 7. VIP Client boost (User cited specific MNCs and major domestics)
            vip_keywords = ["베링거인겔하임", "마운자로", "위고비", "노보노디스크", "릴리", "바이오젠", "화이자", "MSD", "바로팜", "현대약품", "다이이찌산쿄"]
            if any(k in text for k in vip_keywords):
                strategic_score += 4.0

            # 8. Specific Exclusion (User Request)
            exclusion_keywords = ["동아쏘시오", "donga socio", "이뮨온시아", "immuneoncia", "에스바이오메딕스", "s-biomedics", "원바이오젠", "사료", "동물", "반려동물"]
            if any(k in text for k in exclusion_keywords):
                strategic_score = -100.0 # Extreme penalty to ensure it's dropped from Top 20
                
            # 9. Conditional Exclusion: Distribution + (Hospital & Bidding)
            if row.get('category') == 'Distribution':
                if '병원' in text and '입찰' in text:
                    strategic_score -= 20.0 # Force remove (User Request)
                if '도이치뱅크' in text:
                    strategic_score -= 20.0 # Force remove (User Request)
            
            return max(0, strategic_score)

        df['strategic_score'] = df.apply(calculate_bd_strategic_score, axis=1)
        
        # Combine Scores: Final = (LGBM_Component * 0.4) + (Strategic_Score * 0.6)
        # LGBM_Component needs to be on 0-10 scale.
        
        if use_model:
            # lgbm_score is 0-1. Scaling to 10.
            # LGBM share increased to 70% within component (was 50%)
            df['lgbm_component'] = (df['lgbm_score'] * 10 * 0.7) + (df['score_ag'] * 0.3)
        else:
            df['lgbm_component'] = df['score_ag'] # Fallback
            
        # Apply Formula
        # Final_Score = (LGBM_Component * 0.7) + (Strategic_Score * 0.3)
        # Weighting heavily towards AI model per user request
        df['final_score'] = (df['lgbm_component'] * 0.7) + (df['strategic_score'] * 0.3)
        
        # --- Hard Exclusion (User Request: animal/feed) ---
        # Dropping them completely from the display candidates to be 100% safe
        exclude_pool = ["사료", "동물", "반려동물"]
        df['is_excluded'] = df.apply(lambda r: any(k in (str(r['title'])+str(r['summary'])).lower() for k in exclude_pool), axis=1)
        df_sorted = df[df['is_excluded'] == False].sort_values(by='final_score', ascending=False)
        
        # Strategy: Pick top articles from each category proportionally
        # Target: Exactly 20 articles with diverse categories and diversity caps
        selected_urls = set()
        df_top20_list = []
        categories = df['category'].unique()
        
        OBESITY_DRUG_TERMS = ['위고비', '마운자로', '삭센다', '오젬픽', 'GLP-1', '비만치료제', '비만약', '비만']
        MAX_OBESITY = 1
        obesity_count = 0

        def is_obesity_article(row):
            text = (str(row.get('title', '')) + ' ' + str(row.get('summary', '')) + ' ' + str(row.get('keywords', ''))).lower()
            return any(t.lower() in text for t in OBESITY_DRUG_TERMS)

        # 1. First pass: High priority category guarantees
        for cat, limit in [('Distribution', 3), ('Zuellig', 3), ('BD', 8), ('Client', 8)]:
            if cat in categories:
                cat_pool = df_sorted[df_sorted['category'] == cat]
                added_in_cat = 0
                for _, row in cat_pool.iterrows():
                    if added_in_cat >= limit: break
                    if row['url'] in selected_urls: continue
                    
                    is_ob = is_obesity_article(row)
                    if is_ob and obesity_count >= MAX_OBESITY: continue
                    
                    df_top20_list.append(row)
                    selected_urls.add(row['url'])
                    added_in_cat += 1
                    if is_ob: obesity_count += 1

        # 2. Second pass: Max 1 from secondary categories
        MIN_SCORE_OTHER = 5.0
        for cat in categories:
            if cat not in ['Distribution', 'Client', 'BD', 'Zuellig']:
                 cat_pool = df_sorted[df_sorted['category'] == cat]
                 for _, row in cat_pool.iterrows():
                     if row['final_score'] < MIN_SCORE_OTHER: break
                     if row['url'] in selected_urls: continue
                     
                     is_ob = is_obesity_article(row)
                     if is_ob and obesity_count >= MAX_OBESITY: continue
                     
                     df_top20_list.append(row)
                     selected_urls.add(row['url'])
                     if is_ob: obesity_count += 1
                     break # Only 1 per secondary category

        # 3. Third pass: Fill remaining slots until 20
        # No absolute score threshold (picks best available) to guarantee 20 count
        for _, row in df_sorted.iterrows():
            if len(df_top20_list) >= 20: break
            if row['url'] in selected_urls: continue
            
            is_ob = is_obesity_article(row)
            if is_ob and obesity_count >= MAX_OBESITY: continue
            
            df_top20_list.append(row)
            selected_urls.add(row['url'])
            if is_ob: obesity_count += 1

        if df_top20_list:
            df_top20_balanced = pd.DataFrame(df_top20_list).sort_values(by='final_score', ascending=False)
            df_top20_balanced = df_top20_balanced.head(20)
            
            # Mark is_top20 in the main dataframe
            df_sorted['is_top20'] = df_sorted['url'].isin(df_top20_balanced['url'])
            df_top20_display = df_top20_balanced
        else:
            df_sorted['is_top20'] = False
            df_top20_display = df_sorted.head(0)
        
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
