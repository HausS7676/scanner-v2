import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
from utils.data_engine import load_ohlcv, get_investor_flow, get_latest_valid_date, get_recent_news, get_krx_stock_list
from utils.indicators import analyze_technical
from utils.strategy import generate_trading_strategy
from utils.ui_components import render_detail_analysis

@st.cache_data(ttl=1)
def get_krx_mapping():
    import pandas as pd
    import requests
    from io import StringIO
    
    urls = [
        "https://raw.githubusercontent.com/HausS7676/portfolio-web/main/utils/krx_stock_list.csv",
        "https://raw.githubusercontent.com/HausS7676/portfolio-web/main/krx_stock_list.csv"
    ]
    for url in urls:
        try:
            res = requests.get(url, timeout=3)
            if res.status_code == 200:
                df = pd.read_csv(StringIO(res.text), dtype={'Code': str})
                df['Code'] = df['Code'].astype(str).str.zfill(6)
                if not df.empty and 'Name' in df.columns:
                    return dict(zip(df['Name'], df['Code']))
        except: pass
        
    try:
        import FinanceDataReader as fdr
        df1 = fdr.StockListing('KOSPI')
        df2 = fdr.StockListing('KOSDAQ')
        df = pd.concat([df1, df2])
        if not df.empty:
            return dict(zip(df['Name'], df['Code']))
    except: pass

    return {}

st.set_page_config(page_title="종목 상세분석", page_icon="🔍", layout="wide")

st.markdown("""
<style>
.strategy-box {
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(99, 179, 237, 0.4);
    border-radius: 12px;
    padding: 20px;
    margin-top: 10px;
}
.badge {
    padding: 6px 16px;
    border-radius: 20px;
    font-size: 1.1rem;
    font-weight: bold;
    color: white;
}
.badge-buy { background: linear-gradient(135deg, #059669, #10b981); }
.badge-sell { background: linear-gradient(135deg, #b91c1c, #ef4444); }
.badge-hold { background: linear-gradient(135deg, #b45309, #f59e0b); }
</style>
""", unsafe_allow_html=True)

st.title("🔍 종목 심층 분석 및 AI 트레이딩 전략")

with st.form("search_form", clear_on_submit=False):
    col1, col2 = st.columns([1, 2])
    with col1:
        search_query = st.text_input("종목명 또는 종목코드 6자리를 입력하세요", value="", placeholder="종목명 또는 코드 입력 후 엔터")
        engine = st.session_state.get('data_engine', '자동')
        
    submitted = st.form_submit_button("분석 시작", type="primary")

if submitted:
    query = search_query.strip()
    if not query:
        st.warning("종목명이나 코드를 입력해주세요.")
    else:
        mapping = get_krx_mapping()
        mapping_upper = {str(k).upper(): v for k, v in mapping.items()}
        query_upper = query.upper()
        
        # 종목명으로 입력한 경우 코드 변환
        if query_upper in mapping_upper:
            ticker = mapping_upper[query_upper]
            # 원래 이름 찾기
            reverse_mapping = {v: k for k, v in mapping.items()}
            ticker_name = reverse_mapping.get(ticker, query)
        else:
            ticker = query_upper
            # 코드로 입력한 경우 이름 찾기 (역방향)
            reverse_mapping = {v: k for k, v in mapping.items()}
            ticker_name = reverse_mapping.get(ticker, ticker)
            
        base_date = get_latest_valid_date()
        
        with st.spinner(f"'{ticker_name}' ({ticker}) 종목 데이터 및 기관 수급 분석 중..."):
            render_detail_analysis(ticker, ticker_name, base_date, engine)
