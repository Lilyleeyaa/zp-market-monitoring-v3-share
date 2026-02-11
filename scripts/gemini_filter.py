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

GEMINI_API_KEY = os.getenv('GENAI_API_KEY')
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

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
                print(f"  [WARNING] Gemini API error (attempt {attempt+1}): {response.status_code}")
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
    print("\n[Gemini Filter] Starting batch deduplication and scoring...")
    
    if GEMINI_API_KEY is None:
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
{json.dumps(articles_list, ensure_ascii=False, indent=2)}

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
    print(f"  [Gemini] Processing {len(articles_list)} articles...")
    response_text = call_gemini_api(prompt)
    
    if response_text is None:
        print("  [ERROR] Failed to get Gemini response, skipping filter")
        return articles_df
    
    # Parse Gemini response
    try:
        # Extract JSON from response (handle markdown code blocks)
        json_text = response_text
        if "```json" in response_text:
            json_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_text = response_text.split("```")[1].split("```")[0].strip()
        
        gemini_results = json.loads(json_text)
        
        # Add Gemini scores to DataFrame
        for result in gemini_results.get('results', []):
            idx = result['id']
            if idx in articles_df.index:
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
        
    except Exception as e:
        print(f"  [ERROR] Failed to parse Gemini response: {str(e)}")
        print(f"  [DEBUG] Response preview: {response_text[:500]}...")
        return articles_df
