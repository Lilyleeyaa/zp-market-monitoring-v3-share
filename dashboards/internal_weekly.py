"""
Internal Weekly Dashboard - 내부용 (경쟁사 포함)
- Credential 완전 제거
- 최상단 ✨ Weekly AI Highlight (컴팩트 카드)
- 썸네일/BD코멘트 제외, 여백 최적화, 티파니 블루 테마 100% 유지
"""

import streamlit as st
import pandas as pd
import sys
import os
import re
import requests
import json
import time
from datetime import datetime, timedelta
import pytz

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Page configuration
st.set_page_config(
    page_title="Healthcare Market Monitor",
    page_icon="🏥",
    layout="wide"
)

# Title (V2 Style)
st.title("🏥 Healthcare Market Monitoring")
st.markdown("Automated news monitoring & analysis system")

# GitHub Token을 session_state에 캐시
if 'gh_token' not in st.session_state or not st.session_state['gh_token']:
    _gh_token = None
    _gh_repo = "Lilyleeyaa/zp-market-monitoring-v3-share"
    try:
        from auth.simple_auth import load_auth_config
        _config = load_auth_config()
        if 'GITHUB_TOKEN' in _config:
            _gh_token = _config['GITHUB_TOKEN']
        if 'GITHUB_REPO' in _config:
            _gh_repo = _config['GITHUB_REPO']
    except Exception:
        pass
    
    if not _gh_token:
        try:
            if "GITHUB_TOKEN" in st.secrets:
                _gh_token = st.secrets["GITHUB_TOKEN"]
            elif "github_token" in st.secrets:
                _gh_token = st.secrets["github_token"]
            elif "auth" in st.secrets and "GITHUB_TOKEN" in st.secrets["auth"]:
                _gh_token = st.secrets["auth"]["GITHUB_TOKEN"]
        except Exception:
            pass
            
    if not _gh_token:
        _gh_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("github_token")
    
    st.session_state['gh_token'] = _gh_token or ""
    st.session_state['gh_repo'] = _gh_repo

# ====================
# Translation Components (V2)
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
    "건기식": "Health Functional Food", "프리필드": "Pre-filled", "니코틴엘": "Nicotinell",
    "파슬로덱스": "Faslodex", "닥터레디": "Dr. Reddy's", "HK이노엔": "HK InnoN", "포시가": "Forxiga",
    "쥴릭": "Zuellig", "쥴릭파마": "Zuellig Pharma", "쥴릭코리아": "Zuellig Pharma Korea",
}

KEYWORD_MAPPING = {
    "의약품유통": "Pharmaceutical Distribution", "지오영": "GeoYoung", "DKSH": "DKSH", "블루엠텍": "BlueMtech", "바로팜": "Baropharm", "용마": "Yongma", "쉥커": "Schenker", "DHL": "DHL", "LX판토스": "LX Pantos", "CJ": "CJ",
    "공동판매": "Co-Promotion", "코프로모션": "Co-Promotion", "유통계약": "Distribution Agreement", "판권": "Sales Rights", "라이선스": "License", "M&A": "M&A", "인수": "Acquisition", "합병": "Merger", "제휴": "Partnership", "파트너십": "Partnership", "계약": "Contract", "생물학적제제": "Biologics", "콜드체인": "Cold Chain", "CSO": "CSO", "판촉영업자": "Sales Agent", "특허만료": "Patent Expiry", "국가백신": "National Vaccine", "백신": "Vaccine",
    "허가": "Approval", "신제품": "New Product", "출시": "Launch", "신약": "New Drug", "적응증": "Indication", "제형": "Formulation", "용량": "Dosage",
    "보험등재": "Reimbursement", "급여": "NHI Coverage", "약가": "Drug Price",
    "쥴릭": "Zuellig", "지피테라퓨틱스": "ZP Therapeutics", "지피": "ZP Therapeutics", "지피 테라퓨틱스": "ZP Therapeutics",
    "라미실": "Lamisil", "액티넘": "Actinum", "베타딘": "Betadine", "사이클로제스트": "Cyclogest", "리브타요": "Libtayo",
    "한독": "Handok", "MSD": "MSD", "오가논": "Organon", "화이자": "Pfizer", "사노피": "Sanofi", "암젠": "Amgen", "GSK": "GSK", "로슈": "Roche", "릴리": "Lilly", "노바티스": "Novartis", "노보노디스크": "Novo Nordisk", "머크": "Merck", "레코르다티": "Recordati", "셀진": "Celgene", "테바한독": "Teva-Handok", "베링거인겔하임": "Boehringer Ingelheim", "BMS": "BMS", "아스트라제네카": "AstraZeneca", "애브비": "AbbVie", "파마노비아": "Pharmanovia", "리제네론": "Regeneron", "바이엘": "Bayer", "아스텔라스": "Astellas", "얀센": "Janssen", "바이오젠": "Biogen", "입센": "Ipsen", "애보트": "Abbott", "안텐진": "Antengene", "베이진": "BeiGene", "셀트리온": "Celltrion", "헤일리온": "Haelion", "오펠라": "Opella", "켄뷰": "Kenvue", "로레알": "L'Oreal", "메나리니": "Menarini", "위고비": "Wegovy", "마운자로": "Mounjaro",
    "난임": "Infertility", "불임": "Infertility", "항암제": "Anticancer",
    "공급중단": "Supply Disruption", "공급부족": "Supply Shortage", "품절": "Out of Stock", "품귀": "Shortage",
}

GENAI_API_KEY = os.getenv("GENAI_API_KEY") 
if not GENAI_API_KEY and 'GENAI_API_KEY' in st.secrets:
    GENAI_API_KEY = st.secrets["GENAI_API_KEY"]

GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GENAI_API_KEY}"

def translate_text(text, target='en'):
    if not text: return ""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            full_glossary = {**KEYWORD_MAPPING, **EXTRA_GLOSSARY}
            glossary_context = "\n".join([f"- {k}: {v}" for k, v in full_glossary.items()])
            prompt = f"""You are a professional pharmaceutical translator. Translate the following Korean text to English.
Rules:
1. Maintain professional industry terminology.
2. Use the specific glossary below for strict term matching:
{glossary_context}

Text to translate:
"{text}"

Output only the translated English text, no explanations."""
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            headers = {'Content-Type': 'application/json'}
            response = requests.post(GEMINI_API_URL, headers=headers, data=json.dumps(payload), timeout=8)
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and result['candidates']:
                    return result['candidates'][0]['content']['parts'][0]['text'].strip()
            elif response.status_code == 429:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
        except Exception:
            break
            
    try:
        from deep_translator import GoogleTranslator
        full_glossary = {**KEYWORD_MAPPING, **EXTRA_GLOSSARY}
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

INTERNAL_KEYWORDS = list(KEYWORD_MAPPING.keys())
EXCLUDED_KEYWORDS = [
    "네이버 배송", "네이버 쇼핑", "네이버 페이", "도착보장", "쿠팡", "배달의민족", "요기요", "무신사", "컬리", "알리익스프레스", "테무",
    "부동산", "아파트", "전세", "매매", "청약", "건설", "금리 인하", "주식 개장", "환율", "코스피", "코스닥", "증시", "상한가", 
    "주가", "주식", "목표주가", "특징주", "급등", "여행", "호텔", "항공권", "예능", "드라마", "축구", "야구", "올림픽", "연예", "공연", "뮤지컬", "전시회", "관람",
    "이차전지", "배터리", "전기차", "반도체", "디스플레이", "조선", "철강", "채용", "신입사원", "공채", "원서접수", "고양이",
    "음식", "1인분", "문여는", "대전시장", "이뮨온시아", "에스바이오메딕스", "이지메디컴", "낙태", "살인", "의료진", "구속", "선고", "알테오젠"
]
GENERIC_KEYWORDS = ["계약", "M&A", "인수", "합병", "투자", "제휴", "CJ"]
PHARMA_CONTEXT_KEYWORDS = ["제약", "바이오", "신약", "임상", "헬스케어", "의료", "병원", "약국", "치료제", "백신", "진단", "물류", "유통", "공급"]

def is_noise_article(row):
    text = str(row.get('title', '')) + " " + str(row.get('summary', '')) + " " + str(row.get('content', ''))
    for exc in EXCLUDED_KEYWORDS:
        if exc in text: return True
    if "제약" in text:
        if any(x in text for x in ["시간 제약", "공간 제약", "물리적 제약", "발전 제약", "활동 제약"]):
            if not any(pk in text for pk in PHARMA_CONTEXT_KEYWORDS if pk != "제약"):
                return True
    row_kws = str(row.get('keywords', ''))
    if row_kws:
        matched_gen = [gk for gk in GENERIC_KEYWORDS if gk in row_kws]
        if matched_gen and not any(pk in text for pk in PHARMA_CONTEXT_KEYWORDS):
            return True
    if str(row.get('category')) == 'Distribution' and '도이치뱅크' in text:
        return True
    return False

def has_internal_keyword(row_keywords):
    if pd.isna(row_keywords) or row_keywords == '': return False
    return any(k.strip() in INTERNAL_KEYWORDS for k in str(row_keywords).split(','))

def handle_like(row_dict):
    try:
        save_feedback(row_dict, 1)
    except Exception:
        pass
    st.toast("Saved!", icon="👍")

def save_feedback(row, label):
    import base64, csv, io
    try:
        gh_token = st.session_state.get('gh_token', '')
        gh_repo = st.session_state.get('gh_repo') or 'Lilyleeyaa/zp-market-monitoring-v3-share'
        c_url = str(row.get('url', '')).strip()
        c_title = str(row.get('title', '')).replace("\n", " ").strip()
        c_category = str(row.get('category', '')).strip()
        c_keywords = str(row.get('keywords', '')).strip()
        c_score_ag = str(row.get('score_ag', '')).strip()
        kst = pytz.timezone('Asia/Seoul')
        feedback_date = datetime.now(kst).strftime("%Y-%m-%d %H:%M")
        
        buf = io.StringIO()
        writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
        writer.writerow([feedback_date, c_url, c_title, c_category, c_keywords, c_score_ag, label])
        new_line = buf.getvalue().rstrip("\r\n")
        
        local_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "labels")
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, "feedback_log.csv")
        if not os.path.exists(local_path):
            with open(local_path, "w", encoding="utf-8-sig") as f:
                f.write("feedback_date,url,title,category,keywords,score_ag,reward\n")
        with open(local_path, "a", encoding="utf-8-sig") as f:
            f.write(new_line + "\n")
            
        if not gh_token: return
        
        api_url = f"https://api.github.com/repos/{gh_repo}/contents/data/labels/feedback_log.csv"
        headers = {"Authorization": f"Bearer {gh_token}", "Accept": "application/vnd.github.v3+json"}
        resp = requests.get(api_url, headers=headers)
        if resp.status_code == 200:
            file_data = resp.json()
            existing = base64.b64decode(file_data["content"]).decode("utf-8")
            updated = existing.rstrip("\n") + "\n" + new_line + "\n"
            sha = file_data["sha"]
        else:
            updated = "feedback_date,url,title,category,keywords,score_ag,reward\n" + new_line + "\n"
            sha = None
            
        payload = {
            "message": f"Feedback: {c_title[:40]}... ({feedback_date})",
            "content": base64.b64encode(updated.encode("utf-8")).decode("utf-8"),
            "branch": "main"
        }
        if sha: payload["sha"] = sha
        requests.put(api_url, headers=headers, json=payload)
    except Exception as e:
        print(f"[Feedback Exception] {e}")

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

@st.cache_data(ttl=60, show_spinner=False)
def load_weekly_data():
    try:
        import glob
        base_dir = "data/articles_raw"
        if not os.path.exists(base_dir): base_dir = "../data/articles_raw"
        ranked_files = sorted(glob.glob(os.path.join(base_dir, "articles_ranked_*.csv")))
        if not ranked_files: return pd.DataFrame(), {}, "No Files"
        
        latest_file = ranked_files[-1]
        df = pd.read_csv(latest_file, encoding='utf-8-sig') 
        
        if 'published_date' in df.columns:
            df['published_date'] = pd.to_datetime(df['published_date']).dt.date
        if 'category' not in df.columns: df['category'] = 'General'
        if 'keywords' not in df.columns: df['keywords'] = ''
            
        if 'is_top20' in df.columns and df['is_top20'].any():
            top20_df = df[df['is_top20'] == True]
            other_df = df[df['is_top20'] != True]
            other_df['has_internal_kw'] = other_df['keywords'].apply(has_internal_keyword)
            other_df = other_df[other_df['has_internal_kw']]
            if not other_df.empty:
                other_df['is_noise'] = other_df.apply(is_noise_article, axis=1)
                other_df = other_df[~other_df['is_noise']]
            df = pd.concat([top20_df, other_df]).drop_duplicates(subset=['url'])
        else:
            df['has_internal_kw'] = df['keywords'].apply(has_internal_keyword)
            df = df[df['has_internal_kw']]
            if not df.empty:
                df['is_noise'] = df.apply(is_noise_article, axis=1)
                df = df[~df['is_noise']]
            
        return df, os.path.basename(latest_file), "AI Ranked"
    except Exception as e:
        return pd.DataFrame(), None, str(e)

df, filename, file_type = load_weekly_data()

if df.empty:
    st.warning("No data found. Please run the crawler first.")
    st.stop()

# ====================
# Main Layout (기존 원본 Tiffany Blue CSS 그대로 복원)
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
    
    /* Button Styles - Pure Icon Style (No Border) */
    .stButton>button {
        background-color: transparent !important;
        color: inherit !important;
        border: none !important;
        border-radius: 0px !important;
        padding: 0px !important;
        font-size: 20px !important;
        line-height: 1 !important;
        transition: transform 0.2s;
        height: auto !important;
        min-height: 0px !important;
        box-shadow: none !important;
    }
    .stButton>button:hover {
        background-color: transparent !important;
        color: inherit !important;
        border: none !important;
        transform: scale(1.2);
    }
    .stButton>button:active {
        transform: scale(0.95);
        background-color: transparent !important;
    }
    .stButton>button:focus {
        box-shadow: none !important;
        outline: none !important;
    }
    .stButton>button p {
         line-height: normal;
    }
    
    .stButton {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
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

# Apply Final Filter
mask = temp_mask
if selected_keywords:
    mask = mask & (df['keywords'].isin(selected_keywords))

if show_ai_only and 'lgbm_score' in df.columns:
    df_temp = df[mask]
    score_col = 'final_score' if 'final_score' in df_temp.columns else 'lgbm_score'
    if 'is_top20' in df_temp.columns and df_temp['is_top20'].any():
        filtered_df = df_temp[df_temp['is_top20'] == True]
    else:
        VIP_KEYWORDS = [
            'DKSH', 'GSK', 'MSD', '공동판매', '노바티스', '노보노디스크',
            '라미실', '로슈', '릴리', '블루엠텍', '사노피', '암젠', '오가논',
            '위고비', '쥴릭', '지오영', '코프로모션', '특허만료', '한독', '화이자', '메나리니'
        ]
        ai_threshold = 0.18
        ai_candidates = df_temp[df_temp[score_col] >= ai_threshold]
        top_ai = ai_candidates.nlargest(20, score_col)
        vip_pattern = '|'.join(VIP_KEYWORDS)
        has_vip = df_temp[
            df_temp['title'].str.contains(vip_pattern, case=False, na=False) |
            df_temp['summary'].fillna('').str.contains(vip_pattern, case=False, na=False)
        ]
        top_vip = has_vip[has_vip[score_col] >= 0.01].nlargest(5, score_col)
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

st.markdown(f"**Total Articles:** {len(filtered_df)}")
st.divider()

# ==========================================
# 🌟 최상단 ✨ Weekly AI Highlight (컴팩트 카드)
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
    
    c_card, c_btn = st.columns([15, 1])
    with c_card:
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
    with c_btn:
        st.button(
            "👍🏻",
            key="like_hero_" + str(hash(h_url)),
            on_click=handle_like,
            args=(hero_row.to_dict(),),
            help="Good"
        )
    
    # 미니멀 복사용 접힘 메뉴 (...)
    share_brief = f"""🏥 [주간 헬스케어 마켓 모니터링 - Weekly Strategic Brief]

✨ Weekly AI Highlight:
"{h_title}"
- {h_summary[:120]}...

👉 전체 Top 20 및 상세 분석 바로가기:
https://healthcare-market-monitoring.streamlit.app"""

    with st.expander("..."):
        st.code(share_brief, language="markdown")
        
    st.divider()

# ==========================================
# 📂 Category별 리스트 카드 뷰 (기존 원본 복원)
# ==========================================
category_priority = ['Zuellig', 'Distribution', 'Client', 'BD']
unique_categories = filtered_df['category'].dropna().unique()
sorted_categories = [cat for cat in category_priority if cat in unique_categories]
sorted_categories += sorted([cat for cat in unique_categories if cat not in category_priority])

for cat in sorted_categories:
    cat_df = filtered_df[filtered_df['category'] == cat]
    if cat_df.empty: continue
        
    st.markdown(f"""
    <div style="margin-top: 20px; padding-bottom: 5px;">
        <span style="font-size: 24px; font-weight: bold; color: #006666;">{cat}</span>
        <span style="font-size: 16px; color: #666; margin-left: 10px;">({len(cat_df)} articles)</span>
    </div>
    """, unsafe_allow_html=True)
    
    for _, row in cat_df.iterrows():
        title = row['title']
        summary = row.get('summary', '')
        date = row.get('published_date', '')
        keywords = row.get('keywords', '')
        url = row.get('url', '#')
        
        if use_english:
            title, summary, keywords_trans = translate_article_batch(title, summary, keywords)
            keywords = keywords_trans
        
        c_card, c_btn = st.columns([15, 1])
        with c_card:
            st.markdown(f'''
            <div style="
                background-color: #FFFFFF;
                border-left: 6px solid #0ABAB5;
                border-radius: 8px;
                box-shadow: 0 4px 10px rgba(0,0,0,0.05);
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
        
        with c_btn:
            st.button(
                "👍🏻",
                key="like_" + str(hash(url)),
                on_click=handle_like,
                args=(row.to_dict(),),
                help="Good"
            )
