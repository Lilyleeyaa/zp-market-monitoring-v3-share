import requests
import json

API_KEY = "AIzaSyDUaVhDdxQQGSoudbESVv6PRpZrBW7aT_0"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

data = {
    "contents": [{
        "parts": [{"text": "Hello, is this API working?"}]
    }]
}

print(f"Testing API Key: {API_KEY[:5]}...{API_KEY[-3:]}")
print(f"URL: {URL.replace(API_KEY, 'MASKED_KEY')}")

try:
    response = requests.post(URL, headers={'Content-Type': 'application/json'}, json=data)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("Success! Response:", response.json()['candidates'][0]['content']['parts'][0]['text'])
    else:
        print("Error Response:", response.text)

except Exception as e:
    print(f"Exception: {e}")
