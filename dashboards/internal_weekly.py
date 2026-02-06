"""
Internal Weekly Dashboard - 내부용 (경쟁사 포함)
매 접속 시 지난주 금요일~어제 목요일(7일) 기사 자동 크롤링
"""
import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime, timedelta
import pytz

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.simple_auth import authenticate

# 페이지 설정
st.set_page_config(
    page_title="ZP Market Monitoring - Internal Weekly",
    page_icon="📊",
    layout="wide"
)

# 인증 (내부 전용)
email, access_level = authenticate(mode='weekly')

if access_level != 'internal':
    st.error("❌ 이 대시보드는 내부 사용자만 접근 가능합니다.")
    st.stop()

# ====================
# 동적 날짜 계산
# ====================
def get_weekly_date_range():
    """
    지난주 금요일 ~ 어제 목요일 (7일)
    금요일에 접속하면 지난주 금~이번주 목 기사
    """
    kst = pytz.timezone('Asia/Seoul')
    today = datetime.now(kst)
    
    # 어제
    yesterday = today - timedelta(days=1)
    
    # 지난주 금요일 (7일 전)
    last_friday = today - timedelta(days=7)
    
    return last_friday, yesterday


# ====================
# CSV 로딩 함수 (GitHub Actions 결과)
# ====================
@st.cache_data(ttl=3600, show_spinner=False)  # 1시간 캐싱
def load_weekly_data():
    """
    GitHub Actions로 생성된 Weekly CSV 로딩
    """
    try:
        import glob
        
        base_dir = "data/articles_raw"
        if not os.path.exists(base_dir):
            base_dir = "../data/articles_raw"
        
        # articles_ranked_YYYYMMDD.csv 파일 찾기
        ranked_files = sorted(glob.glob(os.path.join(base_dir, "articles_ranked_*.csv")))
        
        if not ranked_files:
            return pd.DataFrame(), {}
        
        # 가장 최신 파일
        latest_file = ranked_files[-1]
        df = pd.read_csv(latest_file, encoding='utf-8-sig')
        
        # 날짜 변환
        if 'published_date' in df.columns:
            df['published_date'] = pd.to_datetime(df['published_date']).dt.date
        
        # 카테고리 확인
        if 'category' not in df.columns:
            df['category'] = 'General'
        
        # 날짜 정보 추출
        start_date, end_date = get_weekly_date_range()
        
        info = {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'total_articles': len(df),
            'data_file': os.path.basename(latest_file),
            'updated_time': datetime.fromtimestamp(os.path.getmtime(latest_file)).strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return df, info
        
    except Exception as e:
        st.error(f"데이터 로딩 중 오류: {str(e)}")
        return pd.DataFrame(), {}


# ====================
# 메인 UI
# ====================
st.title("📊 ZP Market Monitoring - Internal Weekly")
st.caption(f"로그인: {email} ({access_level})")

# CSV 로딩 (GitHub Actions 결과)
df, data_info = load_weekly_data()

if df.empty:
    st.warning("⚠️ 데이터가 없습니다. GitHub Actions 크롤링이 완료되었는지 확인하세요.")
    st.info("💡 GitHub Repository → Actions 탭에서 'Weekly Crawl and Rank' 워크플로우를 수동으로 실행할 수 있습니다.")
    st.stop()

# 데이터 정보 표시
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("크롤링 기간", f"{data_info.get('start_date', 'N/A')} ~ {data_info.get('end_date', 'N/A')}")
with col2:
    st.metric("전체 기사", f"{data_info.get('total_articles', 0):,}개")
with col3:
    st.metric("파일 업데이트", data_info.get('updated_time', 'N/A'))
with col4:
    st.caption(f"📁 {data_info.get('data_file', 'N/A')}")
    if st.button("🔄 새로고침"):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

# ====================
# 필터 (사이드바)
# ====================
with st.sidebar:
    st.header("🔍 필터")
    
    # 카테고리 필터
    categories = ['전체'] + sorted(df['category'].unique().tolist())
    selected_category = st.selectbox("카테고리", categories)
    
    # 날짜 필터
    if 'published_date' in df.columns:
        date_range = st.date_input(
            "발행일",
            value=(df['published_date'].min(), df['published_date'].max()),
            min_value=df['published_date'].min(),
            max_value=df['published_date'].max()
        )
    
    # 점수 필터 (AI Score)
    min_score = st.slider("최소 AI 점수", 0.0, 1.0, 0.2)

# 필터 적용
filtered_df = df.copy()

if selected_category != '전체':
    filtered_df = filtered_df[filtered_df['category'] == selected_category]

if 'published_date' in filtered_df.columns and len(date_range) == 2:
    filtered_df = filtered_df[
        (filtered_df['published_date'] >= date_range[0]) &
        (filtered_df['published_date'] <= date_range[1])
    ]

if 'score_ag' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['score_ag'] >= min_score]

# ====================
# 기사 목록 표시
# ====================
st.subheader(f"📰 기사 목록 ({len(filtered_df):,}개)")

if filtered_df.empty:
    st.info("필터 조건에 맞는 기사가 없습니다.")
else:
    # 점수 순으로 정렬
    if 'score_ag' in filtered_df.columns:
        filtered_df = filtered_df.sort_values('score_ag', ascending=False)
    
    # 기사 카드 표시
    # 기사 카드 표시
    for idx, row in filtered_df.iterrows():
        with st.container():
            col1, col2 = st.columns([0.85, 0.15])
            with col1:
                st.markdown(f"### [{row.get('category', 'N/A')}] {row['title']}")
                st.caption(f"{row.get('published_date', 'N/A')} | {row.get('site_name', 'N/A')}")
                st.markdown(f"{row.get('summary', 'N/A')}")
                st.markdown(f"[🔗 원문 보기]({row['url']})")
            
            with col2:
                score = row.get('score_ag', 0)
                st.metric("AI 점수", f"{score:.2f}")
                
            st.divider()

# ====================
# 통계
# ====================
st.markdown("---")
st.subheader("📊 통계")

stat_col1, stat_col2, stat_col3 = st.columns(3)

with stat_col1:
    st.markdown("### 카테고리별 분포")
    category_counts = filtered_df['category'].value_counts()
    st.bar_chart(category_counts)

with stat_col2:
    st.markdown("### 일자별 기사 수")
    if 'published_date' in filtered_df.columns:
        daily_counts = filtered_df.groupby('published_date').size()
        st.line_chart(daily_counts)

with stat_col3:
    st.markdown("### AI 점수 분포")
    if 'score_ag' in filtered_df.columns:
        st.bar_chart(filtered_df['score_ag'].value_counts().sort_index())

st.markdown("---")
st.caption("🔒 Internal Only - 모든 키워드 포함 (경쟁사 포함)")
