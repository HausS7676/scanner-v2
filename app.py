import streamlit as st

st.set_page_config(page_title="트레이딩 전문가 시스템", page_icon="💹", layout="wide")

st.title("💹 트레이딩 전문가 종합 플랫폼")
st.markdown("""
환영합니다! 이 플랫폼은 단순한 종목 스캐너를 넘어, **거시경제 분석부터 포트폴리오 관리, 매매 전략 수립까지** 
프로 트레이더의 모든 작업 파이프라인을 지원하는 올인원(All-in-one) 시스템입니다.

좌측 사이드바 메뉴를 통해 다음 기능들을 활용해 보세요.
""")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.subheader("📊 1. 거시경제 및 시장동향")
        st.write("주요국 증시, 환율, 금리 흐름과 당일 시장의 주도 테마/섹터를 확인하여 시장의 방향성을 점검합니다.")
        
    with st.container(border=True):
        st.subheader("💼 3. 포트폴리오 관리")
        st.write("보유 중인 종목을 등록하여 실시간 손익을 추적하고, -9% 손절 라인 및 고점 대비 하락폭(트레일링 스탑) 경고 시스템으로 자산을 보호합니다.")
        
    with st.container(border=True):
        st.subheader("🧠 5. 투자 전략 수립")
        st.write("시장 상태(Bull/Bear)에 따른 비중 조절 조언과 보유 종목/관심 종목에 대한 AI 및 전문가 관점의 구체적인 매매 시나리오를 제공합니다.")

with col2:
    with st.container(border=True):
        st.subheader("🎯 2. 프리미엄 스캐너")
        st.write("수급 회전율, 거래대금, 기술적 지표(RSI/이평선)를 결합한 알고리즘으로 장세 맞춤형 및 추세추종형 유망 종목을 발굴합니다.")
        
    with st.container(border=True):
        st.subheader("🔍 4. 종목 상세분석")
        st.write("특정 종목의 기술적 지표, 기관/외국인 누적 수급 동향, 기업 가치평가(PER/PBR)를 다각도로 심층 분석합니다.")
        
st.markdown("---")
st.info("💡 **Tip**: 왼쪽 메뉴바 화살표(>)를 누르면 전체 메뉴를 보실 수 있습니다. 각 메뉴는 서로 연계되어 있습니다.")

# Initialize global session state if needed
if 'data_engine' not in st.session_state:
    st.session_state['data_engine'] = '자동'
