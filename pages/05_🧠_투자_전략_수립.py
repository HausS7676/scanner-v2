import streamlit as st
import pandas as pd
import yfinance as yf
from utils.portfolio_manager import load_portfolio
from datetime import datetime, timedelta

st.set_page_config(page_title="투자 전략 수립", page_icon="🧠", layout="wide")

st.title("🧠 전문가 투자 전략 수립")
st.markdown("거시경제 흐름과 현재 보유 중인 포트폴리오의 기술적 위치를 종합 분석하여 최적의 매매 시나리오를 제시합니다.")

@st.cache_data(ttl=86400) # 1일 캐싱하여 장중 변동 최소화
def analyze_macro_trend():
    end = datetime.now()
    start = end - timedelta(days=200)
    
    # Fetch Data
    nasdaq = yf.download("^IXIC", start=start.strftime('%Y-%m-%d'), end=end.strftime('%Y-%m-%d'), progress=False)
    sp500 = yf.download("^GSPC", start=start.strftime('%Y-%m-%d'), end=end.strftime('%Y-%m-%d'), progress=False)
    usdkrw = yf.download("KRW=X", start=start.strftime('%Y-%m-%d'), end=end.strftime('%Y-%m-%d'), progress=False)
    
    def get_close(df):
        if df.empty: return pd.Series(dtype=float)
        close = df['Close']
        if isinstance(close, pd.DataFrame):
            return close.iloc[:, 0].dropna()
        return close.dropna()
        
    nq_close = get_close(nasdaq)
    sp_close = get_close(sp500)
    krw_close = get_close(usdkrw)
    
    if len(nq_close) < 60 or len(sp_close) < 60 or len(krw_close) < 60:
        return "데이터 부족 (Unknown)", 50, "데이터 수집 부족"
        
    nq_current, nq_ma20, nq_ma60 = nq_close.iloc[-1], nq_close.rolling(20).mean().iloc[-1], nq_close.rolling(60).mean().iloc[-1]
    sp_current, sp_ma20 = sp_close.iloc[-1], sp_close.rolling(20).mean().iloc[-1]
    krw_current, krw_ma20 = krw_close.iloc[-1], krw_close.rolling(20).mean().iloc[-1]
    
    score = 0
    reasons = []
    
    if nq_current > nq_ma20: score += 1; reasons.append("나스닥 단기 상회(20일선)")
    else: score -= 1; reasons.append("나스닥 단기 하회(20일선)")
        
    if nq_current > nq_ma60: score += 1; reasons.append("나스닥 중기 상회(60일선)")
    else: score -= 1; reasons.append("나스닥 중기 하회(60일선)")
        
    if sp_current > sp_ma20: score += 1; reasons.append("S&P500 단기 상회(20일선)")
    else: score -= 1; reasons.append("S&P500 단기 하회(20일선)")
        
    if krw_current > krw_ma20: score -= 1; reasons.append("환율 단기 상승(증시 부담)")
    else: score += 1; reasons.append("환율 단기 하락(증시 호재)")
        
    cash_weight = 50
    if score >= 3: market_status, cash_weight = "강세장 (Strong Bull)", 20
    elif score == 2: market_status, cash_weight = "상승 전환 (Bull)", 30
    elif score in [0, 1]: market_status, cash_weight = "혼조세 (Mixed)", 50
    elif score == -2: market_status, cash_weight = "하락 우려 (Warning)", 60
    else: market_status, cash_weight = "약세장 (Bear)", 80
        
    return market_status, cash_weight, " | ".join(reasons)

market_status, cash_weight, reasons_str = analyze_macro_trend()

col1, col2 = st.columns(2)
with col1:
    st.info(f"### 🌐 글로벌 증시 상태: **{market_status}**")
    st.write(f"판단 근거: {reasons_str}")
with col2:
    st.success(f"### 💰 권장 현금 비중: **{cash_weight}%**")
    st.write(f"현재 장세에서는 계좌 전체 자산 중 **{cash_weight}%**를 현금으로 보유하여 리스크를 관리하는 것을 권장합니다.")

st.markdown("---")
st.subheader("💼 내 포트폴리오 종목별 맞춤 매매 시나리오")

data = load_portfolio()
holdings = data.get("holdings", [])

if not holdings:
    st.warning("등록된 보유 종목이 없습니다. [포트폴리오 관리] 메뉴에서 종목을 추가해 주세요.")
else:
    import FinanceDataReader as fdr
    
    for holding in holdings:
        ticker = holding['ticker']
        name = holding['name']
        avg_price = holding['avg_price']
        
        try:
            df = fdr.DataReader(ticker, (datetime.now() - timedelta(days=150)).strftime('%Y-%m-%d'))
            if df.empty:
                continue
                
            close = df['Close']
            ma20 = close.rolling(20).mean().iloc[-1]
            ma60 = close.rolling(60).mean().iloc[-1]
            current = close.iloc[-1]
            
            delta = close.diff()
            up = delta.clip(lower=0)
            down = (-delta).clip(lower=0)
            rs = up.ewm(com=13, adjust=False).mean() / down.ewm(com=13, adjust=False).mean()
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            pnl_pct = ((current * 0.998 - avg_price) / avg_price) * 100
            
            # 전략 로직
            strategy = ""
            action = ""
            color = ""
            
            if pnl_pct <= -9.0:
                action = "🚨 기계적 손절 요망"
                strategy = "원칙에 따라 손절선(-9%)을 이탈했습니다. 리스크 관리를 위해 비중 축소 또는 전량 매도를 고려하세요."
                color = "error"
            elif current_rsi >= 75:
                action = "✂️ 분할 매도 (차익 실현)"
                strategy = f"RSI가 {current_rsi:.1f}로 심각한 과매수 구간입니다. 단기 고점일 확률이 높으므로 보유 물량의 30~50%를 익절하세요."
                color = "warning"
            elif current_rsi <= 30 and current > ma60:
                action = "🛒 분할 매수 (비중 확대)"
                strategy = f"중장기 추세(60일선)는 살아있으나 단기 낙폭이 과대합니다 (RSI {current_rsi:.1f}). 지지선 부근에서 분할 매수를 고려하세요."
                color = "success"
            elif current > ma20:
                action = "🧘‍♂️ 강력 보유 (Hold)"
                strategy = "20일선 위에서 안정적인 추세를 유지하고 있습니다. 수익을 극대화하며 보유하세요."
                color = "info"
            else:
                action = "👀 관망 (Wait & See)"
                strategy = "명확한 방향성이 부재합니다. 신규 매수는 자제하고 기존 물량만 홀딩하세요."
                color = "normal"
                
            with st.expander(f"📌 {name} ({ticker}) - 현재가: {current:,.0f}원 | 내 평단: {avg_price:,.0f}원 | 수익률: {pnl_pct:.2f}%", expanded=True):
                st.markdown(f"**전략 요약:** {action}")
                st.write(strategy)
                st.caption(f"기술적 지표 - RSI: {current_rsi:.1f} | 20일선: {ma20:,.0f}원 | 60일선: {ma60:,.0f}원")
                
        except Exception as e:
            continue
            
st.markdown("---")
st.subheader("💡 퀀트 및 테마 기반 전략 조언")
st.info("""
- 주식 스캐너 결과에서 **[추세 추종형]** 상위 종목은 포트폴리오의 '공격수' 포지션(전체 비중 20~30% 내외)으로 활용하세요.
- 포트폴리오 관리 탭에서 **[트레일링 스탑]** 알람이 발생한 종목은 미련 없이 익절하여 계좌 수익을 확정 짓는 것이 중요합니다.
- 거시경제 지표상 금리 인하기에 접어들면 바이오/헬스케어 및 중소형 기술주의 비중을 서서히 높이는 것을 고려해 볼 수 있습니다.
""")
