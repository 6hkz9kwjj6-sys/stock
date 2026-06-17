import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 대시보드 기본 설정
st.set_page_config(page_title="AI vs Historical Bubble Dashboard", layout="wide")
st.title("📊 역사적 버블 국면 정밀 비교 및 매크로 진단")
st.subheader("실제 주가 등락(Log Scale)과 펀더멘털/심리 지표 크로스 체크")

# 2. 데이터 수집 및 지표 계산 함수
@st.cache_data(ttl=3600)
def get_extended_bubble_data():
    tickers = {
        'AI_Cycle': {'ticker': '^NDX', 'start': '2023-01-03', 'end': datetime.date.today().strftime("%Y-%m-%d")},
        'Dotcom': {'ticker': '^NDX', 'start': '1995-01-03', 'end': '2002-01-03'},
        'FANG': {'ticker': '^NDX', 'start': '2016-07-01', 'end': '2023-07-01'}
    }
    processed_series = {}
    
    for key, info in tickers.items():
        df = yf.download(info['ticker'], start=info['start'], end=info['end'], progress=False)
        
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            df = df.dropna(subset=['Close'])
            df = df[['Close']].copy()
            
            # 명확하게 1차원 Series/Float로 변환하여 할당 에러 방지
            close_series = pd.Series(df['Close'].values.flatten(), index=df.index)
            base_value = float(close_series.iloc[0])
            df['Scaled'] = (close_series / base_value) * 100
            
            # --- [RSI (14일) 안전한 계산] ---
            delta = close_series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            loss = loss.replace(0, 0.00001)  # 0 분모 방지
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            # ----------------------------------

            df = df.reset_index()
            df['Years'] = df.index / 252
            processed_series[key] = df
            
    return processed_series

@st.cache_data(ttl=86400)
def get_fundamental_metrics():
    try:
        nvda = yf.Ticker("NVDA")
        msft = yf.Ticker("MSFT")
        avg_fwd_per = (nvda.info.get('forwardPE', 35) + msft.info.get('forwardPE', 32)) / 2
    except:
        avg_fwd_per = 33.5
    return avg_fwd_per

# 데이터 로드
data_dict = get_extended_bubble_data()
ai_data = data_dict['AI_Cycle']
dotcom_data = data_dict['Dotcom']
fang_data = data_dict['FANG']

current_years = ai_data['Years'].iloc[-1]
current_value = ai_data['Scaled'].iloc[-1]
current_pct = current_value - 100

dotcom_max_value = dotcom_data['Scaled'].max()
dotcom_max_pct = dotcom_max_value - 100

current_rsi = ai_data['RSI'].dropna().iloc[-1]
ai_fwd_per = get_fundamental_metrics()

# 3. 상단 대시보드 메트릭 배치
m1, m2, m3, m4 = st.columns(4)
m1.metric("현재 AI 사이클 연차", f"T + {current_years:.2f}년")
m2.metric("시작점 대비 수익률 (현재 / 닷컴 최고)", f"{current_value:.1f} / {dotcom_max_value:.1f} pt", f"{current_pct:.1f}% / {dotcom_max_pct:.1f}%")

per_delta = f"닷컴 버블(100+) 대비 안전" if ai_fwd_per < 50 else f"밸류에이션 과열 위험"
m3.metric("AI 대장주 Avg Forward PER", f"{ai_fwd_per:.1f}배", per_delta)

rsi_status = "과열(매도 주의)" if current_rsi > 70 else ("침체(매수 기회)" if current_rsi < 30 else "보통")
m4.metric("현재 AI 사이클 RSI (심리)", f"{current_rsi:.1f}", rsi_status)

st.write("---")
if ai_fwd_per > 40 and current_rsi > 70:
    st.error(f"🚨 **종합 진단:** 현재 시장은 **실적 대비 고평가(PER {ai_fwd_per:.1f}배)** 상태이며, **투자 심리(RSI {current_rsi:.1f}) 또한 극도의 과열 구간**에 진입했습니다. 역사적 상한선 근처에서 분할 현금화가 유리할 수 있습니다.")
else:
    st.success(f"✅ **종합 진단:** **실적 성장세(PER {ai_fwd_per:.1f}배)**가 주가를 일정 부분 방어하고 있으며 심리적 광기(RSI)도 통제 범위 내에 있습니다. 닷컴 버블 수준의 묻지마 폭락 가능성은 낮으나 연차가 쌓임에 따라 변동성 확대를 준비하세요.")

# 4. 서브플롯 차트 생성
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.08, row_heights=[0.7, 0.3])

# [★수정 완료] row, col 파라미터를 go.Scatter 안쪽이 아닌 add_trace의 아규먼트로 올바르게 격리
# [1층] 메인 주가 스케일링 차트
fig.add_trace(go.Scatter(x=dotcom_data['Years'], y=dotcom_data['Scaled'], name="과거 닷컴 버블 (1995~2002)", line=dict(color='#fbbf24', width=1.5, dash='dot'), opacity=0.5), row=1, col=1)
fig.add_trace(go.Scatter(x=fang_data['Years'], y=fang_data['Scaled'], name="과거 FANG 장세 (2016~2023)", line=dict(color='#ef4444', width=1.5), opacity=0.5), row=1, col=1)
fig.add_trace(go.Scatter(x=ai_data['Years'], y=ai_data['Scaled'], name="현재 AI 사이클 (2023~현재)", line=dict(color='#00ff66', width=4)), row=1, col=1)

# 가이드라인 설정
fig.add_vline(x=current_years, line_width=1.5, line_dash="dash", line_color="#7f8c8d")

# [2층] 보조 지표 RSI 차트
fig.add_trace(go.Scatter(x=dotcom_data['Years'], y=dotcom_data['RSI'], name="닷컴 RSI", line=dict(color='#fbbf24', width=1, dash='dot'), opacity=0.4), row=2, col=1)
fig.add_trace(go.Scatter(x=fang_data['Years'], y=fang_data['RSI'], name="FANG RSI", line=dict(color='#ef4444', width=1), opacity=0.4), row=2, col=1)
fig.add_trace(go.Scatter(x=ai_data['Years'], y=ai_data['RSI'], name="현재 AI RSI", line=dict(color='#00ff66', width=2)), row=2, col=1)

# RSI 기준 가이드라인 라인 (70, 30)
fig.add_hline(y=70, line_width=1, line_dash="dash", line_color="rgba(239, 68, 68, 0.5)", row=2, col=1)
fig.add_hline(y=30, line_width=1, line_dash="dash", line_color="rgba(16, 185, 129, 0.5)", row=2, col=1)

# 레이아웃 마스터 설정
fig.update_layout(
    title=dict(text="역사적 버블 실제 등락 vs 현재 AI 위치 및 RSI 심리 지표 크로스 비교", font=dict(size=16)),
    height=750,
    template="plotly_white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

# 축별 디테일 설정 분리
fig.update_yaxes(title_text="지수화 주가 (Log Scale)", type="log", tickvals=[100, 200, 400, 800], tickformat="d", gridcolor='rgba(128,128,128,0.2)', row=1, col=1)
fig.update_yaxes(title_text="RSI (심리 강도)", range=[10, 90], gridcolor='rgba(128,128,128,0.2)', row=2, col=1)
fig.update_xaxes(title_text="진행 시간 (연차: T + n Year)", range=[0, 7], gridcolor='rgba(128,128,128,0.2)', row=2, col=1)

st.plotly_chart(fig, use_container_width=True)
