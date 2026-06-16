import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="거시경제 및 시장동향", page_icon="📈", layout="wide")

st.title("📈 거시경제 및 시장동향")
st.markdown("글로벌 시장 지수, 환율, 금리 흐름을 통해 전체적인 투자 환경을 점검합니다.")

@st.cache_data(ttl=3600)
def fetch_macro_data():
    tickers = {
        "S&P 500": "^GSPC",
        "Nasdaq": "^IXIC",
        "USD/KRW": "KRW=X",
        "US 10Y Yield": "^TNX",
        "Crude Oil (WTI)": "CL=F",
        "Gold": "GC=F",
        "Bitcoin": "BTC-USD"
    }
    
    data = {}
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    for name, ticker in tickers.items():
        try:
            df = yf.download(ticker, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                    
                df = df.dropna(subset=['Close'])
                if len(df) < 2: continue
                # Get the last two valid rows for price and change
                last_row = df.iloc[-1]
                prev_row = df.iloc[-2]
                
                current_price = float(last_row['Close'])
                prev_price = float(prev_row['Close'])
                
                change = current_price - prev_price
                pct_change = (change / prev_price) * 100
                
                data[name] = {
                    "price": current_price,
                    "change": change,
                    "pct_change": pct_change,
                    "history": df['Close'].tail(30)
                }
        except Exception as e:
            st.warning(f"데이터를 불러오는 중 오류가 발생했습니다: {name}")
            
    return data

with st.spinner("거시경제 데이터를 불러오는 중..."):
    macro_data = fetch_macro_data()

if macro_data:
    items = list(macro_data.items())
    for i in range(0, len(items), 4):
        cols = st.columns(4)
        for j, (name, info) in enumerate(items[i:i+4]):
            with cols[j]:
                with st.container(border=True):
                    st.metric(
                        label=name,
                        value=f"{info['price']:,.2f}",
                        delta=f"{info['change']:,.2f} ({info['pct_change']:,.2f}%)"
                    )
                    
                    # Sparkline chart
                    hist = info['history']
                    fig = go.Figure()
                    
                    if isinstance(hist, pd.DataFrame):
                        y_vals = hist.iloc[:, 0].values
                    else:
                        y_vals = hist.values
                        
                    color = "red" if y_vals[-1] > y_vals[0] else "blue"
                    fig.add_trace(go.Scatter(y=y_vals, mode='lines', line=dict(color=color, width=2)))
                    fig.update_layout(
                        margin=dict(l=0, r=0, t=0, b=0),
                        xaxis=dict(visible=False),
                        yaxis=dict(visible=False),
                        height=100,
                        showlegend=False,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

st.markdown("---")
st.subheader("💡 시장 분석 및 트레이딩 전략 가이드")
st.info("""
- **금리 (US 10Y Yield)** 가 오르면 기술주(Nasdaq)에 부담이 될 수 있으므로, 방어주나 가치주 비중 확대를 고려해야 합니다.
- **환율 (USD/KRW)** 상승(원화 약세) 시 외국인 자금 이탈 우려가 커지며, 수출주(자동차, 반도체 등)에는 단기적 호재로 작용할 수 있습니다.
- 시장이 전반적으로 상승장(Bull)일 때는 포트폴리오 비중을 확대하고, 하락장(Bear)일 때는 현금 비중을 높여 대응하세요.
""")
