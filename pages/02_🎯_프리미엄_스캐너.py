import streamlit as st
import pandas as pd
from utils.data_engine import scan_hybrid_flow, load_ohlcv, get_recent_investor_flow_fast
from utils.indicators import analyze_technical, compute_recommendation_score, compute_trend_following_score
from utils.ui_components import render_detail_analysis
import io

st.set_page_config(page_title="프리미엄 스캐너", page_icon="🎯", layout="wide")

st.title("🎯 프리미엄 수급 및 모멘텀 스캐너")
st.markdown("수급 회전율, 거래대금, RSI 및 이평선 추세를 복합 분석하여 급등 확률이 높은 종목을 포착합니다.")

c1, c2 = st.columns(2)
with c1: min_cap = st.number_input('최소 시가총액 (억 단위)', value=1000, step=100)
with c2: min_trade = st.number_input('최소 거래대금 (억 단위)', value=20, step=10)

if 'scan_result' not in st.session_state:
    st.session_state.scan_result = None
    st.session_state.scan_base_date = ""

@st.dialog("🔍 종목 상세 분석 리포트", width="large")
def show_detail_popup(ticker, ticker_name, base_date, engine):
    st.markdown(f"### {ticker_name} ({ticker}) 심층 분석")
    render_detail_analysis(ticker, ticker_name, base_date, engine)

if st.button('🚀 스캐너 가동', type="primary"):
    with st.spinner('시장 전체 종목 스캔 중... (200개 종목 분석에 약 1~2분 소요될 수 있습니다)'):
        engine = st.session_state.get('data_engine', '자동')
        result, base_date = scan_hybrid_flow(min_mktcap=min_cap, min_trading=min_trade)
        
        if result.empty:
            st.warning("조건을 만족하는 종목이 없습니다.")
            st.session_state.scan_result = None
        else:
            st.success(f"✅ {base_date} 기준 데이터 스캔 완료!")
            top_stocks = result.head(200).copy().reset_index(drop=True)
            
            trends, rsis = [], []
            ins_scores, for_scores = [], []
            ins_days_list, for_days_list = [], []
            ins_vols_list, for_vols_list = [], []
            
            my_bar = st.progress(0)
            status_text = st.empty()
            
            for i, ticker in enumerate(top_stocks['티커']):
                status_text.text(f"스캔 진행 중... ({i+1}/{len(top_stocks)})")
                df = load_ohlcv(ticker, base_date, 100, engine)
                tech = analyze_technical(df)
                if tech:
                    trends.append(tech['추세'])
                    rsis.append(tech['RSI'])
                else:
                    trends.append("데이터 부족")
                    rsis.append(50.0)
                
                # 매집 점수 계산
                flow_df = get_recent_investor_flow_fast(ticker)
                
                def calc_acc_score(series):
                    if len(series) == 0: return 50, 0, 0, 0
                    
                    # 최근 20일 기준
                    recent_series = series.tail(20)
                    total_days = (recent_series > 0).sum()
                    total_vol = recent_series[recent_series > 0].sum() - abs(recent_series[recent_series < 0].sum())
                    
                    # 연속 매수/매도일 계산
                    last_val = series.iloc[-1]
                    consec_days = 0
                    if last_val > 0:
                        for v in series.values[::-1]:
                            if v > 0: consec_days += 1
                            else: break
                        score = min(50 + (total_days * 3) + (consec_days * 8) + (total_vol / 100000), 100)
                        return score, total_days, consec_days, total_vol
                    elif last_val < 0:
                        for v in series.values[::-1]:
                            if v < 0: consec_days += 1
                            else: break
                        score = max(50 - (total_days * 3) - (consec_days * 8) - (abs(total_vol) / 100000), 0)
                        return score, total_days, -consec_days, total_vol
                    else:
                        return 50, total_days, 0, total_vol
                        
                i_sc, i_tot_dy, i_cons_dy, i_vol = 50, 0, 0, 0
                f_sc, f_tot_dy, f_cons_dy, f_vol = 50, 0, 0, 0
                if not flow_df.empty:
                    i_sc, i_tot_dy, i_cons_dy, i_vol = calc_acc_score(flow_df['기관합계'])
                    f_sc, f_tot_dy, f_cons_dy, f_vol = calc_acc_score(flow_df['외국인합계'])
                
                ins_scores.append(int(i_sc))
                ins_days_list.append(f"{i_tot_dy}일 / {i_cons_dy}일")
                ins_vols_list.append(int(i_vol))
                for_scores.append(int(f_sc))
                for_days_list.append(f"{f_tot_dy}일 / {f_cons_dy}일")
                for_vols_list.append(int(f_vol))
                
                my_bar.progress((i + 1) / len(top_stocks))
                
            status_text.empty()
            my_bar.empty()
            
            top_stocks['추세'] = trends
            top_stocks['RSI'] = rsis
            top_stocks['기관매집점수'] = ins_scores
            top_stocks['기관매집(20일중/연속)'] = ins_days_list
            top_stocks['기관누적매집량(주)'] = ins_vols_list
            top_stocks['외국인매집점수'] = for_scores
            top_stocks['외국인매집(20일중/연속)'] = for_days_list
            top_stocks['외국인누적매집량(주)'] = for_vols_list
            
            top_stocks['거래대금_rank'] = top_stocks['거래대금(억)'].rank(pct=True)
            top_stocks['추천점수'] = top_stocks.apply(compute_recommendation_score, axis=1)
            top_stocks['추세추종점수'] = top_stocks.apply(compute_trend_following_score, axis=1)
            
            st.session_state.scan_result = top_stocks
            st.session_state.scan_base_date = base_date

if st.session_state.scan_result is not None:
    top_stocks = st.session_state.scan_result.copy()
    base_date = st.session_state.scan_base_date
    
    # 엑셀/CSV 다운로드 버튼
    csv_data = top_stocks.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 스캔 결과 다운로드 (CSV)",
        data=csv_data,
        file_name=f"스캔결과_{base_date}.csv",
        mime="text/csv",
        help="엑셀에서 바로 열 수 있는 CSV 파일로 다운로드합니다."
    )
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 장세 맞춤형 추천", "📈 추세추종형 추천", "🏢 기관 매집 종목", "🗽 외국인 매집 종목"])
    
    display_cols = ['종목명', '현재가', '등락률(%)', '시가총액(억)', '거래대금(억)', '수급점수', '추세', 'RSI']
    
    def rank_label(i): return {1: '🥇', 2: '🥈', 3: '🥉'}.get(i, f'{i}위')

    with tab1:
        st.subheader("📊 장세 맞춤형 추천 리포트")
        df1 = top_stocks.sort_values('추천점수', ascending=False).reset_index(drop=True)
        df1.index += 1
        df1.insert(0, '순위', [rank_label(i) for i in df1.index])
        
        event1 = st.dataframe(df1[['순위'] + display_cols + ['추천점수']].set_index('순위'), use_container_width=True, height=500, on_select="rerun", selection_mode="single-row", key="tab1_df")
        
    with tab2:
        st.subheader("📈 추세추종형 추천 리포트")
        df2 = top_stocks.sort_values('추세추종점수', ascending=False).reset_index(drop=True)
        df2.index += 1
        df2.insert(0, '순위', [rank_label(i) for i in df2.index])
        
        event2 = st.dataframe(df2[['순위'] + display_cols + ['추세추종점수']].set_index('순위'), use_container_width=True, height=500, on_select="rerun", selection_mode="single-row", key="tab2_df")

    with tab3:
        st.subheader("🏢 기관 매집 종목 (스마트머니)")
        st.markdown("최근 20거래일 동안의 매집 강도와 연속 매수일을 복합적으로 분석하여 점수를 산출합니다.")
        df3 = top_stocks.sort_values('기관매집점수', ascending=False).reset_index(drop=True)
        df3 = df3[df3['기관매집점수'] > 50] # 순매수인 경우만 필터링
        df3.index += 1
        df3.insert(0, '순위', [rank_label(i) for i in df3.index])
        
        event3 = st.dataframe(df3[['순위', '종목명', '현재가', '등락률(%)', '시가총액(억)', '기관매집(20일중/연속)', '기관누적매집량(주)', '기관매집점수']].set_index('순위'), use_container_width=True, height=500, on_select="rerun", selection_mode="single-row", key="tab3_df")

    with tab4:
        st.subheader("🗽 외국인 매집 종목 (글로벌 핫픽)")
        st.markdown("최근 20거래일 동안의 매집 강도와 연속 매수일을 복합적으로 분석하여 점수를 산출합니다.")
        df4 = top_stocks.sort_values('외국인매집점수', ascending=False).reset_index(drop=True)
        df4 = df4[df4['외국인매집점수'] > 50] # 순매수인 경우만 필터링
        df4.index += 1
        df4.insert(0, '순위', [rank_label(i) for i in df4.index])
        
        event4 = st.dataframe(df4[['순위', '종목명', '현재가', '등락률(%)', '시가총액(억)', '외국인매집(20일중/연속)', '외국인누적매집량(주)', '외국인매집점수']].set_index('순위'), use_container_width=True, height=500, on_select="rerun", selection_mode="single-row", key="tab4_df")
    
    st.markdown("---")
    st.subheader("🔍 선택 종목 팝업 상세 분석")
    st.info("👆 위 표에서 원하는 종목의 행을 클릭하시면 전문가의 팝업 상세 분석 리포트가 열립니다!")
    
    selected_row = None
    if len(event1.selection.rows) > 0:
        selected_row = df1.iloc[event1.selection.rows[0]]
    elif len(event2.selection.rows) > 0:
        selected_row = df2.iloc[event2.selection.rows[0]]
    elif len(event3.selection.rows) > 0:
        selected_row = df3.iloc[event3.selection.rows[0]]
    elif len(event4.selection.rows) > 0:
        selected_row = df4.iloc[event4.selection.rows[0]]
        
    if selected_row is not None:
        ticker = selected_row['티커']
        selected_stock = selected_row['종목명']
        engine = st.session_state.get('data_engine', '자동')
        show_detail_popup(ticker, selected_stock, base_date, engine)
