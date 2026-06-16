import streamlit as st
import pandas as pd
import yfinance as yf
from utils.portfolio_manager import load_portfolio
from datetime import datetime, timedelta

st.set_page_config(page_title="투자 전략 수립", page_icon="🧠", layout="wide")

st.title("🧠 전문가 투자 전략 수립")
st.markdown("거시경제 흐름과 현재 보유 중인 포트폴리오의 기술적 위치를 종합 분석하여 최적의 매매 시나리오를 제시합니다.")

@st.cache_data(ttl=3600)
def analyze_macro_trend():
    end = datetime.now()
    start = end - timedelta(days=200)
    nasdaq = yf.download("^IXIC", start=start.strftime('%Y-%m-%d'), end=end.strftime('%Y-%m-%d'), progress=False)
    
    if nasdaq.empty:
        return "Unknown", 50
        
    close = nasdaq['Close']
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
        
    ma20 = close.rolling(20).mean().iloc[-1]
    ma60 = close.rolling(60).mean().iloc[-1]
    current = close.iloc[-1]
    
    cash_weight = 50
    market_status = "중립 (Neutral)"
    
    if current > ma20 and ma20 > ma60:
        market_status = "강세장 (Bull Market)"
        cash_weight = 20  # 주식 비중 확대
    elif current < ma20 and ma20 < ma60:
        market_status = "약세장 (Bear Market)"
        cash_weight = 70  # 현금 비중 확대
    elif current > ma60:
        market_status = "조정 후 반등 (Recovery)"
        cash_weight = 40
    else:
        market_status = "혼조세 (Mixed)"
        cash_weight = 50
        
    return market_status, cash_weight

market_status, cash_weight = analyze_macro_trend()

col1, col2 = st.columns(2)
with col1:
    st.info(f"### 🌐 글로벌 증시 상태: **{market_status}**")
    st.write("나스닥 지수의 이동평균선(20일, 60일) 기반 트렌드 분석입니다.")
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
