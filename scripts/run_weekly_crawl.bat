@echo off
REM Weekly Crawler - Runs every Friday at 6:00 AM
REM ================================================

echo ============================================
echo ZP Market Monitoring - Weekly Crawl
echo ============================================
echo.
echo Start Time: %date% %time%
echo.

REM Navigate to project directory
cd /d "c:\Users\samsung\OneDrive\Desktop\GY\AntiGravity\ZP Market Monitoring v3 share"

REM Activate virtual environment if exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

echo [1/3] Running crawler...
python scripts\crawl_naver_news_api.py
if %errorlevel% neq 0 (
    echo ERROR: Crawler failed!
    pause
    exit /b 1
)

echo.
echo [2/3] Ranking articles...
python scripts\rank_articles.py
if %errorlevel% neq 0 (
    echo ERROR: Ranking failed!
    pause
    exit /b 1
)

echo.
echo [3/3] Pushing to GitHub...
git add data\articles_raw\
git commit -m "Auto: Weekly crawl %date% %time%"
git push origin main
if %errorlevel% neq 0 (
    echo WARNING: Git push failed (check if repo exists)
)

echo.
echo ============================================
echo Weekly Crawl Completed Successfully!
echo End Time: %date% %time%
echo ============================================
echo.

REM Optional: Keep window open for debugging
REM pause
