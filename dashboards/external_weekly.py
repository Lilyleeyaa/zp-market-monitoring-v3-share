"""
External Weekly Dashboard - 외부용 (경쟁사 제외)
"""
import streamlit as st
import sys
import os
import requests
import json
import time

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


# --- Constants ---
KEYWORD_MAPPING = {
    'B형간염': 'Hepatitis B',
    'C형간염': 'Hepatitis C',
    'CDMO': 'CDMO',
    'CMD': 'CMD',
    'CSO': 'CSO',
    'CAR-T': 'CAR-T',
    'GLP-1': 'GLP-1',
    'ADC': 'ADC',
    'HIV': 'HIV',
    'M&A': 'M&A',
    'mRNA': 'mRNA',
    'R&D': 'R&D',
    'AI': 'AI',
    '가다실': 'Gardasil',
    '고혈압': 'Hypertension',
    '골다공증': 'Osteoporosis',
    '국가필수예방접종': 'NIP',
    '금연치료': 'Smoking Cessation',
    '당뇨병': 'Diabetes',
    '대상포진': 'Shingles',
    '독감': 'Flu',
    '마약류': 'Narcotics',
    '만성질환': 'Chronic Disease',
    '면역항암제': 'Immuno-oncology',
    '바이오시밀러': 'Biosimilar',
    '백신': 'Vaccine',
    '비만': 'Obesity',
    '산정특례': 'Special Calc',
    '상급종합병원': 'Tertiary Hosp',
    '신약': 'New Drug',
    '심혈관': 'Cardiovascular',
    '암': 'Cancer',
    '약가': 'Drug Price',
    '약국': 'Pharmacy',
    '연말정산': 'Tax Adj',
    '이상지질혈증': 'Dyslipidemia',
    '임상': 'Clinical Trial',
    '자가면역칠환': 'Autoimmune',
    '제네릭': 'Generic',
    '종양': 'Tumor',
    '중증질환': 'Severe Disease',
    '치매': 'Dementia',
    '탈모': 'Hair Loss',
    '특허': 'Patent',
    '폐암': 'Lung Cancer',
    '품절': 'Out of Stock',
    '항암제': 'Anticancer',
    '헬스케어': 'Healthcare',
    '협회': 'Association',
    '희귀질환': 'Rare Disease'
}

# ====================
# Translation Components (Copied from Internal)
# ====================
EXTRA_GLOSSARY = {
    "데일리팜": "Daily Pharm",
    "약사공론": "Yaksagongron",
    "메디파나": "Medipana",
    "의학신문": "Medical Times",
    "청년의사": "Doctor's News",
    "뉴스1": "News1",
    "뉴시스": "Newsis",
    "처방권 진입": "Entry into Prescription Market",
    "처방권": "Prescription Market",
    "급여 확대": "Reimbursement Expansion",
    "급여": "Reimbursement",
    "비급여": "Non-Reimbursement",
    "약가 인하": "Price Cut",
    "약가": "Drug Price",
    "제네릭": "Generic",
    "오리지널": "Original",
    "품절": "Out of Stock",
    "공급부족": "Supply Shortage",
    "공급중단": "Supply Disruption",
    "임상": "Clinical Trial",
    "허가": "Approval",
    "식약처": "MFDS",
    "심평원": "HIRA",
    "건보공단": "NHIS",
    "앱글리스": "Ebglyss",
    "엡글리스": "Ebglyss",
    "상급종합병원": "Tertiary General Hospital",
    "건기식": "Health Functional Food",
    "쥴릭": "Zuellig", 
    "쥴릭파마": "Zuellig Pharma",
    "쥴릭코리아": "Zuellig Pharma Korea",
    "쥴릭 파마": "Zuellig Pharma",
    "니코틴엘": "Nicotinell",
}

import re # For robust replacement

# API Key Security: Load from Streamlit Secrets or Environment Variable
try:
    GENAI_API_KEY = st.secrets["GENAI_API_KEY"]
except:
    import os
    GENAI_API_KEY = os.getenv("GENAI_API_KEY", "")

if not GENAI_API_KEY:
    # Placeholder for local development if secrets not set (Translation will fail gracefully)
    pass
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GENAI_API_KEY}"

@st.cache_data(show_spinner=False)
def translate_text(text, target='en'):
    # Cache Version: v4 (Force Reload for Nicotinell Regex Fix)
    if not text: return ""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 1. Try Gemini First (Better Context)
            full_glossary = {**KEYWORD_MAPPING, **EXTRA_GLOSSARY}
            glossary_context = "\n".join([f"- {k}: {v}" for k, v in full_glossary.items()])
            
            prompt = f"""
            You are a professional pharmaceutical translator. 
            Translate the following Korean text to English.
            
            Rules:
            1. Maintain professional industry terminology.
            2. Use the specific glossary below for strict term matching:
            {glossary_context}
            
            Text to translate:
            "{text}"
            
            Output only the translated English text, no explanations.
            """
            
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            headers = {'Content-Type': 'application/json'}
            response = requests.post(GEMINI_API_URL, headers=headers, data=json.dumps(payload), timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and result['candidates']:
                    translated = result['candidates'][0]['content']['parts'][0]['text'].strip()
                    # Post-processing fix
                    translated = re.sub(r'nicotine\s*l', 'Nicotinell', translated, flags=re.IGNORECASE)
                    return translated
            elif response.status_code == 429:
                time.sleep(2)
                continue
            else:
                break
        except Exception as e:
            break
            
    # 2. Fallback to Google Translator (Deep Translator)
    try:
        from deep_translator import GoogleTranslator
        processed_text = text
        full_glossary = {**KEYWORD_MAPPING, **EXTRA_GLOSSARY}
        sorted_terms = sorted(full_glossary.keys(), key=len, reverse=True)
        for kr_term in sorted_terms:
            if kr_term in processed_text:
                processed_text = processed_text.replace(kr_term, full_glossary[kr_term])
        translated = GoogleTranslator(source='ko', target=target).translate(processed_text)
        translated = re.sub(r'nicotine\s*l', 'Nicotinell', translated, flags=re.IGNORECASE)
        return translated
    except:
        return text

@st.cache_data(show_spinner=False)
def translate_article_batch(title, summary, keywords):
    if not title and not summary: return title, summary, keywords
    combined_text = f"Title: {title}\nSummary: {summary}\nKeywords: {keywords}"
    result_text = translate_text(combined_text)
    
    t_title, t_summary, t_keywords = title, summary, keywords
    try:
        lines = result_text.split('\n')
        for line in lines:
            if line.startswith("Title:") or line.startswith("Title :"):
                t_title = line.split(":", 1)[1].strip()
            elif line.startswith("Summary:") or line.startswith("Summary :"):
                t_summary = line.split(":", 1)[1].strip()
            elif line.startswith("Keywords:") or line.startswith("Keywords :"):
                t_keywords = line.split(":", 1)[1].strip()
    except:
        pass
    return t_title, t_summary, t_keywords


# --- Top Control Bar (Filters) ---
st.markdown("### 🔍 Filters & Settings")

f_col1, f_col2, f_col3, f_col4, f_col5, f_col6 = st.columns([1.5, 2, 2, 2, 2, 1.5])

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

# Dynamic Keyword Filter Preparation
temp_mask = pd.Series([True] * len(df))

# Explicit Exclusion for External Dashboard (User Request)
EXCLUDED_KEYWORDS_EXT = ["고양이"]
if EXCLUDED_KEYWORDS_EXT:
    pat_ext = '|'.join(EXCLUDED_KEYWORDS_EXT)
    temp_mask = temp_mask & ~(
        df['title'].str.contains(pat_ext, case=False, na=False) |
        df['summary'].fillna('').str.contains(pat_ext, case=False, na=False) |
        df['keywords'].fillna('').str.contains(pat_ext, case=False, na=False)
    )

if start_date and end_date:
    temp_mask = temp_mask & (df['published_date'] >= start_date) & (df['published_date'] <= end_date)

if selected_categories:
    temp_mask = temp_mask & (df['category'].isin(selected_categories))

# Apply excluded keywords FIRST to the kw extraction source
excluded_keywords_ext = get_excluded_keywords(access_level='external')
if excluded_keywords_ext:
    pat = '|'.join(excluded_keywords_ext)
    safe_kw_mask = ~(
        df['title'].str.contains(pat, case=False, na=False) |
        df['summary'].fillna('').str.contains(pat, case=False, na=False) |
        df['keywords'].fillna('').str.contains(pat, case=False, na=False)
    )
    df_kw_source = df[temp_mask & safe_kw_mask]
else:
    df_kw_source = df[temp_mask]

with f_col4:
    available_keywords = []
    if 'keywords' in df_kw_source.columns:
        # Extract individual keywords if they are comma-separated strings
        all_kws = []
        for k_str in df_kw_source['keywords'].dropna().astype(str):
            for k in k_str.split(','):
                k = k.strip()
                if k: all_kws.append(k)
        available_keywords = sorted(list(set(all_kws)))
    
    if use_english:
        keyword_options = [KEYWORD_MAPPING.get(k, k) for k in available_keywords]
        en_to_kr = {KEYWORD_MAPPING.get(k, k): k for k in available_keywords}
    else:
        keyword_options = available_keywords
    
    selected_keywords_display = st.multiselect("🔑 Keyword", keyword_options, default=[])
    
    if use_english:
        selected_keywords = [en_to_kr.get(k, k) for k in selected_keywords_display]
    else:
        selected_keywords = selected_keywords_display

with f_col5:
    sort_opts = ["AI Relevance", "Latest Date", "Category", "Keyword"]
    sort_mode = st.selectbox("📊 Sort By", sort_opts)

with f_col6:
    # Changed to Checkbox for "AI Only" matching Internal
    show_ai_only = st.checkbox("🤖 AI Only", value=True, help="Show only AI recommended articles")

# --- Logic Phase 1: Global Exclusion (External Security) ---
excluded_keywords = get_excluded_keywords(access_level='external')

# User Request: Force Exclude 'Cat' in External Dashboard
if "고양이" not in excluded_keywords:
    excluded_keywords.append("고양이")

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

if selected_keywords:
    # Check if ANY of the selected keywords are present in the article's keyword string
    # Simple 'isin' doesn't work for comma-separated, so we use string verify
    # But for performance and standard logic:
    # Construct regex or use apply. Internal uses isin directly if normalized? 
    # Internal code was: mask = mask & (df['keywords'].isin(selected_keywords))
    # This implies Internal assumes single keyword or exact match? 
    # Actually internal loader likely didn't explode keywords?
    # Let's use str.contains logic for safety with partial matches
    kw_pattern = '|'.join([k for k in selected_keywords])
    mask = mask & (df_safe['keywords'].fillna('').str.contains(kw_pattern, na=False))

df_filtered = df_safe[mask]

# --- Logic Phase 3: Quota & Rank ---
if 'final_score' not in df_filtered.columns and 'lgbm_score' in df_filtered.columns:
    df_filtered['final_score'] = df_filtered['lgbm_score']

# Sort by Score for selection
df_sorted = df_filtered.sort_values(by='final_score', ascending=False)

# Quota Logic (Top 4 per category) OR Show All
if show_ai_only:
    # --- Strict AI Mode: Limit to Top 20 ---
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
else:
    # --- Show All Mode ---
    # Just show all filtered articles (Competitors already excluded in Phase 1)
    df_visible = df_sorted

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
    
    .keyword-tag {
        background-color: #f1f3f4;
        color: #5f6368;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 11px;
        margin-right: 5px;
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
    # Display Articles by Category matching Internal Style
    # Priority: Zuellig -> Distribution -> BD -> Client -> Others
    category_priority = ['Zuellig', 'Distribution', 'BD', 'Client']
    all_categories = df_visible['category'].unique()
    
    # Sort categories forcing Zuellig first
    sorted_categories = [cat for cat in category_priority if cat in all_categories]
    sorted_categories += sorted([cat for cat in all_categories if cat not in category_priority])
    
    for category_name in sorted_categories:
        category_df = df_visible[df_visible['category'] == category_name]
        
        if category_df.empty:
            continue
            
        # Clean Header (No border, matching Internal style)
        st.markdown(f"""
        <div style="margin-top: 20px; padding-bottom: 5px;">
            <span style="font-size: 24px; font-weight: bold; color: #006666;">{category_name}</span>
            <span style="font-size: 16px; color: #666; margin-left: 10px;">({len(category_df)} articles)</span>
        </div>
        """, unsafe_allow_html=True)
        
        for _, row in category_df.iterrows():
            title = row['title']
            summary = row.get('summary', '')
            date = row.get('published_date', '')
            keywords = row.get('keywords', '')
            url = row.get('url', '#')
            
            # --- FAILSAFE EXCLUSION (User Request) ---
            # Check Original Korean
            if "고양이" in title or "고양이" in summary or "고양이" in keywords:
                continue

            # Translate if needed
            if use_english:
                title, summary, keywords_trans = translate_article_batch(title, summary, keywords)
                keywords = keywords_trans
                
                # Check Translated Text
                if "Cat" in title or "Cat" in summary:
                    continue
            
            # Internal Style: Title ... | Date | Keywords
            st.markdown(f'''
            <div class="article-card">
                <div style="font-size: 16px; line-height: 1.5; color: #333;">
                    <a href="{url}" target="_blank" style="font-size: 18px; font-weight: bold; text-decoration: none; color: #008080;">{title}</a>
                    <span style="color: #666; font-size: 12px;"> | {date} | {keywords}</span>
                </div>
                <div style="font-size: 16px; margin-top: 8px; color: #555; line-height: 1.6;">
                    {summary}
                </div>
            </div>
            ''', unsafe_allow_html=True)
