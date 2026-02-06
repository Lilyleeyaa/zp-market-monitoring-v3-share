"""
Internal Weekly Dashboard - 내부용 (경쟁사 포함)
V2 Design & Filter Logic Restoration (Exact Replica + Feb 06 Fix)
"""
import streamlit as st
import pandas as pd
import sys
import os
import requests
import json
import time
from datetime import datetime, timedelta
import pytz

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.simple_auth import authenticate

# Page configuration
st.set_page_config(
    page_title="Health Market Monitor",
    page_icon="🏥",
    layout="wide"
)

# Apply Noto Sans KR font globally (V2 Style)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');

* {
    font-family: 'Noto Sans KR', sans-serif !important;
}

html, body, div, span, p, h1, h2, h3, h4, h5, h6 {
    font-family: 'Noto Sans KR', sans-serif !important;
}

.stMarkdown, .stText, .stButton button, .stSelectbox, .stMultiSelect {
    font-family: 'Noto Sans KR', sans-serif !important;
}

/* Apply to text areas and inputs */
textarea, input, .stTextArea textarea, .stTextInput input {
    font-family: 'Noto Sans KR', sans-serif !important;
}

/* Streamlit specific */
[data-testid="stMarkdownContainer"] {
    font-family: 'Noto Sans KR', sans-serif !important;
}
</style>
""", unsafe_allow_html=True)

# Title (V2 Style)
st.title("🏥 Healthcare Market Monitoring")
st.markdown("Automated news monitoring & analysis system")

# 인증 (내부 전용)
email, access_level = authenticate(mode='weekly')

if access_level != 'internal':
    st.error("❌ 이 대시보드는 내부 사용자만 접근 가능합니다.")
    st.stop()
    
# Add version toast to confirm update
st.toast("Updated Code Loaded (v3.0.5)", icon="✅")

# ====================
# Translation Components (V2)
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
    "프리필드": "Pre-filled",
}

KEYWORD_MAPPING = {
    "의약품유통": "Pharmaceutical Distribution", "지오영": "GeoYoung", "DKSH": "DKSH", "블루엠텍": "BlueMtech", "바로팜": "Baropharm", "용마": "Yongma", "쉥커": "Schenker", "DHL": "DHL", "LX판토스": "LX Pantos", "CJ": "CJ",
    "공동판매": "Co-Promotion", "코프로모션": "Co-Promotion", "유통계약": "Distribution Agreement", "판권": "Sales Rights", "라이선스": "License", "M&A": "M&A", "인수": "Acquisition", "합병": "Merger", "제휴": "Partnership", "파트너십": "Partnership", "계약": "Contract", "생물학적제제": "Biologics", "콜드체인": "Cold Chain", "CSO": "CSO", "판촉영업자": "Sales Agent", "특허만료": "Patent Expiry", "국가백신": "National Vaccine", "백신": "Vaccine",
    "허가": "Approval", "신제품": "New Product", "출시": "Launch", "신약": "New Drug", "적응증": "Indication", "제형": "Formulation", "용량": "Dosage",
    "보험등재": "Reimbursement", "급여": "NHI Coverage", "약가": "Drug Price",
    "쥴릭": "Zuellig", "지피테라퓨틱스": "ZP Therapeutics", "라미실": "Lamisil", "액티넘": "Actinum", "베타딘": "Betadine", "사이클로제스트": "Cyclogest", "리브타요": "Libtayo",
    "한독": "Handok", "MSD": "MSD", "오가논": "Organon", "화이자": "Pfizer", "사노피": "Sanofi", "암젠": "Amgen", "GSK": "GSK", "로슈": "Roche", "릴리": "Lilly", "노바티스": "Novartis", "노보노디스크": "Novo Nordisk", "머크": "Merck", "레코르다티": "Recordati", "셀진": "Celgene", "테바한독": "Teva-Handok", "베링거인겔하임": "Boehringer Ingelheim", "BMS": "BMS", "아스트라제네카": "AstraZeneca", "애브비": "AbbVie", "파마노비아": "Pharmanovia", "리제네론": "Regeneron", "바이엘": "Bayer", "아스텔라스": "Astellas", "얀센": "Janssen", "바이오젠": "Biogen", "입센": "Ipsen", "애보트": "Abbott", "안텐진": "Antengene", "베이진": "BeiGene", "셀트리온": "Celltrion", "헤일리온": "Haelion", "오펠라": "Opella", "켄뷰": "Kenvue", "로레알": "L'Oreal", "메나리니": "Menarini", "위고비": "Wegovy", "마운자로": "Mounjaro",
    "난임": "Infertility", "불임": "Infertility", "항암제": "Anticancer",
    "공급중단": "Supply Disruption", "공급부족": "Supply Shortage", "품절": "Out of Stock", "품귀": "Shortage",
}

# ====================
# Filter Logic Definitions (Global)
# ====================
INTERNAL_KEYWORDS = list(KEYWORD_MAPPING.keys())

EXCLUDED_KEYWORDS = [
    "네이버 배송", "네이버 쇼핑", "네이버 페이", "도착보장", 
    "쿠팡", "배달의민족", "요기요", "무신사", "컬리", "알리익스프레스", "테무",
    "부동산", "아파트", "전세", "매매", "청약", "건설", 
    "금리 인하", "주식 개장", "환율", "코스피", "코스닥", "증시", "상한가", 
    "주가", "주식", "목표주가", "특징주", "급등",
    "여행", "호텔", "항공권", "예능", "드라마", "축구", "야구", "올림픽", "연예", "공연", "뮤지컬", "전시회", "관람",
    "이차전지", "배터리", "전기차", "반도체", "디스플레이", "조선", "철강",
    "채용", "신입사원", "공채"
]

GENERIC_KEYWORDS = ["계약", "M&A", "인수", "합병", "투자", "제휴", "CJ"]
PHARMA_CONTEXT_KEYWORDS = ["제약", "바이오", "신약", "임상", "헬스케어", "의료", "병원", "약국", "치료제", "백신", "진단", "물류", "유통", "공급"]

def is_noise_article(row):
    text = str(row['title']) + " " + str(row.get('summary', ''))
    
    # 1. Check Explicit Exclusions
    for exc in EXCLUDED_KEYWORDS:
        if exc in text:
            return True
            
    # 2. Homonym Check: "제약" (Constraint vs Pharma)
    if "제약" in text:
        if any(x in text for x in ["시간 제약", "공간 제약", "물리적 제약", "발전 제약", "활동 제약"]):
            if not any(pk in text for pk in PHARMA_CONTEXT_KEYWORDS if pk != "제약"):
                return True

    # 3. Generic Keyword Context Check
    row_kws = str(row.get('keywords', ''))
    if row_kws:
        matched_gen = [gk for gk in GENERIC_KEYWORDS if gk in row_kws]
        if matched_gen:
             if not any(pk in text for pk in PHARMA_CONTEXT_KEYWORDS):
                 return True
    return False

def has_internal_keyword(row_keywords):
    if pd.isna(row_keywords) or row_keywords == '':
        return False
    row_k_list = str(row_keywords).split(',') 
    for k in row_k_list:
        if k.strip() in INTERNAL_KEYWORDS:
            return True
    return False

GENAI_API_KEY = "AIzaSyD5HUixHFDEeifmY5NhJCnL4cLlxOp7fp0"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GENAI_API_KEY}"

@st.cache_data(show_spinner=False)
def translate_text(text, target='en'):
    if not text: return ""
    max_retries = 3
    for attempt in range(max_retries):
        try:
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
                    return result['candidates'][0]['content']['parts'][0]['text'].strip()
            elif response.status_code == 429:
                time.sleep(2)
                continue
            else:
                break
        except Exception as e:
            break
            
    try:
        from deep_translator import GoogleTranslator
        processed_text = text
        full_glossary = {**KEYWORD_MAPPING, **EXTRA_GLOSSARY}
        sorted_terms = sorted(full_glossary.keys(), key=len, reverse=True)
        for kr_term in sorted_terms:
            if kr_term in processed_text:
                processed_text = processed_text.replace(kr_term, full_glossary[kr_term])
        return GoogleTranslator(source='ko', target=target).translate(processed_text)
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

# ====================
# Data Loading (V3 Logic with Strict Filter)
# ====================
def get_weekly_date_range():
    # 2월 6일 기준 주간 (User Request)
    target_date = datetime(2026, 2, 6).date()
    start_date = target_date - timedelta(days=7) # ~7 days range
    return start_date, target_date

@st.cache_data(ttl=3600, show_spinner=False)
def load_weekly_data():
    try:
        import glob
        base_dir = "data/articles_raw"
        if not os.path.exists(base_dir):
            base_dir = "../data/articles_raw"
        
        ranked_files = sorted(glob.glob(os.path.join(base_dir, "articles_ranked_*.csv")))
        if not ranked_files:
            return pd.DataFrame(), {}, "No Files"
        
        latest_file = ranked_files[-1]
        df = pd.read_csv(latest_file, encoding='utf-8-sig') 
        
        if 'published_date' in df.columns:
            df['published_date'] = pd.to_datetime(df['published_date']).dt.date
        
        if 'category' not in df.columns:
            df['category'] = 'General'
        
        if 'keywords' not in df.columns:
            df['keywords'] = ''
            
        # --- Apply Cached Filters Here (Performance Optimization) ---
        # 1. Internal Keyword Strict Filter
        df['has_internal_kw'] = df['keywords'].apply(has_internal_keyword)
        df = df[df['has_internal_kw']]
        
        # 2. Noise Filter
        if not df.empty:
            df['is_noise'] = df.apply(is_noise_article, axis=1)
            df = df[~df['is_noise']]
            
        return df, os.path.basename(latest_file), "AI Ranked"
    except Exception as e:
        return pd.DataFrame(), None, str(e)

df, filename, file_type = load_weekly_data()

if filename:
    if file_type == "AI Ranked":
         st.toast(f"Loaded: {filename} (AI Ranked)", icon="🤖")
    else:
         st.toast(f"Loaded: {filename} (Raw Data)", icon="📂")
elif file_type and "None" not in str(file_type): 
    st.error(f"Error loading data: {file_type}")

if df.empty:
    st.warning("No data found. Please run the crawler first.")
    st.stop()

# Internal Keyword Strict Filter & Noise Filter applied inside load_weekly_data for caching


# ====================
# Main Layout (V2 Style)
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

# Noise Cleanup Logic moved to global scope and applied in cached loader



# Top Control Bar (Language & Filters)
st.markdown("### 🔍 Filters & Settings")

f_col1, f_col2, f_col3, f_col4, f_col5, f_col6 = st.columns([1.5, 2, 2, 2, 2, 1.5])

with f_col1:
    lang_opt = st.selectbox("🌐 Language", ["Korean", "English"], index=0)
    use_english = (lang_opt == "English")

with f_col2:
    # Force 2/6 Week as default
    start_week, end_week = get_weekly_date_range()
    
    if 'published_date' in df.columns:
        min_date = df['published_date'].min()
        max_date = df['published_date'].max()
        
        # Override with strict user requirement if available in data
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
    if not selected_categories: 
        selected_categories = all_categories

# Dynamic Keyword Filter
temp_mask = pd.Series([True] * len(df))
if start_date and end_date:
    temp_mask = (df['published_date'] >= start_date) & (df['published_date'] <= end_date) & (df['category'].isin(selected_categories))

df_filtered_step1 = df[temp_mask]

with f_col4:
    available_keywords = []
    if 'keywords' in df_filtered_step1.columns:
        available_keywords = sorted(df_filtered_step1['keywords'].astype(str).unique().tolist())
    
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
    show_ai_only = st.checkbox("🤖 AI Only", value=True, help="Show only AI recommended articles")

# --- Apply Final Filter ---
mask = temp_mask
if selected_keywords:
    mask = mask & (df['keywords'].isin(selected_keywords))

if show_ai_only and 'lgbm_score' in df.columns:
    VIP_KEYWORDS = [
        'DKSH', 'GSK', 'MSD', '공동판매', '노바티스', '노보노디스크',
        '라미실', '로슈', '릴리', '블루엠텍', '사노피', '암젠', '오가논',
        '위고비', '쥴릭', '지오영', '코프로모션', '특허만료', '한독', '화이자',
        '메나리니'
    ]
    df_temp = df[mask]
    
    score_col = 'final_score' if 'final_score' in df_temp.columns else 'lgbm_score'
    
    # 1. AI Top 20
    ai_threshold = 0.18
    ai_candidates = df_temp[df_temp[score_col] >= ai_threshold]
    top_ai = ai_candidates.nlargest(20, score_col)
    
    # 2. VIP Top 5 (Safety net)
    vip_pattern = '|'.join(VIP_KEYWORDS)
    has_vip = df_temp[
        df_temp['title'].str.contains(vip_pattern, case=False, na=False) |
        df_temp['summary'].fillna('').str.contains(vip_pattern, case=False, na=False)
    ]
    vip_threshold = 0.01
    vip_candidates = has_vip[has_vip[score_col] >= vip_threshold]
    top_vip = vip_candidates.nlargest(5, score_col)
    
    filtered_df = pd.concat([top_ai, top_vip]).drop_duplicates(subset=['url'])
else:
    filtered_df = df[mask]

# Sorting
if sort_mode == "AI Relevance":
    if 'final_score' in df.columns:
        filtered_df = filtered_df.sort_values('final_score', ascending=False)
    elif 'lgbm_score' in df.columns:
        filtered_df = filtered_df.sort_values('lgbm_score', ascending=False)
    elif 'score_ag' in df.columns:
        filtered_df = filtered_df.sort_values('score_ag', ascending=False)
elif sort_mode == "Category":
    filtered_df = filtered_df.sort_values('category', ascending=True)
elif sort_mode == "Keyword":
     if 'keywords' in df.columns:
        filtered_df = filtered_df.sort_values('keywords', ascending=True)
else:
    filtered_df = filtered_df.sort_values('published_date', ascending=False)

# Metrics
st.markdown(f"**Total Articles:** {len(filtered_df)}")
st.divider()

# --- Article List Display (Card Style) ---
if filtered_df.empty:
    st.info("No articles found.")
else:
    category_priority = ['Distribution', 'BD', 'Client', 'Zuellig']
    all_categories = filtered_df['category'].unique()
    sorted_categories = [cat for cat in category_priority if cat in all_categories]
    sorted_categories += sorted([cat for cat in all_categories if cat not in category_priority])
    
    for category_name in sorted_categories:
        category_df = filtered_df[filtered_df['category'] == category_name]
        display_category = translate_text(category_name) if use_english else category_name
        
        st.markdown(f'''
        <div style="margin-top: 20px; margin-bottom: 15px;">
            <h3 style="font-size: 22px; color: #006666; border-bottom: 2px solid #0ABAB5; padding-bottom: 8px;">
                {display_category} <span style="color: #888; font-size: 18px;">({len(category_df)} articles)</span>
            </h3>
        </div>
        ''', unsafe_allow_html=True)
        
        for _, row in category_df.iterrows():
            title = row['title']
            summary_text = row.get('summary', '')
            category = row['category']
            date = row.get('published_date', '')
            keywords = row.get('keywords', '')
            
            if use_english:
                title, summary_text, keywords_trans = translate_article_batch(title, summary_text, keywords)
                keywords = keywords_trans
            
            st.markdown(f'''
            <div class="article-card">
                <div style="font-size: 16px; line-height: 1.5; color: #333;">
                    <a href="{row['url']}" target="_blank" style="font-size: 18px; font-weight: bold; text-decoration: none; color: #008080;">{title}</a>
                    <span style="color: #666;"> | {date} | {keywords}</span>
                </div>
                <div style="font-size: 16px; margin-top: 8px; color: #555; line-height: 1.6;">
                    {summary_text}
                </div>
            </div>
            ''', unsafe_allow_html=True)

# --- KakaoTalk Summary Generator (Sidebar) ---
with st.sidebar:
    st.divider()
    st.subheader("💬 Kakao Update")
    if st.button("📝 Create Summary"):
        with st.spinner("Selecting best articles & formatting..."):
            k_df = filtered_df.copy()
            COMPETITORS = ["지오영", "DKSH", "블루엠텍", "바로팜", "용마", "쉥커", "DHL", "LX판토스", "CJ"]
            def has_competitor(text):
                return any(comp in str(text) for comp in COMPETITORS)
            k_df = k_df[~k_df['title'].apply(has_competitor)]
            
            sort_c = 'final_score' if 'final_score' in k_df.columns else ('lgbm_score' if 'lgbm_score' in k_df.columns else 'published_date')
            k_df = k_df.sort_values(sort_c, ascending=False).head(20)
            
            NEGATIVE_KEYWORDS = ["과징금", "행정처분", "적발", "위반", "검찰", "소송", "불만", "매각", "철수"]
            def is_distribution_article(row):
                category = row.get('category', '')
                text = str(row['title']) + " " + str(row.get('summary', ''))
                if category == 'Distribution': return True
                if category == 'Supply Issues': return True
                if category == 'Zuellig':
                    if not any(neg in text for neg in NEGATIVE_KEYWORDS): return True
                return False
            
            dist_df = k_df[k_df.apply(is_distribution_article, axis=1)].head(10)
            ind_df = k_df[~k_df.apply(is_distribution_article, axis=1)].head(10)
            
            header_dist = "📦 [의약품 유통 (Distribution)]"
            header_ind = "🏢 [제약 업계 (Pharma Industry)]"
            msg_none = "- (관련 주요 기사 없음)"
            
            if use_english:
                header_dist = "📦 [Distribution News]"
                header_ind = "🏢 [Pharma Industry News]"
                msg_none = "- (No major articles found)"

            kakao_msg = f"[ZP Market Monitoring Weekly Update]\n📅 Period: {start_date} ~ {end_date}\n\n"
            
            def format_block(df_block):
                msg = ""
                if df_block.empty:
                    msg += f"{msg_none}\n"
                else:
                    for _, row in df_block.iterrows():
                        t = row['title']
                        s = row.get('summary', '')
                        k = row.get('keywords', '')
                        d = row.get('published_date', '')
                        if use_english:
                            t, s, _ = translate_article_batch(t, s, k)
                        msg += f"{t} | {d}\n{s}\n{row['url']}\n\n"
                return msg

            kakao_msg += f"{header_dist}\n" + format_block(dist_df)
            kakao_msg += f"\n{header_ind}\n" + format_block(ind_df)
            
            if use_english:
                kakao_msg += "\n\nℹ️ Note: AI-generated summary."
            else:
                kakao_msg += "\n\nℹ️ 알림: AI 모델 자동 생성 요약입니다."
                
            st.success("✅ Summary Generated!")
            st.code(kakao_msg, language=None)
