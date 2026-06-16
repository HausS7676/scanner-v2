import streamlit as st
import pandas as pd
from utils.portfolio_manager import load_portfolio, add_holding, remove_holding, update_peak
import FinanceDataReader as fdr

st.set_page_config(page_title="포트폴리오 관리", page_icon="💼", layout="wide")

st.title("💼 포트폴리오 관리")
st.markdown("현재 보유 중인 주식을 관리하고, 수익률 및 위험(손절/트레일링 스탑) 알림을 확인하세요.")

# 포트폴리오 데이터 로드
data = load_portfolio()
holdings = data.get("holdings", [])
peaks = data.get("peaks", {})

@st.cache_data(ttl=1)
def get_stock_list():
    import pandas as pd
    import requests
    from io import StringIO
    
    # 1. 깃허브에서 직접 CSV 읽어오기 (폴더 위치 실수 방어)
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
                    return df[['Code', 'Name']].dropna()
        except: pass

    # 2. fdr KOSPI/KOSDAQ 실시간 로드
    try:
        import FinanceDataReader as fdr
        df1 = fdr.StockListing('KOSPI')
        df2 = fdr.StockListing('KOSDAQ')
        df = pd.concat([df1, df2])
        if not df.empty:
            return df[['Code', 'Name']].dropna()
    except: pass

    return pd.DataFrame(columns=['Code', 'Name'])

stock_df = get_stock_list()
stock_names = stock_df['Name'].tolist() if not stock_df.empty else []

if not stock_names:
    st.error("🚨 종목 데이터를 불러오지 못했습니다! 방금 생성해드린 `krx_stock_list.csv` 파일을 깃허브에 꼭 업로드해주세요!")

# 신규 종목 추가 폼
with st.expander("➕ 새 종목 추가", expanded=False):
    with st.form("add_holding_form"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            name = st.selectbox("종목명 검색", [""] + stock_names)
        with col2:
            broker = st.selectbox("증권사 (계좌)", ["관심종목", "키움증권", "삼성증권", "미래에셋증권", "NH투자증권", "KB증권", "한국투자증권", "토스증권", "카카오페이증권", "기타"])
        with col3:
            shares = st.number_input("수량 (관심은 0)", min_value=0, step=1)
        with col4:
            avg_price = st.number_input("평균단가", min_value=0, step=100)
            
        submitted = st.form_submit_button("추가")
        if submitted:
            if not name:
                st.error("종목을 선택해주세요.")
            else:
                ticker = stock_df[stock_df['Name'] == name]['Code'].values[0]
                add_holding(ticker, name, shares, avg_price, broker)
                st.success(f"[{broker}] {name} 종목이 추가되었습니다!")
                st.rerun()

st.markdown("---")
st.subheader("📋 내 보유 종목 현황")

if not holdings:
    st.info("현재 등록된 보유 종목이 없습니다. 위 메뉴에서 새 종목을 추가해 보세요.")
else:
    # 데이터 처리 로직
    df = pd.DataFrame(holdings)
    
    # 실시간 가격 조회
    current_prices = {}
    for t in df['ticker'].unique():
        try:
            # fdr을 통해 최근 1~2일 데이터 가져오기
            price_df = fdr.DataReader(t, '2024-01-01') # This might be slow if we query everything, let's just get latest
            if not price_df.empty:
                current_price = int(price_df['Close'].iloc[-1])
                current_prices[t] = current_price
                update_peak(t, current_price)
            else:
                current_prices[t] = 0
        except:
            current_prices[t] = 0
            
    # 최신 피크 값 다시 로드
    peaks = load_portfolio().get("peaks", {})
    
    table_data = []
    total_invested = 0
    total_value = 0
    
    for _, row in df.iterrows():
        t = row['ticker']
        n = row['name']
        s = row['shares']
        avg_p = row['avg_price']
        
        cur_p = current_prices.get(t, 0)
        
        # 수수료 고려 (매도 시 0.2%)
        real_cur_p = cur_p * 0.998
        
        invested = s * avg_p
        value = s * real_cur_p
        
        total_invested += invested
        total_value += value
        
        pnl = value - invested
        pnl_pct = (pnl / invested) * 100 if invested > 0 else 0
        
        peak_p = peaks.get(t, avg_p)
        trailing_drop = ((real_cur_p - peak_p) / peak_p) * 100 if peak_p > 0 else 0
        
        # 상태 뱃지 생성 로직 (portfolio-web 컨벤션)
        status = []
        if s == 0:
            status.append("👀 관심종목")
        else:
            if pnl_pct <= -9.0:
                status.append("🔴 손절 경고 (-9% 하회)")
            if trailing_drop <= -9.0:
                status.append("🔵 트레일링 스탑 (고점대비 -9%)")
                
            if not status:
                if pnl_pct > 0:
                    status.append("🟢 수익 중")
                else:
                    status.append("⚪ 관망 중")
                
        table_data.append({
            "계좌": row.get('account', '보유'),
            "종목코드": t,
            "종목명": n,
            "수량": f"{s:,}주",
            "평균단가": f"{avg_p:,.0f}원",
            "현재가": f"{cur_p:,.0f}원",
            "투자원금": f"{invested:,.0f}원",
            "평가금액": f"{value:,.0f}원",
            "수익률(%)": pnl_pct,
            "상태 (알림)": " / ".join(status)
        })

    # 전체 요약
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        st.metric("총 투자원금", f"{total_invested:,.0f} 원")
    with col_t2:
        total_pnl = total_value - total_invested
        st.metric("총 평가금액", f"{total_value:,.0f} 원", f"{total_pnl:,.0f} 원")
    with col_t3:
        total_pnl_pct = (total_pnl / total_invested) * 100 if total_invested > 0 else 0
        st.metric("총 수익률", f"{total_pnl_pct:.2f}%")
        
    st.markdown("---")
    
    # 수익률 포맷팅용
    def format_pct(val):
        color = 'red' if val > 0 else 'blue' if val < 0 else 'gray'
        return f'color: {color}; font-weight: bold;'
        
    res_df = pd.DataFrame(table_data)
    
    # 삭제 폼 연동을 위해 선택 기능 추가
    st.dataframe(res_df.style.map(format_pct, subset=["수익률(%)"]).format({"수익률(%)": "{:.2f}%"}), use_container_width=True)

    with st.expander("🗑 종목 삭제"):
        with st.form("delete_holding_form"):
            del_ticker = st.selectbox("삭제할 종목 선택", df['ticker'].unique(), format_func=lambda x: f"{x} - {df[df['ticker']==x]['name'].values[0]}")
            del_submit = st.form_submit_button("삭제")
            if del_submit:
                remove_holding(del_ticker)
                st.warning(f"종목이 포트폴리오에서 삭제되었습니다.")
                st.rerun()

st.info("💡 **수익률 계산 방식**: 보수적인 포트폴리오 관리를 위해 매도 수수료(0.2%)를 미리 차감한 '실수익 기준'으로 계산됩니다.")
