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
    GEMINI_API_KEY = GEMINI_API_KEY.strip()

# Primary endpoint (v1 for stability)
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

# BD Manager Persona Prompt
BD_PERSONA_PROMPT = """
[Role: Senior Business Development Manager at Zuellig Pharma Korea]
너는 쥴릭파마코리아(Zuellig Pharma Korea)의 시니어 사업개발(BD) 매니저야. 너의 임무는 수많은 제약 산업 뉴스 중 우리 회사의 의약품 유통(Distribution) 및 커머셜(Commercial) 비즈니스에 실질적인 영향을 미칠 핵심 기사를 선별하고 전략적 점수를 매기는 것이다.

[Core Interest & Priorities]
아래 기준에 따라 기사의 중요도를 1점(무관)에서 10점(매우 중요) 사이로 평가하라.
1. 의약품 유통 (Distribution & Logistics): 경쟁사 동향(지오영, 백제약품, 용마로지스 등), 유통 구조 변화.
2. 커머셜 (Commercial & Solution): 고객사 동향(신약 출시, 철수), 전략적 파트너십(Co-promotion).
3. 약가 및 제도 (Market Access): 약가 인하, 급여 등재 규제.

[Strict Filtering Rules]
다음은 1~2점으로 제외하라: 단순 수상/포상, 단순 실적 공시(전략 없으면), 단순 CSR, 단순 인사, 초기 R&D(임상 1상 등).
"""

def call_gemini_api(prompt, max_retries=5):
    """Call Gemini API with retry logic and multi-endpoint fallback"""
    if not GEMINI_API_KEY:
        return None

    # Try different endpoints/models to overcome potential regional/tier blocks
    Endpoints = [
        GEMINI_API_URL,
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    ]
    
    for url_idx, current_url in enumerate(Endpoints):
        model_name = current_url.split("/models/")[1].split(":")[0]
        if url_idx > 0:
            print(f"  [INFO] Trying fallback model: {model_name}")

        for attempt in range(max_retries):
            try:
                masked_url = current_url.replace(GEMINI_API_KEY, "KEY_MASKED")
                if attempt == 0:
                    print(f"  [DEBUG] Requesting: {masked_url}")

                response = requests.post(
                    current_url,
                    headers={'Content-Type': 'application/json'},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048}
                    },
                    timeout=45
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if 'candidates' in result and result['candidates']:
                        return result['candidates'][0]['content']['parts'][0]['text']
                    return None
                elif response.status_code == 429:
                    wait_time = 80 * (attempt + 1) # Very conservative for Free Tier (1.5 RPM)
                    print(f"  [429] Rate Limit. Resp: {response.text[:100]}")
                    print(f"  [429] Waiting {wait_time}s before retry {attempt+1}/{max_retries}...")
                    time.sleep(wait_time)
                elif response.status_code == 404:
                    print(f"  [404] Model {model_name} not found. Skipping to next fallback.")
                    break # Go to next endpoint
                else:
                    print(f"  [WARNING] API Error {response.status_code}. Resp: {response.text[:100]}")
                    time.sleep(10 * (attempt + 1))
            except Exception as e:
                print(f"  [WARNING] Request failed: {str(e)}")
                time.sleep(15)
    
    return None

def gemini_batch_deduplicate_and_score(articles_df):
    """Batch process with strict rate limit respect"""
    print("\n[Gemini Filter] Process starting...")
    
    if not GEMINI_API_KEY:
        print("  [ERROR] No API Key provided.")
        return articles_df
    
    articles_list = []
    for idx, row in articles_df.iterrows():
        articles_list.append({
            "id": idx, "title": row['title'], "summary": row.get('summary', ''), "category": row.get('category', '')
        })
    
    # Large batches = fewer requests (better for RPM limits)
    BATCH_SIZE = 20 
    all_gemini_results = []
    total_batches = (len(articles_list) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for i in range(0, len(articles_list), BATCH_SIZE):
        batch_idx = i // BATCH_SIZE + 1
        chunk = articles_list[i:i + BATCH_SIZE]
        print(f"  [Gemini] Batch {batch_idx}/{total_batches} ({len(chunk)} articles)...")
        
        prompt = f"""{BD_PERSONA_PROMPT}
[Task]
1. 중복 제거: 동일 이벤트 기사 중 정보가 가장 많은 것 1개만 남길 것.
2. 각 기사 평가 (score: 1-10, is_duplicate: true/false, strategic_insight: 1문장 요약)

[Articles]
{json.dumps(chunk, ensure_ascii=False, indent=2)}

[Output Format JSON]
{{ "results": [ {{ "id": ID, "score": 1-10, "is_duplicate": bool, "strategic_insight": "string" }} ] }}
"""
        
        response_text = call_gemini_api(prompt)
        
        if response_text:
            try:
                clean_text = response_text.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_text)
                if "results" in data:
                    all_gemini_results.extend(data["results"])
                    print(f"    -> Success: Got {len(data['results'])} items")
            except Exception as e:
                print(f"    -> [ERROR] Parse failed: {e}")
        
        if i + BATCH_SIZE < len(articles_list):
            print("    -> Cool-down 85s (Shared IP protection)...")
            time.sleep(85)

    # Map back
    articles_df['gemini_score'] = 0.0
    articles_df['is_duplicate'] = False
    articles_df['strategic_insight'] = ""
    
    updates = 0
    for res in all_gemini_results:
        art_id = res.get('id')
        if art_id in articles_df.index:
            articles_df.at[art_id, 'gemini_score'] = float(res.get('score', 0))
            articles_df.at[art_id, 'is_duplicate'] = res.get('is_duplicate', False)
            articles_df.at[art_id, 'strategic_insight'] = res.get('strategic_insight', '')
            updates += 1
            
    print(f"  [Gemini] Finished. {updates} articles updated.")
    return articles_df
