"""
Daily News Crawler - For Agency Comparison
============================================
- Crawls YESTERDAY ONLY (00:00 ~ 23:59)
- Uses keywords from config/keywords.yaml (daily section)
- Purpose: Compare results with agency daily crawl
"""

import datetime
import os
import pandas as pd
import yaml
import requests
import time
import html
from crawl_naver_news_api import (
    get_naver_news_api,
    parse_naver_api_date,
    normalize_title,
    is_healthcare_related,
    is_similar_to_seen,
    get_full_content,
    summarize_text,
    calculate_score_by_category,
    NAVER_CLIENT_ID,
    NAVER_CLIENT_SECRET
)

# Load daily keywords from config
def load_daily_keywords():
    """Load daily keywords from config/keywords.yaml"""
    config_path = os.path.join('config', 'keywords.yaml')
    
    if not os.path.exists(config_path):
        print(f"ERROR: {config_path} not found!")
        return []
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    daily_keywords = config.get('daily', [])
    print(f"Loaded {len(daily_keywords)} daily keywords from config")
    
    return daily_keywords


def get_yesterday_date_range():
    """Get yesterday's date range (00:00 ~ 23:59)"""
    today = datetime.datetime.now()
    yesterday = today - datetime.timedelta(days=1)
    
    start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=0)
    
    return start_date, end_date


def main():
    print("=" * 60)
    print(">>> Daily News Crawler (Agency Comparison)")
    print("=" * 60)
    
    # Get yesterday's date range
    START_DATE, END_DATE = get_yesterday_date_range()
    print(f"\nCrawling Period: {START_DATE.strftime('%Y-%m-%d')} (Yesterday)")
    print(f"Purpose: Agency comparison validation")
    
    # Load daily keywords
    daily_keywords = load_daily_keywords()
    
    if not daily_keywords:
        print("\nERROR: No daily keywords found in config/keywords.yaml!")
        print("Please check config/keywords.yaml and ensure 'daily:' section exists.")
        return
    
    print(f"Keywords to search: {len(daily_keywords)}")
    print(f"Expected time: ~1-2 minutes\n")
    
    all_articles = []
    seen_urls = set()
    seen_titles = set()
    
    start_time = time.time()
    
    # Crawl with daily keywords
    for idx, keyword in enumerate(daily_keywords, 1):
        keyword_start = time.time()
        print(f"  [{idx}/{len(daily_keywords)}] '{keyword}'... ", end='', flush=True)
        
        # Get articles via API
        articles = get_naver_news_api(keyword, display=5)
        
        new_count = 0
        for art in articles:
            # Check URL duplicate
            if art['url'] in seen_urls:
                continue
            
            # Check normalized title duplicate
            normalized_title = normalize_title(art['title'])
            if normalized_title in seen_titles:
                continue
            
            # Healthcare domain check
            article_text = art['title'] + " " + art['summary']
            if not is_healthcare_related(article_text):
                continue
            
            # Check title similarity
            if is_similar_to_seen(art['title'], all_articles):
                continue
            
            # Keyword relevance check
            if keyword not in art['title'] and keyword not in art['summary']:
                continue
            
            # Recruitment filter
            if '채용' in art['title'] or '채용' in art['summary']:
                continue
            
            # Date filtering - CRITICAL for daily crawl
            pub_date_str = art.get('published_date', '')
            try:
                import email.utils
                pub_date = email.utils.parsedate_to_datetime(pub_date_str)
                pub_date_naive = pub_date.replace(tzinfo=None)
                
                # Only include articles from yesterday
                if not (START_DATE <= pub_date_naive <= END_DATE):
                    continue
            except:
                pass
            
            # Add to collection
            seen_urls.add(art['url'])
            seen_titles.add(normalized_title)
            
            art['body'] = ""
            art['summary'] = art['summary']
            art['category'] = 'Daily'  # Mark as daily
            art['search_keyword'] = keyword
            
            all_articles.append(art)
            new_count += 1
            
            if new_count >= 10:  # Limit per keyword
                break
        
        elapsed = time.time() - keyword_start
        print(f" OK - {new_count} new articles ({elapsed:.1f}s)")
        
        time.sleep(0.1)
    
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"[COMPLETED] Collected {len(all_articles)} unique articles")
    print(f"Total time: {total_time:.1f} seconds")
    print("=" * 60)
    
    # Prepare DataFrame
    if all_articles:
        df = pd.DataFrame(all_articles)
        
        # Process dates
        df['published_date'] = df['published_date'].apply(parse_naver_api_date)
        df['date'] = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # Add region
        df['region'] = 'local'
        
        # Calculate scores
        df['keywords_matched'] = df['search_keyword']
        df['score_ag'] = 5  # Default score for daily articles
        
        # Healthcare filter
        print(f"\n[FILTER] Applying healthcare domain filter...")
        before_count = len(df)
        df = df[df.apply(lambda row: is_healthcare_related(row['title'] + ' ' + row['summary']), axis=1)]
        after_count = len(df)
        print(f"[FILTER] Removed {before_count - after_count} unrelated articles ({before_count} → {after_count})")
        
        # Add empty columns for compatibility
        df['keywords'] = df['search_keyword']
        df['reward'] = ''
        df['rl_score'] = ''
        
        # Reorder columns
        df = df[['date', 'category', 'published_date', 'site_name', 'url', 'title', 'summary', 
                 'region', 'score_ag', 'keywords', 'reward', 'rl_score']]
        
        # Sort by date
        df = df.sort_values('published_date', ascending=False)
        
        # Save with daily prefix
        DATA_DIR = "data/articles_raw"
        os.makedirs(DATA_DIR, exist_ok=True)
        
        yesterday_str = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y%m%d')
        filename = f"articles_daily_{yesterday_str}.csv"
        filepath = os.path.join(DATA_DIR, filename)
        
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        print(f"\n[SAVED] Daily output file: {filepath}")
        print(f"\nTop 10 articles:")
        for idx, row in df.head(10).iterrows():
            print(f"  - {row['title'][:70]}")
        
        print(f"\n✅ Daily crawl completed! Ready for agency comparison.")
        
    else:
        print("\n[WARNING] No articles collected!")
        print("Please check your date range and keywords.")


if __name__ == "__main__":
    main()
