"""
Daily Validation Dashboard - Daily 검증용 (내부 전용)
"""
import streamlit as st
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.simple_auth import authenticate, get_current_user
from scripts.config import load_keywords

# 페이지 설정
st.set_page_config(
    page_title="ZP Market Monitoring - Daily Validation",
    page_icon="📊",
    layout="wide"
)

# 인증 (내부 전용)
email, access_level = authenticate(mode='daily')

if access_level != 'internal':
    st.error("❌ Daily 버전은 내부 사용자만 접근 가능합니다.")
    st.stop()

# 대시보드 메인 코드
st.title("📊 ZP Market Monitoring - Daily Validation")
st.caption(f"로그인: {email} ({access_level})")

st.markdown("---")

# Daily 키워드 로드
daily_keywords = load_keywords(mode='daily')

st.info("🚧 Daily 검증 대시보드를 구현 중입니다...")
st.write(f"Daily 키워드 ({len(daily_keywords)}개): {', '.join(daily_keywords)}")
st.write("에이전시 결과와 비교 분석을 제공합니다.")
