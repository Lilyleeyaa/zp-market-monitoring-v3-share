"""
Naver News API Crawler v2 (NLP) - Using official Naver Search API
Enhanced with NLP for smart keyword expansion and semantic deduplication
"""

# Auto-install KoNLPy for Colab (required for accurate Korean tokenization)
HAS_KONLPY = False
try:
    from konlpy.tag import Okt
    _test_okt = Okt()  # Test if it works
    HAS_KONLPY = True
    print("[OK] KoNLPy active")
except:
    print("[INFO] KoNLPy inactive (using simple tokenization) - This is normal on Windows")

import datetime
import os
import pandas as pd
from dotenv import load_dotenv

# Load dependencies from .env file for local testing
load_dotenv()
import re
import requests
import time
import torch
import difflib  # For fuzzy matching
import warnings
import datetime
import concurrent.futures # For parallel scraping
from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse

# NLP utilities for smart search
try:
    from nlp_utils import expand_keyword, calculate_relevance_score, semantic_similarity
    HAS_NLP = True
    print("[NLP] Smart search enabled")
except ImportError:
    HAS_NLP = False
    print("[WARNING] nlp_utils not found. NLP features disabled.")

# KoBART Model removed for speed optimization
# Use heuristic summarizer (og:description extraction)
HAS_SUMMARIZER = True  # Fetch full title + og:description (fast with parallel processing)

# ============================================================================
# CONFIGURATION - Naver API Keys
# ============================================================================
# Get your API keys from: https://developers.naver.com/
# Security: Load from Environment Variables (GitHub Secrets)
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")

if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
   print("[WARNING] Naver API Keys not found in environment variables. Functionality may be limited.")

# Or read from environment variables (recommended for security)
NAVER_CLIENT_ID = os.getenv('NAVER_CLIENT_ID', NAVER_CLIENT_ID)
NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET', NAVER_CLIENT_SECRET)

# Data directory
DATA_DIR = "data/articles_raw"
os.makedirs(DATA_DIR, exist_ok=True)

# CONFIGURATION
# -----------------------------------------------------------------------------
# Date range: Look back N days from today (for weekly updates)
DAYS_LOOKBACK = 7  # Collect articles from the past 7 days
END_DATE = datetime.datetime.now()
START_DATE = END_DATE - datetime.timedelta(days=DAYS_LOOKBACK)

# 1. Distribution (의약품유통 + Competitors)
DISTRIBUTION_KEYWORDS = ["의약품유통", "지오영", "DKSH", "블루엠텍", "바로팜", "용마", "쉥커", "DHL", "LX판토스", "CJ"]

# 2. BD
BD_KEYWORDS = ["공동판매", "코프로모션", "유통계약", "판권", "라이선스", "M&A", "인수", "합병", "제휴", "파트너십", "계약",
    "생물학적제제", "콜드체인", "CSO", "판촉영업자", "제네릭", "특허만료", "국가백신", "백신"]

# 3. Approval
APPROVAL_KEYWORDS = ["허가", "신제품", "출시", "신약", "적응증", "제형", "용량"]

# 4. Reimbursement
REIMBURSEMENT_KEYWORDS = ["보험등재", "급여", "약가"]

# 5. Zuellig
ZUELLIG_KEYWORDS = ["쥴릭", "\"지피테라퓨틱스\"", "라미실", "액티넘", "베타딘", "사이클로제스트", "리브타요"]

# 6. Client (renamed from Partner)
CLIENT_KEYWORDS = [    "한독", "MSD", "오가논", "화이자", "사노피", "암젠", "GSK", "로슈", "릴리", "노바티스", "노보노디스크",
    "머크", "레코르다티", "셀진", "테바한독", "베링거인겔하임", "BMS", "아스트라제네카", "애브비", "파마노비아", "리제네론",
    "바이엘", "아스텔라스", "얀센", "바이오젠", "입센", "애보트", "안텐진", "베이진", 
    "헤일리온", "오펠라", "켄뷰", "로레알", "메나리니",
    "위고비", "마운자로"]

# 7. Therapeutic
THERAPEUTIC_KEYWORDS = ["난임", "불임", "항암제"]

# 8. Supply Issues
SUPPLY_KEYWORDS = ["공급중단", "공급부족", "품절", "품귀", "백신"]

# Global domain filter - articles MUST contain at least one of these
DOMAIN_FILTER_KEYWORDS = [
    "의약품", "제약", "바이오", "병원", "환자", "치료",
    "신약", "임상", "FDA", "식약처", "약국", "약사", "의사"
]

def normalize_title(title):
    """
    Normalize title for duplicate detection
    Remove spaces, special characters, convert to lowercase
    """
    import re
    # Remove all whitespace and special characters
    normalized = re.sub(r'[\s\[\]\(\)\{\}\.\,\'\"\_\-\~\!\@\#\$\%\^\&\*\+\=\|\\\:\/\?\<\>]', '', title)
    return normalized.lower()



# 9. Exclusion Filter (User Request)
EXCLUDED_KEYWORDS = [
    "네이버 배송", "네이버 쇼핑", "네이버 페이", "도착보장", 
    "쿠팡", "배달의민족", "요기요", "무신사", "컬리", "알리익스프레스", "테무",
    "부동산", "아파트", "전세", "매매", "청약", "건설", 
    "금리 인하", "주식 개장", "환율", "코스피", "코스닥", "증시", "상한가", 
    "주가", "주식", "목표주가", "특징주", "급등",
    "여행", "호텔", "항공권", "예능", "드라마", "축구", "야구", "올림픽", "연예",
    "이차전지", "배터리", "전기차", "반도체", "디스플레이", "조선", "철강",
    "채용", "신입사원", "공채", "원서접수",
    "자동차", "경차", "출고", "캐스퍼", "아반떼", "현대차", "기아", "테슬라",
    # CSR and Executive keywords
    "CSR", "사회공헌", "기부", "봉사활동", "환경보호", 
    "대표이사 선임", "대표이사 교체", "임원 인사", "인사 발령", "사장 취임",
    "축하 파티", "창립기념", "사옥 이전", "사옥 준공",
    # Clinical trials and R&D (low commercial value)
    "임상1상", "임상2상", "임상3상", "임상시험 진행", "파이프라인 확대",
    "전임상", "초기 연구", "단순 건강", "건강 팁", "건강관리", "운동법", "식단",
    "한약", "한약사", # Herbal medicine noise (User Request)
    
    # Awards and Recognition (NEW - Specific User Request)
    "수상", "포상", "시상식", "표창", "대상을 수상", "금상을 수상", "선정",
    # Financial/Corporate Noise (NEW)
    "지주사", "연결재무제표", "잠정실적", "공시", "주식매수선택권", 
    "주주총회", "배당", "자사주", "매입", "소각", "설탕", # Commodity
    "분회 총회", "구약사회", # Local district meetings (User Request: Keep main KPA meetings)
    # Irrelevant
    "인사", "동정", "부고", "모집", "게시판", "알림",
    # Specific User Requests (Manual Filters)
    "새마을금고", "용마산", "용마폭포", "중랑구", # Yongma noise
    "엑셀세라퓨틱스", # Specific User Request (Irrelevant company)
    # Stronger Exclusion (Syncd with Gemini Prompt)
    "임상1상", "임상2상", "임상3상", "임상시험 진행", "파이프라인 확대", # Clinical Pipeline (Low priority)
    "전임상", "초기 연구", "단순 건강", "건강 팁", "건강관리", "운동법", "식단" # Health/Research noise
]

GENERIC_KEYWORDS = ["파트너십", "계약", "M&A", "인수", "합병", "투자", "제휴"]
PHARMA_CONTEXT_KEYWORDS = ["제약", "바이오", "신약", "임상", "헬스케어", "의료", "병원", "약국", "치료제", "백신", "진단"]

def is_noise_article(text):
    """
    Check if article is noise/garbage based on keywords and context
    """
    if not text: return False
    
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
    # (Since we passed concatenated text, we check membership directly)
    # Check if matched keywords are ONLY generic ones
    # This logic is slightly different from dashboard (which checks 'keywords' col)
    # Here we check if the text contains generic keywords BUT NO pharma keywords
    has_generic = any(gk in text for gk in GENERIC_KEYWORDS)
    if has_generic:
         if not any(pk in text for pk in PHARMA_CONTEXT_KEYWORDS):
             return True

    return False

def deduplicate_articles(articles, threshold=0.80):
    """
    Remove articles with similar title + description using SequenceMatcher
    Threshold lowered to 0.80 for stricter deduplication (catching rephrased ads)
    """
    if not articles:
        return []

    print(f"\n[Deduplication] Starting with {len(articles)} articles...")
    unique_articles = []
    
    # Sort by length (descending) to prefer longer/richer content
    articles.sort(key=lambda x: len(x.get('summary', '')) if x.get('summary') else 0, reverse=True)
    
    for article in articles:
        is_duplicate = False
        # Combine title and summary for comparison (Stronger deduplication)
        current_text = article['title'] + " " + article['summary']
        
        for existing in unique_articles:
            existing_text = existing['title'] + " " + existing['summary']
            
            # SequenceMatcher is O(N*M), but fine for < 500 articles
            similarity = difflib.SequenceMatcher(None, current_text, existing_text).ratio()
            
            # Increased threshold slightly to avoid false positives with long common boilerplate
            if similarity >= threshold:
                is_duplicate = True
                # print(f"  [Duplicate] ({similarity:.2f}) {article['title'][:30]}... <==> {existing['title'][:30]}...")
                break
        
        if not is_duplicate:
            unique_articles.append(article)
            
    print(f"[Deduplication] Reduced from {len(articles)} to {len(unique_articles)} articles.")
    return unique_articles

def is_healthcare_related(text):
    """
    Check if article is healthcare-related by looking for domain keywords
    AND ensure it is NOT noise.
    """
    text_lower = text.lower()
    
    # 1. Must have domain keyword
    has_domain = any(keyword in text for keyword in DOMAIN_FILTER_KEYWORDS)
    if not has_domain:
        return False
        
    # 2. Must NOT be noise
    if is_noise_article(text):
        return False
        
    return True


def tokenize_title(title):
    """
    Hybrid tokenization to overcome KoNLPy limitations:
    1. Domain keyword matching (highest priority)
    2. Space-based split (safe fallback)
    3. 2-gram extraction from long words (backup)
    
    Handles compound words correctly:
    - "약가 인하" → ['약가', '인하']
    - "약가인하" → ['약가', '인하', '약가인하']
    """
    if not title:
        return set()
    
    tokens = set()
    
    # Clean text
    clean = re.sub(r'[^0-9a-zA-Z가-힣\s]', '', title)
    text_lower = clean.lower()
    
    # 1. Match domain keywords (removed: DOMAIN_KEYWORDS was deleted)
    # Falling back to space-based split which works well for most cases
    pass
    
    # 2. Space-based split (safe fallback)
    words = clean.split()
    for word in words:
        if len(word) > 1:
            tokens.add(word.lower())
    
    # 3. Extract 2-grams from long words (backup for missed compounds)
    for word in words:
        if len(word) >= 4:  # Only for 4+ char words
            for i in range(len(word) - 1):
                bigram = word[i:i+2]
                # Only add if it's a known important bigram
                if bigram in ['약가', '인하', '제약']:
                    tokens.add(bigram)
    
    return tokens

def is_similar_to_seen(new_article_text, existing_articles, threshold=0.85):
    """
    Check if article is similar using semantic similarity (if NLP enabled)
    Falls back to Jaccard similarity if NLP not available
    
    Args:
        new_article_text: New article title + summary (User enforced Title+Body check)
        existing_articles: List of existing articles (dicts with 'title', 'summary')
        threshold: Similarity threshold (0.85 for semantic, 0.4 for Jaccard)
    """
    # Always use fast Jaccard similarity (semantic embedding is too slow for bulk crawling)
    new_tokens = tokenize_title(new_article_text)
    if not new_tokens: return False
    
    recent_articles = existing_articles[-500:]
    
    for art in recent_articles:
        # Compare Title + Summary for stronger deduplication (V2 approach - user requested)
        existing_text = art.get('title', '') + " " + art.get('summary', '') 
        existing_tokens = tokenize_title(existing_text)
        
        if not existing_tokens: continue
        
        intersection = len(new_tokens.intersection(existing_tokens))
        union = len(new_tokens.union(existing_tokens))
        
        if union == 0: continue
        similarity = intersection / union
        
        # Hybrid tokenization with stricter threshold to reduce noise
        # 2+ shared tokens OR 60%+ similarity = duplicate (Reduced from 3/30%)
        # Note: Since we use more text (Title+Summary), the overlap should be naturally higher.
        # We keep 0.6 as a conservative threshold for now.
        if similarity >= 0.6:
            # print(f"  [Skip Duplicate] {similarity:.2f}")
            return True
            
    return False


def get_full_content(url):
    """
    Fetch full article content using structural analysis & meta fallback
    """
    try:
        # 2. Add headers to mimic browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=5)
        
        # Encoding Fix: Detect encoding or force UTF-8/EUC-KR
        if response.encoding and response.encoding.lower() == 'iso-8859-1':
             # Try UTF-8 first, fallback to CP949 (EUC-KR) commonly used in Korea
             if response.content[:1024].find(b'charset=euc-kr') > 0 or response.content[:1024].find(b'charset=cp949') > 0:
                 response.encoding = 'cp949'
             else:
                 response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        content = ""
        
        # Priority 1: Semantic Metadata (OG Description)
        # User Feedback: Prioritize OG Description, but filter out "Forbidden" errors.
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            og_text = og_desc.get("content").strip()
            # Forbidden Filter: Only use if NOT an error message
            if "Forbidden" not in og_text and "Access Denied" not in og_text and "You don't have permission" not in og_text:
                if len(og_text) > 50:
                    content = og_text

        # Priority 2: CSS Selectors (If OG failed or was Forbidden)
        if not content:
            selectors = [
                 '#dic_area', '.article_body', '#articleBody', '.news_body', '#newsEndContents',
                 '.view_con', '.art_txt', '#art_txt', '#news_body_id', '.content_view'
            ]
            for selector in selectors:
                element = soup.select_one(selector)
                if element:
                    for script in element(["script", "style", "iframe", "button", "figure", "figcaption"]):
                        script.decompose()
                    body_text = element.get_text(separator='\n', strip=True)
                    if len(body_text) > 200:
                        content = body_text
                        break
        
        # Priority 3: Structural Analysis (If selectors also failed)
        if not content:
            paragraphs = soup.find_all(['p', 'div'])
            parent_scores = {}
            for p in paragraphs:
                if p.name == 'div' and len(p.find_all(['div', 'p'])) > 0:
                     continue
                text = p.get_text(strip=True)
                if len(text) < 10: continue
                parent = p.parent
                if parent in parent_scores:
                    parent_scores[parent] += len(text)
                else:
                    parent_scores[parent] = len(text)
            
            if parent_scores:
                best_parent = max(parent_scores, key=parent_scores.get)
                for tag in best_parent(["script", "style", "iframe", "button", "figure", "figcaption"]):
                    tag.decompose()
                content = best_parent.get_text(separator='\n', strip=True)

        # Get full title fallback
        og_title = soup.find("meta", property="og:title")
        if og_title:
             full_title = html.unescape(og_title.get("content").strip())
        else:
             full_title = ""

        return full_title, content

    except Exception as e:
        return "", ""


import html

def clean_extracted_text(text):
    """
    Advanced Cleaner v3: Handles HTML entities, extended artifacts.
    """
    # 0. Formatting & HTML Artifacts
    text = html.unescape(text) # Fix &#039; -> '
    text = text.replace('fullscreen', '')
    
    # 1. "Reporter =" Cut & "Data =" Cut
    # If "Name Reporter =" exists, discard PRECEDING.
    if ('기자' in text or '특파원' in text) and ('=' in text or 'ㅣ' in text):
         text = re.sub(r'.*?(기자|특파원)\s*[=ㅣ]\s*', '', text)
    
    # Remove "Data =" lines (Source attribution)
    if '자료=' in text or '자료 =' in text:
        text = re.sub(r'.*?자료\s*=\s*', '', text)

    # 2. Recursive Leading/Trailing Bracket Removal
    while True:
        original_text = text
        # Leading: Start -> Bracket -> End Bracket
        text = re.sub(r'^\s*[\(\[\[\<\【].*?[\)\]\]\>\】]', '', text)
        text = re.sub(r'^\s*[▲△■▶▷]\s*', '', text)
        
        # Trailing: Bracket -> End -> Line End
        # e.g. [Freepik]$
        text = re.sub(r'[\(\[].*?[\)\]]\s*$', '', text)
        
        text = text.strip()
        if text == original_text:
            break

    # 3. Remove "Pre-release" notice
    text = re.sub(r'이 기사는.*?선공개 되었습니다\.?', '', text)

    # 4. Remove Captions (/ Photo = ...) appearing clearly 
    text = re.sub(r'\/.*?(사진|이미지)\s*=.*', '', text)
    
    # 5. Remove Emails
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', text)

    # 6. Remove Pipe-enclosed Reporter Info (e.g. | HansEconomy=Lee |)
    text = re.sub(r'\|\s*.*?(기자|특파원).*?\s*\|', '', text)
    
    # 7. Remove Breadcrumbs and Navigation
    # Match Start -> Text -> > -> Text -> > or :
    # Be careful not to kill "Samsung Bio > Celltrion" within sentences
    # Anchor to start of line only
    text = re.sub(r'^.*?>\s*.*?>\s*.*?:?\s*', '', text)
    
    # 8. Remove Specific Artifacts
    text = re.sub(r'ChatGPT\s*생성\s*이미지', '', text)
    
    return text.strip()


def summarize_text(text):
    """
    Smart Summary v6: 
    1. Unescape HTML.
    2. Deep clean lines.
    3. Merge & Split (Decimal safe).
    4. No forced truncation in fallback.
    """
    if not text:
        return ""
    
    text = html.unescape(text)
        
    # 1. Clean Line-by-Line first
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if len(line) < 2: continue
        
        # Apply Advanced Cleaning
        cleaned = clean_extracted_text(line)
        if len(cleaned) < 5: continue 
        
        cleaned_lines.append(cleaned)
    
    # 2. Merge into single blob
    full_text = ' '.join(cleaned_lines)
    
    # 3. Smart Split
    sentences = re.split(r'(?<=[.?!])\s+', full_text)
    
    valid_sentences = []
    current_length = 0
    target_sentences = 3
    
    for s in sentences:
        s = s.strip()
        if len(s) < 10: continue
        
        # Ensure single dot at the end
        if not s.endswith(('.', '?', '!')):
            s += '.'
            
        valid_sentences.append(s)
        current_length += len(s)
        
        if len(valid_sentences) >= target_sentences and current_length > 200:
            break
            
    # Fallback: Just return cleaned text without adding "..."
    if not valid_sentences:
         return full_text[:400] if len(full_text) > 400 else full_text

    return ' '.join(valid_sentences)


def get_naver_news_api(query, display=100):
    """
    Call Naver News Search API
    
    Args:
        query: Search keyword
        display: Number of results to retrieve (max 100 per request)
    
    Returns:
        List of article dictionaries
    """
    # API endpoint
    url = "https://openapi.naver.com/v1/search/news.json"
    
    # Headers with API credentials
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    
    articles = []
    start = 1
    max_results = 1000  # API limit
    MAX_ARTICLES_PER_KEYWORD = 5  # <--- BUFFER LIMIT: Allow 50 raw (Stratified Sampling picks 10 unique)
    
    while start <= max_results:
        # Check if we reached the limit for this keyword
        if len(articles) >= MAX_ARTICLES_PER_KEYWORD:
            break

        # Parameters
        params = {
            "query": query,
            "display": 100,  # Request max items per page
            "start": start,
            "sort": "date"  # Sort by date (newest first)
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"  [stop] API status {response.status_code}")
                break
                
            data = response.json()
            items = data.get('items', [])
            
            if not items:
                break  # No more results
            
            # Process this batch
            batch_added = 0
            stop_crawling = False
            
            for item in items:
                # Clean HTML tags and decode HTML entities properly
                import html
                title = item.get('title', '').replace('<b>', '').replace('</b>', '')
                title = html.unescape(title)  # Decode &amp; &quot; etc.
                
                description = item.get('description', '').replace('<b>', '').replace('</b>', '')
                description = html.unescape(description)
                
                # Check date filtering
                pub_date_str = item.get('pubDate', '')
                try:
                    import email.utils
                    pub_date = email.utils.parsedate_to_datetime(pub_date_str)
                    pub_date_naive = pub_date.replace(tzinfo=None)
                    
                    if pub_date_naive < START_DATE:
                        stop_crawling = True  # We reached older articles, stop fetching
                        continue  # Skip this old article
                except:
                    pass
                
                articles.append({
                    'title': title,
                    'url': item.get('originallink', item.get('link', '')),
                    'summary': description,
                    'site_name': 'Naver News',
                    'published_date': pub_date_str,
                    'search_keyword': query
                })
                batch_added += 1
            
            if stop_crawling:
                # print("  [stop] Reached date limit")
                break
                
            if batch_added == 0:
                break
                
            # Next page
            start += 100
            time.sleep(0.1)  # Respect rate limit
            
        except Exception as e:
            print(f"  [error] {e}")
            break
            
    return articles


def parse_naver_api_date(date_str):
    """
    Parse Naver API date format (RFC 1123)
    Example: "Wed, 08 Jan 2026 12:00:00 +0900"
    """
    if not date_str:
        return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        # Parse RFC 1123 format
        dt = datetime.datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        try:
            # Try alternative format without timezone
            dt = datetime.datetime.strptime(date_str[:25], '%a, %d %b %Y %H:%M:%S')
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def calculate_score_by_category(category):
    """Calculate importance score based on category (Rebalanced)"""
    CATEGORY_SCORES = {
        'Distribution': 6,    # Reduced from 8 (was too dominant)
        'Client': 5,          # Reduced from 6 (slight adjustment)
        'BD': 4,              # Increased from 3 (more important than thought)
        'Zuellig': 5,         # Increased from 3 (company-specific)
        # All others default to 3
    }
    
    return CATEGORY_SCORES.get(category, 3)  # Others: 3 (Approval, Reimbursement, etc.)



def main():
    # Check API credentials
    if NAVER_CLIENT_ID == "YOUR_CLIENT_ID_HERE" or NAVER_CLIENT_SECRET == "YOUR_CLIENT_SECRET_HERE":
        print("=" * 60)
        print("[ERROR] Please set your Naver API credentials!")
        print("=" * 60)
        print("\n1. Visit https://developers.naver.com/")
        print("2. Create an application and enable 'Search' API")
        print("3. Get your Client ID and Client Secret")
        print("4. Set them in this script or as environment variables:")
        print("   export NAVER_CLIENT_ID='your_client_id'")
        print("   export NAVER_CLIENT_SECRET='your_client_secret'")
        print("=" * 60)
        return
    
    start_time = time.time()
    
    print("=" * 60)
    print(">>> Naver News API Crawler (Healthcare Articles)")
    print("=" * 60)
    print(f"\nDate range: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")
    
    # Count total keywords
    total_keywords = (len(DISTRIBUTION_KEYWORDS) + len(BD_KEYWORDS) + len(APPROVAL_KEYWORDS) +
                      len(REIMBURSEMENT_KEYWORDS) + len(ZUELLIG_KEYWORDS) +
                      len(CLIENT_KEYWORDS) + len(THERAPEUTIC_KEYWORDS) + 
                      len(SUPPLY_KEYWORDS))
    print(f"Total keywords to search: {total_keywords}")
    print(f"Expected time: ~1-2 minutes\n")
    
    all_articles = []
    seen_urls = set()
    seen_titles = set()  # For duplicate title detection
    
    # Combine all keyword groups for comprehensive search
    keyword_groups = [
        ("Distribution", DISTRIBUTION_KEYWORDS, 5),
        ("BD", BD_KEYWORDS, 5),
        ("Product Approval", APPROVAL_KEYWORDS, 5),
        ("Reimbursement", REIMBURSEMENT_KEYWORDS, 5),
        ("Zuellig", ZUELLIG_KEYWORDS, 5),
        ("Client", CLIENT_KEYWORDS, 5),
        ("Therapeutic Areas", THERAPEUTIC_KEYWORDS, 5),
        ("Supply Issues", SUPPLY_KEYWORDS, 5)
    ]
    
    for group_idx, (group_name, keywords, display_count) in enumerate(keyword_groups, 1):
        print(f"\n[STEP {group_idx}/{len(keyword_groups)}] Searching {group_name} ({len(keywords)} keywords)")
        print("-" * 60)
        
        for idx, keyword in enumerate(keywords, 1):
            keyword_start = time.time()
            print(f"  [{idx}/{len(keywords)}] '{keyword}'... ", end='', flush=True)
            
            # NLP: Expand ONLY "의약품유통" keyword for broader search
            # All other keywords are proper nouns/single words - use as-is for speed
            if HAS_NLP and keyword == "의약품유통":
                expanded_keywords = expand_keyword(keyword)
                search_queries = list(expanded_keywords)[:3]  # Limit to 3 to avoid too many API calls
            else:
                search_queries = [keyword]  # Use original keyword directly
            
            # Search with expanded keywords
            articles_from_all_queries = []
            for query in search_queries:
                articles = get_naver_news_api(query, display=display_count)
                articles_from_all_queries.extend(articles)
            
            new_count = 0
            for art in articles_from_all_queries:
                # Check URL duplicate
                if art['url'] in seen_urls:
                    continue
                
                # Check normalized title duplicate (CRITICAL - prevents same article with slight variations)
                normalized_title = normalize_title(art['title'])
                if normalized_title in seen_titles:
                    continue  # Skip duplicate titles immediately
                
                # EARLY FILTER: Healthcare domain check (FAST - avoids expensive checks below)
                article_text = art['title'] + " " + art['summary']
                if not is_healthcare_related(article_text):
                    continue  # Skip non-healthcare articles immediately
                
                # NLP: Calculate relevance score
                article_text = art['title'] + " " + art['summary']
                if HAS_NLP:
                    relevance = calculate_relevance_score(article_text, [keyword])
                    if relevance < 0.3:  # Filter low relevance
                        continue
                
                # Check title similarity (V1 approach)
                if is_similar_to_seen(art['title'], all_articles):
                    continue
                
                # KEYWORD RELEVANCE CHECK (from V1 - critical for filtering!)
                # Only keep articles that actually contain the search keyword
                if keyword not in art['title'] and keyword not in art['summary']:
                    continue
                
                # RECRUITMENT FILTER: Exclude job postings
                if '채용' in art['title'] or '채용' in art['summary']:
                    continue

                # Add to collection
                seen_urls.add(art['url'])
                seen_titles.add(normalize_title(art['title']))
                
                art['body'] = ""
                art['summary'] = art['summary']
                art['category'] = group_name
                art['search_keyword'] = keyword  # Original keyword, not expanded
                
                all_articles.append(art)
                new_count += 1
                
                # More articles for NLP-expanded keywords, fewer for exact match
                max_per_keyword = 10 if keyword == "의약품유통" else 5
                if new_count >= max_per_keyword:
                    break
            
            elapsed = time.time() - keyword_start
            print(f" OK - {new_count} new articles ({elapsed:.1f}s)")
            
            time.sleep(0.1)  # Small delay to respect rate limits
    
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"[COMPLETED] Collected {len(all_articles)} unique articles (Before Filtering)")
    print(f"Total time: {total_time:.1f} seconds")
    print("=" * 60)
    
    # Prepare DataFrame
    if all_articles:
        # --- POST-PROCESSING: Re-classify categories based on priority ---
        # User Feedback: "Distribution" articles were missed or misclassified.
        # Force category assignment if keywords are present in text, regardless of search query.
        print("\n[INFO] Re-classifying categories based on content priority...")
        
        for art in all_articles:
            # Check full text (Title + Summary)
            text = (art['title'] + " " + art['summary']).lower()
            
            # Priority 1: Distribution (Absolute Top Priority)
            if any(k.lower() in text for k in DISTRIBUTION_KEYWORDS):
                art['category'] = 'Distribution'
                continue
                
            # Priority 2: Zuellig (Specific Priority)
            if any(k.lower() in text for k in ZUELLIG_KEYWORDS):
                art['category'] = 'Zuellig'
                continue

            # Priority 3: BD
            if any(k.lower() in text for k in BD_KEYWORDS):
                art['category'] = 'BD'
                continue
                
            # Priority 4: Client
            if any(k.lower() in text for k in CLIENT_KEYWORDS):
                art['category'] = 'Client'
                continue
                
        # --- NEW: Semantic Deduplication before DataFrame creation ---
        # 1. Topic-Specific Deduplication (User Request: Geo-Young Ads)
        def deduplicate_by_topic(articles):
            print("[Deduplication] Applying specific topic caps...")
            kept_articles = []
            geoyoung_ad_count = 0
            
            for art in articles:
                text = (art['title'] + " " + art['summary']).lower()
                
                # Filter: Geo-Young Vehicle Ads (Max 1)
                # Matches: "지오영" AND ("차량" OR "광고" OR "배송")
                if "지오영" in text and ("차량" in text or "광고" in text or "배송" in text):
                     # Additional context check to ensure it's the ad
                     if "감기약" in text or "브랜드" in text or "랩핑" in text:
                        if geoyoung_ad_count >= 1:
                            # print(f"  [Skip Topic] Geo-Young Ad Duplicate: {art['title'][:20]}...")
                            continue
                        geoyoung_ad_count += 1
                
                kept_articles.append(art)
            return kept_articles

        all_articles = deduplicate_by_topic(all_articles)

        # 2. General SequenceMatcher Deduplication
        all_articles = deduplicate_articles(all_articles, threshold=0.80)
        
        df = pd.DataFrame(all_articles)
        
        # Process dates
        df['published_date'] = df['published_date'].apply(parse_naver_api_date)
        df['date'] = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # Add region (all local for Naver)
        df['region'] = 'local'
        
        # Calculate scores - Moved to end of script (using category-based scoring)
        df['keywords_matched'] = df['search_keyword']
        # df['score_ag'] calculation moved to finalize step

        
        # === FILTERING STEP ===
        print("\n>>> Filtering non-healthcare articles...")
        initial_count = len(df)
        df = df[df.apply(lambda x: is_healthcare_related(x['title'] + ' ' + x['summary']), axis=1)]
        final_count = len(df)
        print(f"   Removed {initial_count - final_count} irrelevant articles. Remaining: {final_count}")

        # === SUMMARIZATION STEP (Only for survivors) ===
        if HAS_SUMMARIZER and not df.empty:
            print(f"\n>>> Processing {len(df)} articles (Parallel Fast Mode)...")
            
            # Helper function for parallel execution
            def process_article_row(row):
                try:
                    full_title, full_body = get_full_content(row['url'])
                    
                    # Use full title if available and looks valid, otherwise keep existing
                    final_title = full_title if full_title and len(full_title) > 5 else row['title']
                    
                    if full_body:
                        summary_text = summarize_text(full_body)
                    else:
                        summary_text = row['summary']
                        full_body = row['summary'] # Fallback
                except:
                    final_title = row['title']
                    summary_text = row['summary']
                    full_body = row['summary']

                # Final Safety Net: Ensure Title and Summary are Clean (Fixes &#039; and <b> tags from API fallback)
                if final_title:
                    final_title = html.unescape(final_title)
                    final_title = re.sub(r'<[^>]+>', '', final_title)
                
                if summary_text:
                    summary_text = html.unescape(summary_text)
                    summary_text = re.sub(r'<[^>]+>', '', summary_text)
                
                return final_title, summary_text, full_body

            # Execute in parallel processing using threads
            # Network I/O bound, so threads are perfect
            new_titles = []
            summaries = [] # Initialize summaries list
            bodies = []
            
            # Use map to maintain order automatically
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                # Create a list of rows to map over
                rows = [row for _, row in df.iterrows()]
                
                # Executor map returns results in the same order as inputs
                results = executor.map(process_article_row, rows)
                
                # Convert generator to list and show progress
                for i, (tit, sum_txt, body) in enumerate(results, 1):
                    if i % 20 == 0:
                         print(f"   Processing {i}/{len(df)}... ({(i/len(df))*100:.1f}%)")
                    new_titles.append(tit)
                    summaries.append(sum_txt)
                    bodies.append(body)
            
            df['title'] = new_titles
            df['summary'] = summaries
            # Use body for filtering
            df['temp_body'] = bodies
            print(f"   Done! Processed all {len(df)} articles.")

            # === FILTERING STEP 2 (Deep Body Level) ===
            print(f"\n>>> Deep Filtering (Pass 2: Full Body Check)...")
            count_before_deep = len(df)
            # Check exclusions on Title + Summary + Full Body
            # If body triggers exclusion (e.g. "Yongma Saemaul Geumgo"), remove it.
            df = df[df.apply(lambda x: not is_noise_article(str(x['title']) + ' ' + str(x['temp_body'])), axis=1)]
            
            # Drop the temp body column to keep CSV clean
            df = df.drop(columns=['temp_body'])
            
            count_after_deep = len(df)
            print(f"   Removed {count_before_deep - count_after_deep} articles based on full content. Final: {count_after_deep}")

        # Calculate score_ag based on category
        df['score_ag'] = df['category'].apply(calculate_score_by_category)
        
        # Add empty columns for compatibility
        df['keywords'] = df['search_keyword']
        df['reward'] = ''
        df['rl_score'] = ''
        
        # Reorder columns (Removed 'body' as requested to reduce clutter)
        # Added 'category' which was missing
        df = df[['date', 'category', 'published_date', 'site_name', 'url', 'title', 'summary', 
                 'region', 'score_ag', 'keywords', 'reward', 'rl_score']]
        
        # ✅ Apply global healthcare domain filter
        print(f"\n[FILTER] Applying healthcare domain filter...")
        before_count = len(df)
        df = df[df.apply(lambda row: is_healthcare_related(row['title'] + ' ' + row['summary']), axis=1)]
        after_count = len(df)
        filtered_count = before_count - after_count
        print(f"[FILTER] Removed {filtered_count} unrelated articles ({before_count} → {after_count})")
        
        # Sort by score
        df = df.sort_values('score_ag', ascending=False)
        
        # Save
        today_str = datetime.datetime.now().strftime('%Y%m%d')
        filename = f"articles_naver_api_{today_str}.csv"
        filepath = os.path.join(DATA_DIR, filename)
        
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        print(f"\n[SAVED] Output file: {filepath}")
        print(f"\nTop 10 articles by score:")
        for idx, row in df.head(10).iterrows():
            print(f"  [{row['score_ag']:.0f}] {row['title'][:70]}")
        
        print(f"\nScore distribution:")
        print(df['score_ag'].describe())
        
    else:
        print("\n[WARNING] No articles collected!")
        print("Please check your API credentials and network connection.")


if __name__ == "__main__":
    main()
