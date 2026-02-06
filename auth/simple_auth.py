"""
간소화된 인증 시스템 (이메일 + 공통 비밀번호)
"""
import streamlit as st
import yaml
import hashlib
import os

def load_auth_config():
    """인증 설정 로드"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_path) as f:
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
