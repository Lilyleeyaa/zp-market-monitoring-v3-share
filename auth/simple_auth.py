"""
통합 인증 시스템 - st.secrets 전용 (config.yaml 제거)
비밀번호로 Internal/External 모드 자동 전환
"""
import streamlit as st
import hashlib


def load_auth_config():
    """st.secrets에서 인증 설정 로드 (유일한 소스)"""
    if "auth" not in st.secrets:
        st.error("⚠️ Authentication secrets not configured. Please set secrets in Streamlit Cloud or .streamlit/secrets.toml")
        st.stop()
    return st.secrets["auth"]


def _login_style():
    """공통 로그인 페이지 스타일 (티파니 블루)"""
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


def _load_external_users():
    """외부 사용자 목록 로드 (st.secrets 전용)"""
    try:
        # TOML: [auth] 섹션 아래에 있으면 auth.EXTERNAL_EMAILS로 파싱됨
        if "EXTERNAL_EMAILS" in st.secrets:
            return list(st.secrets["EXTERNAL_EMAILS"])
        elif "auth" in st.secrets and "EXTERNAL_EMAILS" in st.secrets["auth"]:
            return list(st.secrets["auth"]["EXTERNAL_EMAILS"])
        return []
    except Exception:
        return []


def authenticate_unified():
    """
    통합 인증 - 이메일 + 비밀번호
    비밀번호에 따라 Internal/External 모드 자동 결정

    Returns: (email, access_level) or stops app
    """
    config = load_auth_config()

    # 이미 로그인된 경우
    if st.session_state.get('authenticated'):
        return st.session_state['email'], st.session_state['access_level']

    _login_style()
    st.title("🔐 Healthcare Market Monitor")
    st.caption("Login with your email and password")

    with st.form("unified_login_form"):
        email = st.text_input("Email", placeholder="your.name@company.com").strip()
        password = st.text_input("Password", type="password").strip()
        submit = st.form_submit_button("Login")

        if submit:
            if not email or not password:
                st.error("❌ Please enter both email and password.")
                st.stop()

            pw_hash = hash_password(password)
            internal_hash = config.get("internal_password_hash", "")
            external_hash = config.get("external_password_hash", "")
            internal_domains = config.get("internal_domains", [])

            # Case 1: Internal password
            if pw_hash == internal_hash:
                is_internal = any(email.lower().endswith(d) for d in internal_domains)
                if not is_internal:
                    st.error(f"❌ Internal access requires a company email (@{internal_domains[0]}).")
                    st.stop()

                st.session_state['authenticated'] = True
                st.session_state['email'] = email
                st.session_state['access_level'] = 'internal'
                st.success("✅ Internal login successful!")
                st.rerun()

            # Case 2: External password
            elif pw_hash == external_hash:
                external_users = [e.lower() for e in _load_external_users()]
                if email.lower() not in external_users:
                    st.error(f"❌ Access denied. Your email is not registered.")
                    st.stop()

                st.session_state['authenticated'] = True
                st.session_state['email'] = email
                st.session_state['access_level'] = 'external'
                st.success("✅ Login successful!")
                st.rerun()

            # Case 3: Wrong password
            else:
                st.error("❌ Incorrect password.")
                st.stop()

    st.stop()


# ===== Legacy wrappers (기존 코드 호환용) =====
def authenticate_internal():
    """Legacy: internal_weekly.py 호환"""
    email, level = authenticate_unified()
    if level != 'internal':
        st.error("❌ Internal access only.")
        st.stop()
    return email


def authenticate_external():
    """Legacy: external_weekly.py 호환"""
    email, level = authenticate_unified()
    return email


def authenticate(mode='weekly'):
    """Legacy wrapper"""
    return authenticate_internal()


def get_current_user():
    """현재 로그인한 사용자 정보 반환"""
    if 'authenticated' not in st.session_state:
        return None, None
    return st.session_state.get('email'), st.session_state.get('access_level')
