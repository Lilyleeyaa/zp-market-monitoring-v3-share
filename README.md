# ZP Market Monitoring v3 Share

쥴릭파마코리아의 헬스케어 뉴스 모니터링 시스템 v3

## 주요 기능

### 1. **3가지 대시보드 버전**
- **Internal Weekly**: 내부용 (모든 키워드 포함, 경쟁사 정보 포함)
- **External Weekly**: MNC_BD 공유용 (경쟁사 유통업체/제품 제외)
- **Daily Validation**: 일일 검증용 (에이전시 키워드 18개)

### 2. **간소화된 인증 시스템**
- 이메일 + 공통 비밀번호 방식
- 이메일 도메인으로 자동 권한 분류 (internal/external)
- Private GitHub Repository + Streamlit Cloud 배포

### 3. **키워드 기반 크롤링**
- Weekly: 모든 키워드로 주간 크롤링
- Daily: 에이전시 키워드로 일일 크롤링 (Weekly와 중복 없음)

## 프로젝트 구조

```
ZP Market Monitoring v3 Share/
├── auth/                      # 인증 시스템
│   ├── simple_auth.py        # 인증 로직
│   ├── config.yaml.example   # 설정 템플릿
│   └── generate_password.py  # 비밀번호 해시 생성기
├── config/                    # 설정 파일
│   └── keywords.yaml         # 키워드 설정 (Weekly/Daily 분리)
├── dashboards/                # Streamlit 대시보드
│   ├── internal_weekly.py    # 내부용 주간 대시보드
│   ├── external_weekly.py    # 외부용 주간 대시보드
│   └── daily_validation.py   # 일일 검증 대시보드
├── scripts/                   # 데이터 처리 스크립트
│   ├── config.py             # 설정 로딩 유틸
│   └── crawl_naver_news_api.py  # 크롤링 스크립트
├── docs/                      # 문서
│   ├── implementation_plan.md
│   ├── keyword_classification.md
│   └── ...
├── requirements.txt           # Python 패키지 목록
└── README.md                  # 이 파일
```

## 설치 및 실행

### 1. 환경 설정

```bash
# Python 가상환경 생성 (권장)
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# 패키지 설치
pip install -r requirements.txt
```

### 2. 인증 설정

```bash
# 1. auth/config.yaml 생성
copy auth\config.yaml.example auth\config.yaml

# 2. 비밀번호 해시 생성
python auth/generate_password.py

# 3. auth/config.yaml 파일을 편집하여 설정
# - common_password_hash: 생성된 해시 입력
# - internal_domains: 내부 이메일 도메인 추가
```

### 3. 로컬 실행

```bash
# 내부용 대시보드
streamlit run dashboards/internal_weekly.py

# 외부용 대시보드
streamlit run dashboards/external_weekly.py

# Daily 검증 대시보드
streamlit run dashboards/daily_validation.py
```

## 배포 (Streamlit Cloud)

1. **GitHub Private Repository 생성**
2. **코드 Push**
3. **Streamlit Cloud 배포**
   - https://streamlit.io/cloud 접속
   - Private repo 권한 부여
   - Secrets에 auth/config.yaml 내용 추가
4. **3개 앱 배포**:
   - internal-weekly: `dashboards/internal_weekly.py`
   - external-weekly: `dashboards/external_weekly.py`
   - daily-validation: `dashboards/daily_validation.py`

자세한 배포 가이드: `docs/daily_strategy_and_deployment.md`

## 주요 변경사항 (v2 → v3)

1. **인증 시스템 추가**: 이메일 + 비밀번호 로그인
2. **대시보드 분리**: Internal/External/Daily 3가지 버전
3. **키워드 분리**: Weekly와 Daily 키워드 완전 분리 (중복 없음)
4. **설정 파일 기반**: 코드 수정 없이 keywords.yaml에서 키워드 관리
5. **Private Repository**: 코드 및 키워드 보안 강화

## 문서

- [Implementation Plan](docs/implementation_plan.md)
- [Keyword Classification](docs/keyword_classification.md)
- [Daily Strategy & Deployment](docs/daily_strategy_and_deployment.md)
- [Keyword Assignment Logic](docs/keyword_assignment_improvement.md)

## 라이선스

Internal use only - Zuellig Pharma Korea
