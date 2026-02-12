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
# --- Data Loading Logic ---
import pandas as pd
import glob
import datetime

@st.cache_data
def load_data():
    try:
        # Path relative to dashboards/ folder
        base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "articles_raw")
        
        # Priority 1: Ranked files
        ranked_files = glob.glob(os.path.join(base_dir, "articles_ranked_*.csv"))
        if not ranked_files:
            return pd.DataFrame(), "No Data"
            
        target_file = max(ranked_files, key=os.path.getctime)
        df = pd.read_csv(target_file)
        
        # Date conversion
        if 'published_date' in df.columns:
            df['published_date'] = pd.to_datetime(df['published_date']).dt.date
            
        return df, os.path.basename(target_file)
    except Exception as e:
        return pd.DataFrame(), str(e)

df, filename = load_data()

if df.empty:
    st.error(f"데이터를 불러올 수 없습니다: {filename}")
    st.stop()

# --- Filtering Logic ---
# 1. Select Top 20 (Same as Internal)
if 'is_top20' in df.columns:
    df_visible = df[df['is_top20'] == True]
elif 'final_score' in df.columns:
    df_visible = df.nlargest(20, 'final_score')
else:
    df_visible = df.head(20)

# 2. Apply External Filter (Hide Sensitive Keywords)
# Get exclusion list for 'external' role
excluded_keywords = get_excluded_keywords(access_level='external')

if excluded_keywords:
    pattern = '|'.join(excluded_keywords)
    # Check Title + Summary + Keywords for sensitive terms
    mask_sensitive = (
        df_visible['title'].str.contains(pattern, case=False, na=False) |
        df_visible['summary'].fillna('').str.contains(pattern, case=False, na=False) | 
        df_visible['keywords'].fillna('').str.contains(pattern, case=False, na=False)
    )
    # Filter OUT sensitive articles
    df_visible = df_visible[~mask_sensitive]

st.success(f"최신 뉴스 업데이트 완료 ({len(df_visible)}건)")

# --- Display Logic (Tiffany Blue Theme) ---
st.markdown("""
<style>
    .article-card {
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
        background-color: #ffffff;
        border-left: 5px solid #0ABAB5; /* Tiffany Blue */
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .category-badge {
        background-color: #E0F2F1;
        color: #00695C;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
    }
    a {
        text-decoration: none;
        color: #008080 !important;
        font-weight: bold;
        font-size: 18px;
    }
    a:hover {
        color: #0ABAB5 !important;
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)

if df_visible.empty:
    st.warning("표시할 뉴스가 없습니다.")
else:
    # Sort by Score or Date
    if 'final_score' in df_visible.columns:
        df_visible = df_visible.sort_values('final_score', ascending=False)
    
    for _, row in df_visible.iterrows():
        title = row['title']
        summary = row.get('summary', '')
        date = row.get('published_date', '')
        category = row.get('category', 'News')
        url = row.get('url', '#')
        
        st.markdown(f"""
        <div class="article-card">
            <div>
                <span class="category-badge">{category}</span>
                <span style="color: #888; font-size: 12px; margin-left: 10px;">{date}</span>
            </div>
            <div style="margin-top: 8px;">
                <a href="{url}" target="_blank">{title}</a>
            </div>
            <div style="margin-top: 8px; color: #555; font-size: 14px; line-height: 1.6;">
                {summary}
            </div>
        </div>
        """, unsafe_allow_html=True)
