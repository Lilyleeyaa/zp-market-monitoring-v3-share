"""
간소화된 인증 시스템 - 내부/외부 완전 분리
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

def _login_style():
    """공통 로그인 페이지 스타일"""
    st.markdown("""
    <style>
        .stTextInput input {
            border: 2px solid #0ABAB5 !important;
            border-radius: 8px;
        }
        .stTextInput input:focus {
            box-shadow: 0 0 5px #0ABAB5;
        }
        .stButton>button {
            background-color: #0ABAB5 !important;
            color: white !important;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            width: 100%;
        }
        .stButton>button:hover {
            background-color: #008080 !important;
        }
        h1 {
            color: #0ABAB5 !important;
        }
    </style>
    """, unsafe_allow_html=True)

def hash_password(password):
    """비밀번호 해싱"""
    return hashlib.sha256(password.encode()).hexdigest()

def _load_external_users(config):
    """외부 사용자 목록 로드"""
    external_users = []
    
    # 1. Config/Secrets
    if 'external_users' in config:
        external_users.extend(config['external_users'])

    # 2. File
    try:
        ext_path = os.path.join(os.path.dirname(__file__), 'external_users.txt')
        if os.path.exists(ext_path):
            with open(ext_path, 'r', encoding='utf-8') as f:
                file_users = [line.strip() for line in f if line.strip()]
                external_users.extend(file_users)
    except:
        pass
    
    return list(set(external_users))


def authenticate_internal():
    """
    내부 전용 인증
    - @zuelligpharma.com 이메일 + 내부 비밀번호
    Returns: email or None
    """
    config = load_auth_config()
    
    if 'authenticated' in st.session_state and st.session_state['authenticated']:
        return st.session_state['email']
    
    _login_style()
    st.title("🔐 Internal Login")
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="your.name@zuelligpharma.com")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            # 내부 도메인 확인
            is_internal = any(email.endswith(domain) for domain in config.get('internal_domains', []))
            
            if not is_internal:
                st.error("❌ Internal users only. Please use your @zuelligpharma.com email.")
                st.stop()
            
            # 비밀번호 확인
            if hash_password(password) != config['common_password_hash']:
                st.error("❌ Incorrect password.")
                st.stop()
            
            # 로그인 성공
            st.session_state['authenticated'] = True
            st.session_state['email'] = email
            st.session_state['access_level'] = 'internal'
            st.success("✅ Login successful!")
            st.rerun()
    
    st.stop()


def authenticate_external():
    """
    외부 전용 인증
    - external_users.txt에 등록된 이메일 + 외부 비밀번호 (MNCbd!)
    Returns: email or None
    """
    config = load_auth_config()
    
    if 'authenticated' in st.session_state and st.session_state['authenticated']:
        return st.session_state['email']
    
    _login_style()
    st.title("🔐 Login")
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="your.email@company.com")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            external_users = _load_external_users(config)
            
            if email not in external_users:
                st.error("❌ Access denied. Only authorized users can access this dashboard.")
                st.stop()
            
            if password != "MNCbd!":
                st.error("❌ Incorrect password.")
                st.stop()
            
            # 로그인 성공
            st.session_state['authenticated'] = True
            st.session_state['email'] = email
            st.session_state['access_level'] = 'external'
            st.success("✅ Login successful!")
            st.rerun()
    
    st.stop()


# 하위 호환용 (기존 코드에서 authenticate() 호출 시)
def authenticate(mode='weekly'):
    """Legacy wrapper"""
    return authenticate_internal()

def get_current_user():
    """현재 로그인한 사용자 정보 반환"""
    if 'authenticated' not in st.session_state:
        return None, None
    return st.session_state.get('email'), st.session_state.get('access_level')
