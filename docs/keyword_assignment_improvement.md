# 키워드 할당 로직 분석 및 개선 방안

## 현재 키워드 할당 방식 (v2)

### 1. 크롤링 단계 (Line 650)
```python
art['search_keyword'] = keyword  # 검색에 사용한 키워드 저장
```
- **문제**: 검색 키워드를 그대로 할당
- **예시**: "공동판매"로 검색 → 기사에 "공동판매"가 없어도 `search_keyword = "공동판매"`

### 2. 카테고리 재분류 (Line 673-700)
```python
# Priority 1: Distribution
if any(k.lower() in text for k in DISTRIBUTION_KEYWORDS):
    art['category'] = 'Distribution'
    continue

# Priority 2: Zuellig
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
```
- **장점**: 카테고리는 본문 기준으로 재분류됨
- **문제**: `keywords` 필드는 여전히 검색 키워드 그대로

### 3. 최종 키워드 할당 (Line 782)
```python
df['keywords'] = df['search_keyword']
```
- **문제**: 검색 키워드를 그대로 `keywords` 컬럼에 복사
- **결과**: 기사 내용과 무관한 키워드 할당 가능

---

## 문제 사례

### 예시 1: 잘못된 키워드 할당
```
검색 키워드: "공동판매"
기사 제목: "노보노디스크, 위고비 국내 출시"
기사 본문: "노보노디스크가 비만치료제 위고비를 국내에 출시했다..."

현재 결과:
- category: "Client" (✅ 정확 - 노보노디스크 포함)
- keywords: "공동판매" (❌ 부정확 - 기사에 없음)

기대 결과:
- category: "Client" (✅)
- keywords: "노보노디스크" 또는 "위고비" (✅)
```

### 예시 2: 중복 키워드
```
기사 제목: "쥴릭, 지오영과 유통계약 체결"
기사 본문: "쥴릭파마가 지오영과 공동판매 계약을 맺었다..."

현재 결과:
- 검색 키워드: "쥴릭" (첫 번째 검색)
- category: "Distribution" (✅ - 지오영 포함)
- keywords: "쥴릭" (⚠️ 부분적 정확 - 지오영, 공동판매도 중요)

기대 결과:
- keywords: "쥴릭, 지오영, 공동판매" (✅ 모든 중요 키워드)
```

---

## 개선 방안

### 방안 1: 제목 우선 키워드 추출 ⭐ **추천**

**로직**:
1. 제목에서 키워드 매칭 (최우선)
2. 본문 요약 첫 문장에서 키워드 매칭
3. 전체 본문에서 키워드 매칭
4. 검색 키워드 (최후 폴백)

**장점**:
- ✅ 제목에 있는 키워드 = 기사의 핵심 주제
- ✅ 빠른 처리 (제목만 확인)
- ✅ 사용자 제안과 일치

**구현 코드**:
```python
def assign_primary_keyword(article, all_keywords):
    """
    제목 우선 키워드 할당
    
    Args:
        article: 기사 dict (title, summary, search_keyword)
        all_keywords: 모든 키워드 리스트
    
    Returns:
        primary_keyword: 가장 관련성 높은 키워드
    """
    title = article['title'].lower()
    summary = article['summary'].lower()
    
    # 1. 제목에서 매칭 (최우선)
    title_matches = [kw for kw in all_keywords if kw.lower() in title]
    if title_matches:
        # 여러 개 있으면 가장 긴 키워드 선택 (더 구체적)
        return max(title_matches, key=len)
    
    # 2. 본문 요약 첫 100자에서 매칭
    summary_first = summary[:100]
    summary_matches = [kw for kw in all_keywords if kw.lower() in summary_first]
    if summary_matches:
        return max(summary_matches, key=len)
    
    # 3. 전체 본문에서 매칭
    full_matches = [kw for kw in all_keywords if kw.lower() in summary]
    if full_matches:
        return max(full_matches, key=len)
    
    # 4. 검색 키워드 (폴백)
    return article['search_keyword']
```

**적용 예시**:
```python
# 모든 키워드 통합
ALL_KEYWORDS = (DISTRIBUTION_KEYWORDS + BD_KEYWORDS + APPROVAL_KEYWORDS +
                REIMBURSEMENT_KEYWORDS + ZUELLIG_KEYWORDS + CLIENT_KEYWORDS +
                THERAPEUTIC_KEYWORDS + SUPPLY_KEYWORDS)

# 각 기사에 적용
for art in all_articles:
    art['keywords'] = assign_primary_keyword(art, ALL_KEYWORDS)
```

---

### 방안 2: 중요도 기반 다중 키워드 할당

**로직**:
- 기사에 포함된 모든 키워드 추출
- 중요도 순으로 정렬 (VIP > 일반)
- 상위 3개까지 할당

**장점**:
- ✅ 기사의 모든 중요 측면 포착
- ✅ 검색 필터링 향상

**단점**:
- ⚠️ 대시보드에서 표시 복잡해짐
- ⚠️ 키워드가 너무 많으면 혼란

**구현 코드**:
```python
def assign_multiple_keywords(article, all_keywords, max_keywords=3):
    """
    중요도 기반 다중 키워드 할당
    """
    title = article['title'].lower()
    summary = article['summary'].lower()
    text = title + " " + summary
    
    # VIP 키워드 (회사명, 제품명)
    VIP_KEYWORDS = ZUELLIG_KEYWORDS + CLIENT_KEYWORDS
    
    # 매칭된 키워드 찾기
    matched_keywords = []
    
    # 1. VIP 키워드 우선
    for kw in VIP_KEYWORDS:
        if kw.lower() in text:
            matched_keywords.append((kw, 'vip'))
    
    # 2. 일반 키워드
    for kw in all_keywords:
        if kw.lower() in text and kw not in [m[0] for m in matched_keywords]:
            # 제목에 있으면 우선순위 높임
            priority = 'title' if kw.lower() in title else 'summary'
            matched_keywords.append((kw, priority))
    
    # 3. 우선순위 정렬 (vip > title > summary)
    priority_order = {'vip': 0, 'title': 1, 'summary': 2}
    matched_keywords.sort(key=lambda x: priority_order[x[1]])
    
    # 4. 상위 N개 선택
    top_keywords = [kw for kw, _ in matched_keywords[:max_keywords]]
    
    # 5. 없으면 검색 키워드
    if not top_keywords:
        top_keywords = [article['search_keyword']]
    
    return ", ".join(top_keywords)
```

**결과 예시**:
```
기사: "쥴릭, 지오영과 유통계약 체결"
keywords: "쥴릭, 지오영, 유통계약"  (3개)
```

---

### 방안 3: 하이브리드 (단일 + 서브 키워드)

**로직**:
- `primary_keyword`: 제목 우선 단일 키워드
- `sub_keywords`: 본문의 추가 키워드 (최대 2개)

**장점**:
- ✅ 명확한 주 키워드
- ✅ 추가 정보도 보존

**구현 코드**:
```python
def assign_hybrid_keywords(article, all_keywords):
    """
    하이브리드: 주 키워드 + 서브 키워드
    """
    title = article['title'].lower()
    summary = article['summary'].lower()
    
    # 1. 주 키워드 (제목 우선)
    primary = assign_primary_keyword(article, all_keywords)
    
    # 2. 서브 키워드 (본문에서 추가)
    sub_keywords = []
    for kw in all_keywords:
        if kw.lower() in summary and kw != primary:
            sub_keywords.append(kw)
            if len(sub_keywords) >= 2:
                break
    
    # 3. 결합
    if sub_keywords:
        return f"{primary} ({', '.join(sub_keywords)})"
    else:
        return primary
```

**결과 예시**:
```
keywords: "쥴릭 (지오영, 유통계약)"
```

---

## 최종 추천: 방안 1 (제목 우선 단일 키워드)

### 이유

1. **사용자 제안과 일치**
   - "제목이나 본문 요약 처음에 나오는 부분"

2. **단순하고 명확**
   - 하나의 주 키워드만 표시
   - 대시보드에서 보기 쉬움

3. **빠른 처리**
   - 제목만 확인하면 대부분 해결

4. **정확도 향상**
   - 제목 = 기사의 핵심 주제
   - 검색 키워드보다 훨씬 정확

### 구현 위치

**파일**: `scripts/crawl_naver_news_api.py`
**라인**: 782 (현재 `df['keywords'] = df['search_keyword']`)

**변경 전**:
```python
df['keywords'] = df['search_keyword']
```

**변경 후**:
```python
# 모든 키워드 통합
ALL_KEYWORDS = (DISTRIBUTION_KEYWORDS + BD_KEYWORDS + APPROVAL_KEYWORDS +
                REIMBURSEMENT_KEYWORDS + ZUELLIG_KEYWORDS + CLIENT_KEYWORDS +
                THERAPEUTIC_KEYWORDS + SUPPLY_KEYWORDS)

# 제목 우선 키워드 할당
df['keywords'] = df.apply(
    lambda row: assign_primary_keyword(row, ALL_KEYWORDS), 
    axis=1
)
```

---

## 추가 개선: 키워드 우선순위

**문제**: 여러 키워드가 제목에 있을 때 어떤 것을 선택?

**해결**: 카테고리 우선순위 적용

```python
def assign_primary_keyword_with_priority(article, all_keywords):
    """
    제목 우선 + 카테고리 우선순위
    """
    title = article['title'].lower()
    summary = article['summary'].lower()
    
    # 제목에서 매칭
    title_matches = [kw for kw in all_keywords if kw.lower() in title]
    
    if title_matches:
        # 카테고리별 우선순위
        PRIORITY_ORDER = [
            ZUELLIG_KEYWORDS,      # 1순위: 회사 키워드
            DISTRIBUTION_KEYWORDS, # 2순위: 유통
            CLIENT_KEYWORDS,       # 3순위: 고객사
            BD_KEYWORDS,           # 4순위: BD
            # ... 나머지
        ]
        
        # 우선순위 높은 카테고리부터 확인
        for keyword_group in PRIORITY_ORDER:
            for kw in title_matches:
                if kw in keyword_group:
                    return kw
        
        # 우선순위 없으면 가장 긴 키워드
        return max(title_matches, key=len)
    
    # 본문 요약 첫 100자
    summary_first = summary[:100]
    summary_matches = [kw for kw in all_keywords if kw.lower() in summary_first]
    if summary_matches:
        return max(summary_matches, key=len)
    
    # 전체 본문
    full_matches = [kw for kw in all_keywords if kw.lower() in summary]
    if full_matches:
        return max(full_matches, key=len)
    
    # 폴백
    return article['search_keyword']
```

---

## 검증 방법

### 1. 수동 검증
```python
# 샘플 기사 10개 확인
sample = df.sample(10)
for _, row in sample.iterrows():
    print(f"제목: {row['title']}")
    print(f"키워드: {row['keywords']}")
    print(f"검색어: {row['search_keyword']}")
    print(f"일치: {'✅' if row['keywords'] in row['title'] else '❌'}")
    print("-" * 60)
```

### 2. 통계 분석
```python
# 키워드가 제목에 포함된 비율
title_match_rate = df.apply(
    lambda row: row['keywords'].lower() in row['title'].lower(), 
    axis=1
).mean()

print(f"제목 일치율: {title_match_rate * 100:.1f}%")
# 목표: 80% 이상
```

---

## 구현 우선순위

1. **즉시 구현**: 방안 1 (제목 우선 단일 키워드)
2. **v3.1 고려**: 방안 3 (하이브리드)
3. **향후 검토**: 방안 2 (다중 키워드)

---

## 요약

### 현재 문제
- ❌ 검색 키워드를 그대로 할당
- ❌ 기사 내용과 무관한 키워드 표시

### 해결 방법
- ✅ 제목에서 키워드 우선 추출
- ✅ 본문 요약 첫 부분 확인
- ✅ 카테고리 우선순위 적용

### 기대 효과
- ✅ 키워드-기사 일치율 80%+ 달성
- ✅ 대시보드 신뢰도 향상
- ✅ 사용자 경험 개선
