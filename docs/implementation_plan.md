# ZP Market Monitoring v3 Share - 설계 제안서

## 문제 분석

### 현재 상황
1. **v2 Weekly 버전**: 링크가 오픈되어 있어 접근 제한 필요
2. **외부 공유 필요**: MNC_BD Community (다수 인원)에 공유하되 경쟁사 정보는 제외
3. **Daily 검증 필요**: 에이전시 대체 검증 - **매일 당일 기사만** 수집
4. **Streamlit 동작 방식**: 접속 시마다 스크립트 재실행 → 크롤링 반복 문제
5. **GitHub 보안**: 현재 Public repo → 코드 및 README 노출 우려

### 핵심 과제
- **접근 제어**: 이메일 기반, 공통 비밀번호 (MNC_BD 다수 인원)
- **키워드 구조 복잡도**:
  - Weekly: 기존 키워드 (Daily 키워드 제외)
  - Daily: 별도 키워드 (Weekly와 중복 방지)
  - 외부용: 경쟁사 제외 + 회사명 키워드 포함
- **성능 최적화**: 크롤링-대시보드 분리
- **관리 효율성**: 단일 코드베이스 + 설정 파일
- **코드 보안**: Private GitHub Repository

---

## 제안 아키텍처

### 1. 프로젝트 구조

```
ZP Market Monitoring v3 (Share)/
├── data/                          # 데이터 저장소 (gitignore)
│   ├── weekly/                    # Weekly 크롤링 결과
│   │   ├── 2026-W05/
│   │   │   ├── raw_articles.csv
│   │   │   ├── ranked_articles.csv
│   │   │   └── metadata.json
│   │   └── latest -> 2026-W05/   # 심볼릭 링크
│   ├── daily/                     # Daily 크롤링 결과
│   │   ├── 2026-02-05/
│   │   └── latest -> 2026-02-05/
│   └── cache/                     # API 캐시
│
├── scripts/                       # 백엔드 스크립트
│   ├── crawl_scheduler.py        # 크롤링 스케줄러 (Weekly/Daily)
│   ├── crawl_naver_news_api.py   # 네이버 뉴스 크롤링
│   ├── train_lgbm_model.py       # LGBM 모델 학습
│   ├── rank_articles.py          # 기사 랭킹
│   └── config.py                 # 설정 관리
│
├── dashboards/                    # 대시보드 앱들
│   ├── internal_weekly.py        # 내부용 Weekly (경쟁사 포함)
│   ├── external_weekly.py        # 외부용 Weekly (경쟁사 제외)
│   ├── daily_validation.py       # Daily 검증용
│   └── shared_components.py      # 공통 컴포넌트
│
├── auth/                          # 인증 시스템
│   ├── users.yaml                # 사용자 정보 (gitignore)
│   ├── authenticator.py          # Streamlit-Authenticator
│   └── access_control.py         # 권한 관리
│
├── config/                        # 설정 파일
│   ├── keywords.yaml             # 키워드 설정
│   │   ├── internal:             # 내부용 (경쟁사 포함)
│   │   └── external:             # 외부용 (경쟁사 제외)
│   ├── agency_keywords.yaml      # 에이전시 키워드
│   └── streamlit_config.toml     # Streamlit 설정
│
├── requirements.txt
├── .env.example                   # 환경 변수 템플릿
└── README.md
```

### 2. 핵심 설계 원칙

#### A. 데이터 파이프라인 분리 (크롤링 ↔ 대시보드)

**문제점**: 현재는 대시보드 접속 시마다 크롤링 실행
**해결책**: 크롤링을 별도 스케줄러로 분리

```python
# scripts/crawl_scheduler.py
# Weekly: 매주 금요일 06:00 실행 → data/weekly/YYYY-WW/ 저장
# Daily: 매일 06:00 실행 → data/daily/YYYY-MM-DD/ 저장
```

**장점**:
- 대시보드 로딩 속도 향상 (크롤링 없이 저장된 데이터만 읽음)
- 데이터 일관성 보장 (같은 기간 동안 동일 데이터)
- API 호출 최소화

#### B. 단일 코드베이스 + 설정 기반 분기

**문제점**: 여러 대시보드 링크 관리 복잡
**해결책**: 하나의 코드베이스, 설정 파일로 동작 제어

```yaml
# config/keywords.yaml
internal:
  important_keywords:
    - "제픽스"
    - "제픽스펜"
    # ... 기존 키워드
  competitor_keywords:  # 경쟁사 (내부 전용)
    - "노보 노디스크"
    - "일라이 릴리"
    - "사노피"
    - "머크"
    # ...

external:
  important_keywords:
    - "제픽스"
    - "제픽스펜"
    # ... 동일
  competitor_keywords: []  # 외부에는 경쟁사 제외
```

#### C. Streamlit 인증 시스템

**Streamlit-Authenticator** 라이브러리 사용 (가장 검증된 방법)

```python
# auth/users.yaml (예시)
credentials:
  usernames:
    # 내부 사용자
    hong_gildong:
      email: hong@company.com
      name: 홍길동
      password: $2b$12$hashed_password  # bcrypt 해시
      access_level: internal
    
    kim_chulsoo:
      email: kim@company.com
      name: 김철수
      password: $2b$12$hashed_password
      access_level: internal
    
    # 외부 사용자 (MNC_BD Community)
    mnc_member1:
      email: member1@external.com
      name: MNC Member 1
      password: $2b$12$hashed_password
      access_level: external
```

**대시보드별 접근 제어**:
```python
# dashboards/internal_weekly.py
if st.session_state["access_level"] != "internal":
    st.error("내부 사용자만 접근 가능합니다.")
    st.stop()
```

#### D. 배포 전략

**옵션 1: Streamlit Cloud (권장)**
- **장점**: 무료, 관리 편함, GitHub 연동
- **방법**: 
  - Private GitHub repo 생성
  - 3개의 앱 배포:
    1. `internal-weekly` (내부용 Weekly)
    2. `external-weekly` (외부용 Weekly)
    3. `daily-validation` (Daily 검증용)
  - 각 앱마다 다른 URL 생성
  - `users.yaml`은 Streamlit Cloud Secrets에 저장

**옵션 2: 자체 서버**
- **장점**: 완전한 제어
- **단점**: 서버 관리 필요

---

## 상세 구현 계획

### Phase 1: 프로젝트 셋업 및 데이터 파이프라인 분리

#### 1.1 새 프로젝트 생성
```
c:\Users\samsung\OneDrive\Desktop\GY\AntiGravity\ZP Market Monitoring v3 (Share)
```

#### 1.2 크롤링 스케줄러 구현
- v2의 크롤링 로직 재사용
- Weekly/Daily 모드 지원
- 결과를 `data/weekly/` 또는 `data/daily/`에 저장
- Windows Task Scheduler 설정

#### 1.3 대시보드 데이터 로딩 수정
- 크롤링 제거
- `data/weekly/latest/` 또는 `data/daily/latest/`에서 읽기

---

### Phase 2: 인증 시스템 구현

#### 2.1 간소화된 인증 시스템 (이메일 + 공통 비밀번호)

**요구사항**:
- MNC_BD 인원이 많아 개별 비밀번호 관리 어려움
- 이메일로 사용자 식별, 공통 비밀번호 1개 사용
- 이메일 도메인으로 내부/외부 자동 구분

```python
# auth/simple_auth.py
import streamlit as st
import yaml
import hashlib

def load_auth_config():
    """인증 설정 로드"""
    with open('auth/config.yaml') as f:
        return yaml.safe_load(f)

def hash_password(password):
    """비밀번호 해싱"""
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(mode='weekly'):
    """
    간소화된 인증
    mode: 'weekly' or 'daily'
    Returns: (email, access_level) or None
    """
    config = load_auth_config()
    
    # 세션에 이미 로그인되어 있으면 스킵
    if 'authenticated' in st.session_state and st.session_state['authenticated']:
        return st.session_state['email'], st.session_state['access_level']
    
    # 로그인 폼
    st.title("🔐 로그인")
    
    with st.form("login_form"):
        email = st.text_input("이메일", placeholder="your.email@company.com")
        password = st.text_input("비밀번호", type="password")
        submit = st.form_submit_button("로그인")
        
        if submit:
            # 비밀번호 확인 (공통 비밀번호)
            if hash_password(password) != config['common_password_hash']:
                st.error("❌ 비밀번호가 올바르지 않습니다.")
                st.stop()
            
            # 이메일 도메인으로 접근 레벨 판단
            access_level = 'external'  # 기본값
            
            for domain in config['internal_domains']:
                if email.endswith(domain):
                    access_level = 'internal'
                    break
            
            # Daily는 내부 전용
            if mode == 'daily' and access_level != 'internal':
                st.error("❌ Daily 버전은 내부 사용자만 접근 가능합니다.")
                st.stop()
            
            # 세션에 저장
            st.session_state['authenticated'] = True
            st.session_state['email'] = email
            st.session_state['access_level'] = access_level
            
            st.success(f"✅ 로그인 성공! ({access_level})")
            st.rerun()
    
    st.stop()  # 로그인 전까지 대시보드 표시 안 함

def get_current_user():
    """현재 로그인한 사용자 정보 반환"""
    if 'authenticated' not in st.session_state:
        return None, None
    return st.session_state.get('email'), st.session_state.get('access_level')
```

**설정 파일**:
```yaml
# auth/config.yaml
common_password_hash: "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"  # 'password123' 예시

internal_domains:
  - "@lgchem.com"
  - "@lgls.com"
  - "@yourcompany.com"
  # ... 내부 이메일 도메인

# 외부 도메인은 별도 관리 안 함 (내부 아니면 모두 외부)
```

**비밀번호 생성 스크립트**:
```python
# auth/generate_password.py
import hashlib

password = input("공통 비밀번호 입력: ")
password_hash = hashlib.sha256(password.encode()).hexdigest()
print(f"\nconfig.yaml에 추가할 해시:\ncommon_password_hash: \"{password_hash}\"")
```

#### 2.2 대시보드에서 인증 사용
```python
# dashboards/internal_weekly.py
import streamlit as st
from auth.simple_auth import authenticate, get_current_user

# 페이지 설정
st.set_page_config(page_title="ZP Market Monitoring - Internal Weekly", layout="wide")

# 인증 (내부 전용)
email, access_level = authenticate(mode='weekly')

if access_level != 'internal':
    st.error("❌ 이 대시보드는 내부 사용자만 접근 가능합니다.")
    st.stop()

# 대시보드 메인 코드
st.title("📊 ZP Market Monitoring - Internal Weekly")
st.caption(f"로그인: {email}")
# ...
```

```python
# dashboards/external_weekly.py
import streamlit as st
from auth.simple_auth import authenticate, get_current_user

st.set_page_config(page_title="ZP Market Monitoring - MNC_BD", layout="wide")

# 인증 (내부/외부 모두 가능)
email, access_level = authenticate(mode='weekly')

st.title("📊 ZP Market Monitoring - MNC_BD Community")
st.caption(f"로그인: {email}")

# 경쟁사 정보 필터링
df = load_weekly_data()
df = df[df['category'] != 'competitor']  # 경쟁사 제외
# ...
```

---

### Phase 3: 키워드 필터링 시스템

#### 3.1 설정 파일 기반 키워드 관리

```yaml
# config/keywords.yaml

# 공통 키워드 (모든 버전에서 사용)
common:
  company_keywords:  # 회사명 관련 (내부/외부 모두 포함)
    - "제픽스"
    - "제픽스펜"
    - "LG화학"
    - "LG생명과학"
    # ... 회사 관련 키워드

# Weekly 버전 키워드
weekly:
  important_keywords:
    - "GLP-1"
    - "비만치료제"
    - "당뇨치료제"
    # ... (기존 v2 키워드, Daily 키워드 제외)
  
  competitor_keywords:  # 경쟁사 (내부 전용)
    - "노보 노디스크"
    - "일라이 릴리"
    - "사노피"
    - "머크"
    - "오젬픽"
    - "위고비"
    - "마운자로"
    # ... (경쟁사 키워드)

# Daily 버전 키워드 (에이전시 검증용, Weekly와 완전 분리)
daily:
  agency_keywords:
    - "에이전시_키워드1"
    - "에이전시_키워드2"
    # ... (에이전시가 수집하는 키워드만)

# 외부 공유용 필터 설정
external:
  exclude_categories:
    - "competitor"  # 경쟁사 카테고리 제외
  include_company_keywords: true  # 회사명 키워드는 포함
```

**키워드 로딩 로직**:
```python
# scripts/config.py
def load_keywords(mode='weekly', access_level='internal'):
    """
    mode: 'weekly' or 'daily'
    access_level: 'internal' or 'external'
    """
    with open('config/keywords.yaml') as f:
        config = yaml.safe_load(f)
    
    # 공통 키워드는 항상 포함
    keywords = config['common']['company_keywords'].copy()
    
    if mode == 'weekly':
        keywords.extend(config['weekly']['important_keywords'])
        
        # 내부용이면 경쟁사 키워드 추가
        if access_level == 'internal':
            keywords.extend(config['weekly']['competitor_keywords'])
    
    elif mode == 'daily':
        keywords.extend(config['daily']['agency_keywords'])
    
    return keywords
```

#### 3.2 대시보드별 필터링
```python
# dashboards/internal_weekly.py
keywords = load_keywords('internal')
df = load_data('weekly')
# 모든 키워드 (경쟁사 포함) 표시

# dashboards/external_weekly.py
keywords = load_keywords('external')
df = load_data('weekly')
df = df[~df['category'].str.contains('competitor')]  # 경쟁사 제외
```

---

### Phase 4: Daily 버전 구현 (에이전시 검증)

#### 4.1 Daily 크롤링 스케줄러 (당일만)
```python
# scripts/crawl_scheduler.py --mode daily
# 매일 06:00 실행
# 크롤링 기간: 당일 00:00 ~ 현재 시각 (지난 7일 아님!)
# 저장 위치: data/daily/YYYY-MM-DD/
```

**크롤링 날짜 계산**:
```python
# scripts/crawl_naver_news_api.py
def get_date_range(mode='weekly'):
    """크롤링 날짜 범위 계산"""
    today = datetime.now()
    
    if mode == 'weekly':
        # 지난 7일
        end_date = today
        start_date = today - timedelta(days=7)
    
    elif mode == 'daily':
        # 당일만 (00:00 ~ 현재)
        start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = today
    
    return start_date, end_date
```

#### 4.2 Daily 대시보드
```python
# dashboards/daily_validation.py
# - 에이전시 키워드만 사용
# - 동일 조건 (기간, 필터링 로직)
# - 에이전시 결과와 비교 기능
# - 내부 사용자만 접근 가능
```

#### 4.3 비교 분석 기능
- 에이전시 결과 업로드 기능
- 키워드별 기사 수 비교
- 중복/누락 기사 분석
- 품질 지표 비교 (관련도, 중요도)

---

### Phase 5: 배포 및 관리

#### 5.1 GitHub Private Repository (코드 보안)

**문제**: 현재 Public repo → 코드, README, 키워드 등 노출
**해결**: Private Repository 생성

```bash
# GitHub에서 Private repo 생성
Repository name: zp-market-monitoring-v3-share
Visibility: Private ✅
Description: ZP Market Monitoring v3 - Shared Version (Internal Use Only)
```

**Private Repo 장점**:
1. **코드 보안**: 아무도 코드 볼 수 없음
2. **키워드 보호**: 경쟁사 키워드 등 민감 정보 보호
3. **Streamlit Cloud 연동 가능**: Private repo도 배포 가능
4. **협업자 관리**: 필요한 사람만 초대

**Streamlit Cloud 배포 시 Private Repo 연동**:
1. Streamlit Cloud → New app
2. GitHub 연동 시 Private repo 선택 가능
3. Streamlit이 repo 접근 권한 요청 → 승인
4. 배포 완료

**중요**: 
- Private repo는 GitHub 무료 계정에서도 무제한 생성 가능
- Streamlit Cloud 무료 플랜도 Private repo 배포 지원
- 모바일에서도 Private repo는 권한 없으면 접근 불가

#### 5.2 Streamlit Cloud 배포
- **App 1**: `internal-weekly`
  - Entry point: `dashboards/internal_weekly.py`
  - URL: `https://zp-internal-weekly.streamlit.app`
  - 내부 사용자만 접근

- **App 2**: `external-weekly`
  - Entry point: `dashboards/external_weekly.py`
  - URL: `https://zp-external-weekly.streamlit.app`
  - MNC_BD Community 공유

- **App 3**: `daily-validation`
  - Entry point: `dashboards/daily_validation.py`
  - URL: `https://zp-daily-validation.streamlit.app`
  - 내부 검증용

#### 5.3 데이터 동기화
**문제**: Streamlit Cloud는 로컬 파일 시스템 접근 불가
**해결책**:
1. **GitHub 저장** (작은 데이터)
   - `data/` 폴더를 GitHub에 커밋
   - 크롤링 후 자동 push
   
2. **Google Drive/Dropbox** (큰 데이터)
   - 크롤링 결과를 클라우드 저장소에 업로드
   - 대시보드에서 다운로드

3. **데이터베이스** (권장, 확장성)
   - Google Sheets API (무료, 간단)
   - PostgreSQL (Supabase 무료 티어)

---

## 사용자 질문 답변

### Q1: 접근 제한이 어떤 식으로 되어서 인증하고 들어가는 거야?

**A: Streamlit 앱 실행 시 인증 플로우**

```
1. 사용자가 URL 접속 (예: https://zp-internal-weekly.streamlit.app)
   ↓
2. Streamlit 앱 시작 → auth/simple_auth.py의 authenticate() 함수 실행
   ↓
3. 세션 확인: 이미 로그인되어 있나?
   - YES → 대시보드 바로 표시
   - NO → 로그인 폼 표시 (이메일 + 비밀번호)
   ↓
4. 사용자가 이메일 + 비밀번호 입력 후 제출
   ↓
5. 비밀번호 검증 (공통 비밀번호와 비교)
   - 틀리면 → 에러 메시지, 재입력 요구
   - 맞으면 → 다음 단계
   ↓
6. 이메일 도메인으로 접근 레벨 자동 판단
   - @lgchem.com, @lgls.com 등 → 'internal'
   - 그 외 → 'external'
   ↓
7. 앱별 권한 확인
   - Internal Weekly: internal만 허용
   - External Weekly: internal/external 모두 허용
   - Daily: internal만 허용
   ↓
8. 권한 OK → 세션에 저장 → 대시보드 표시
   권한 NO → 에러 메시지 + 접근 차단
```

**핵심**:
- **웹 앱 자체에 인증 로직이 내장**되어 있음
- 로그인 전까지는 `st.stop()`으로 대시보드 코드 실행 안 함
- 세션 기반이라 한 번 로그인하면 브라우저 닫기 전까지 유지
- **Streamlit Cloud URL은 누구나 접속 가능하지만, 로그인 없이는 아무것도 볼 수 없음**

### Q2: GitHub가 Public이면 누군가 들어가서 코드를 볼 수 있는데, Private으로 못 하나?

**A: Private Repository로 완벽하게 보호 가능**

#### GitHub Private Repo 설정
```bash
# 1. GitHub에서 새 repo 생성 시
Repository name: zp-market-monitoring-v3-share
Visibility: ✅ Private (중요!)
Description: ZP Market Monitoring v3 - Internal Use Only

# 2. 로컬에서 push
git init
git remote add origin https://github.com/Lilyleeyaa/zp-market-monitoring-v3-share.git
git add .
git commit -m "Initial commit"
git push -u origin main
```

#### Private Repo 보안 효과
| 항목 | Public Repo | Private Repo |
|------|-------------|--------------|
| 코드 열람 | ❌ 누구나 가능 | ✅ 권한자만 가능 |
| README 열람 | ❌ 누구나 가능 | ✅ 권한자만 가능 |
| 키워드 노출 | ❌ 노출됨 | ✅ 보호됨 |
| 모바일 접근 | ❌ 쉽게 접근 | ✅ 로그인 필요 |
| Streamlit 배포 | ✅ 가능 | ✅ 가능 (동일) |
| 비용 | 무료 | 무료 |

#### Streamlit Cloud + Private Repo 배포 프로세스
```
1. Streamlit Cloud (https://streamlit.io/cloud) 로그인
   ↓
2. "New app" 클릭
   ↓
3. GitHub 연동
   - Repository: Lilyleeyaa/zp-market-monitoring-v3-share (Private)
   - Branch: main
   - Main file path: dashboards/internal_weekly.py
   ↓
4. Streamlit이 Private repo 접근 권한 요청
   → GitHub에서 "Authorize Streamlit" 클릭
   ↓
5. 배포 완료!
   → URL: https://zp-internal-weekly.streamlit.app
```

**중요 포인트**:
- **Private repo여도 Streamlit Cloud 배포 가능** (무료 플랜 포함)
- **GitHub repo는 권한자만 볼 수 있음** (모바일 포함)
- **Streamlit 앱 URL은 공개되지만, 앱 자체에 인증이 있어서 로그인 필요**
- 즉, **2중 보안**: GitHub Private + Streamlit 앱 인증

### Q3: 모바일에서 GitHub 연결로 바로 들어갈 수 있는데?

**A: Private Repo는 권한 없으면 모바일에서도 접근 불가**

#### 시나리오 비교

**Public Repo (현재 v2)**:
```
모바일에서 GitHub 링크 클릭
→ 바로 코드/README 열람 가능 ❌
→ 키워드, 로직 등 모두 노출 ❌
```

**Private Repo (v3)**:
```
모바일에서 GitHub 링크 클릭
→ "404 Not Found" 또는 "You don't have access" ✅
→ 권한이 있는 GitHub 계정으로 로그인해야만 열람 가능 ✅
```

#### Streamlit 앱 접근 (모바일)
```
모바일에서 Streamlit 앱 URL 접속
→ 로그인 화면 표시
→ 이메일 + 비밀번호 입력
→ 인증 성공 시에만 대시보드 표시
```

**결론**:
- **GitHub Private Repo**: 모바일에서도 권한 없으면 아예 열람 불가
- **Streamlit 앱**: URL은 공개되지만 로그인 필수
- **귀하의 자산 완벽 보호** ✅

---

## 추가 제안

### 1. 알림 시스템
```python
# 크롤링 완료 시 Slack/Email 알림
# "Weekly 리포트 준비 완료: https://zp-internal-weekly.streamlit.app"
```

### 2. 버전 관리
```python
# data/weekly/2026-W05/metadata.json
{
  "version": "v3.0",
  "crawl_date": "2026-02-05T06:00:00",
  "keywords_used": ["제픽스", ...],
  "total_articles": 1234,
  "model_version": "lgbm_v2.pkl"
}
```

### 3. 모니터링 대시보드
```python
# dashboards/admin.py (관리자 전용)
# - 크롤링 상태 확인
# - 사용자 활동 로그
# - API 사용량 모니터링
```

### 4. 에이전시 대체 검증 프로세스
1. **1주일 병행 운영**: 에이전시 + Daily 버전 동시 실행
2. **비교 분석**: 
   - 기사 커버리지 (우리가 놓친 기사 vs 에이전시가 놓친 기사)
   - 관련도 정확도
   - 비용 대비 효과
3. **의사결정**: 검증 결과 기반 에이전시 대체 여부 결정

---

## 타임라인 (내일까지 구현 가능 범위)

### 우선순위 1 (필수, ~12시간)
- [x] v3 프로젝트 구조 생성
- [ ] 크롤링-대시보드 분리 (데이터 파일 기반)
- [ ] Streamlit 인증 시스템 구현
- [ ] 내부/외부 대시보드 분리 (키워드 필터링)
- [ ] Streamlit Cloud 배포 (3개 앱)

### 우선순위 2 (중요, ~4시간)
- [ ] Daily 크롤링 스케줄러
- [ ] Daily 검증 대시보드 기본 버전

### 우선순위 3 (추후)
- [ ] 에이전시 비교 분석 기능
- [ ] 모니터링 대시보드
- [ ] 알림 시스템

---

## 비용 및 리소스

### 무료 옵션 (권장)
- **Streamlit Cloud**: 무료 (Private repo 3개 앱)
- **GitHub**: 무료 (Private repo)
- **Google Sheets API**: 무료 (데이터 저장)
- **Windows Task Scheduler**: 무료 (크롤링 스케줄링)

### 예상 시간
- **셋업 및 구조**: 2시간
- **인증 시스템**: 3시간
- **대시보드 분리**: 2시간
- **Daily 버전**: 3시간
- **배포 및 테스트**: 2시간
- **총**: ~12시간 (우선순위 1 기준)

---

## 다음 단계 및 확인사항

### 구현 시작 전 확인 필요

1. **에이전시 키워드 리스트**: 
   - 에이전시가 수집하는 정확한 키워드 목록 공유 필요
   - Daily 버전에서 사용할 키워드

2. **내부 이메일 도메인**:
   - 내부 직원 이메일 도메인 확인 (예: @lgchem.com, @lgls.com)
   - 이 도메인으로 자동 internal 권한 부여

3. **경쟁사 제외 키워드**:
   - 외부 공유 시 제외할 경쟁사 키워드 전체 리스트
   - 현재 v2의 `PARTNER_KEYWORDS`에서 선별

4. **공통 비밀번호**:
   - MNC_BD 공유용 공통 비밀번호 설정
   - 보안을 위해 복잡한 비밀번호 권장

5. **설계안 승인**:
   - 위 설계안 검토 및 승인
   - 수정/추가 요청사항

### 승인 후 즉시 진행

1. **v3 프로젝트 생성**
   - 새 폴더 구조 생성
   - v2 코드 마이그레이션

2. **GitHub Private Repo 생성**
   - Private repository 설정
   - 초기 커밋

3. **Phase별 구현**
   - Phase 1: 크롤링-대시보드 분리
   - Phase 2: 인증 시스템
   - Phase 3: 키워드 필터링
   - Phase 4: Daily 버전
   - Phase 5: Streamlit Cloud 배포

4. **테스트 및 검증**
   - 내부 사용자 테스트
   - 외부 공유 테스트
   - Daily 버전 에이전시 비교

---

## 요약

### 핵심 변경사항 (v2 → v3)

| 항목 | v2 | v3 |
|------|----|----|
| **접근 제어** | ❌ 없음 (오픈) | ✅ 이메일 + 공통 비밀번호 |
| **대시보드** | 1개 (Weekly) | 3개 (Internal/External Weekly, Daily) |
| **키워드 관리** | 하드코딩 | YAML 설정 파일 |
| **크롤링** | 대시보드 접속 시 | 스케줄러 분리 (미리 실행) |
| **GitHub** | Public | Private |
| **경쟁사 정보** | 모두 공개 | 내부만 표시 |
| **Daily 버전** | ❌ 없음 | ✅ 에이전시 검증용 |

### 예상 소요 시간
- **우선순위 1** (필수): ~12시간
  - 프로젝트 셋업: 2시간
  - 인증 시스템: 3시간
  - 대시보드 분리: 2시간
  - Daily 버전: 3시간
  - 배포: 2시간

### 다음 액션
**설계안 검토 및 피드백 → 승인 시 즉시 구현 시작**
