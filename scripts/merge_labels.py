"""
Merge labeled data and prepare for training
After user completes labeling, run this script to merge old and new labeled data
"""
import pandas as pd
import os
import glob

# File paths
OLD_LABELS = 'data/labels/labels_master.csv'
OUTPUT = 'data/labels/labels_master.csv'
BACKUP = 'data/labels/labels_master_backup.csv'

def find_latest_file(pattern):
    """Find the most recent file matching the pattern"""
    files = glob.glob(pattern)
    if not files:
        return None
    # Sort by modification time, return newest
    return max(files, key=os.path.getmtime)

def merge_labels():
    # Backup existing labels
    if os.path.exists(OLD_LABELS):
        # Try multiple encodings
        encodings_to_try = ['utf-8-sig', 'cp949', 'euc-kr', 'utf-8']
        old_df = None
        for enc in encodings_to_try:
            try:
                old_df = pd.read_csv(OLD_LABELS, encoding=enc)
                print(f"✓ Loaded existing labels with encoding: {enc}")
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        if old_df is None:
            print(f"⚠ Could not read {OLD_LABELS} with any encoding, treating as empty")
            old_df = pd.DataFrame()
        else:
            old_df.to_csv(BACKUP, index=False, encoding='utf-8-sig')
            print(f"✓ Backed up existing labels to {BACKUP}")
            print(f"  Old labeled data: {len(old_df)} articles")
    else:
        old_df = pd.DataFrame()
        print("No existing labels found. Creating new file.")
    
    # Find the latest labeled file (exclude master files)
    new_labels_paths = [
        'data/labels/articles_to_label_*.csv',
        'articles_to_label_*.csv'
    ]
    
    files_found = []
    for path in new_labels_paths:
        matches = glob.glob(path)
        # Exclude master/backup files
        matches = [f for f in matches if 'master' not in f.lower() and 'backup' not in f.lower()]
        files_found.extend(matches)
    
    if not files_found:
        print(f"Error: No labeled file found matching 'articles_to_label_*.csv'!")
        print("Please upload your labeled file to the file system.")
        return False
    
    # Get the most recent file
    NEW_LABELS = max(files_found, key=os.path.getmtime)
    print(f"  Found latest labeled file: {NEW_LABELS}")
    
    # Load new labeled data (try multiple encodings)
    encodings = ['utf-8-sig', 'cp949', 'euc-kr', 'utf-8']
    new_labeled = None
    for enc in encodings:
        try:
            new_labeled = pd.read_csv(NEW_LABELS, encoding=enc)
            print(f"  Loaded labeled file with encoding: {enc}")
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    if new_labeled is None:
        print("Error: Could not read labeled file with any encoding!")
        return False
    
    # Check if reward column exists and is filled
    if 'reward' not in new_labeled.columns:
        print("Error: 'reward' column not found in labeled file!")
        return False
        
    if new_labeled['reward'].isna().all() or (new_labeled['reward'] == '').all():
        print("Error: reward column is empty in new labels file!")
        print("Please complete labeling first.")
        return False
    
    # Only keep rows with valid reward
    new_labeled = new_labeled[new_labeled['reward'].notna() & (new_labeled['reward'] != '')]
    print(f"  New labeled data: {len(new_labeled)} articles")
    
    # If old data exists and is not empty, combine
    if not old_df.empty:
        # Check if this date already exists in old data
        if 'date' in old_df.columns and 'date' in new_labeled.columns:
            existing_dates = old_df['date'].unique()
            new_date = new_labeled['date'].iloc[0]
            
            if new_date in existing_dates:
                print(f"\n⚠ WARNING: Date {new_date} already exists in master!")
                print(f"  This will replace {len(old_df[old_df['date'] == new_date])} existing articles from that date.")
        
        combined = pd.concat([old_df, new_labeled], ignore_index=True)
    else:
        combined = new_labeled
    
    # Remove duplicates (keep newest = last occurrence)
    initial_count = len(combined)
    combined = combined.drop_duplicates(subset=['url'], keep='last')
    duplicates_removed = initial_count - len(combined)
    
    if duplicates_removed > 0:
        print(f"  Removed {duplicates_removed} duplicate URLs")
    
    # Save
    combined.to_csv(OUTPUT, index=False, encoding='utf-8-sig')
    
    print(f"\n✓ Successfully merged labels!")
    print(f"  Total labeled articles: {len(combined)}")
    print(f"  Saved to: {OUTPUT}")
    
    # Show date distribution
    if 'date' in combined.columns:
        print(f"\nDate distribution:")
        print(combined['date'].value_counts().sort_index())
    
    # Show reward distribution
    print(f"\nReward distribution:")
    print(combined['reward'].value_counts().sort_index())
    
    return True


    # Backup existing labels
    if os.path.exists(OLD_LABELS):
        # Try multiple encodings
        encodings_to_try = ['utf-8-sig', 'cp949', 'euc-kr', 'utf-8']
        old_df = None
        for enc in encodings_to_try:
            try:
                old_df = pd.read_csv(OLD_LABELS, encoding=enc)
                print(f"✓ Loaded existing labels with encoding: {enc}")
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        if old_df is None:
            print(f"⚠ Could not read {OLD_LABELS} with any encoding, treating as empty")
            old_df = pd.DataFrame()
        else:
            old_df.to_csv(BACKUP, index=False, encoding='utf-8-sig')
            print(f"✓ Backed up existing labels to {BACKUP}")
            print(f"  Old labeled data: {len(old_df)} articles")
    else:
        old_df = pd.DataFrame()
        print("No existing labels found. Creating new file.")
    
    # Auto-detect latest labeled file (Check both data dir and root dir)
    new_labels_paths = [
        'data/labels/articles_to_label_*.csv',
        'articles_to_label_*.csv'  # Check root directory (common upload location)
    ]
    
    NEW_LABELS = None
    files_found = []
    
    for path in new_labels_paths:
        matches = glob.glob(path)
        files_found.extend(matches)
        
    if files_found:
        NEW_LABELS = max(files_found, key=os.path.getmtime)
    
    if not NEW_LABELS or not os.path.exists(NEW_LABELS):
        print(f"Error: No labeled file found matching 'articles_to_label_*.csv'!")
        print("Please upload your labeled file to the file system.")
        return False
    
    print(f"  Found labeled file: {NEW_LABELS}")
    
    # Auto-detect corresponding raw file
    # Extract date from labeled file (e.g., 20260116)
    import re
    date_match = re.search(r'(\d{8})', os.path.basename(NEW_LABELS))
    if date_match:
        date_str = date_match.group(1)
        RAW_NEW = f'data/articles_raw/articles_naver_api_{date_str}.csv'
    else:
        # Fallback: find latest raw file
        RAW_NEW = find_latest_file('data/articles_raw/articles_naver_api_*.csv')
    
    if not RAW_NEW or not os.path.exists(RAW_NEW):
        print(f"Error: Raw data file not found!")
        print(f"Expected: {RAW_NEW if RAW_NEW else 'articles_naver_api_YYYYMMDD.csv'}")
        return False
    
    print(f"  Found raw data: {RAW_NEW}")
    
    # Load new labeled data (try multiple encodings)
    encodings = ['utf-8-sig', 'cp949', 'euc-kr', 'utf-8']
    new_labeled = None
    for enc in encodings:
        try:
            new_labeled = pd.read_csv(NEW_LABELS, encoding=enc)
            print(f"  Loaded labeled file with encoding: {enc}")
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    if new_labeled is None:
        print("Error: Could not read labeled file with any encoding!")
        return False
    
    # Check if reward column is filled
    if new_labeled['reward'].isna().all() or (new_labeled['reward'] == '').all():
        print("Error: reward column is empty in new labels file!")
        print("Please complete labeling first.")
        return False
    
    # Load raw data (try multiple encodings)
    raw_new = None
    for enc in encodings:
        try:
            raw_new = pd.read_csv(RAW_NEW, encoding=enc)
            print(f"  Loaded raw data with encoding: {enc}")
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    if raw_new is None:
        print("Error: Could not read raw data file with any encoding!")
        return False
    
    # Merge: keep all columns from raw data, update reward from labeled data
    merged_new = raw_new.merge(
        new_labeled[['url', 'reward']], 
        on='url', 
        how='left',
        suffixes=('_old', '')
    )
    
    # Drop duplicate reward column if exists
    if 'reward_old' in merged_new.columns:
        merged_new = merged_new.drop(columns=['reward_old'])
    
    # Only keep rows with valid reward
    merged_new = merged_new[merged_new['reward'].notna() & (merged_new['reward'] != '')]
    
    print(f"  New labeled data: {len(merged_new)} articles")
    
    # Combine with old data
    if not old_df.empty:
        # Ensure both have same columns
        common_cols = list(set(old_df.columns) & set(merged_new.columns))
        old_df = old_df[common_cols]
        merged_new = merged_new[common_cols]
        
        combined = pd.concat([old_df, merged_new], ignore_index=True)
    else:
        combined = merged_new
    
    # Remove duplicates (keep newest)
    combined = combined.drop_duplicates(subset=['url'], keep='last')
    
    # Save
    combined.to_csv(OUTPUT, index=False, encoding='utf-8-sig')
    
    print(f"\n✓ Successfully merged labels!")
    print(f"  Total labeled articles: {len(combined)}")
    print(f"  Saved to: {OUTPUT}")
    
    # Show reward distribution
    print(f"\nReward distribution:")
    print(combined['reward'].value_counts().sort_index())
    
    return True

if __name__ == "__main__":
    print("="*60)
    print("Merging Labeled Data")
    print("="*60 + "\n")
    
    success = merge_labels()
    
    if success:
        print("\n" + "="*60)
        print("NEXT STEP: Run model training")
        print("  python scripts/train_lgbm_model.py")
        print("="*60)
