@echo off
REM Daily Crawler - Runs every day at 6:00 AM
REM ================================================

echo ============================================
echo ZP Market Monitoring - Daily Crawl
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

echo [1/3] Running daily crawler (Yesterday only)...
REM Using dedicated daily crawler with config/keywords.yaml
python scripts\crawl_daily_news.py
if %errorlevel% neq 0 (
    echo ERROR: Daily crawler failed!
    pause
    exit /b 1
)

echo.
echo [2/3] Ranking daily articles...
python scripts\rank_articles.py
if %errorlevel% neq 0 (
    echo ERROR: Ranking failed!
    pause
    exit /b 1
)

echo.
echo [3/3] Pushing to GitHub...
git add data\articles_raw\
git commit -m "Auto: Daily crawl %date% %time%"
git push origin main
if %errorlevel% neq 0 (
    echo WARNING: Git push failed (check if repo exists)
)

echo.
echo ============================================
echo Daily Crawl Completed Successfully!
echo End Time: %date% %time%
echo ============================================
echo.

REM Optional: Keep window open for debugging
REM pause
