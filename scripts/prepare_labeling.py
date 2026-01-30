"""
Prepare articles for manual labeling
Extracts recent articles from crawled data for user to add reward labels
"""
import pandas as pd
from datetime import datetime, timedelta
import os
import glob

# Configuration
def find_latest_file(pattern):
    """Find the most recent file matching the pattern"""
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)

# Auto-detect latest crawled data
INPUT_FILE = find_latest_file('data/articles_raw/articles_naver_api_*.csv')
if not INPUT_FILE:
    print("Error: No crawled data found in data/articles_raw/")
    print("Expected file pattern: articles_naver_api_YYYYMMDD.csv")
    exit(1)

print(f"Using crawled data: {INPUT_FILE}")

OUTPUT_DIR = 'data/labels'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load newest articles file
new_articles = pd.read_csv(INPUT_FILE, encoding='utf-8-sig')

# Filter for last 45 days (full dataset for initial labeling)
period_ago = datetime.now() - timedelta(days=45)
new_articles['published_date_dt'] = pd.to_datetime(new_articles['published_date'])
this_period = new_articles[new_articles['published_date_dt'] >= period_ago].copy()

print(f"Total articles in file: {len(new_articles)}")
print(f"Last 45 days articles: {len(this_period)}")
print(f"Date range: {this_period['published_date'].min()} to {this_period['published_date'].max()}")

# Create simplified labeling file
labeling_df = this_period[['date', 'category', 'published_date', 'site_name', 'url', 'title', 'summary', 'region', 'score_ag', 'keywords']].copy()

# Add empty reward column for manual labeling
labeling_df['reward'] = ''

# Sort by score_ag (high to low) to prioritize labeling important articles
labeling_df = labeling_df.sort_values('score_ag', ascending=False)

# Save to labeling file (with today's date)
today_str = datetime.now().strftime('%Y%m%d')
output_file = f'data/labels/articles_to_label_{today_str}.csv'
labeling_df.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"\nCreated labeling file: {output_file}")
print(f"Total articles to label: {len(labeling_df)}")
print("\nTop 10 articles by score_ag:")
for idx, row in labeling_df.head(10).iterrows():
    print(f"  [{row['score_ag']:.1f}] [{row['category']}] {row['title'][:70]}")

print("\n" + "="*80)
print("NEXT STEP: Please open the CSV file and fill in the 'reward' column")
print("  - reward = 0: Not important / Not relevant")
print("  - reward = 1: Important / Relevant article")
print("="*80)
