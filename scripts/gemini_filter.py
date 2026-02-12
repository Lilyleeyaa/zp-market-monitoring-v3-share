import os
import json
import time
import requests
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

GEMINI_API_KEY = os.getenv('GENAI_API_KEY')
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

# BD Manager Persona Prompt - Focused on Commercialized Products
BD_PERSONA_PROMPT = """
[Role: Senior Business Development Manager at Zuellig Pharma Korea]

너는 쥴릭파마코리아(Zuellig Pharma Korea)의 시니어 사업개발(BD) 매니저야. 너의 임무는 수많은 제약 산업 뉴스 중 우리 회사의 의약품 유통(Distribution) 및 커머셜(Commercial) 비즈니스에 실질적인 영향을 미칠 핵심 기사를 선별하고 전략적 점수를 매기는 것이다.

[CRITICAL: Business Focus - 상업화 된 제품 중심]
- 우리는 이미 시판 허가를 받아 상업화된(Commercialized) 제품의 유통/판매 파트너십에 관심이 있다.
- 임상 1상/2상/3상 단계의 파이프라인 기사는 관심 없음 → 낮은 점수
- 신약 허가 '완료' 후 국내 판매 파트너를 찾는 기사 → 높은 점수
- 제품 인허가 '진행 중'이나 '예정' 수준은 관심 낮음

[Core Interest & Priorities]
아래 기준에 따라 기사의 중요도를 1점(무관)에서 10점(매우 중요) 사이로 평가하라.

1. 의약품 유통 (Distribution & Logistics) - 가중치 높음
   - 경쟁사 동향: 지오영, 백제약품 등 주요 유통사의 물류 센터 확장, M&A, 신규 계약
   - 유통 구조 변화: 직거래 비중 변화, 온라인몰 확장, 콜드체인 규제 변화

2. 커머셜 (Commercial & Solution) - 가중치 높음
   - 고객사 동향: 외자사 및 국내사의 ***상업화된 제품*** 신규 판매 파트너 모색, 한국 시장 철수/진출
   - 전략적 파트너십: 공동판매(Co-promotion), 코마케팅, 판권 이전
   - CSO/CMO 계약 체결 또는 변경

3. 약가 및 제도 - 가중치 높음
   - 약가 인하 정책: MNC 철수로 이어질 수 있는 급여 삭감, 약가 조정
   - 급여 등재: 기존 제품의 급여 변경, 경쟁 제품 급여 등재
   - 리베이트 규제, 유통 규제 변화

4. 기업 전략 (M&A): 고객사나 경쟁사의 인수합병, 사업부 매각, 한국 사업 철수

[Explicit Exclusions - 낮은 점수 (1-3점)]
- 임상시험 진행 중인 파이프라인 기사 (임상1상, 2상, 3상 진행)
- 연구개발(R&D) 초기 단계 기사
- 제약과 무관한 자동차, 부동산, IT 산업 기사
- 단순 CSR 활동, 일반 인사 동정
- 단순 건강 정보, 건강 팁

[Filtering Rules]
- "임상 진입", "1상 시작", "2상 결과", "3상 승인", "파이프라인 확대" 등 → 1-3점
- "판매 파트너", "유통 계약", "공동판매", "품목 인수", "한국 출시" → 7-10점
"""

def call_gemini_api(prompt, max_retries=3):
    """Call Gemini API with retry logic"""
    for attempt in range(max_retries):
        try:
            response = requests.post(
                GEMINI_API_URL,
                headers={'Content-Type': 'application/json'},
                json={
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }],
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 2048
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                print(f"  [WARNING] Gemini API error (attempt {attempt+1}): {response.status_code} {response.text}")
                time.sleep(2 ** attempt)  # Exponential backoff
        except Exception as e:
            print(f"  [WARNING] Gemini API exception (attempt {attempt+1}): {str(e)}")
            time.sleep(2 ** attempt)
    
    return None

def gemini_batch_deduplicate_and_score(articles_df):
    """
    Batch process articles through Gemini for:
    1. Semantic deduplication
    2. Strategic importance scoring
    
    Returns: DataFrame with added columns: gemini_score, is_duplicate, strategic_insight
    """
    print("\n[Gemini Filter] Starting batch deduplication and scoring (Requests Mode)...")
    
    if GEMINI_API_KEY is None:
        print("  [WARNING] GENAI_API_KEY not found, skipping Gemini filter")
        return articles_df
    
    # Check if empty
    if articles_df.empty:
        return articles_df

    # Prepare article list for Gemini
    all_articles_list = []
    for idx, row in articles_df.iterrows():
        all_articles_list.append({
            "id": idx,
            "title": row['title'],
            "summary": row.get('summary', ''),
            "category": row.get('category', '')
        })
    
    # Process in batches of 5
    BATCH_SIZE = 5
    total_articles = len(all_articles_list)
    all_gemini_results = []
    
    print(f"  [Info] Processing {total_articles} articles in batches of {BATCH_SIZE}...")
    
    for i in range(0, total_articles, BATCH_SIZE):
        batch = all_articles_list[i:i+BATCH_SIZE]
        print(f"  [Batch {i//BATCH_SIZE + 1}] Processing articles {i+1} to {min(i+BATCH_SIZE, total_articles)}...")

        # Construct batch prompt
        prompt = f"""{BD_PERSONA_PROMPT}

[Deduplication Task]
1. 제공된 기사 리스트 중 동일한 사건(Event)이나 이슈를 다루고 있는 중복 기사들을 그룹화하라.
2. 중복 그룹 중에서는 가장 정보량이 많고 구체적인(수치, 날짜, 파트너명 포함) 기사 하나만 남기고 나머지는 제거하라.
3. 제목은 다르더라도 본질적인 비즈니스 임팩트가 같다면 동일 기사로 간주하라.

[Scoring Task]
중복 제거 후 남은 각 기사에 대해:
- score: 1-10 (우리 비즈니스에 미치는 영향도)
- strategic_insight: BD 관점에서 왜 중요한지 1문장으로 기술
- is_high_priority: true (8점 이상) or false

[Input Articles]
{json.dumps(batch, ensure_ascii=False, indent=2)}

[Output Format]
반드시 아래 JSON 형식으로 응답하라. 중복 기사는 "is_duplicate": true로 표시하되 리스트에 포함시켜라.

{{
  "results": [
    {{
      "id": 기사 ID,
      "score": 1-10,
      "is_duplicate": true/false,
      "duplicate_of": 중복이면 원본 기사 ID (선택),
      "strategic_insight": "BD 관점 인사이트",
      "is_high_priority": true/false
    }}
  ]
}}
"""
        # Call Gemini API
        response_text = call_gemini_api(prompt)
        
        if response_text:
             try:
                # Extract JSON
                json_text = response_text
                if "```json" in response_text:
                    json_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    json_text = response_text.split("```")[1].split("```")[0].strip()
                
                batch_results = json.loads(json_text)
                if 'results' in batch_results:
                    all_gemini_results.extend(batch_results['results'])
                    print(f"    -> Success: Received {len(batch_results['results'])} results.")
                else:
                    print(f"    -> Warning: Unexpected JSON structure.")
             except Exception as e:
                print(f"    -> Error parsing JSON: {e}")
        else:
             print(f"    -> Error: No response for this batch.")

        # Sleep between batches if not the last one
        if i + BATCH_SIZE < total_articles:
            print("    -> Sleeping 10 seconds to respect rate limits...")
            time.sleep(10)

    # Apply results to DataFrame
    print(f"  [Gemini] Aggregated results for {len(all_gemini_results)} articles.")

    for result in all_gemini_results:
        idx = result.get('id')
        if idx is not None and idx in articles_df.index:
            articles_df.at[idx, 'gemini_score'] = result.get('score', 5)
            articles_df.at[idx, 'is_duplicate'] = result.get('is_duplicate', False)
            articles_df.at[idx, 'strategic_insight'] = result.get('strategic_insight', '')
            articles_df.at[idx, 'is_high_priority'] = result.get('is_high_priority', False)
    
    # Filter out duplicates
    deduplicated = articles_df[articles_df.get('is_duplicate', False) == False].copy()
    
    print(f"  [OK] Gemini filter complete:")
    print(f"       - Original: {len(articles_df)} articles")
    print(f"       - Removed: {len(articles_df) - len(deduplicated)} duplicates")
    print(f"       - Final: {len(deduplicated)} articles")
    
    high_priority_count = len(deduplicated[deduplicated.get('is_high_priority', False) == True])
    print(f"       - High priority (8+ score): {high_priority_count} articles")
    
    return deduplicated
