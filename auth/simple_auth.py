"""
간소화된 인증 시스템 (이메일 + 공통 비밀번호)
"""
import streamlit as st
import yaml
import hashlib
import os

def load_auth_config():
    """인증 설정 로드 (Secrets 우선, 파일 후순위)"""
    # 1. Try Streamlit Secrets
    if "auth" in st.secrets:
        return st.secrets["auth"]
        
    # 2. Try local config.yaml
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    if os.path.exists(config_path):
        with open(config_path, encoding='utf-8') as f:
            return yaml.safe_load(f)
            
    # 3. Fail gracefully
    st.error("Auth configuration not found. Please set secrets or add auth/config.yaml.")
    st.stop()

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
    st.title("🔐 Login")
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="your.email@company.com")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            # Password verification (common password)
            if hash_password(password) != config['common_password_hash']:
                st.error("❌ Incorrect password.")
                st.stop()
            
            # Determine access level by email domain
            access_level = 'external'  # 기본값
            
            for domain in config['internal_domains']:
                if email.endswith(domain):
                    access_level = 'internal'
                    break
            
            # Daily is internal only
            if mode == 'daily' and access_level != 'internal':
                st.error("❌ Daily version is only accessible to internal users.")
                st.stop()
            
            # Save to session
            st.session_state['authenticated'] = True
            st.session_state['email'] = email
            st.session_state['access_level'] = access_level
            
            st.success(f"✅ Login successful! ({access_level})")
            st.rerun()
    
    st.stop()  # Don't show dashboard until logged in

def get_current_user():
    """현재 로그인한 사용자 정보 반환"""
    if 'authenticated' not in st.session_state:
        return None, None
    return st.session_state.get('email'), st.session_state.get('access_level')
