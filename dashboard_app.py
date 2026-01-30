import streamlit as st
import pandas as pd
import datetime

# Updated: 2026-01-09 (Final Fix for English Mode)

# Page configuration
st.set_page_config(
    page_title="Health Market Monitor",
    page_icon="🏥",
    layout="wide"
)

# Apply Noto Sans KR font globally
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

# Title
st.title("🏥 Healthcare Market Monitoring")
st.markdown("Automated news monitoring & analysis system")

import glob
import os

# Load data
@st.cache_data
def load_data():
    try:
        base_dir = "data/articles_raw"
        if not os.path.exists(base_dir):
            base_dir = "../data/articles_raw"
            
        # Priority 1: Ranked files
        ranked_files = glob.glob(os.path.join(base_dir, "articles_ranked_*.csv"))
        # Priority 2: Raw files
        raw_files = glob.glob(os.path.join(base_dir, "articles_*.csv"))
        
        target_file = None
        file_type = "None"
        
        if ranked_files:
            target_file = max(ranked_files, key=os.path.getctime)
            file_type = "AI Ranked"
        elif raw_files:
            target_file = max(raw_files, key=os.path.getctime)
            file_type = "Raw Data"
            
        if not target_file:
            return pd.DataFrame(), None, None
            
        df = pd.read_csv(target_file)
        
        # Convert date column
        try:
            df['published_date'] = pd.to_datetime(df['published_date']).dt.date
        except:
            pass
            
        # Ensure category column exists
        if 'category' not in df.columns:
            df['category'] = 'General'
            
        # Ensure keywords column exists (for filtering)
        if 'keywords' not in df.columns:
            df['keywords'] = 'General'
            
        return df, os.path.basename(target_file), file_type
        
    except Exception as e:
        return pd.DataFrame(), None, str(e)

df, filename, file_type = load_data()

if filename:
    if file_type == "AI Ranked":
         st.toast(f"Loaded: {filename} (AI Ranked)", icon="🤖")
    else:
         st.toast(f"Loaded: {filename} (Raw Data)", icon="📂")
elif file_type and "None" not in str(file_type): # Error case
    st.error(f"Error loading data: {file_type}")

if df.empty:
    st.warning("No data found. Please run the crawler first.")
    st.stop()


# Main Layout
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

# Custom Glossary for Pre-translation check
# (Applied BEFORE Google Translate to ensure correct terminology)
EXTRA_GLOSSARY = {
    "데일리팜": "Daily Pharm",
    "약사공론": "Yaksagongron",
    "메디파나": "Medipana",
    "의학신문": "Medical Times",
    "청년의사": "Doctor's News",
    "뉴스1": "News1",
    "뉴시스": "Newsis",
    
    # Industry Terms
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

# Helper function for translation (Global Scope)
import requests
import json
import sys

# Force UTF-8 encoding for Windows console (just in case)
# sys.stdout.reconfigure(encoding='utf-8')

# Configure Gemini API (Direct REST API for Python 3.8 compatibility)
GENAI_API_KEY = "AIzaSyD5HUixHFDEeifmY5NhJCnL4cLlxOp7fp0"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GENAI_API_KEY}"

@st.cache_data(show_spinner=False)
def translate_text(text, target='en'):
    if not text: return ""
    
    # 1. Try Gemini API first (High Quality) with Retry Logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Construct explicit prompt with glossary context
            full_glossary = {**KEYWORD_MAPPING, **EXTRA_GLOSSARY}
            glossary_context = "\n".join([f"- {k}: {v}" for k, v in full_glossary.items()])
            
            prompt = f"""
            You are a professional medical translator for pharmaceutical business news.
            Translate the following Korean text to English.
            
            Guidelines:
            1. **Medical Context**: Interpret ambiguous phonetic terms (Konglish) using standard medical terminology (e.g., '프리필드' -> 'Pre-filled', NOT 'Free-filled').
            2. **Industry Standards**: Use formal business language ('Entering market', 'Conclusion of contract').
            3. **Glossary Adherence**: You MUST strictly use the glossary below:
            {glossary_context}
            
            Text to translate:
            "{text}"
            
            Output only the translated English text, no explanations.
            """
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            headers = {'Content-Type': 'application/json'}
            response = requests.post(GEMINI_API_URL, headers=headers, data=json.dumps(payload), timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and result['candidates']:
                    return result['candidates'][0]['content']['parts'][0]['text'].strip()
            elif response.status_code == 429:
                if attempt < max_retries - 1:
                    time.sleep(2) # Wait 2s before retry
                    continue
            else:
                print(f"[Gemini API Error] {response.status_code}: {response.text}")
                break 
                
        except Exception as e:
            print(f"[Gemini Exception] {e}")
            break
        
    # Check if we should retry (Simple retry logic wrapper)
    # Since we are inside the function, we can just loop. 
    # But to minimize diff, let's wrap the logic above in a loop.
    pass

@st.cache_data(show_spinner=False)
def translate_article_batch(title, summary, keywords):
    """
    Translates Title, Summary, and Keywords in a single API call to reduce latency.
    Returns: (translated_title, translated_summary, translated_keywords)
    """
    if not title and not summary: return title, summary, keywords

    # Construct combined text
    combined_text = f"Title: {title}\nSummary: {summary}\nKeywords: {keywords}"
    
    # 1. Try Gemini Combined Call
    result_text = translate_text(combined_text)
    
    # 2. Parse the result (Simple heuristic parsing)
    # Gemini usually returns the format requested, but we need to be robust.
    # Since translate_text returns a string, we hope it preserves the structure.
    # Let's verify if we need to adjust the prompt in translate_text.
    # Actually, reusing translate_text is risky if the prompt expects 'Ko -> En'.
    # It might treat "Title: ..." as part of the sentence to translate.
    # So we need a specialized implementation or just trust translate_text handles newlines well.
    
    # BETTER APPROACH: Just use translate_text logic but with a specific prompt structure?
    # No, translate_text has a fixed prompt.
    # Let's modify translate_text to be more generic OR clearer.
    # The current translate_text prompt says "Translate the following Korean text...".
    # If we pass structured text, it essentially translates the Values. 
    # Let's parse the output.
    
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
        pass # Fallback to original if parsing fails
        
    return t_title, t_summary, t_keywords

# Helper function for translation (Global Scope)
import requests
import json
import time

# Configure Gemini API (Direct REST API for Python 3.8 compatibility)
GENAI_API_KEY = "AIzaSyD5HUixHFDEeifmY5NhJCnL4cLlxOp7fp0"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GENAI_API_KEY}"

def translate_text(text, target='en'):
    if not text: return ""
    
    # 1. Try Gemini API first (High Quality) with Retry Logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Construct explicit prompt with glossary context
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
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            headers = {'Content-Type': 'application/json'}
            response = requests.post(GEMINI_API_URL, headers=headers, data=json.dumps(payload), timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and result['candidates']:
                    return result['candidates'][0]['content']['parts'][0]['text'].strip()
            elif response.status_code == 429:
                if attempt < max_retries - 1:
                    time.sleep(2) # Wait 2s before retry
                    continue
            else:
                print(f"[Gemini API Error] {response.status_code}: {response.text}")
                break # Don't retry on 400/500 errors usually (unless 503)
                
        except Exception as e:
            print(f"[Gemini Exception] {e}")
            break
            
    # 2. Fallback to Google Translator + Pre-processing (If Gemini fails)
    try:
        # Pre-translate Glossary Terms manually
        full_glossary = {**KEYWORD_MAPPING, **EXTRA_GLOSSARY}
        sorted_terms = sorted(full_glossary.keys(), key=len, reverse=True)
        
        processed_text = text
        for kr_term in sorted_terms:
            if kr_term in processed_text:
                processed_text = processed_text.replace(kr_term, full_glossary[kr_term])
                
        from deep_translator import GoogleTranslator
        # Force source='ko' to ensure it translates the remaining Korean parts even with English glossary terms mixed in
        return GoogleTranslator(source='ko', target=target).translate(processed_text)
    except Exception as e:
        st.toast(f"Translation Error: {e}", icon="⚠️")
        return text

# Keyword EN/KR Mapping for Filter
KEYWORD_MAPPING = {
    # Distribution
    "의약품유통": "Pharmaceutical Distribution",
    "지오영": "GeoYoung",
    "DKSH": "DKSH",
    "블루엠텍": "BlueMtech",
    "바로팜": "Baropharm",
    "용마": "Yongma",
    "쉥커": "Schenker",
    "DHL": "DHL",
    "LX판토스": "LX Pantos",
    "CJ": "CJ",
    
    # BD
    "공동판매": "Co-Promotion",
    "코프로모션": "Co-Promotion",
    "유통계약": "Distribution Agreement",
    "판권": "Sales Rights",
    "라이선스": "License",
    "M&A": "M&A",
    "인수": "Acquisition",
    "합병": "Merger",
    "제휴": "Partnership",
    "파트너십": "Partnership",
    "계약": "Contract",
    "생물학적제제": "Biologics",
    "콜드체인": "Cold Chain",
    "CSO": "CSO",
    "판촉영업자": "Sales Agent",
    "제네릭": "Generic",
    "특허만료": "Patent Expiry",
    "국가백신": "National Vaccine",
    "백신": "Vaccine",
    
    # Approval
    "허가": "Approval",
    "신제품": "New Product",
    "출시": "Launch",
    "신약": "New Drug",
    "적응증": "Indication",
    "제형": "Formulation",
    "용량": "Dosage",
    
    # Reimbursement
    "보험등재": "Reimbursement",
    "급여": "NHI Coverage",
    "약가": "Drug Price",
    
    # Zuellig
    "쥴릭": "Zuellig",
    "지피테라퓨틱스": "ZP Therapeutics",
    "라미실": "Lamisil",
    "액티넘": "Actinum",
    "베타딘": "Betadine",
    "사이클로제스트": "Cyclogest",
    "리브타요": "Libtayo",
    
    # Client
    "한독": "Handok",
    "MSD": "MSD",
    "오가논": "Organon",
    "화이자": "Pfizer",
    "사노피": "Sanofi",
    "암젠": "Amgen",
    "GSK": "GSK",
    "로슈": "Roche",
    "릴리": "Lilly",
    "노바티스": "Novartis",
    "노보노디스크": "Novo Nordisk",
    "머크": "Merck",
    "레코르다티": "Recordati",
    "셀진": "Celgene",
    "테바한독": "Teva-Handok",
    "베링거인겔하임": "Boehringer Ingelheim",
    "BMS": "BMS",
    "아스트라제네카": "AstraZeneca",
    "애브비": "AbbVie",
    "파마노비아": "Pharmanovia",
    "리제네론": "Regeneron",
    "바이엘": "Bayer",
    "아스텔라스": "Astellas",
    "얀센": "Janssen",
    "바이오젠": "Biogen",
    "입센": "Ipsen",
    "애보트": "Abbott",
    "안텐진": "Antengene",
    "베이진": "BeiGene",
    "셀트리온": "Celltrion",
    "헤일리온": "Haelion",
    "오펠라": "Opella",
    "켄뷰": "Kenvue",
    "로레알": "L'Oreal",
    "메나리니": "Menarini",
    "위고비": "Wegovy",
    "마운자로": "Mounjaro",
    
    # Therapeutic
    "난임": "Infertility",
    "불임": "Infertility",
    "항암제": "Anticancer",
    
    # Supply
    "공급중단": "Supply Disruption",
    "공급부족": "Supply Shortage",
    "품절": "Out of Stock",
    "품귀": "Shortage",
}

# Top Control Bar (Language & Filters)
# Use a clearer layout
st.markdown("### 🔍 Filters & Settings")

f_col1, f_col2, f_col3, f_col4, f_col5, f_col6 = st.columns([1.5, 2, 2, 2, 2, 1.5])

with f_col1:
    # 1. Language Selector (Filter Style)
    lang_opt = st.selectbox("🌐 Language", ["Korean", "English"], index=0)
    use_english = (lang_opt == "English")

with f_col2:
    # 2. Date Filter
    min_date = df['published_date'].min()
    max_date = df['published_date'].max()
    date_range = st.date_input("📅 Date Range", [min_date, max_date])
    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date

with f_col3:
    # 3. Category Filter
    all_categories = sorted(df['category'].dropna().unique().tolist())
    selected_categories = st.multiselect("📂 Category", all_categories, default=[]) # Default empty = All
    if not selected_categories: 
         selected_categories = all_categories

# --- Logic for Dynamic Keyword Filter ---
# Filter data by Date & Category FIRST to determine available keywords
temp_mask = (
    (df['published_date'] >= start_date) & 
    (df['published_date'] <= end_date) &
    (df['category'].isin(selected_categories))
)
df_filtered_step1 = df[temp_mask]

with f_col4:
    # 4. Keyword Filter (Dynamic Options)
    available_keywords = []
    if 'keywords' in df_filtered_step1.columns:
        # Assuming keywords column might have multiple values?
        # If it's single value per row:
        available_keywords = sorted(df_filtered_step1['keywords'].dropna().unique().tolist())
    
    # Translate keyword options if English mode
    if use_english:
        keyword_options = [KEYWORD_MAPPING.get(k, k) for k in available_keywords]
        # Create reverse mapping for selection
        en_to_kr = {KEYWORD_MAPPING.get(k, k): k for k in available_keywords}
    else:
        keyword_options = available_keywords
    
    selected_keywords_display = st.multiselect("🔑 Keyword", keyword_options, default=[])
    
    # Convert back to Korean for filtering (data is in Korean)
    if use_english:
        selected_keywords = [en_to_kr.get(k, k) for k in selected_keywords_display]
    else:
        selected_keywords = selected_keywords_display


with f_col5:
    # 5. Sort Option
    sort_opts = ["AI Relevance", "Latest Date", "Category", "Keyword"]
    sort_mode = st.selectbox("📊 Sort By", sort_opts)

with f_col6:
    # 6. AI Recommended Filter
    show_ai_only = st.checkbox("🤖 AI Only", value=True, help="Show only AI recommended articles (final_score >= 0.5)")


# --- Apply Final Filter ---
mask = temp_mask # Start with date/cat mask
if selected_keywords:
    mask = mask & (df['keywords'].isin(selected_keywords))

# Apply AI filter if checkbox is enabled
if show_ai_only and 'lgbm_score' in df.columns:
    # VIP Keywords (critical companies/topics)
    VIP_KEYWORDS = [
        'DKSH', 'GSK', 'MSD', '공동판매', '노바티스', '노보노디스크',
        '라미실', '로슈', '릴리', '블루엠텍', '사노피', '암젠', '오가논',
        '위고비', '쥴릭', '지오영', '코프로모션', '특허만료', '한독', '화이자',
        '메나리니'
    ]
    
    # 1. LGBM Top 20 (Pure AI discovery)
    # SAFE THRESHOLD: lgbm_score >= 0.18 (Slightly relaxed to catch borderline cases like 0.21)
    df_temp = df[mask]
    
    # Filter candidates first
    ai_candidates = df_temp[df_temp['lgbm_score'] >= 0.18]
    top_ai = ai_candidates.nlargest(20, 'lgbm_score')
    
    # 2. VIP Keyword Top 10 (Safety net)
    # VIP THRESHOLD: Removed rigorous threshold (>= 0.01) to ensure KEYWORD matches always show up
    vip_pattern = '|'.join(VIP_KEYWORDS)
    has_vip = df_temp[
        df_temp['title'].str.contains(vip_pattern, case=False, na=False) |
        df_temp['summary'].fillna('').str.contains(vip_pattern, case=False, na=False)
    ]
    
    # Safety net: Show if score is non-zero (avoid absolute failures, but trust keywords)
    # Reverting to STRICT Top 5 LIMIT as per user request (Total ~25 articles)
    vip_candidates = has_vip[has_vip['lgbm_score'] >= 0.01]
    top_vip = vip_candidates.nlargest(5, 'lgbm_score')
    
    # 3. Combine and remove duplicates → ~25 articles
    filtered_df = pd.concat([top_ai, top_vip]).drop_duplicates(subset=['url'])
else:
    filtered_df = df[mask]

# Sorting Logic
if sort_mode == "AI Relevance" and 'final_score' in df.columns:
    filtered_df = filtered_df.sort_values('final_score', ascending=False)
elif sort_mode == "Category":
    filtered_df = filtered_df.sort_values('category', ascending=True)
elif sort_mode == "Keyword":
     if 'keywords' in df.columns:
        filtered_df = filtered_df.sort_values('keywords', ascending=True)
else: # Default
    filtered_df = filtered_df.sort_values('published_date', ascending=False)


# Display Metrics
st.markdown(f"**Total Articles:** {len(filtered_df)}")
st.divider()

# Article List Display - Grouped by Category
if filtered_df.empty:
    st.info("No articles found.")
else:
    # Define category display order (priority categories first)
    category_priority = ['Distribution', 'BD', 'Client', 'Zuellig']
    all_categories = filtered_df['category'].unique()
    
    # Sort: priority categories first, then others alphabetically
    sorted_categories = [cat for cat in category_priority if cat in all_categories]
    sorted_categories += sorted([cat for cat in all_categories if cat not in category_priority])
    
    # Group by category
    for category_name in sorted_categories:
        category_df = filtered_df[filtered_df['category'] == category_name]
        
        # Translate category name if needed
        display_category = translate_text(category_name) if use_english else category_name
        
        # Category Header with count (larger font size)
        st.markdown(f"""
        <div style="margin-top: 20px; margin-bottom: 15px;">
            <h3 style="font-size: 22px; color: #006666; border-bottom: 2px solid #0ABAB5; padding-bottom: 8px;">
                📂 {display_category} <span style="color: #888; font-size: 18px;">({len(category_df)} articles)</span>
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        for _, row in category_df.iterrows():
            title = row['title']
            summary = row.get('summary', '')
            category = row['category']
            date = row['published_date']
            keywords = row.get('keywords', '')
            
            # Translation Logic
            if use_english:
                title, summary, keywords = translate_article_batch(title, summary, keywords)

            st.markdown(f"""
            <div class="article-card">
                <div style="font-size: 16px; line-height: 1.5; color: #333;">
                    <a href="{row['url']}" target="_blank" style="font-size: 18px; font-weight: bold; text-decoration: none; color: #008080;">{title}</a>
                    <span style="color: #666;"> | {date} | {keywords}</span>
                </div>
                <div style="font-size: 16px; margin-top: 8px; color: #555; line-height: 1.6;">
                    {summary}
                </div>
            </div>
            """, unsafe_allow_html=True)

# --- KakaoTalk Summary Generator (New Feature) ---
# Moved to Sidebar as requested for better accessibility
with st.sidebar:
    st.divider()
    st.subheader("💬 Kakao Update")
    if st.button("📝 Create Summary"):
        with st.spinner("Selecting best articles and formatting..."):
            # 1. Prepare Base Data
            mask_kakao = (df['published_date'] >= start_date) & (df['published_date'] <= end_date)
            k_df = df[mask_kakao].copy()
            
            # 2. Competitor Exclusion
            COMPETITORS = ["지오영", "DKSH", "블루엠텍", "바로팜", "용마", "쉥커", "DHL", "LX판토스", "CJ"]
            def has_competitor(text):
                return any(comp in str(text) for comp in COMPETITORS)
            
            k_df = k_df[~k_df['title'].apply(has_competitor)]
            
            # 3. Use SAME category-balanced selection as dashboard
            # Sort by final_score (category + AI hybrid)
            sort_col = 'final_score' if 'final_score' in k_df.columns else 'published_date'
            k_df_sorted = k_df.sort_values(sort_col, ascending=False)
            
            # 4. Category-balanced selection (same as dashboard)
            balanced_selection = []
            categories = k_df['category'].unique()
            
            # Major categories: Top 3 each
            for cat in ['Distribution', 'Client', 'BD', 'Zuellig']:
                if cat in categories:
                    cat_articles = k_df_sorted[k_df_sorted['category'] == cat].head(3)
                    balanced_selection.append(cat_articles)
            
            # Other categories: Top 2 each
            for cat in categories:
                if cat not in ['Distribution', 'Client', 'BD', 'Zuellig']:
                    cat_articles = k_df_sorted[k_df_sorted['category'] == cat].head(2)
                    balanced_selection.append(cat_articles)
            
            # Combine and get top 15 for KakaoTalk
            if balanced_selection:
                k_df = pd.concat(balanced_selection, ignore_index=True)
                k_df = k_df.drop_duplicates(subset=['url'])
                k_df = k_df.sort_values(sort_col, ascending=False).head(15)
            else:
                k_df = k_df_sorted.head(15)
            
            # 5. Split into Distribution and Pharma Industry
            # Distribution: Distribution category + Supply Issues
            NEGATIVE_KEYWORDS = ["과징금", "행정처분", "적발", "위반", "검찰", "소송", "불만", "매각", "철수"]
            
            def is_distribution_article(row):
                category = row.get('category', '')
                text = str(row['title']) + " " + str(row.get('summary', ''))
                
                # Distribution category
                if category == 'Distribution':
                    return True
                
                # Supply Issues
                if category == 'Supply Issues':
                    return True
                
                # Zuellig Positive (no negative keywords)
                if category == 'Zuellig':
                    if not any(neg in text for neg in NEGATIVE_KEYWORDS):
                        return True
                
                return False
            
            dist_df = k_df[k_df.apply(is_distribution_article, axis=1)].head(5)
            ind_df = k_df[~k_df.apply(is_distribution_article, axis=1)].head(10)
            
            # 5. Format Output
            header_dist = "📦 [의약품 유통 (Distribution)]"
            header_ind = "🏢 [제약 업계 (Pharma Industry)]"
            msg_none = "- (관련 주요 기사 없음)"
            footer_ai = "\n(AI 선정 주요 뉴스입니다.)"
            footer_rec = "\n(최신순 주요 뉴스입니다.)"
            
            if use_english:
                header_dist = "📦 [Distribution News]"
                header_ind = "🏢 [Pharma Industry News]"
                msg_none = "- (No major articles found)"
                footer_ai = "\n(AI Selected Top News)"
                footer_rec = "\n(Latest Top News)"

            kakao_msg = f"[ZP Market Monitoring Weekly Update]\n📅 Period: {start_date} ~ {end_date}\n\n"
            
            kakao_msg += f"{header_dist}\n"
            if dist_df.empty:
                kakao_msg += f"{msg_none}\n"
            else:
                for _, row in dist_df.iterrows():
                    title = row['title']
                    summary_text = row.get('summary', '')
                    keywords = row.get('keywords', '')
                    date = row.get('published_date', '')
                    
                    if use_english:
                         title, summary_text, _ = translate_article_batch(title, summary_text, keywords)
                    
                    kakao_msg += f"{title} | {date}\n{summary_text}\n{row['url']}\n\n"
                    
            kakao_msg += f"\n{header_ind}\n"
            if ind_df.empty:
                kakao_msg += f"{msg_none}\n"
            else:
                for _, row in ind_df.iterrows():
                    title = row['title']
                    summary_text = row.get('summary', '')
                    keywords = row.get('keywords', '')
                    date = row.get('published_date', '')
                    
                    if use_english:
                         title, summary_text, _ = translate_article_batch(title, summary_text, keywords)
                         
                    kakao_msg += f"{title} | {date}\n{summary_text}\n{row['url']}\n\n"
            
            if 'final_score' in k_df.columns:
                kakao_msg += footer_ai
            else:
                kakao_msg += footer_rec
            
            # Add Disclaimer (Cushion Comment)
            if use_english:
                kakao_msg += "\n\nℹ️ Note: This summary is automatically generated by AI. Please refer to the original link for full details."
            else:
                kakao_msg += "\n\nℹ️ 알림: 본 요약은 AI 모델을 통해 자동 생성되었습니다. 상세 내용은 원문을 참고해 주시기 바랍니다."

            # Display - Using st.code with built-in copy button
            st.success("✅ Summary Generated! Use the copy button (top right) to copy.")
            st.code(kakao_msg, language=None)

