"""
External Weekly Dashboard - 외부용 (경쟁사 제외)
"""
import streamlit as st
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.simple_auth import authenticate, get_current_user
from scripts.config import get_excluded_keywords, should_exclude_article

# 페이지 설정
st.set_page_config(
    page_title="ZP Market Monitoring - MNC_BD",
    page_icon="📊",
    layout="wide"
)

# 인증 (내부/외부 모두 가능)
email, access_level = authenticate(mode='weekly')

# 대시보드 메인 코드
st.title("📊 ZP Market Monitoring - MNC_BD Community")
st.caption(f"로그인: {email} ({access_level})")

st.markdown("---")

# 경쟁사 정보 필터링
excluded_keywords = get_excluded_keywords(access_level='external')

st.info("🚧 대시보드를 구현 중입니다...")
st.write("이 대시보드는 경쟁사 정보를 제외하고 표시합니다.")
st.write(f"제외되는 키워드: {', '.join(excluded_keywords)}")
