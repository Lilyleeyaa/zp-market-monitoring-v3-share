# Windows Task Scheduler 설정 가이드

## 자동 크롤링 설정 (Weekly + Daily)

### 📋 필요한 스케줄:
1. **Weekly 크롤링**: 매주 금요일 오전 6시
2. **Daily 크롤링**: 매일 오전 6시

---

## 🔧 설정 방법

### 1. Task Scheduler 열기
- Windows 검색창에 "작업 스케줄러" 또는 "Task Scheduler" 입력
- 또는 `Win + R` → `taskschd.msc` 입력 → Enter

### 2. Weekly 크롤링 작업 만들기

#### Step 1: 기본 작업 만들기
1. 우측 패널에서 **"기본 작업 만들기"** 클릭
2. 이름: `ZP Market Monitoring - Weekly Crawl`
3. 설명: `매주 금요일 오전 6시 자동 크롤링`
4. **다음** 클릭

#### Step 2: 트리거 설정
1. **"매주"** 선택 → **다음**
2. 시작 날짜: 다음 금요일 날짜 선택
3. 시작 시간: `오전 6:00`
4. 간격: `1주마다`
5. 요일: **"금요일"** 체크
6. **다음** 클릭

#### Step 3: 작업 설정
1. **"프로그램 시작"** 선택 → **다음**
2. 프로그램/스크립트: 찾아보기 클릭
3. 파일 선택: `c:\Users\samsung\OneDrive\Desktop\GY\AntiGravity\ZP Market Monitoring v3 share\scripts\run_weekly_crawl.bat`
4. **다음** 클릭

#### Step 4: 완료
1. **"마침을 클릭할 때 이 작업의 속성 대화 상자 열기"** 체크
2. **마침** 클릭

#### Step 5: 고급 설정 (속성 창)
1. **"일반"** 탭:
   - ✅ "가장 높은 수준의 권한으로 실행" 체크
   
2. **"조건"** 탭:
   - ⬜ "컴퓨터의 AC 전원이 켜져 있을 때만 작업 시작" 체크 해제 (선택)
   - ⬜ "작업을 실행하기 위해 대기 중일 때 다음 시간 동안 유휴 상태이면 시작" 체크 해제
   
3. **"설정"** 탭:
   - ✅ "작업이 실패하면 다시 시작 간격" 체크 → `1분` 설정
   - ✅ "작업이 요청 시 실행 중지되지 않으면 강제 중지" 체크 → `1시간` 설정

4. **확인** 클릭

---

### 3. Daily 크롤링 작업 만들기

#### Step 1: 기본 작업 만들기
1. 우측 패널에서 **"기본 작업 만들기"** 클릭
2. 이름: `ZP Market Monitoring - Daily Crawl`
3. 설명: `매일 오전 6시 자동 크롤링 (에이전시 비교용)`
4. **다음** 클릭

#### Step 2: 트리거 설정
1. **"매일"** 선택 → **다음**
2. 시작 날짜: 내일 날짜 선택
3. 시작 시간: `오전 6:00`
4. 간격: `1일마다`
5. **다음** 클릭

#### Step 3: 작업 설정
1. **"프로그램 시작"** 선택 → **다음**
2. 프로그램/스크립트: 찾아보기 클릭
3. 파일 선택: `c:\Users\samsung\OneDrive\Desktop\GY\AntiGravity\ZP Market Monitoring v3 share\scripts\run_daily_crawl.bat`
4. **다음** 클릭

#### Step 4: 완료
1. **"마침을 클릭할 때 이 작업의 속성 대화 상자 열기"** 체크
2. **마침** 클릭

#### Step 5: 고급 설정 (속성 창)
- Weekly와 동일하게 설정

---

## ✅ 테스트 방법

### 배치 파일 직접 실행 테스트
1. 파일 탐색기 열기
2. `scripts` 폴더로 이동
3. `run_weekly_crawl.bat` 더블클릭
4. 콘솔 창에서 실행 결과 확인

### Task Scheduler에서 수동 실행
1. Task Scheduler 열기
2. 왼쪽에서 생성한 작업 찾기
3. 우클릭 → **"실행"** 클릭
4. 상태가 "실행 중"으로 변경되는지 확인

---

## 📝 주의사항

### 1. PC가 켜져 있어야 함
- ⚠️ Task Scheduler는 PC가 켜져 있을 때만 작동
- 금요일/매일 오전 6시에 PC를 켜두거나 절전 모드 해제 설정 필요

### 2. Python 환경 확인
- 가상환경(venv)이 있으면 자동으로 활성화됨
- 없으면 시스템 Python 사용

### 3. GitHub 자동 Push
- Git 계정 로그인 상태 확인
- SSH 키 또는 Credential Manager 설정 필요
- 처음 실행 시 인증 요청 가능

### 4. 로그 확인
- 배치 파일 실행 중 오류 발생 시 창이 자동으로 닫힘
- 디버깅 필요 시 배치 파일 마지막 줄 `REM pause` → `pause`로 변경

---

## 🔍 문제 해결

### 작업이 실행되지 않음
1. Task Scheduler Library에서 작업 상태 확인
2. "기록" 탭에서 실행 로그 확인
3. 배치 파일 경로가 정확한지 확인

### Git Push 실패
```batch
# Git credential 저장 (한 번만 실행)
git config --global credential.helper wincred
```

### Python 오류
- 가상환경 활성화 확인
- 필요한 패키지 설치 확인: `pip install -r requirements.txt`

---

## 🎯 최종 스케줄 요약

| 크롤링 | 실행 시간 | 배치 파일 | 목적 |
|--------|-----------|-----------|------|
| Weekly | 매주 금요일 06:00 | `run_weekly_crawl.bat` | 주간 리포트 생성 |
| Daily | 매일 06:00 | `run_daily_crawl.bat` | 에이전시 비교 검증 |

---

## 다음 단계

1. ✅ 배치 파일 생성 완료
2. ⬜ Task Scheduler 설정 (위 가이드 따라하기)
3. ⬜ 테스트 실행
4. ⬜ 금요일/매일 자동 실행 확인
