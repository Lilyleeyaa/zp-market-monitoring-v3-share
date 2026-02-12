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

# [Admin/Internal Only] Show external email list for verification
if access_level == 'internal':
    with st.sidebar.expander("📧 External Emails (Internal Only)"):
        try:
            # Construct path to external_users.txt relative to this script
            user_list_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'auth', 'external_users.txt')
            if os.path.exists(user_list_path):
                with open(user_list_path, 'r', encoding='utf-8') as f:
                    emails = f.read()
                st.text_area("Registered Emails", emails, height=300)
            else:
                st.warning("external_users.txt not found")
        except Exception as e:
            st.error(f"Error loading emails: {e}")

# 대시보드 메인 코드
st.title("📊 ZP Market Monitoring - MNC_BD Community")
st.caption(f"로그인: {email} ({access_level})")

st.markdown("---")

# 경쟁사 정보 필터링
excluded_keywords = get_excluded_keywords(access_level='external')

st.info("🚧 대시보드를 구현 중입니다...")
