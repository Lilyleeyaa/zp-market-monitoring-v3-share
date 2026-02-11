"""
Gemini API helper functions for article filtering and scoring
"""
import os
import json
import time
import requests

from dotenv import load_dotenv

# Load key from .env for local testing
load_dotenv()

GEMINI_API_KEY = os.getenv('GENAI_API_KEY', '')
if GEMINI_API_KEY:
    GEMINI_API_KEY = GEMINI_API_KEY.strip()  # Remove potential whitespace/newlines

GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

# BD Manager Persona Prompt
BD_PERSONA_PROMPT = """
[Role: Senior Business Development Manager at Zuellig Pharma Korea]

너는 쥴릭파마코리아(Zuellig Pharma Korea)의 시니어 사업개발(BD) 매니저야. 너의 임무는 수많은 제약 산업 뉴스 중 우리 회사의 의약품 유통(Distribution) 및 커머셜(Commercial) 비즈니스에 실질적인 영향을 미칠 핵심 기사를 선별하고 전략적 점수를 매기는 것이다.

[Core Interest & Priorities]
아래 기준에 따라 기사의 중요도를 1점(무관)에서 10점(매우 중요) 사이로 평가하라.

1. 의약품 유통 (Distribution & Logistics) - [비즈니스 핵심]
   - 경쟁사 동향: 지오영, 백제약품, 용마로지스 등 주요 유통사의 물류 센터 확장, M&A, 신규 대형 계약, IT 인프라/콜드체인 투자.
   - 유통 구조 변화: 제약사의 직거래 전환, 온라인몰 확장, 의약품 배송 규제 변화.

2. 커머셜 (Commercial & Solution) - [비즈니스 기회]
   - 고객사(제약사) 동향: 외자사 및 국내사의 신약 출시, 파이프라인 변경, 한국 시장 철수/진출.
   - 전략적 파트너십: 공동판매(Co-promotion), 코마케팅, 판권 이전 계약.

3. 약가 및 제도 (Market Access): 보건복지부/심평원의 약가 인하, 급여 등재, 리베이트 규제 (유통 마진에 영향).

[Strict Filtering Rules (Negative Factors)]
다음 내용은 비즈니스 가치가 낮으므로 1~2점으로 평가하고 '제외'로 분류하라.
- **단순 수상/포상**: '대상 수상', '금상 수상', '표창', '000 선정', '혁신상' 등 (비즈니스 임팩트 없음)
- **단순 실적 공시**: '매출 000억 달성', '영업이익 흑자전환' 등 (구체적 전략 언급 없으면 제외)
- **단순 사회공헌(CSR)**: 기부, 봉사활동, 플로깅 등.
- **단순 인사/동정**: 임원급(대표이사) 변경이 아닌 단순 팀장급 인사, 부고, 결혼.
- **연구개발(R&D) 초기**: 임상 1상/2상 진입 등 먼 미래의 이야기 (유통/판매와 거리가 멂).

[Scoring Guide]
- 8~10점: 경쟁사의 대형 M&A, 주요 제약사의 유통 파트너 변경, 정부의 유통 마진 관련 중대 규제, 쥴릭파마 직접 언급.
- 6~7점: 주요 고객사의 신약 허가/출시, 경쟁사의 물류 센터 오픈, 백신 입찰 공고.
- 3~5점: 일반적인 제약 업계 동향, 약가 인하 소식.
- 1~2점: 수상 소식, 단순 흑자/적자 공시, CSR 활동, 임상 초기 단계.
"""

def call_gemini_api(prompt, max_retries=4):
    """Call Gemini API with retry logic"""
    # Fallback URLs in case of 404 or persistent failures
    URLs = [
        GEMINI_API_URL,
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    ]
    
    for url_idx, current_url in enumerate(URLs):
        if url_idx > 0:
            print(f"  [INFO] Trying alternative endpoint/model: {current_url.split('/models/')[1].split(':')[0]}")

        for attempt in range(max_retries):
            try:
                # Debug: Print URL (Masked Key)
                masked_url = current_url.replace(GEMINI_API_KEY, "API_KEY_MASKED") if GEMINI_API_KEY else "NO_KEY"
                if attempt == 0:
                    print(f"  [DEBUG] Requesting Gemini API: {masked_url}")

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
                if 'candidates' in result and result['candidates']:
                    return result['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 429:
                wait_time = 30 * (attempt + 1)
                print(f"  [429] Rate limit hit. Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            elif response.status_code == 429:
                wait_time = 70 * (attempt + 1)
                print(f"  [429] Rate limit hit. Response: {response.text[:200]}")
                print(f"  [429] Rate limit hit. Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            elif response.status_code == 404:
                print(f"  [404] Model not found at this endpoint. Trying next model...")
                break # Move to next URL in URLs list
            else:
                print(f"  [WARNING] Gemini API error (attempt {attempt+1}): {response.status_code}")
                print(f"  [DEBUG] Response: {response.text[:200]}")
                time.sleep(5 * (attempt + 1))
        except Exception as e:
            print(f"  [WARNING] Gemini API exception (attempt {attempt+1}): {str(e)}")
            time.sleep(10)
    
    return None

def gemini_batch_deduplicate_and_score(articles_df):
    """
    Batch process articles through Gemini for deduplication & scoring.
    Uses chunking (batch size 5) to avoid 429 Rate Limit errors.
    """
    print("\n[Gemini Filter] Starting batch deduplication and scoring...")
    
    if not GEMINI_API_KEY:
        print("  [WARNING] GENAI_API_KEY not found, skipping Gemini filter")
        return articles_df
    
    # Prepare article list for Gemini
    articles_list = []
    for idx, row in articles_df.iterrows():
        articles_list.append({
            "id": idx,
            "title": row['title'],
            "summary": row.get('summary', ''),
            "category": row.get('category', '')
        })
    
    # Process in chunks (Free Tier: 2 RPM limit)
    BATCH_SIZE = 20
    all_gemini_results = []
    
    total_batches = (len(articles_list) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for i in range(0, len(articles_list), BATCH_SIZE):
        batch_idx = i // BATCH_SIZE + 1
        chunk = articles_list[i:i + BATCH_SIZE]
        print(f"  [Gemini] Processing batch {batch_idx}/{total_batches} ({len(chunk)} articles)...")
        
        # Construct prompt for this chunk
        prompt = f"""{BD_PERSONA_PROMPT}

[Deduplication Task]
1. 제공된 기사 리스트 중 동일한 사건(Event)이나 이슈를 다루고 있는 중복 기사들을 그룹화하라.
2. 중복 그룹 중에서는 가장 정보량이 많고 구체적인(수치, 날짜, 파트너명 포함) 기사 하나만 남기고 나머지는 제거하라.

[Scoring Task]
중복 제거 후 남은 각 기사에 대해:
- score: 1-10 (우리 비즈니스에 미치는 영향도)
- strategic_insight: BD 관점에서 왜 중요한지 1문장으로 기술
- is_high_priority: true (8점 이상) or false

[Input Articles]
{json.dumps(chunk, ensure_ascii=False, indent=2)}

[Output Format]
반드시 아래 JSON 형식으로 응답하라. 중복 기사는 "is_duplicate": true로 표시하되 리스트에 포함시켜라.

{{
  "results": [
    {{
      "id": 기사 ID,
      "score": 1-10,
      "is_duplicate": true/false,
      "strategic_insight": "string"
    }}
  ]
}}
"""
        
        # Call API
        response_text = call_gemini_api(prompt)
        
        if response_text:
            # Parse Response
            try:
                # Remove code blocks if present
                clean_text = response_text.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_text)
                if "results" in data:
                    all_gemini_results.extend(data["results"])
                    print(f"    -> Batch {batch_idx} success: Got {len(data['results'])} results")
            except Exception as e:
                print(f"    -> [ERROR] Batch {batch_idx} processing failed: {e}")
        else:
            print(f"    -> [WARNING] Batch {batch_idx} API call failed")

        # Rate Limit Delay (Free Tier safety: max 1.5 RPM)
        if i + BATCH_SIZE < len(articles_list):
            print("    -> Sleeping 75s to respect shared IP limits...")
            time.sleep(75)

    # Initialize columns
    articles_df['gemini_score'] = 0.0
    articles_df['is_duplicate'] = False
    articles_df['strategic_insight'] = ""
    
    # Map results back to DataFrame
    updates = 0
    for res in all_gemini_results:
        try:
            art_id = res.get('id')
            # Check if index matches (articles_df index is usually the original IDs)
            if art_id in articles_df.index:
                articles_df.at[art_id, 'gemini_score'] = float(res.get('score', 0))
                articles_df.at[art_id, 'is_duplicate'] = res.get('is_duplicate', False)
                articles_df.at[art_id, 'strategic_insight'] = res.get('strategic_insight', '')
                updates += 1
        except Exception as e:
            pass
            
    print(f"  [Gemini] Updated {updates} articles with AI scores")
    return articles_df
