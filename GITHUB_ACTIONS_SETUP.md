# GitHub Actions 자동화 설정 가이드

## 🎯 완전 자동화 달성!

PC 안 켜도 되는 완전 클라우드 자동화:
- **Weekly**: 매주 금요일 오전 6시 (KST)
- **Daily**: 매일 오전 6시 (KST)
- **비용**: 무료 (GitHub Actions 월 2000분 무료)

---

## 📁 생성된 파일

```
.github/
└── workflows/
    ├── weekly-crawl.yml  # 금요일 06:00 자동 실행
    └── daily-crawl.yml   # 매일 06:00 자동 실행
```

---

## ⚙️ 설정 방법

### 1. GitHub Private Repository 생성

```bash
# 로컬에서 실행
cd "c:\Users\samsung\OneDrive\Desktop\GY\AntiGravity\ZP Market Monitoring v3 share"

# Git 초기화 (아직 안했다면)
git init
git branch -M main

# GitHub에서 Private Repository 생성 후
git remote add origin https://github.com/Lilyleeyaa/zp-market-monitoring-v3-share.git
```

### 2. GitHub Secrets 설정

**GitHub Repository → Settings → Secrets and variables → Actions → New repository secret**

추가할 Secrets:
- `NAVER_CLIENT_ID` = 네이버 API 클라이언트 ID
- `NAVER_CLIENT_SECRET` = 네이버 API 시크릿
- `GENAI_API_KEY` = Gemini API 키

### 3. 코드 Push

```bash
# .gitignore 확인 (이미 있음)
# auth/config.yaml은 제외되어야 함

git add .
git commit -m "feat: GitHub Actions 자동화 설정"
git push -u origin main
```

### 4. GitHub Actions 활성화 확인

1. GitHub Repository → **Actions** 탭
2. 두 개의 워크플로우 확인:
   - ✅ Weekly Crawl and Rank
   - ✅ Daily Crawl and Rank

---

## 🧪 테스트 방법

### 수동 실행 테스트:

1. GitHub Repository → **Actions** 탭
2. **Weekly Crawl and Rank** 선택
3. **Run workflow** 버튼 클릭
4. **Run workflow** 확인
5. 실행 상태 확인 (5-10분 소요)
6. ✅ 완료 후 `data/articles_raw/` 폴더에 CSV 파일 생성 확인

---

## 📅 자동 실행 스케줄

| 작업 | 실행 시간 (KST) | 실행 주기 | 예상 소요 시간 |
|------|----------------|-----------|---------------|
| Weekly | 금요일 06:00 | 매주 | 8-10분 |
| Daily | 매일 06:00 | 매일 | 3-5분 |

### Cron 시간 설명:
- `0 21 * * 4` = UTC 21:00 목요일 = **KST 금요일 06:00**
- `0 21 * * *` = UTC 21:00 매일 = **KST 매일 06:00**

한국은 UTC+9 시간대이므로 9시간을 뺀 시간으로 설정해야 합니다.

---

## 🔍 동작 확인

### 1. GitHub Actions 로그 확인:
- Repository → Actions → 실행된 워크플로우 클릭
- 각 step별 로그 확인

### 2. 결과 파일 확인:
- `data/articles_raw/articles_ranked_YYYYMMDD.csv` (Weekly)
- `data/articles_raw/articles_daily_ranked_YYYYMMDD.csv` (Daily)

### 3. Streamlit 대시보드 확인:
- 대시보드 접속 시 최신 CSV 파일 자동 로딩
- 즉시 표시 (크롤링 대기 없음)

---

## 💰 비용 계산

**GitHub Actions 무료 한도**: 월 2000분

**예상 사용량**:
- Weekly: 10분 × 4회/월 = 40분
- Daily: 5분 × 30회/월 = 150분
- **총**: 190분/월 (무료 범위 내)

**결론**: 완전 무료! ✅

---

## 🛠️ 문제 해결

### Actions가 실행되지 않을 때:

1. **Settings → Actions → General** 확인
   - ✅ "Allow all actions and reusable workflows" 선택
   
2. **Secrets 확인**
   - NAVER_CLIENT_ID
   - NAVER_CLIENT_SECRET
   - GENAI_API_KEY

3. **권한 확인**
   - Settings → Actions → General → Workflow permissions
   - ✅ "Read and write permissions" 선택

### 실행 실패 시:

1. Actions 탭에서 실패한 워크플로우 클릭
2. 빨간색 step 클릭하여 에러 로그 확인
3. 주요 에러:
   - `pip install` 실패 → requirements.txt 확인
   - API 에러 → Secrets 확인
   - git push 실패 → 권한 확인

---

## 🎉 완료!

이제 PC를 안 켜도:
- ✅ 매주 금요일 오전 6시 자동 크롤링
- ✅ 매일 오전 6시 자동 크롤링
- ✅ GitHub에 결과 자동 저장
- ✅ 대시보드 즉시 업데이트

**완전 자동화 달성!** 🚀
