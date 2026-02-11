import pandas as pd
import sys
import os
sys.path.insert(0, '.')

# Simulate exact dashboard logic
import glob

base_dir = "data/articles_raw"
ranked_files = sorted(glob.glob(os.path.join(base_dir, "articles_ranked_*.csv")))
latest_file = ranked_files[-1]

print(f"Loading file: {latest_file}")

df = pd.read_csv(latest_file, encoding='utf-8-sig')
print(f"\nStep 0 - Loaded from CSV: {len(df)} articles")

# Convert date
if 'published_date' in df.columns:
    df['published_date'] = pd.to_datetime(df['published_date']).dt.date

if 'category' not in df.columns:
    df['category'] = 'General'
    
if 'keywords' not in df.columns:
    df['keywords'] = ''

# DASHBOARD FILTER 1: Internal Keywords
INTERNAL_KEYWORDS = [
    "의약품유통", "지오영", "DKSH", "블루엠텍", "바로팜", "용마", "쉥커", "DHL", "LX판토스", "CJ",
    "공동판매", "코프로모션", "유통계약", "판권", "라이선스", "M&A", "인수", "합병", "제휴", "파트너십", "계약",
    "생물학적제제", "콜드체인", "CSO", "판촉영업자", "특허만료", "국가백신", "백신",
    "허가", "신제품", "출시", "신약", "적응증", "제형", "용량",
    "보험등재", "급여", "약가",
    "쥴릭", "지피테라퓨틱스", "라미실", "액티넘", "베타딘", "사이클로제스트", "리브타요",
    "한독", "MSD", "오가논", "화이자", "사노피", "암젠", "GSK", "로슈", "릴리", "노바티스", "노보노디스크", "머크", "레코르다티", "셀진", "테바한독", "베링거인겔하임", "BMS", "아스트라제네카", "애브비", "파마노비아", "리제네론", "바이엘", "아스텔라스", "얀센", "바이오젠", "입센", "애보트", "안텐진", "베이진", "셀트리온", "헤일리온", "오펠라", "켄뷰", "로레알", "메나리니", "위고비", "마운자로",
    "난임", "불임", "항암제",
    "공급중단", "공급부족", "품절", "품귀"
]

def has_internal_keyword(row_keywords):
    if pd.isna(row_keywords) or row_keywords == '':
        return False
    row_k_list = str(row_keywords).split(',')
    for k in row_k_list:
        if k.strip() in INTERNAL_KEYWORDS:
            return True
    return False

df['has_internal_kw'] = df['keywords'].apply(has_internal_keyword)
df = df[df['has_internal_kw']]
print(f"Step 1 - After Internal Keyword Filter: {len(df)} articles")

# DASHBOARD FILTER 2: Noise Filter
EXCLUDED_KEYWORDS = [
    "네이버 배송", "네이버 쇼핑", "네이버 페이", "도착보장", 
    "쿠팡", "배달의민족", "요기요", "무신사", "컬리", "알리익스프레스", "테무",
    "부동산", "아파트", "전세", "매매", "청약", "건설", 
    "금리 인하", "주식 개장", "환율", "코스피", "코스닥", "증시", "상한가", 
    "주가", "주식", "목표주가", "특징주", "급등",
    "여행", "호텔", "항공권", "예능", "드라마", "축구", "야구", "올림픽", "연예", "공연", "뮤지컬", "전시회", "관람",
    "이차전지", "배터리", "전기차", "반도체", "디스플레이", "조선", "철강",
    "채용", "신입사원", "공채", "원서접수"
]

GENERIC_KEYWORDS = ["계약", "M&A", "인수", "합병", "투자", "제휴", "CJ"]
PHARMA_CONTEXT_KEYWORDS = ["제약", "바이오", "신약", "임상", "헬스케어", "의료", "병원", "약국", "치료제", "백신", "진단", "물류", "유통", "공급"]

def is_noise_article(row):
    text = str(row['title']) + " " + str(row.get('summary', ''))
    
    for exc in EXCLUDED_KEYWORDS:
        if exc in text:
            return True
            
    if "제약" in text:
        if any(x in text for x in ["시간 제약", "공간 제약", "물리적 제약", "발전 제약", "활동 제약"]):
            if not any(pk in text for pk in PHARMA_CONTEXT_KEYWORDS if pk != "제약"):
                return True

    row_kws = str(row.get('keywords', ''))
    if row_kws:
        matched_gen = [gk for gk in GENERIC_KEYWORDS if gk in row_kws]
        if matched_gen:
             if not any(pk in text for pk in PHARMA_CONTEXT_KEYWORDS):
                 return True
    return False

if not df.empty:
    df['is_noise'] = df.apply(is_noise_article, axis=1)
    df = df[~df['is_noise']]
    
print(f"Step 2 - After Noise Filter: {len(df)} articles")

print(f"\n=== CATEGORY DISTRIBUTION ===")
print(df['category'].value_counts())

print(f"\n=== DATE DISTRIBUTION ===")
if 'published_date' in df.columns:
    print(df['published_date'].value_counts().sort_index())

print(f"\n=== This is what dashboard SHOULD show (without AI filter) ===")
print(f"Total: {len(df)} articles")
