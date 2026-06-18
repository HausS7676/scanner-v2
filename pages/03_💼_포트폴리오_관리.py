import streamlit as st
import pandas as pd
from datetime import datetime
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

# 탭 분리
tab_hold, tab_watch = st.tabs(["💼 보유종목 현황", "👀 관심종목 관리"])

with tab_hold:
    with st.expander("➕ 새 보유 종목 추가 / 물타기(추가 매수)", expanded=False):
        if "selected_stocks_hold" not in st.session_state:
            st.session_state.selected_stocks_hold = []
            
        names = st.multiselect("종목명 검색 (여러 개 선택 가능)", stock_names, key="selected_stocks_hold")
        
        if names:
            st.markdown("---")
            with st.form("add_holding_form", clear_on_submit=True):
                st.markdown("**선택한 종목 설정**")
                input_data = {}
                for name in names:
                    st.markdown(f"🔹 **{name}**")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        broker = st.selectbox("증권사 (계좌)", ["키움증권", "삼성증권", "미래에셋증권", "NH투자증권", "KB증권", "한국투자증권", "토스증권", "카카오페이증권", "현대차증권", "기타"], key=f"broker_{name}")
                    with col2:
                        shares = st.number_input("수량", min_value=1, step=1, key=f"shares_{name}")
                    with col3:
                        avg_price = st.number_input("평균단가", min_value=0, step=100, key=f"price_{name}")
                    with col4:
                        buy_date = st.date_input("매입일", value=datetime.today(), key=f"date_{name}")
                        
                    input_data[name] = {"broker": broker, "shares": shares, "avg_price": avg_price, "buy_date": buy_date.strftime("%Y-%m-%d")}
                    
                submitted = st.form_submit_button("일괄 추가")
                if submitted:
                    for name, d in input_data.items():
                        ticker = stock_df[stock_df['Name'] == name]['Code'].values[0]
                        add_holding(ticker, name, d['shares'], d['avg_price'], d['broker'], buy_date=d['buy_date'])
                    st.success(f"{len(names)}개 보유 종목이 추가되었습니다!")
                    del st.session_state.selected_stocks_hold
                    st.rerun()

    st.markdown("---")
    
    data = load_portfolio()
    holdings = data.get("holdings", [])
    real_holdings = [h for h in holdings if h.get('account', '') != '관심종목']
    
    if not real_holdings:
        st.info("현재 등록된 보유 종목이 없습니다. 위 메뉴에서 새 종목을 추가해 보세요.")
    else:
        df = pd.DataFrame(real_holdings)
        
        # 증권사 필터링
        brokers = ["전체"] + sorted(list(df['account'].unique()))
        selected_broker = st.selectbox("📊 증권사 필터", brokers)
        if selected_broker != "전체":
            df = df[df['account'] == selected_broker]
            
        current_prices = {}
        for t in df['ticker'].unique():
            try:
                price_df = fdr.DataReader(t, '2024-01-01')
                if not price_df.empty:
                    current_price = int(price_df['Close'].iloc[-1])
                    current_prices[t] = current_price
                    update_peak(t, current_price)
                else:
                    current_prices[t] = 0
            except:
                current_prices[t] = 0
                
        peaks = load_portfolio().get("peaks", {})
        
        table_data = []
        total_invested = 0
        total_value = 0
        
        today = datetime.now()
        
        for _, row in df.iterrows():
            t = row['ticker']
            n = row['name']
            s = row['shares']
            avg_p = row['avg_price']
            acc = row.get('account', '기타')
            b_date_str = row.get('buy_date', today.strftime("%Y-%m-%d"))
            
            try:
                b_date = datetime.strptime(b_date_str, "%Y-%m-%d")
                holding_days = (today - b_date).days
                if holding_days >= 90: holding_display = f"{holding_days}일 🔴"
                elif holding_days >= 60: holding_display = f"{holding_days}일 🟠"
                elif holding_days >= 14: holding_display = f"{holding_days}일 🟡"
                else: holding_display = f"{holding_days}일"
            except:
                holding_display = "0일"
                
            cur_p = current_prices.get(t, 0)
            real_cur_p = cur_p * 0.998
            invested = s * avg_p
            value = s * real_cur_p
            
            total_invested += invested
            total_value += value
            pnl = value - invested
            pnl_pct = (pnl / invested) * 100 if invested > 0 else 0
            
            peak_p = peaks.get(t, avg_p)
            trailing_drop = ((real_cur_p - peak_p) / peak_p) * 100 if peak_p > 0 else 0
            
            status = []
            if pnl_pct <= -9.0: status.append("🔴 손절 경고 (-9% 하회)")
            if trailing_drop <= -9.0: status.append("🔵 트레일링 스탑 (고점대비 -9%)")
            if not status:
                if pnl_pct > 0: status.append("🟢 수익 중")
                else: status.append("⚪ 관망 중")
                
            table_data.append({
                "계좌": acc,
                "종목코드": t,
                "종목명": n,
                "매입일": b_date_str,
                "보유기간": holding_display,
                "수량": s,
                "평균단가": avg_p,
                "현재가": cur_p,
                "투자원금": invested,
                "평가금액": value,
                "수익률(%)": round(pnl_pct, 2),
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
            
        res_df = pd.DataFrame(table_data)
        res_df = res_df.sort_values(by=['계좌', '종목명']).reset_index(drop=True)
        
        # 엑셀 다운로드
        st.download_button(
            label="📥 보유종목 엑셀 다운로드 (CSV)",
            data=res_df.to_csv(index=False).encode('utf-8-sig'),
            file_name=f"보유종목_{today.strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
        st.markdown("💡 **Tip:** 아래 표의 **수량**, **평균단가**, **계좌(증권사)**, **매입일** 부분을 클릭하면 엑셀처럼 직접 수정할 수 있습니다. (2주 🟡, 2달 🟠, 3달 🔴 경과 시 알림)")
        
        edited_df = st.data_editor(
            res_df,
            use_container_width=True,
            num_rows="dynamic",
            height=500,
            disabled=["종목코드", "종목명", "보유기간", "현재가", "투자원금", "평가금액", "수익률(%)", "상태 (알림)"]
        )
        
        if st.button("💾 테이블 변경사항 저장", type="primary"):
            for _, row in edited_df.iterrows():
                if row['수량'] > 0:
                    add_holding(
                        ticker=row['종목코드'],
                        name=row['종목명'],
                        shares=row['수량'],
                        avg_price=row['평균단가'],
                        account=row['계좌'],
                        buy_date=row['매입일']
                    )
                else:
                    remove_holding(row['종목코드'])
            st.success("포트폴리오가 성공적으로 업데이트되었습니다!")
            st.rerun()
        
        st.info("💡 **수익률 계산 방식**: 보수적인 포트폴리오 관리를 위해 매도 수수료(0.2%)를 미리 차감한 '실수익 기준'으로 계산됩니다.")

with tab_watch:
    with st.expander("➕ 새 관심 종목 추가", expanded=False):
        if "selected_stocks_watch" not in st.session_state:
            st.session_state.selected_stocks_watch = []
            
        names = st.multiselect("종목명 검색 (여러 개 선택 가능)", stock_names, key="selected_stocks_watch")
        
        if names:
            st.markdown("---")
            with st.form("add_watch_form", clear_on_submit=True):
                st.markdown("**선택한 종목 설정**")
                input_data = {}
                for name in names:
                    st.markdown(f"🔹 **{name}**")
                    col1, col2 = st.columns(2)
                    with col1:
                        folder = st.text_input("폴더명 (예: 스윙후보, 장기투자)", value="기본", key=f"folder_{name}")
                    with col2:
                        sector = st.text_input("섹터/테마 (예: 2차전지, 반도체)", value="", key=f"sector_{name}")
                        
                    input_data[name] = {"folder": folder, "sector": sector}
                    
                submitted = st.form_submit_button("일괄 추가")
                if submitted:
                    for name, d in input_data.items():
                        ticker = stock_df[stock_df['Name'] == name]['Code'].values[0]
                        add_holding(ticker, name, 0, 0, "관심종목", folder=d['folder'], sector=d['sector'])
                    st.success(f"{len(names)}개 관심 종목이 추가되었습니다!")
                    del st.session_state.selected_stocks_watch
                    st.rerun()

    st.markdown("---")
    watch_holdings = [h for h in holdings if h.get('account', '') == '관심종목']
    
    if not watch_holdings:
        st.info("현재 등록된 관심 종목이 없습니다. 위 메뉴에서 새 종목을 추가해 보세요.")
    else:
        df_watch = pd.DataFrame(watch_holdings)
        if 'folder' not in df_watch.columns: df_watch['folder'] = '기본'
        if 'sector' not in df_watch.columns: df_watch['sector'] = ''
        
        # 필터링
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            folders = ["전체"] + sorted(list(df_watch['folder'].fillna('기본').unique()))
            selected_folder = st.selectbox("📁 폴더 필터", folders)
            if selected_folder != "전체":
                df_watch = df_watch[df_watch['folder'] == selected_folder]
        with col_f2:
            sectors = ["전체"] + sorted(list(df_watch['sector'].fillna('').unique()))
            selected_sector = st.selectbox("🏭 섹터 필터", sectors)
            if selected_sector != "전체":
                df_watch = df_watch[df_watch['sector'] == selected_sector]
                
        # 현재가 
        current_prices_watch = {}
        for t in df_watch['ticker'].unique():
            try:
                price_df = fdr.DataReader(t, '2024-01-01')
                if not price_df.empty:
                    current_prices_watch[t] = int(price_df['Close'].iloc[-1])
                else:
                    current_prices_watch[t] = 0
            except:
                current_prices_watch[t] = 0
                
        watch_data = []
        for _, row in df_watch.iterrows():
            t = row['ticker']
            n = row['name']
            f = row.get('folder', '기본')
            sec = row.get('sector', '')
            cur_p = current_prices_watch.get(t, 0)
            
            watch_data.append({
                "폴더명": f,
                "섹터": sec,
                "종목코드": t,
                "종목명": n,
                "현재가": f"{cur_p:,.0f}원",
                "등록일": row.get('buy_date', '')
            })
            
        res_watch = pd.DataFrame(watch_data).sort_values(by=['폴더명', '섹터', '종목명']).reset_index(drop=True)
        
        st.download_button(
            label="📥 관심종목 엑셀 다운로드 (CSV)",
            data=res_watch.to_csv(index=False).encode('utf-8-sig'),
            file_name=f"관심종목_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
        st.markdown("💡 **Tip:** 아래 표의 **폴더명**, **섹터**, **등록일**을 직접 클릭해서 엑셀처럼 수정하고 저장할 수 있습니다. (종목을 삭제하려면 폴더명과 섹터를 지우지 마시고, 보유종목 탭에서 0주로 매도 처리하거나 포트폴리오 초기화를 이용하세요.)")
        
        edited_watch = st.data_editor(
            res_watch,
            use_container_width=True,
            num_rows="dynamic",
            height=500,
            disabled=["종목코드", "종목명", "현재가"]
        )
        
        if st.button("💾 관심종목 변경사항 저장", type="primary"):
            for _, row in edited_watch.iterrows():
                # For watchlists, keep account as '관심종목'
                add_holding(
                    ticker=row['종목코드'],
                    name=row['종목명'],
                    shares=0,
                    avg_price=0,
                    account='관심종목',
                    buy_date=row['등록일'],
                    folder=row['폴더명'],
                    sector=row['섹터']
                )
            st.success("관심종목이 성공적으로 업데이트되었습니다!")
            st.rerun()
