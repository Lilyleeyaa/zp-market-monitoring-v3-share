"""
External Weekly Dashboard - 외부용 (경쟁사 제외)
"""
import streamlit as st
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.simple_auth import authenticate, get_current_user
from scripts.config import get_excluded_keywords, should_exclude_article

# 페이지 설정
st.set_page_config(
    page_title="ZP Market Monitoring - MNC_BD",
    page_icon="📊",
    layout="wide"
)

# 인증 (내부/외부 모두 가능)
email, access_level = authenticate(mode='weekly')

# [Admin/Internal Only] Show external email list for verification
if access_level == 'internal':
    with st.sidebar.expander("📧 External Emails (Internal Only)"):
        try:
            # Construct path to external_users.txt relative to this script
            user_list_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'auth', 'external_users.txt')
            if os.path.exists(user_list_path):
                with open(user_list_path, 'r', encoding='utf-8') as f:
                    emails = f.read()
                st.text_area("Registered Emails", emails, height=300)
            else:
                st.warning("external_users.txt not found")
        except Exception as e:
            st.error(f"Error loading emails: {e}")

# 대시보드 메인 코드
# --- Data Loading Logic (Synced with Internal) ---
import pandas as pd
import glob
import datetime
from datetime import datetime, timedelta

def get_weekly_date_range():
    today = datetime.now().date()
    start_date = today - timedelta(days=7)
    return start_date, today

@st.cache_data(ttl=60, show_spinner=False)
def load_data():
    try:
        # Path relative to dashboards/ folder
        base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "articles_raw")
        if not os.path.exists(base_dir):
            base_dir = "../data/articles_raw"
            
        ranked_files = sorted(glob.glob(os.path.join(base_dir, "articles_ranked_*.csv")))
        if not ranked_files:
            return pd.DataFrame(), "No Data"
            
        latest_file = ranked_files[-1]
        df = pd.read_csv(latest_file, encoding='utf-8-sig')
        
        # Date conversion
        if 'published_date' in df.columns:
            df['published_date'] = pd.to_datetime(df['published_date']).dt.date
            
        return df, os.path.basename(latest_file)
    except Exception as e:
        return pd.DataFrame(), str(e)

df, filename = load_data()

if df.empty:
    st.error(f"데이터를 불러올 수 없습니다: {filename}")
    st.stop()


# --- Top Control Bar (Filters) ---
st.markdown("### 🔍 Filters & Settings")

f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns([1.5, 2, 2, 2, 1.5])

with f_col1:
    lang_opt = st.selectbox("🌐 Language", ["Korean", "English"], index=0)
    use_english = (lang_opt == "English")

with f_col2:
    start_week, end_week = get_weekly_date_range()
    if 'published_date' in df.columns:
        min_date = df['published_date'].min()
        max_date = df['published_date'].max()
        default_start = max(min_date, start_week) if min_date else start_week
        default_end = min(max_date, end_week) if max_date else end_week
        date_range = st.date_input("📅 Date Range", [default_start, default_end])
        if isinstance(date_range, list) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date, end_date = default_start, default_end
    else:
        start_date, end_date = None, None

with f_col3:
    all_categories = sorted(df['category'].dropna().unique().tolist())
    selected_categories = st.multiselect("📂 Category", all_categories, default=[])

with f_col4:
    sort_opts = ["AI Relevance", "Latest Date", "Category"]
    sort_mode = st.selectbox("📊 Sort By", sort_opts)

# --- Logic Phase 1: Global Exclusion (External Security) ---
excluded_keywords = get_excluded_keywords(access_level='external')
df_safe = df.copy()

if excluded_keywords:
    pattern = '|'.join(excluded_keywords)
    mask_sensitive = (
        df_safe['title'].str.contains(pattern, case=False, na=False) |
        df_safe['summary'].fillna('').str.contains(pattern, case=False, na=False) | 
        df_safe['keywords'].fillna('').str.contains(pattern, case=False, na=False)
    )
    df_safe = df_safe[~mask_sensitive]

# --- Logic Phase 2: User Filters ---
mask = pd.Series([True] * len(df_safe))
if start_date and end_date:
    mask = (df_safe['published_date'] >= start_date) & (df_safe['published_date'] <= end_date)

if selected_categories:
    mask = mask & (df_safe['category'].isin(selected_categories))

df_filtered = df_safe[mask]

# --- Logic Phase 3: Quota & Rank (Re-calculate Top 20 from Safe Pool) ---
if 'final_score' not in df_filtered.columns and 'lgbm_score' in df_filtered.columns:
    df_filtered['final_score'] = df_filtered['lgbm_score']

# Sort by Score for selection
df_sorted = df_filtered.sort_values(by='final_score', ascending=False)

# Quota Logic (Top 4 per category)
balanced_selection = []
selected_urls = set()
categories = df_sorted['category'].unique()

for cat in ['Distribution', 'Client', 'BD', 'Zuellig']:
    if cat in categories:
        cat_articles = df_sorted[df_sorted['category'] == cat].head(4)
        balanced_selection.append(cat_articles)
        selected_urls.update(cat_articles['url'].tolist())

if balanced_selection:
    df_balanced = pd.concat(balanced_selection)
else:
    df_balanced = pd.DataFrame()

# Backfill remaining slots
remaining_slots = 20 - len(df_balanced)
if remaining_slots > 0:
    remaining_candidates = df_sorted[~df_sorted['url'].isin(selected_urls)]
    df_fill = remaining_candidates.head(remaining_slots)
    df_visible = pd.concat([df_balanced, df_fill])
else:
    df_visible = df_balanced.head(20)

# Final Sorting for Display
if sort_mode == "AI Relevance":
    if 'final_score' in df_visible.columns:
        df_visible = df_visible.sort_values('final_score', ascending=False)
elif sort_mode == "Category":
    df_visible = df_visible.sort_values('category', ascending=True)
else:
    df_visible = df_visible.sort_values('published_date', ascending=False)

# Metrics
st.markdown(f"**Total Articles:** {len(df_visible)}")
st.divider()

# --- Display Logic (Tiffany Blue Theme - Exact Match with Internal) ---
st.markdown("""
<style>
    /* Global Background & Font */
    .stApp {
        background-color: #F0F8F8; /* Very Light Teal/Grey */
    }
    
    /* Header/Title */
    h1 {
        color: #006666 !important; /* Deep Teal */
    }
    
    /* Article Card Styles */
    .article-card {
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
        background-color: #ffffff; /* White card */
        border-left: 5px solid #0ABAB5; /* Tiffany Blue Accent */
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    .article-title {
        font-size: 18px;
        font-weight: bold;
        color: #008080; /* Teal */
        text-decoration: none;
    }
    .article-title:hover {
        color: #0ABAB5; /* Tiffany Blue on Hover */
        text_decoration: underline;
    }
    
    .article-meta {
        font-size: 12px;
        color: #888;
    }
    
    .category-badge {
        background-color: #E0F2F1; /* Light Teal background */
        color: #00695C; /* Dark Teal text */
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 500;
        margin-left: 5px;
    }

    .article-summary {
        font-size: 14px;
        color: #444;
        margin-top: 8px;
        line-height: 1.6;
    }
    
    /* Button Styles */
    .stButton>button {
        background-color: #0ABAB5 !important;
        color: white !important;
        border: none;
    }
</style>
""", unsafe_allow_html=True)

if df_visible.empty:
    st.warning("표시할 뉴스가 없습니다.")
else:
    # Group by Category for Display (Same as Internal)
    category_priority = ['Distribution', 'BD', 'Client', 'Zuellig']
    all_categories = df_visible['category'].unique()
    sorted_categories = [cat for cat in category_priority if cat in all_categories]
    sorted_categories += sorted([cat for cat in all_categories if cat not in category_priority])
    
    for category_name in sorted_categories:
        category_df = df_visible[df_visible['category'] == category_name]
        
        # Category Header
        st.markdown(f'''
        <div style="margin-top: 20px; margin-bottom: 15px;">
            <h3 style="font-size: 22px; color: #006666; border-bottom: 2px solid #0ABAB5; padding-bottom: 8px;">
                {category_name} <span style="color: #888; font-size: 18px;">({len(category_df)} articles)</span>
            </h3>
        </div>
        ''', unsafe_allow_html=True)
        
        for _, row in category_df.iterrows():
            title = row['title']
            summary = row.get('summary', '')
            date = row.get('published_date', '')
            # keywords = row.get('keywords', '') # Optional: Add keywords if needed
            url = row.get('url', '#')
            
            # Article Card (Exact Match)
            st.markdown(f'''
            <div class="article-card">
                <div style="font-size: 16px; line-height: 1.5; color: #333;">
                    <a href="{url}" target="_blank" style="font-size: 18px; font-weight: bold; text-decoration: none; color: #008080;">{title}</a>
                    <span style="color: #666;"> | {date}</span>
                </div>
                <div style="font-size: 16px; margin-top: 8px; color: #555; line-height: 1.6;">
                    {summary}
                </div>
            </div>
            ''', unsafe_allow_html=True)
