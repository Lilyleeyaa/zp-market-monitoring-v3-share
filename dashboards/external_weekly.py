"""
External Weekly Dashboard - 외부 고객사용 (경쟁사 완전 제외)
- Credential 완전 제거
- 최상단 ✨ Weekly AI Highlight (컴팩트 카드 뷰)
- 번역 파싱 버그 수정 & 영문 모드 완벽 연동
- 공유용 미니멀 메뉴 (...) 내 키워드 포함 및 다국어 자동 전환
- 기존 회사 고유 티파니 블루 테마 & 리스트 뷰 100% 유지
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
    page_title="ZP Market Monitoring - MNC_BD",
    page_icon="📊",
    layout="wide"
)

# Title (V2 Style)
st.title("🏥 Healthcare Market Monitoring")
st.markdown("Curated Strategic Insights & Industry Developments")

# ====================
# Constants & Glossary
# ====================
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

GENAI_API_KEY = os.getenv("GENAI_API_KEY") 
if not GENAI_API_KEY and 'GENAI_API_KEY' in st.secrets:
    GENAI_API_KEY = st.secrets["GENAI_API_KEY"]

GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GENAI_API_KEY}"

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
            line_str = line.strip()
            if re.match(r'^(Title|제목)\s*:', line_str, re.IGNORECASE):
                t_title = re.sub(r'^(Title|제목)\s*:\s*', '', line_str, flags=re.IGNORECASE).strip()
            elif re.match(r'^(Summary|요약)\s*:', line_str, re.IGNORECASE):
                t_summary = re.sub(r'^(Summary|요약)\s*:\s*', '', line_str, flags=re.IGNORECASE).strip()
            elif re.match(r'^(Keywords?|키워드)\s*:', line_str, re.IGNORECASE):
                t_keywords = re.sub(r'^(Keywords?|키워드)\s*:\s*', '', line_str, flags=re.IGNORECASE).strip()
    except Exception:
        pass
    return t_title, t_summary, t_keywords

@st.cache_data(ttl=60, show_spinner=False)
def load_weekly_data():
    try:
        base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "articles_raw")
        if not os.path.exists(base_dir): base_dir = "../data/articles_raw"
        ranked_files = sorted(glob.glob(os.path.join(base_dir, "articles_ranked_*.csv")))
        if not ranked_files: return pd.DataFrame(), "No Data"
        
        latest_file = ranked_files[-1]
        df = pd.read_csv(latest_file, encoding='utf-8-sig')
        
        if 'published_date' in df.columns:
            df['published_date'] = pd.to_datetime(df['published_date']).dt.date
        if 'category' not in df.columns: df['category'] = 'General'
        if 'keywords' not in df.columns: df['keywords'] = ''
        
        # 1. Noise Filter
        if not df.empty:
            df['is_noise'] = df.apply(is_noise_article, axis=1)
            df = df[~df['is_noise']]
        
        # 2. Competitor Hard Filter
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
    st.warning("표시할 뉴스가 없습니다.")
    st.stop()

# ====================
# Main Layout (기존 원본 Tiffany Blue CSS 100% 복원)
# ====================
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
    
    .article-title {
        font-size: 18px;
        font-weight: bold;
        color: #008080; /* Teal */
        text-decoration: none;
    }
    .article-title:hover {
        color: #0ABAB5; /* Tiffany Blue on Hover */
        text-decoration: underline;
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
</style>
""", unsafe_allow_html=True)

# Top Control Bar (Filters)
st.markdown("### 🔍 Filters & Settings")
f_col1, f_col2, f_col3, f_col4, f_col5, f_col6 = st.columns([1.5, 2, 2, 2, 2, 1.5])
with f_col1:
    lang_opt = st.selectbox("🌐 Language", ["Korean", "English"], index=0)
    use_english = (lang_opt == "English")
with f_col2:
    if 'published_date' in df.columns:
        min_date = df['published_date'].min()
        max_date = df['published_date'].max()
        date_range = st.date_input("📅 Date Range", [min_date, max_date])
        if isinstance(date_range, list) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date, end_date = min_date, max_date
    else:
        start_date, end_date = None, None
with f_col3:
    all_categories = sorted(df['category'].dropna().unique().tolist())
    selected_categories = st.multiselect("📂 Category", all_categories, default=[])
    if not selected_categories: selected_categories = all_categories

temp_mask = pd.Series([True] * len(df))
if start_date and end_date:
    temp_mask = (df['published_date'] >= start_date) & (df['published_date'] <= end_date) & (df['category'].isin(selected_categories))
df_filtered_step1 = df[temp_mask]

with f_col4:
    available_keywords = []
    if 'keywords' in df_filtered_step1.columns:
        all_kws = []
        for k_str in df_filtered_step1['keywords'].dropna().astype(str):
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
    sort_opts = ["AI Relevance", "Latest Date", "Category"]
    sort_mode = st.selectbox("📊 Sort By", sort_opts)
with f_col6:
    show_ai_only = st.checkbox("🤖 AI Only", value=True, help="Show curated top strategic articles")

# Filter execution
mask = temp_mask
if selected_keywords:
    kw_pattern = '|'.join(map(re.escape, selected_keywords))
    mask = mask & (df['keywords'].fillna('').str.contains(kw_pattern, na=False))

filtered_df = df[mask].copy()

score_col = 'final_score' if 'final_score' in filtered_df.columns else ('lgbm_score' if 'lgbm_score' in filtered_df.columns else None)
if score_col:
    filtered_df = filtered_df.sort_values(score_col, ascending=False)
else:
    filtered_df = filtered_df.sort_values('published_date', ascending=False)

if show_ai_only:
    filtered_df = filtered_df.head(20)

if sort_mode == "Latest Date":
    filtered_df = filtered_df.sort_values('published_date', ascending=False)
elif sort_mode == "Category":
    filtered_df = filtered_df.sort_values('category', ascending=True)

st.markdown(f"**Total Articles:** {len(filtered_df)}")
st.divider()

# ==========================================
# 🌟 최상단 ✨ Weekly AI Highlight (컴팩트 카드 뷰)
# ==========================================
if not filtered_df.empty:
    hero_row = filtered_df.iloc[0]
    h_title = hero_row['title']
    h_summary = hero_row.get('summary', '')
    h_date = str(hero_row.get('published_date', ''))
    h_keywords = hero_row.get('keywords', '')
    h_url = hero_row.get('url', '#')
    
    if use_english:
        h_title, h_summary, h_keywords = translate_article_batch(h_title, h_summary, h_keywords)

    st.markdown("""
    <div style="margin-top: 10px; margin-bottom: 8px;">
        <span style="font-size: 20px; font-weight: bold; color: #006666;">✨ Weekly AI Highlight</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f'''
    <div style="
        background-color: #FFFFFF;
        border-left: 6px solid #008080;
        border-radius: 8px;
        box-shadow: 0 4px 10px rgba(0, 102, 102, 0.08);
        padding: 16px 20px;
        margin-bottom: 8px;
    ">
        <div style="font-size: 16px; line-height: 1.5; color: #333;">
            <span style="background-color: #E0F2F1; color: #00695C; padding: 2px 7px; border-radius: 6px; font-size: 11px; font-weight: bold; margin-right: 6px;">Top Pick</span>
            <a href="{h_url}" target="_blank" style="font-size: 18px; font-weight: bold; text-decoration: none; color: #008080;">{h_title}</a>
            <span style="color: #666; font-size: 12px; margin-left: 10px;"> | {h_date} | {h_keywords}</span>
        </div>
        <div style="font-size: 14px; margin-top: 8px; color: #555; line-height: 1.6;">
            {h_summary}
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    # 미니멀 복사용 접힘 메뉴 (...) - 키워드 포함 및 영문 자동 전환
    if use_english:
        share_brief = f"""🏥 [Healthcare Market Intelligence - Weekly Strategic Brief]

✨ Weekly AI Highlight:
"{h_title}" | {h_keywords}
- {h_summary[:120]}...

👉 Access full Top 20 & detailed analysis:
https://zp-market-client.streamlit.app"""
    else:
        share_brief = f"""🏥 [주간 헬스케어 마켓 모니터링 - Weekly Strategic Brief]

✨ Weekly AI Highlight:
"{h_title}" | {h_keywords}
- {h_summary[:120]}...

👉 전체 Top 20 및 상세 분석 바로가기:
https://zp-market-client.streamlit.app"""

    with st.expander("..."):
        st.code(share_brief, language="markdown")
        
    st.divider()

# ==========================================
# 📂 Category별 리스트 카드 뷰 (기존 원본 복원)
# ==========================================
category_priority = ['Zuellig', 'Distribution', 'BD', 'Client']
unique_categories = filtered_df['category'].dropna().unique()
sorted_categories = [cat for cat in category_priority if cat in unique_categories]
sorted_categories += sorted([cat for cat in unique_categories if cat not in category_priority])

for category_name in sorted_categories:
    category_df = filtered_df[filtered_df['category'] == category_name]
    if category_df.empty: continue
        
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
        
        if "고양이" in title or "고양이" in summary or "고양이" in keywords:
            continue
            
        if use_english:
            title, summary, keywords_trans = translate_article_batch(title, summary, keywords)
            keywords = keywords_trans
            if "Cat" in title or "Cat" in summary: continue
        
        st.markdown(f'''
        <div style="
            background-color: #FFFFFF;
            border-left: 6px solid #0ABAB5;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            padding: 20px;
            margin-bottom: 15px;
        ">
            <div style="font-size: 16px; line-height: 1.5; color: #333;">
                <a href="{url}" target="_blank" style="font-size: 18px; font-weight: bold; text-decoration: none; color: #008080;">{title}</a>
                <span style="color: #666; font-size: 12px; margin-left: 10px;"> | {date} | {keywords}</span>
            </div>
            <div style="font-size: 14px; margin-top: 8px; color: #555; line-height: 1.6;">
                {summary}
            </div>
        </div>
        ''', unsafe_allow_html=True)
