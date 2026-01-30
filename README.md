# ZP Market Monitoring v2 (NLP)

AI 기반 의료/제약 뉴스 모니터링 시스템

## 🎯 주요 성과

- **중복 제거 정확도**: 8개 → 2개 (75% 개선)
- **AI 추천 성능**: Top-5 Reward **0.6** (3/5개 정확)
- **데이터 품질**: KoNLPy 형태소 분석 기반 중복 제거

## ✨ 핵심 기능

### 3. global 🌍 Multilingual AI Translation
- **Gemini API (High Quality)**: 의학 전문 번역 프롬프트 적용 (예: "건기식" → "Health Functional Food")
- **Prompt Engineering**: 'Konglish' 자동 보정 (예: "프리필드" → "Pre-filled")
- **Hybrid System**: Gemini Quota 초과 시 Google Translate 자동 전환 (3중 안전장치)
- **성능 최적화**: 
  - **Batch Processing**: 기사 제목+요약+키워드 일괄 번역 (속도 3배 ↑)
  - **Caching**: 한 번 번역된 내용은 즉시 로딩 (@st.cache_data)

### 4. 📊 스마트 대시보드
- **AI/VIP 필터**: AI 점수(0.18↑) 또는 중요 키워드 포함 기사만 선별
- **Dynamic Keywords**: 현재 조회된 기사들의 키워드만 필터에 노출
- **💬 KakaoTalk Update**: 
  - AI가 엄선한 핵심 기사만 요약
  - 국/영문 자동 변환 지원
  - 원클릭 복사

## 🚀 빠른 시작

### 설치

```bash
pip install -r requirements.txt
```

### 실행 (로컬)

```bash
# 대시보드 실행
run_dashboard.bat
```

*브라우저에서 http://localhost:8501 자동 오픈*

---

## 📋 주간 워크플로우 (Data Pipeline)

### 1. 뉴스 데이터 수집 (Crawling)

```python
%run scripts/crawl_naver_news_api.py
```

**결과**: `articles_naver_api_YYYYMMDD.csv` (네이버 뉴스 API 기반 수집)

### 2. 라벨링 데이터 준비 (Preprocessing)

```python
%run scripts/prepare_labeling.py
```
# 🏥 ZP Market Monitoring v2 (NLP)

**Last Updated:** 2026-01-30  
AI-powered healthcare news monitoring and analysis system for pharmaceutical business intelligence.

## 🌟 Features

- ✅ **Automated Weekly Crawling**: Collects latest 7 days of pharmaceutical news from Naver
- ✅ **NLP-based Deduplication**: Semantic similarity using Sentence Transformers
- ✅ **Category-Balanced Ranking**: Ensures diverse coverage (Distribution, Client, BD, etc.)
- ✅ **Rule-Based + AI Hybrid**: 70% category scoring + 30% AI prediction
- ✅ **Interactive Dashboard**: Streamlit web interface with real-time filtering
- ✅ **Multi-language Support**: Korean/English translation (Gemini API)
- ✅ **KakaoTalk Summary**: One-click weekly summary generation

## 🎯 System Architecture

### Ranking Algorithm (Current Configuration)

```python
Final Score = 0.7 × Category Score + 0.3 × AI Score

Category Scores:
- Distribution: 6 points
- Client: 5 points
- Zuellig: 5 points
- BD: 4 points
- Others: 3 points

Top 20 Selection:
- Distribution: Top 3 articles
- Client: Top 3 articles
- BD: Top 3 articles
- Zuellig: Top 3 articles
- Other categories: Top 2 each
```

**Why this approach?**
- AI model (AUC ~0.55) has limited predictive power for business-specific relevance
- Rule-based category scoring provides stable, consistent results
- Category balancing prevents single-category dominance

## � Quick Start

### Prerequisites

- Python 3.8+
- Naver API credentials (Client ID & Secret)
- Gemini API key (for translation)

### Installation

```bash
pip install -r requirements.txt
```

### Running the Dashboard

```bash
streamlit run dashboard_app.py
```

Or use the batch file (Windows):
```bash
run_dashboard.bat
```

## � Project Structure

```
├── dashboard_app.py              # Main Streamlit dashboard
├── scripts/

### AI 모델 성능

| 메트릭 | Neural Net (v1) | LightGBM (v2) | 개선 |
|--------|-----------------|---------------|------|
| Top-5 Reward | 0.20 | **0.60** | **3배 ↑** |
| AUC | ~0.40 | **0.61** | 50% ↑ |
| Accuracy | ~0.60 | **0.76** | 26% ↑ |

## 🎓 v1 대비 개선사항

1. **중복 제거**: 단순 문자열 비교 → KoNLPy 형태소 기반
2. **AI 모델**: 3-layer MLP → LightGBM (소규모 데이터 최적화)
3. **데이터 분할**: 시간순 70/30 → Stratified split (공정한 평가)
4. **자동화**: 파일명 하드코딩 → 날짜 자동 감지
5. **실행 편의성**: 수동 명령어 → `.bat` 파일 원클릭

## 📝 라이선스

내부 사용 전용

## 👥 문의

ZP Market Intelligence Team
