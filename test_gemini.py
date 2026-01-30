import requests
import json
import sys

# Force UTF-8 encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

GENAI_API_KEY = "AIzaSyD5HUixHFDEeifmY5NhJCnL4cLlxOp7fp0"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GENAI_API_KEY}"

def test_translate(text):
    print(f"Original: {text}")
    print("-" * 50)
    
    # Mimic dashboard glossary mechanism
    KEYWORD_MAPPING = {"위고비": "Wegovy", "건기식": "Health Functional Food"}
    EXTRA_GLOSSARY = {"건기식": "Health Functional Food"}
    
    full_glossary = {**KEYWORD_MAPPING, **EXTRA_GLOSSARY}
    glossary_context = "\n".join([f"- {k}: {v}" for k, v in full_glossary.items()])
    
    # Pre-process text like dashboard
    processed_text = text
    sorted_terms = sorted(full_glossary.keys(), key=len, reverse=True)
    for kr_term in sorted_terms:
        if kr_term in processed_text:
            processed_text = processed_text.replace(kr_term, full_glossary[kr_term])

    prompt = f"""
    You are a professional pharmaceutical translator. 
    Translate the following Korean text to English.
    
    Rules:
    1. Maintain professional industry terminology.
    2. Use the specific glossary below for strict term matching:
    {glossary_context}
    
    Text to translate:
    "{processed_text}"
    
    Output only the translated English text, no explanations.
    """
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(GEMINI_API_URL, headers=headers, data=json.dumps(payload), timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and result['candidates']:
                translated = result['candidates'][0]['content']['parts'][0]['text'].strip()
                print(f"Gemini:   {translated}")
            else:
                print("Gemini:   [Empty Response]")
        else:
            print(f"Gemini:   [Error {response.status_code}] {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_translate("건기식 시장 이 성장하고 있다")
    test_translate("이 기사는 위고비 에 대한 내용이다")
    test_translate("위고비")
