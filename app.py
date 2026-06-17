import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import plotly.graph_objects as go

# 1. 대시보드 기본 설정
st.set_page_config(page_title="AI vs Historical Bubble Comparison", layout="wide")
st.title("📊 역사적 버블 국면 정밀 비교 (실제 등락 반영)")
st.subheader("과거 실제 주가 데이터 기반 Base = 100, Log Scale 비교")

# 2. 데이터 수집 및 스케일링 함수
@st.cache_data(ttl=3600)
def get_all_bubble_data():
    tickers = {
        'AI_Cycle': {'ticker': '^NDX', 'start': '2023-01-03', 'end': datetime.date.today().strftime("%Y-%m-%d")},
        'Dotcom': {'ticker': '^NDX', 'start': '1995-01-03', 'end': '2002-01-03'},
        'FANG': {'ticker': '^NDX', 'start': '2016-07-01', 'end': '2023-07-01'}
    }
    processed_series = {}
    
    for key, info in tickers.items():
        # 데이터프레임 구조 유지를 위해 group_by=False 추가 권장 (MultiIndex 방지)
        df = yf.download(info['ticker'], start=info['start'], end=info['end'], progress=False)
        
        if not df.empty:
            # 최신 yfinance의 MultiIndex 컬럼 구조 평탄화
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            df = df.dropna(subset=['Close'])
            df = df[['Close']].copy()
            base_value = float(df.iloc[0]['Close'])
            df['Scaled'] = (df['Close'] / base_value) * 100
            
            df = df.reset_index()
            df['Years'] = df.index / 252  # 252 영업일 기준 연차 환산
            processed_series[key] = df
            
    return processed_series

# 데이터 로드
data_dict = get_all_bubble_data()
ai_data = data_dict['AI_Cycle']
dotcom_data = data_dict['Dotcom']
fang_data = data_dict['FANG']

# --- [★ 수정 및 추가된 로직 시작] ---
# 1. 현재 AI 사이클 실시간 수치
current_years = ai_data['Years'].iloc[-1]
current_value = ai_data['Scaled'].iloc[-1]
current_pct = current_value - 100  # 현재 AI 상승률 (%)

# 2. 닷컴 버블의 최고점(상한선) 계산
dotcom_max_value = dotcom_data['Scaled'].max()
dotcom_max_pct = dotcom_max_value - 100  # 닷컴 최고점 상승률 (%)
# --- [★ 수정 및 추가된 로직 끝] ---

# 3. 상단 메트릭 화면 레이아웃
c1, c2, c3 = st.columns(3)
c1.metric("현재 AI 사이클 연차", f"T + {current_years:.2f}년")

# --- [★ 메트릭 표시 방식 수정] ---
# 목표하신 "현재pt / 닷컴최고pt", "현재% / 닷컴최고%" 형태로 포맷팅
metric_value = f"{current_value:.1f} / {dotcom_max_value:.1f} pt"
metric_delta = f"{current_pct:.1f}% / {dotcom_max_pct:.1f}% (닷컴 상한선 대비)"

c2.metric(
    label="시작점 대비 수익률 (현재 / 닷컴 최고점)", 
    value=metric_value, 
    delta=metric_delta,
    delta_color="normal" # 상승/하락 색상 유지를 원치 않으시면 "off"로 변경 가능
)
# ----------------------------------

if current_years < 3.0:
    status = "초기 3년 완만한 상승 구간"
    color = "#10b981"
elif current_years < 5.0:
    status = "4~5년 차 본격 가속화 변곡점 진입 국면"
    color = "#f59e0b"
else:
    status = "과거 버블 붕괴 임계점 도달 및 과열 주의"
    color = "#ef4444"
c3.markdown(f"**현재 국면 진단:** <span style='color:{color}; font-size:20px; font-weight:bold;'>{status}</span>", unsafe_allow_html=True)

# 4. Plotly 인터랙티브 차트 생성
st.write("---")
fig = go.Figure()

# 닷컴 버블 등락 (노란색 점선)
fig.add_trace(go.Scatter(
    x=dotcom_data['Years'], 
    y=dotcom_data['Scaled'], 
    name="과거 닷컴 버블 실제 등락 (1995~2002)", 
    line=dict(color='#fbbf24', width=1.5, dash='dot'),
    opacity=0.6
))

# FANG 장세 등락 (빨간색 실선)
fig.add_trace(go.Scatter(
    x=fang_data['Years'], 
    y=fang_data['Scaled'], 
    name="과거 FANG 장세 실제 등락 (2016~2023)", 
    line=dict(color='#ef4444', width=1.5),
    opacity=0.6
))

# 현재 AI 사이클 실시간 주가 (밝고 선명한 네온 초록색 두꺼운 선)
fig.add_trace(go.Scatter(
    x=ai_data['Years'], 
    y=ai_data['Scaled'], 
    name="현재 AI 사이클 실시간 (2023~현재)", 
    line=dict(color='#00ff66', width=4)
))

# 오늘 시점 수직 가이드라인 추가
fig.add_shape(
    type="line", x0=current_years, y0=100, x1=current_years, y1=1000,
    line=dict(color="#ffffff", width=1.5, dash="dash")
)

# 레이아웃 스타일링 (로그 스케일 및 다크/화이트 밸런스 조정)
fig.update_layout(
    title=dict(text="역사적 버블 실제 등락 데이터 vs 현재 AI 사이클 실시간 위치 비교", font=dict(size=16)),
    xaxis=dict(title="진행 시간 (연차: T + n Year)", range=[0, 7], gridcolor='rgba(128,128,128,0.2)'),
    yaxis=dict(
        title="지수화된 주가 추이 (Log Scale, 시작점 = 100)", 
        type="log", 
        tickvals=[100, 200, 400, 800],
        tickformat="d",
        gridcolor='rgba(128,128,128,0.2)'
    ),
    height=600,
    template="plotly_white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)
