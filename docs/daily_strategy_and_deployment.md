# Daily 크롤링 전략 & GitHub Private 배포 가이드

## 1. Daily 크롤링 기간 전략

### 옵션 비교

#### 옵션 A: 당일 크롤링 (00:00 ~ 현재)
```python
# 예: 2026-02-05 06:00 실행 시
start_date = datetime(2026, 2, 5, 0, 0, 0)  # 2월 5일 00:00
end_date = datetime.now()  # 2월 5일 06:00
# → 6시간치 기사 수집
```

**장점**:
- ✅ 실시간성 높음 (당일 새벽 기사까지)
- ✅ 진짜 "Daily" 개념

**단점**:
- ❌ 기사 수가 매우 적음 (6시간치만)
- ❌ 06:00 실행 시 새벽 기사만 → 의미 없을 수 있음
- ❌ 마켓 센싱에 불충분

---

#### 옵션 B: 전날 크롤링 (전날 00:00 ~ 23:59) ⭐ **추천**
```python
# 예: 2026-02-05 06:00 실행 시
yesterday = datetime.now() - timedelta(days=1)
start_date = yesterday.replace(hour=0, minute=0, second=0)  # 2월 4일 00:00
end_date = yesterday.replace(hour=23, minute=59, second=59)  # 2월 4일 23:59
# → 전날 하루치 기사 수집 (24시간)
```

**장점**:
- ✅ **충분한 기사 수** (하루치 전체)
- ✅ **완전한 데이터** (전날 하루가 완료됨)
- ✅ **마켓 센싱에 적합** (전날 동향 파악)
- ✅ **에이전시 비교 가능** (에이전시도 보통 전날 기준)
- ✅ **비즈니스 관점**: 아침 출근 시 "어제 무슨 일 있었나" 확인

**단점**:
- ⚠️ 실시간성 약간 낮음 (하루 딜레이)
  - 하지만 06:00 실행이므로 실질적으로 큰 차이 없음

---

#### 옵션 C: 지난 24시간 (현재 - 24시간)
```python
# 예: 2026-02-05 06:00 실행 시
end_date = datetime.now()  # 2월 5일 06:00
start_date = end_date - timedelta(hours=24)  # 2월 4일 06:00
# → 2월 4일 06:00 ~ 2월 5일 06:00
```

**장점**:
- ✅ 정확히 24시간치
- ✅ 실시간성 높음

**단점**:
- ❌ 날짜 경계가 애매함 (4일 오후 + 5일 새벽)
- ❌ "Daily" 개념과 맞지 않음 (날짜별 구분 어려움)
- ❌ 에이전시 비교 어려움 (에이전시는 보통 날짜 단위)

---

### 최종 추천: **옵션 B (전날 크롤링)** ⭐

**이유**:
1. **비즈니스 목적에 부합**
   - 아침 출근 시 "어제 시장에서 무슨 일이 있었나" 확인
   - 에이전시 대체 검증에 적합 (에이전시도 전날 기준)

2. **데이터 완전성**
   - 전날 하루가 완전히 끝난 상태 → 누락 없음
   - 날짜별 명확한 구분 가능

3. **충분한 기사 수**
   - 24시간치 → 마켓 센싱에 충분

4. **구현 간단**
   - 날짜 계산 명확
   - 파일명도 깔끔 (`data/daily/2026-02-04/`)

**구현 코드**:
```python
def get_daily_date_range():
    """Daily 크롤링 날짜 범위 (전날 하루)"""
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    
    start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=0)
    
    return start_date, end_date

# 사용 예시
start, end = get_daily_date_range()
print(f"크롤링 기간: {start} ~ {end}")
# 2026-02-05 06:00 실행 시
# → 크롤링 기간: 2026-02-04 00:00:00 ~ 2026-02-04 23:59:59
```

---

## 2. GitHub Private + Streamlit Cloud 배포

### 과거 문제 원인 분석

**"Private으로 하니까 안 됐었다"는 이유**:

1. **GitHub OAuth 권한 문제**
   - Streamlit Cloud가 Private repo 접근 권한을 받지 못함
   - 해결: GitHub에서 Streamlit에 명시적으로 권한 부여

2. **Secrets 설정 누락**
   - Private repo의 환경 변수/API 키가 Streamlit Cloud에 없음
   - 해결: Streamlit Cloud Secrets에 수동 추가

3. **잘못된 배포 순서**
   - Private repo 생성 → 배포 시도 → 실패
   - 올바른 순서: Public으로 배포 성공 → Private 전환 → 권한 재설정

---

### 올바른 배포 방법 (2가지)

#### 방법 1: 처음부터 Private으로 배포 (권장)

**단계별 가이드**:

```bash
# 1. GitHub에서 Private Repo 생성
Repository name: zp-market-monitoring-v3-share
Visibility: Private ✅
Initialize: README.md 체크

# 2. 로컬에서 코드 push
cd "c:\Users\samsung\OneDrive\Desktop\GY\AntiGravity\ZP Market Monitoring v3 (Share)"
git init
git remote add origin https://github.com/Lilyleeyaa/zp-market-monitoring-v3-share.git
git add .
git commit -m "Initial commit - v3 with authentication"
git push -u origin main
```

**3. Streamlit Cloud 배포**:

1. https://streamlit.io/cloud 접속 → 로그인
2. "New app" 클릭
3. **Repository 선택**:
   - Repository: `Lilyleeyaa/zp-market-monitoring-v3-share` (Private 표시됨)
   - Branch: `main`
   - Main file path: `dashboards/internal_weekly.py`

4. **GitHub 권한 요청 팝업**:
   ```
   Streamlit Cloud wants to access your private repository
   [Authorize Streamlit] 버튼 클릭 ✅
   ```

5. **Secrets 설정** (Advanced settings):
   ```toml
   # .streamlit/secrets.toml 내용 복사
   GENAI_API_KEY = "AIzaSy..."
   
   # auth/config.yaml 내용 복사
   [auth]
   common_password_hash = "5e88489..."
   internal_domains = ["@lgchem.com", "@lgls.com"]
   ```

6. **Deploy** 클릭

**결과**:
- ✅ Private repo에서 바로 배포 성공
- ✅ URL: `https://zp-internal-weekly.streamlit.app`

---

#### 방법 2: Public → Private 전환 (기존 앱이 있는 경우)

**현재 v2가 Public으로 배포되어 있다면**:

```bash
# 1. GitHub에서 Private으로 전환
Settings → Danger Zone → Change visibility → Make private

# 2. Streamlit Cloud에서 권한 재설정
Streamlit Cloud → 해당 앱 → Settings → GitHub Connection
→ "Reconnect" 버튼 클릭
→ GitHub 권한 재승인 팝업 → Authorize

# 3. Reboot 앱
Settings → Reboot app
```

**주의사항**:
- ⚠️ Private 전환 후 즉시 Reconnect 해야 함
- ⚠️ Secrets가 유지되는지 확인 필요

---

### 배포 후 확인사항

**1. Private Repo 보안 확인**:
```bash
# 로그아웃 상태에서 GitHub URL 접속
https://github.com/Lilyleeyaa/zp-market-monitoring-v3-share

# 결과: "404 Not Found" 또는 "You don't have access" ✅
```

**2. Streamlit 앱 접근 확인**:
```bash
# 브라우저에서 URL 접속
https://zp-internal-weekly.streamlit.app

# 결과: 로그인 화면 표시 ✅
```

**3. 모바일 테스트**:
- GitHub 링크: 접근 불가 ✅
- Streamlit 앱: 로그인 화면 표시 ✅

---

### 문제 해결 (Troubleshooting)

#### 문제 1: "Repository not found" 에러
**원인**: Streamlit이 Private repo 접근 권한 없음
**해결**:
```bash
1. Streamlit Cloud → Settings → GitHub Connection
2. "Reconnect" 클릭
3. GitHub 팝업에서 "Authorize Streamlit" 클릭
4. Private repo 체크박스 선택 ✅
```

#### 문제 2: "Module not found" 에러
**원인**: `requirements.txt` 누락 또는 잘못됨
**해결**:
```bash
# requirements.txt 확인
streamlit
pandas
pyyaml
requests
# ... (필요한 모든 패키지)
```

#### 문제 3: "Secrets not found" 에러
**원인**: Streamlit Cloud Secrets 설정 안 됨
**해결**:
```bash
1. Streamlit Cloud → 앱 Settings → Secrets
2. auth/config.yaml 내용 복사 붙여넣기
3. Save
4. Reboot app
```

---

## 3. 최종 권장 사항

### Daily 크롤링
- ✅ **전날 하루치 크롤링** (00:00 ~ 23:59)
- ✅ 매일 06:00 실행
- ✅ 파일명: `data/daily/YYYY-MM-DD/`
- ✅ 에이전시 비교 가능

### GitHub + Streamlit 배포
- ✅ **처음부터 Private Repo로 생성**
- ✅ Streamlit Cloud에서 권한 승인
- ✅ Secrets 수동 설정
- ✅ 3개 앱 별도 배포:
  1. `internal-weekly` (내부용)
  2. `external-weekly` (MNC_BD용)
  3. `daily-validation` (검증용)

### 보안
- ✅ GitHub Private Repo
- ✅ Streamlit 앱 인증 (이메일 + 공통 비밀번호)
- ✅ 2중 보안 (Repo + App)
- ✅ 모바일 접근 제어

---

## 4. 구현 체크리스트

- [ ] Daily 크롤링 스크립트 수정 (전날 기준)
- [ ] GitHub Private Repo 생성
- [ ] Streamlit Cloud 배포 (3개 앱)
- [ ] GitHub 권한 승인
- [ ] Secrets 설정
- [ ] 접근 테스트 (Desktop + Mobile)
- [ ] 에이전시 키워드 확인 및 추가
