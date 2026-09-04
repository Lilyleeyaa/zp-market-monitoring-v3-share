"""
Internal Weekly Dashboard - Healthcare Market Monitoring (V3.1 Visual Edition)
- Credential removed for frictionless access
- Hero (Featured) Article & Thumbnail Grid UI
- Category-specific visual badging & Fallback image support
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

# ====================
# GitHub Token for Feedback Logging (Non-blocking)
# ====================
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
    "건기식": "Health Functional Food", "프리필드": "Pre-filled", "니코틴엘": "Nicotinell",
    "파슬로덱스": "Faslodex", "닥터레디": "Dr. Reddy's", "HK이노엔": "HK InnoN", "포시가": "Forxiga",
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
        return GoogleTranslator(source='ko', target=target).translate(processed_text)
    except:
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
# Feedback & Data Handling
# ====================
def handle_like(row_dict):
    try:
        save_feedback(row_dict, 1)
    except Exception:
        pass
    st.toast("Saved to Feedback Log!", icon="👍")

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
        
        # Local append
        local_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "labels")
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, "feedback_log.csv")
        if not os.path.exists(local_path):
            with open(local_path, "w", encoding="utf-8-sig") as f:
                f.write("feedback_date,url,title,category,keywords,score_ag,reward\n")
        with open(local_path, "a", encoding="utf-8-sig") as f:
            f.write(new_line + "\n")
            
        if not gh_token:
            return
            
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

INTERNAL_KEYWORDS = list(KEYWORD_MAPPING.keys())
EXCLUDED_KEYWORDS = [
    "네이버 배송", "네이버 쇼핑", "네이버 페이", "도착보장", "쿠팡", "배달의민족", "요기요", "무신사", "컬리", "알리익스프레스", "테무",
    "부동산", "아파트", "전세", "매매", "청약", "건설", "금리 인하", "주식 개장", "환율", "코스피", "코스닥", "증시", "상한가", 
    "주가", "주식", "목표주가", "특징주", "급등", "여행", "호텔", "항공권", "예능", "드라마", "축구", "야구", "올림픽", "연예", "공연", "뮤지컬", "전시회", "관람",
    "이차전지", "배터리", "전기차", "반도체", "디스플레이", "조선", "철강", "채용", "신입사원", "공채", "원서접수", "고양이",
    "음식", "1인분", "문여는", "대전시장", "이뮨온시아", "에스바이오메딕스", "이지메디컴", "낙태", "살인", "의료진", "구속", "선고", "알테오젠"
]

def is_noise_article(row):
    text = str(row.get('title', '')) + " " + str(row.get('summary', '')) + " " + str(row.get('content', ''))
    for exc in EXCLUDED_KEYWORDS:
        if exc in text: return True
    return False

def has_internal_keyword(row_keywords):
    if pd.isna(row_keywords) or row_keywords == '': return False
    return any(k.strip() in INTERNAL_KEYWORDS for k in str(row_keywords).split(','))

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
        if 'image_url' not in df.columns: df['image_url'] = ''
        
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
    st.warning("⚠️ 수집된 데이터가 없습니다. 크롤러를 실행해 주세요.")
    st.stop()

# ====================
# Visual Styling (Modern CSS)
# ====================
st.markdown("""
<style>
    .stApp { background-color: #F8FAFB; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    
    /* Header Area */
    .dashboard-header {
        padding: 10px 0 20px 0;
        border-bottom: 2px solid #E2E8F0;
        margin-bottom: 25px;
    }
    .main-title { font-size: 28px; font-weight: 800; color: #0D5C75; letter-spacing: -0.5px; }
    .sub-title { font-size: 14px; color: #64748B; margin-top: 4px; }
    
    /* Hero Featured Card */
    .hero-container {
        background: linear-gradient(135deg, #0F766E 0%, #0D5C75 100%);
        border-radius: 16px;
        padding: 24px;
        color: #FFFFFF;
        box-shadow: 0 10px 25px -5px rgba(13, 92, 117, 0.25);
        margin-bottom: 30px;
        transition: transform 0.2s ease;
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
        letter-spacing: 0.5px;
    }
    .hero-title {
        font-size: 22px;
        font-weight: 700;
        color: #FFFFFF !important;
        text-decoration: none;
        line-height: 1.4;
    }
    .hero-title:hover { text-decoration: underline; }
    .hero-summary {
        font-size: 14px;
        color: #E2E8F0;
        margin-top: 12px;
        line-height: 1.6;
    }
    .hero-meta {
        font-size: 12px;
        color: #99F6E4;
        margin-top: 15px;
    }

    /* Standard News Card */
    .news-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .news-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-color: #0D9488;
    }
    .news-thumb {
        width: 100%;
        height: 150px;
        object-fit: cover;
        border-radius: 8px;
        margin-bottom: 12px;
        background-color: #F1F5F9;
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
    <div class="main-title">🏥 Healthcare Market Intelligence</div>
    <div class="sub-title">Automated AI Market Monitoring & Strategic Competitive Brief</div>
</div>
""", unsafe_allow_html=True)

# Control & Filter Bar
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
    show_ai_only = st.checkbox("🤖 Top AI Only", value=True, help="Show AI Top 20 ranked articles")

# Filter execution
mask = (df['category'].isin(selected_categories))
if start_date and end_date and 'published_date' in df.columns:
    mask = mask & (df['published_date'] >= start_date) & (df['published_date'] <= end_date)

if show_ai_only and 'is_top20' in df.columns and df['is_top20'].any():
    filtered_df = df[mask & (df['is_top20'] == True)].copy()
else:
    filtered_df = df[mask].copy()

score_col = 'final_score' if 'final_score' in filtered_df.columns else ('lgbm_score' if 'lgbm_score' in filtered_df.columns else 'score_ag')
if sort_mode == "AI Relevance" and score_col in filtered_df.columns:
    filtered_df = filtered_df.sort_values(score_col, ascending=False)
elif sort_mode == "Latest Date":
    filtered_df = filtered_df.sort_values('published_date', ascending=False)
elif sort_mode == "Category":
    filtered_df = filtered_df.sort_values('category', ascending=True)

# Default Fallback Images per Category
FALLBACK_IMAGES = {
    "Zuellig": "https://images.unsplash.com/photo-1586015555751-63c2305d2146?w=600&auto=format&fit=crop&q=60",
    "Distribution": "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?w=600&auto=format&fit=crop&q=60",
    "Client": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=600&auto=format&fit=crop&q=60",
    "BD": "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=600&auto=format&fit=crop&q=60",
    "General": "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=600&auto=format&fit=crop&q=60"
}

# ====================
# 1. Hero / Featured Article Section
# ====================
if not filtered_df.empty:
    # Identify the Top Featured Article (Priority: Top AI score + with valid image, or Top 1)
    hero_candidates = filtered_df[filtered_df['image_url'].str.startswith('http', na=False)]
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
        
    st.markdown("### 🔥 This Week's Key Strategic Focus")
    h_col1, h_col2 = st.columns([1.2, 2.2])
    
    with h_col1:
        st.image(h_img, use_container_width=True)
    with h_col2:
        st.markdown(f"""
        <div style="padding: 5px 10px;">
            <span class="hero-badge">★ Top AI Strategic Pick ({h_cat})</span>
            <div style="font-size: 22px; font-weight: 800; margin: 8px 0;">
                <a href="{h_url}" target="_blank" style="color: #0F766E; text-decoration: none;">{h_title}</a>
            </div>
            <p style="font-size: 14px; color: #475569; line-height: 1.6;">{h_summary}</p>
            <div style="font-size: 12px; color: #64748B; margin-top: 10px;">
                📅 <b>{h_date}</b> | 🏷️ {h_keywords}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        btn_col, _ = st.columns([1, 4])
        with btn_col:
            st.button("👍 Useful", key="hero_like", on_click=handle_like, args=(hero_row.to_dict(),))
            
    st.divider()

# ====================
# 2. Category-based 2-Column Grid View
# ====================
category_priority = ['Zuellig', 'Distribution', 'Client', 'BD']
unique_cats = filtered_df['category'].dropna().unique()
sorted_cats = [c for c in category_priority if c in unique_cats] + [c for c in unique_cats if c not in category_priority]

for cat in sorted_cats:
    cat_df = filtered_df[filtered_df['category'] == cat]
    if cat_df.empty: continue
    
    st.markdown(f"### 📂 {cat} <span style='font-size:15px; color:#64748B;'>({len(cat_df)} articles)</span>", unsafe_allow_html=True)
    
    # Render in 2 columns grid
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
                
                if use_english:
                    title, summary, keywords = translate_article_batch(title, summary, keywords)
                
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
                            
                            b1, _ = st.columns([1, 4])
                            with b1:
                                st.button("👍", key=f"like_{cat}_{i+j}_{hash(url)}", on_click=handle_like, args=(row.to_dict(),))
                        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
    st.divider()
