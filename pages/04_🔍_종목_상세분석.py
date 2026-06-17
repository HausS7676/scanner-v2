import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
from utils.data_engine import load_ohlcv, get_investor_flow, get_latest_valid_date, get_recent_news, get_krx_stock_list
from utils.indicators import analyze_technical
from utils.strategy import generate_trading_strategy
from utils.ui_components import render_detail_analysis, get_stock_summary
import pandas as pd

@st.cache_data(ttl=1)
def get_krx_mapping():
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

col1, col2 = st.columns([1, 2])
with col1:
    search_query = st.text_input("종목명 또는 종목코드 6자리를 입력하세요 (쉼표로 구분하여 여러 종목 동시 비교 가능)", value="", placeholder="예: 삼성전자, SK하이닉스, 005380")
    engine = st.session_state.get('data_engine', '자동')
    
st.button("분석 시작", type="primary")

if search_query:
    raw_queries = [q.strip() for q in search_query.split(',') if q.strip()]
    if not raw_queries:
        st.warning("종목명이나 코드를 입력해주세요.")
    else:
        mapping = get_krx_mapping()
        mapping_upper = {str(k).upper(): v for k, v in mapping.items()}
        reverse_mapping = {v: k for k, v in mapping.items()}
        base_date = get_latest_valid_date()
        
        parsed_queries = []
        for query in raw_queries:
            query_upper = query.upper()
            if query_upper in mapping_upper:
                ticker = mapping_upper[query_upper]
                ticker_name = reverse_mapping.get(ticker, query)
            else:
                ticker = query_upper
                ticker_name = reverse_mapping.get(ticker, ticker)
            parsed_queries.append((ticker, ticker_name))
            
        if len(parsed_queries) == 1:
            # 단일 종목 검색
            ticker, ticker_name = parsed_queries[0]
            with st.spinner(f"'{ticker_name}' ({ticker}) 분석 중..."):
                render_detail_analysis(ticker, ticker_name, base_date, engine)
        else:
            # 다중 종목 검색 (비교 테이블)
            st.markdown("### 📊 다중 종목 비교 분석")
            
            # 데이터 수집 (캐싱을 피하기 위해 직접 호출하거나, 성능을 위해 st.cache_data를 쓸 수 있지만 여기선 직접 수집)
            summary_list = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, (ticker, ticker_name) in enumerate(parsed_queries):
                status_text.text(f"[{idx+1}/{len(parsed_queries)}] '{ticker_name}' 데이터 수집 중...")
                summ = get_stock_summary(ticker, ticker_name, base_date, engine)
                if summ:
                    summary_list.append(summ)
                progress_bar.progress((idx + 1) / len(parsed_queries))
            
            status_text.empty()
            progress_bar.empty()
            
            if not summary_list:
                st.error("분석 가능한 종목 데이터가 없습니다.")
            else:
                df_summary = pd.DataFrame(summary_list)
                
                st.info("👇 **표에서 종목을 클릭(선택)하면 하단에 상세 분석 리포트가 표시됩니다.**")
                
                # 데이터프레임 이벤트
                event = st.dataframe(
                    df_summary,
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row"
                )
                
                selected_rows = event.selection.rows
                
                if selected_rows:
                    selected_idx = selected_rows[0]
                    sel_ticker = df_summary.iloc[selected_idx]['코드']
                    sel_name = df_summary.iloc[selected_idx]['종목명']
                    
                    st.markdown(f"<hr style='margin: 30px 0; border: 1px solid #4a5568;'>", unsafe_allow_html=True)
                    with st.spinner(f"'{sel_name}' 상세 리포트 렌더링 중..."):
                        render_detail_analysis(sel_ticker, sel_name, base_date, engine)
