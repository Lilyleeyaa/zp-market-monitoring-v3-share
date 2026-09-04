"""
External Weekly Dashboard - Healthcare Market Intelligence (MNC / Client Edition)
- Authentication removed for frictionless client access
- Strict Competitor & Sensitive Keyword Exclusion Pipeline
- Featured Hero Article & Visual 2-Column Thumbnail Grid UI
"""

import streamlit as st
import pandas as pd
import sys
import os
import re
import requests
import json
import time
import glob
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Page configuration
st.set_page_config(
    page_title="ZP Market Monitoring - Strategic Intelligence",
    page_icon="📊",
    layout="wide"
)

# ====================
# Translation & Glossary
# ====================
EXTRA_GLOSSARY = {
    "데일리팜": "Daily Pharm", "약사공론": "Yaksagongron", "메디파나": "Medipana",
    "의학신문": "Medical Times", "청년의사": "Doctor's News", "뉴스1": "News1", "뉴시스": "Newsis",
    "처방권 진입": "Entry into Prescription Market", "처방권": "Prescription Market",
    "급여 확대": "Reimbursement Expansion", "급여": "Reimbursement", "비급여": "Non-Reimbursement",
    "약가 인하": "Price Cut", "약가": "Drug Price", "제네릭": "Generic", "오리지널": "Original",
    "품절": "Out of Stock", "공급부족": "Supply Shortage", "공급중단": "Supply Disruption",
    "임상": "Clinical Trial", "허가": "Approval", "식약처": "MFDS", "심평원": "HIRA", "건보공단": "NHIS",
    "앱글리스": "Ebglyss", "엡글리스": "Ebglyss", "상급종합병원": "Tertiary General Hospital",
    "건기식": "Health Functional Food", "쥴릭": "Zuellig", "쥴릭파마": "Zuellig Pharma",
    "쥴릭코리아": "Zuellig Pharma Korea", "쥴릭 파마": "Zuellig Pharma",
    "니코틴엘": "Nicotinell", "파슬로덱스": "Faslodex", "닥터레디": "Dr. Reddy's",
    "HK이노엔": "HK InnoN", "포시가": "Forxiga",
}

KEYWORD_MAPPING = {
    'B형간염': 'Hepatitis B', 'C형간염': 'Hepatitis C', 'CDMO': 'CDMO', 'CMD': 'CMD',
    'CSO': 'CSO', 'CAR-T': 'CAR-T', 'GLP-1': 'GLP-1', 'ADC': 'ADC', 'HIV': 'HIV',
    'M&A': 'M&A', 'mRNA': 'mRNA', 'R&D': 'R&D', 'AI': 'AI', '가다실': 'Gardasil',
    '고혈압': 'Hypertension', '골다공증': 'Osteoporosis', '국가필수예방접종': 'NIP',
    '금연치료': 'Smoking Cessation', '당뇨병': 'Diabetes', '대상포진': 'Shingles', '독감': 'Flu',
    '마약류': 'Narcotics', '만성질환': 'Chronic Disease', '면역항암제': 'Immuno-oncology',
    '바이오시밀러': 'Biosimilar', '백신': 'Vaccine', '비만': 'Obesity', '산정특례': 'Special Calc',
    '상급종합병원': 'Tertiary Hosp', '신약': 'New Drug', '심혈관': 'Cardiovascular', '암': 'Cancer',
    '약가': 'Drug Price', '약국': 'Pharmacy', '연말정산': 'Tax Adj', '이상지질혈증': 'Dyslipidemia',
    '임상': 'Clinical Trial', '자가면역질환': 'Autoimmune', '제네릭': 'Generic', '종양': 'Tumor',
    '중증질환': 'Severe Disease', '치매': 'Dementia', '탈모': 'Hair Loss', '특허': 'Patent',
    '폐암': 'Lung Cancer', '품절': 'Out of Stock', '항암제': 'Anticancer', '헬스케어': 'Healthcare',
    '협회': 'Association', '희귀질환': 'Rare Disease', '지피테라퓨틱스': 'ZP Therapeutics',
    '지피': 'ZP Therapeutics', '지피 테라퓨틱스': 'ZP Therapeutics'
}

# Competitor & Noise Filter Lists
COMPETITOR_KEYWORDS = [
    "지오영", "블루엠텍", "바로팜", "DKSH", "쉥커", "용마", "DHL", "위고비", "마운자로", "백제약품", "이지메디컴",
    "대웅", "종근당", "한미약품", "유한양행", "녹십자", "일동제약", "보령", "동아ST", "JW중외", "광동제약"
]

EXCLUDED_KEYWORDS = [
    "네이버 배송", "네이버 쇼핑", "네이버 페이", "도착보장", "쿠팡", "배달의민족", "요기요", "무신사", "컬리", "알리익스프레스", "테무",
    "부동산", "아파트", "전세", "매매", "청약", "건설", "금리 인하", "주식 개장", "환율", "코스피", "코스닥", "증시", "상한가", 
    "주가", "주식", "목표주가", "특징주", "급등", "여행", "호텔", "항공권", "예능", "드라마", "축구", "야구", "올림픽", "연예", "공연", "뮤지컬", "전시회", "관람",
    "이차전지", "배터리", "전기차", "반도체", "디스플레이", "조선", "철강", "채용", "신입사원", "공채", "원서접수", "고양이",
    "음식", "1인분", "문여는", "대전시장", "이뮨온시아", "에스바이오메딕스", "알테오젠"
]

PHARMA_CONTEXT_KEYWORDS = ["제약", "바이오", "신약", "임상", "헬스케어", "의료", "병원", "약국", "치료제", "백신", "진단", "물류", "유통", "공급"]
GENERIC_KEYWORDS = ["계약", "M&A", "인수", "합병", "투자", "제휴", "CJ"]

def is_noise_article(row):
    text = str(row.get('title', '')) + " " + str(row.get('summary', '')) + " " + str(row.get('content', ''))
    for exc in EXCLUDED_KEYWORDS:
        if exc in text: return True
    if "제약" in text:
        if any(x in text for x in ["시간 제약", "공간 제약", "물리적 제약", "발전 제약", "활동 제약"]):
            if not any(pk in text for pk in PHARMA_CONTEXT_KEYWORDS if pk != "제약"):
                return True
    if any(k in text for k in GENERIC_KEYWORDS):
        if not any(pk in text for pk in PHARMA_CONTEXT_KEYWORDS):
            return True
    if str(row.get('category')) == 'Distribution' and '도이치뱅크' in text:
        return True
    return False

# ====================
# Translation Engine
# ====================
@st.cache_data(show_spinner=False, ttl=3600)
def translate_text(text, target='en'):
    if not text: return ""
    full_glossary = {**KEYWORD_MAPPING, **EXTRA_GLOSSARY}
    try:
        from deep_translator import GoogleTranslator
        processed_text = text
        sorted_terms = sorted(full_glossary.keys(), key=len, reverse=True)
        for kr_term in sorted_terms:
            if kr_term in processed_text:
                processed_text = processed_text.replace(kr_term, full_glossary[kr_term])
        translated = GoogleTranslator(source='ko', target=target).translate(processed_text)
        translated = re.sub(r'nicotine\s*ll?', 'Nicotinell', translated, flags=re.IGNORECASE)
        return translated
    except Exception:
        return text

@st.cache_data(show_spinner=False, ttl=3600)
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
    except Exception:
        pass
    return t_title, t_summary, t_keywords

# ====================
# Data Loading (External - Strict Cleaned)
# ====================
@st.cache_data(ttl=60, show_spinner=False)
def load_weekly_data():
    try:
        base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "articles_raw")
        if not os.path.exists(base_dir):
            base_dir = "../data/articles_raw"
            
        ranked_files = sorted(glob.glob(os.path.join(base_dir, "articles_ranked_*.csv")))
        if not ranked_files:
            return pd.DataFrame(), "No Data"
            
        latest_file = ranked_files[-1]
        df = pd.read_csv(latest_file, encoding='utf-8-sig')
        
        if 'published_date' in df.columns:
            df['published_date'] = pd.to_datetime(df['published_date']).dt.date
        if 'category' not in df.columns: df['category'] = 'General'
        if 'keywords' not in df.columns: df['keywords'] = ''
        if 'image_url' not in df.columns: df['image_url'] = ''
        
        # 1. Noise Filter
        if not df.empty:
            df['is_noise'] = df.apply(is_noise_article, axis=1)
            df = df[~df['is_noise']]
        
        # 2. Competitor Hard Filter (Title, Summary, Keywords, Body)
        if not df.empty and COMPETITOR_KEYWORDS:
            comp_pattern = '|'.join(map(re.escape, COMPETITOR_KEYWORDS))
            comp_mask = (
                df['title'].astype(str).str.contains(comp_pattern, case=False, na=False) |
                df['summary'].fillna('').astype(str).str.contains(comp_pattern, case=False, na=False) |
                df['keywords'].fillna('').astype(str).str.contains(comp_pattern, case=False, na=False)
            )
            df = df[~comp_mask]
            
        return df, os.path.basename(latest_file)
    except Exception as e:
        return pd.DataFrame(), str(e)

df, filename = load_weekly_data()

if df.empty:
    st.warning("⚠️ 표시할 뉴스가 없습니다.")
    st.stop()

# ====================
# UI Styles (Tiffany Blue & Modern Cards)
# ====================
st.markdown("""
<style>
    .stApp { background-color: #F8FAFB; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    
    .dashboard-header {
        padding: 10px 0 20px 0;
        border-bottom: 2px solid #E2E8F0;
        margin-bottom: 25px;
    }
    .main-title { font-size: 28px; font-weight: 800; color: #0D5C75; letter-spacing: -0.5px; }
    .sub-title { font-size: 14px; color: #64748B; margin-top: 4px; }
    
    .hero-container {
        background: linear-gradient(135deg, #0F766E 0%, #0D5C75 100%);
        border-radius: 16px;
        padding: 24px;
        color: #FFFFFF;
        box-shadow: 0 10px 25px -5px rgba(13, 92, 117, 0.25);
        margin-bottom: 30px;
    }
    .hero-badge {
        background-color: #F59E0B;
        color: #FFFFFF;
        font-weight: 700;
        font-size: 12px;
        padding: 4px 10px;
        border-radius: 20px;
        display: inline-block;
        margin-bottom: 12px;
        text-transform: uppercase;
    }
    .news-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px;
        height: 100%;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .news-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-color: #0D9488;
    }
    .news-title {
        font-size: 16px;
        font-weight: 700;
        color: #0F172A !important;
        text-decoration: none;
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .news-title:hover { color: #0D9488 !important; }
    .news-summary {
        font-size: 13px;
        color: #475569;
        margin-top: 8px;
        line-height: 1.5;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .category-tag {
        background-color: #CCFBF1;
        color: #0F766E;
        font-size: 11px;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 6px;
        display: inline-block;
    }
    .date-tag { font-size: 11px; color: #94A3B8; margin-left: 6px; }
</style>
""", unsafe_allow_html=True)

# Header Section
st.markdown("""
<div class="dashboard-header">
    <div class="main-title">📊 Healthcare Market Intelligence</div>
    <div class="sub-title">Curated Strategic Insights & Industry Developments</div>
</div>
""", unsafe_allow_html=True)

# Controls & Filters
f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns([1.5, 2, 2, 2, 1.5])
with f_col1:
    lang_opt = st.selectbox("🌐 Language", ["Korean", "English"], index=0)
    use_english = (lang_opt == "English")
with f_col2:
    min_date = df['published_date'].min() if 'published_date' in df.columns else None
    max_date = df['published_date'].max() if 'published_date' in df.columns else None
    date_range = st.date_input("📅 Date Range", [min_date, max_date]) if min_date else None
    if isinstance(date_range, list) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date
with f_col3:
    all_categories = sorted(df['category'].dropna().unique().tolist())
    selected_categories = st.multiselect("📂 Category", all_categories, default=[])
    if not selected_categories: selected_categories = all_categories
with f_col4:
    sort_opts = ["AI Relevance", "Latest Date", "Category"]
    sort_mode = st.selectbox("📊 Sort By", sort_opts)
with f_col5:
    show_ai_only = st.checkbox("🤖 Top AI Focus", value=True, help="Show curated top strategic articles")

# Filter execution
mask = df['category'].isin(selected_categories)
if start_date and end_date and 'published_date' in df.columns:
    mask = mask & (df['published_date'] >= start_date) & (df['published_date'] <= end_date)

filtered_df = df[mask].copy()

# Score sorting
score_col = 'final_score' if 'final_score' in filtered_df.columns else ('lgbm_score' if 'lgbm_score' in filtered_df.columns else None)
if score_col:
    filtered_df = filtered_df.sort_values(score_col, ascending=False)
else:
    filtered_df = filtered_df.sort_values('published_date', ascending=False)

if show_ai_only:
    # Retain top 20 safe articles
    filtered_df = filtered_df.head(20)

if sort_mode == "Latest Date":
    filtered_df = filtered_df.sort_values('published_date', ascending=False)
elif sort_mode == "Category":
    filtered_df = filtered_df.sort_values('category', ascending=True)

FALLBACK_IMAGES = {
    "Zuellig": "https://images.unsplash.com/photo-1586015555751-63c2305d2146?w=600&auto=format&fit=crop&q=60",
    "Distribution": "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?w=600&auto=format&fit=crop&q=60",
    "Client": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=600&auto=format&fit=crop&q=60",
    "BD": "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=600&auto=format&fit=crop&q=60",
    "General": "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=600&auto=format&fit=crop&q=60"
}

# ====================
# 1. Hero Featured Article
# ====================
if not filtered_df.empty:
    hero_candidates = filtered_df[filtered_df['image_url'].astype(str).str.startswith('http', na=False)]
    hero_row = hero_candidates.iloc[0] if not hero_candidates.empty else filtered_df.iloc[0]
    
    h_title = hero_row['title']
    h_summary = hero_row.get('summary', '')
    h_keywords = hero_row.get('keywords', '')
    h_url = hero_row.get('url', '#')
    h_date = str(hero_row.get('published_date', ''))
    h_cat = hero_row.get('category', 'Featured')
    h_img = hero_row.get('image_url', '') or FALLBACK_IMAGES.get(h_cat, FALLBACK_IMAGES["General"])
    
    if use_english:
        h_title, h_summary, h_keywords = translate_article_batch(h_title, h_summary, h_keywords)
        
    st.markdown("### 🔥 Key Strategic Focus of the Week")
    h_col1, h_col2 = st.columns([1.2, 2.2])
    
    with h_col1:
        st.image(h_img, use_container_width=True)
    with h_col2:
        st.markdown(f"""
        <div style="padding: 5px 10px;">
            <span class="hero-badge">★ Market Highlight ({h_cat})</span>
            <div style="font-size: 22px; font-weight: 800; margin: 8px 0;">
                <a href="{h_url}" target="_blank" style="color: #0F766E; text-decoration: none;">{h_title}</a>
            </div>
            <p style="font-size: 14px; color: #475569; line-height: 1.6;">{h_summary}</p>
            <div style="font-size: 12px; color: #64748B; margin-top: 10px;">
                📅 <b>{h_date}</b> | 🏷️ {h_keywords}
            </div>
        </div>
        """, unsafe_allow_html=True)
            
    st.divider()

# ====================
# 2. Category 2-Column Grid View
# ====================
category_priority = ['Zuellig', 'Distribution', 'BD', 'Client']
unique_cats = filtered_df['category'].dropna().unique()
sorted_cats = [c for c in category_priority if c in unique_cats] + [c for c in unique_cats if c not in category_priority]

for cat in sorted_cats:
    cat_df = filtered_df[filtered_df['category'] == cat]
    if cat_df.empty: continue
    
    st.markdown(f"### 📂 {cat} <span style='font-size:15px; color:#64748B;'>({len(cat_df)} articles)</span>", unsafe_allow_html=True)
    
    rows = list(cat_df.iterrows())
    for i in range(0, len(rows), 2):
        g_col1, g_col2 = st.columns(2)
        cols = [g_col1, g_col2]
        
        for j in range(2):
            if i + j < len(rows):
                _, row = rows[i + j]
                title = row['title']
                summary = row.get('summary', '')
                keywords = row.get('keywords', '')
                url = row.get('url', '#')
                date = str(row.get('published_date', ''))
                img_url = row.get('image_url', '') or FALLBACK_IMAGES.get(cat, FALLBACK_IMAGES["General"])
                
                # Failsafe check
                if "고양이" in title or "고양이" in summary: continue
                
                if use_english:
                    title, summary, keywords = translate_article_batch(title, summary, keywords)
                    if "Cat" in title or "Cat" in summary: continue
                
                with cols[j]:
                    with st.container():
                        card_c1, card_c2 = st.columns([1, 2])
                        with card_c1:
                            st.image(img_url, use_container_width=True)
                        with card_c2:
                            st.markdown(f"""
                            <div>
                                <span class="category-tag">{cat}</span>
                                <span class="date-tag">{date}</span>
                                <div style="margin-top: 6px;">
                                    <a href="{url}" target="_blank" class="news-title">{title}</a>
                                </div>
                                <div class="news-summary">{summary}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
    st.divider()
