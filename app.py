import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 대시보드 기본 설정
st.set_page_config(page_title="AI vs Historical Bubble Dashboard v2", layout="wide")
st.title("📊 역사적 버블 국면 정밀 비교 및 매크로 진단 대시보드")
st.subheader("주가 등락(Log Scale), 펀더멘털(PER), 심리(RSI), 매크로 유동성(금리) 크로스 체크")

# 사이드바 컨트롤러 (추근 개선 기능 반영)
st.sidebar.header("⚙️ 대시보드 옵션 변경")
analysis_target = st.sidebar.radio("1. 분석 타겟 선택", ["시장 지수 기준", "주도 대장주 기준"])
alignment_style = st.sidebar.radio("2. 시계열 정렬 기준", ["사이클 시작점 기준 (T=0)", "역사적 최고점 기준 (Peak=0)"])

# 2. 데이터 수집 및 지표 계산 함수
@st.cache_data(ttl=3600)
def get_extended_bubble_data(target="시장 지수 기준"):
    # 분석 타겟에 따른 티커 맵핑 (개선안 3: SOX 지수 포함 가능하도록 설계 기반 마련 및 타겟 분리)
    if target == "시장 지수 기준":
        tickers = {
            'AI_Cycle': {'ticker': '^NDX', 'start': '2023-01-03', 'end': datetime.date.today().strftime("%Y-%m-%d")},
            'Dotcom': {'ticker': '^NDX', 'start': '1995-01-03', 'end': '2002-01-03'},
            'FANG': {'ticker': '^NDX', 'start': '2016-07-01', 'end': '2023-07-01'}
        }
    else:  # 주도 대장주 기준 (개선안 2: Cisco vs Nvidia)
        tickers = {
            'AI_Cycle': {'ticker': 'NVDA', 'start': '2023-01-03', 'end': datetime.date.today().strftime("%Y-%m-%d")},
            'Dotcom': {'ticker': 'CSCO', 'start': '1995-01-03', 'end': '2002-01-03'},
            'FANG': {'ticker': 'AAPL', 'start': '2016-07-01', 'end': '2023-07-01'}
        }
        
    # 개선안 4: 매크로 유동성 지표 (미국 10년물 국채 금리 ^TNX) 추가 다운로드
    macro_ticker = '^TNX'
    
    processed_series = {}
    
    for key, info in tickers.items():
        # 주가 데이터 다운로드
        df = yf.download(info['ticker'], start=info['start'], end=info['end'], progress=False)
        # 금리 데이터 함께 다운로드
        df_macro = yf.download(macro_ticker, start=info['start'], end=info['end'], progress=False)
        
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if isinstance(df_macro.columns, pd.MultiIndex):
                df_macro.columns = df_macro.columns.get_level_values(0)
            
            df = df.dropna(subset=['Close']).copy()
            df_macro = df_macro.dropna(subset=['Close']).copy()
            
            # 금리 데이터 병합
            df['Macro_Yield'] = df_macro['Close']
            df['Macro_Yield'] = df['Macro_Yield'].bfill().ffill() # 결측치 처리
            
            close_series = pd.Series(df['Close'].values.flatten(), index=df.index)
            base_value = float(close_series.iloc[0])
            df['Scaled'] = (close_series / base_value) * 100
            
            # --- [RSI (14일) 안전한 계산] ---
            delta = close_series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            loss = loss.replace(0, 0.00001)
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            # ----------------------------------
            
            df = df.reset_index()
            
            # 개선안 1: 최고점 기준 정렬 (Peak Alignment) 알고리즘 적용
            if alignment_style == "역사적 최고점 기준 (Peak=0)":
                peak_idx = df['Scaled'].idxmax()
                df['Years'] = (df.index - peak_idx) / 252
            else:
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

# 데이터 로드 (선택된 타겟 반영)
data_dict = get_extended_bubble_data(target=analysis_target)
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
time_prefix = "Peak " if alignment_style == "역사적 최고점 기준 (Peak=0)" else "T + "
m1.metric(f"현재 AI 사이클 위치", f"{time_prefix}{current_years:.2f}년")
m2.metric("시작점 대비 수익률 (현재 / 과거 최고)", f"{current_value:.1f} / {dotcom_max_value:.1f} pt", f"{current_pct:.1f}% / {dotcom_max_pct:.1f}%")

per_delta = "닷컴 최고점 시스코(131배) 대비 낮음" if ai_fwd_per < 50 else "밸류에이션 점검 필요"
m3.metric("AI 대장주 Avg Forward PER", f"{ai_fwd_per:.1f}배", per_delta)

rsi_status = "과열(매도 주의)" if current_rsi > 70 else ("침체(매수 기회)" if current_rsi < 30 else "보통")
m4.metric("현재 AI 사이클 RSI (심리)", f"{current_rsi:.1f}", rsi_status)

st.write("---")
if ai_fwd_per > 40 and current_rsi > 70:
    st.error(f"🚨 **종합 진단:** 현재 시장은 **실적 대비 고평가(PER {ai_fwd_per:.1f}배)** 상태이며, **투자 심리(RSI {current_rsi:.1f}) 또한 극도의 과열 구간**에 진입했습니다. 역사적 상한선 근처에서 분할 현금화가 유리할 수 있습니다.")
else:
    st.success(f"✅ **종합 진단:** **실적 성장세(PER {ai_fwd_per:.1f}배)**가 주가를 일정 부분 방어하고 있으며 심리적 광기(RSI)도 통제 범위 내에 있습니다. 닷컴 버블 수준의 묻지마 폭락 가능성은 낮으나 연차가 쌓임에 따라 변동성 확대를 준비하세요.")

# 4. 서브플롯 차트 생성 (개선안 4: 매크로 유동성을 위해 row를 3층으로 확장)
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.05, row_heights=[0.5, 0.25, 0.25])

# [1층] 메인 주가 스케일링 차트
fig.add_trace(go.Scatter(x=dotcom_data['Years'], y=dotcom_data['Scaled'], name="과거 닷컴 버블 (1995~2002)", line=dict(color='#fbbf24', width=1.5, dash='dot'), opacity=0.5), row=1, col=1)
fig.add_trace(go.Scatter(x=fang_data['Years'], y=fang_data['Scaled'], name="과거 FANG 장세 (2016~2023)", line=dict(color='#ef4444', width=1.5), opacity=0.5), row=1, col=1)
fig.add_trace(go.Scatter(x=ai_data['Years'], y=ai_data['Scaled'], name="현재 AI 사이클 (2023~현재)", line=dict(color='#00ff66', width=4)), row=1, col=1)

# 현재 시점 가이드라인
fig.add_vline(x=current_years, line_width=1.5, line_dash="dash", line_color="#7f8c8d")

# [2층] 보조 지표 RSI 차트
fig.add_trace(go.Scatter(x=dotcom_data['Years'], y=dotcom_data['RSI'], name="닷컴 RSI", line=dict(color='#fbbf24', width=1, dash='dot'), opacity=0.4), row=2, col=1)
fig.add_trace(go.Scatter(x=fang_data['Years'], y=fang_data['RSI'], name="FANG RSI", line=dict(color='#ef4444', width=1), opacity=0.4), row=2, col=1)
fig.add_trace(go.Scatter(x=ai_data['Years'], y=ai_data['RSI'], name="현재 AI RSI", line=dict(color='#00ff66', width=2)), row=2, col=1)

fig.add_hline(y=70, line_width=1, line_dash="dash", line_color="rgba(239, 68, 68, 0.5)", row=2, col=1)
fig.add_hline(y=30, line_width=1, line_dash="dash", line_color="rgba(16, 185, 129, 0.5)", row=2, col=1)

# [3층] 매크로 유동성 차트 (개선안 4: 미국 10년물 국채 금리 환경 비교)
fig.add_trace(go.Scatter(x=dotcom_data['Years'], y=dotcom_data['Macro_Yield'], name="닷컴 당시 금리", line=dict(color='#fbbf24', width=1, dash='dot'), opacity=0.6), row=3, col=1)
fig.add_trace(go.Scatter(x=fang_data['Years'], y=fang_data['Macro_Yield'], name="FANG 당시 금리", line=dict(color='#ef4444', width=1), opacity=0.6), row=3, col=1)
fig.add_trace(go.Scatter(x=ai_data['Years'], y=ai_data['Macro_Yield'], name="현재 국채 금리", line=dict(color='#00ff66', width=2.5)), row=3, col=1)

# 레이아웃 마스터 설정
fig.update_layout(
    title=dict(text=f"역사적 국면 정밀 크로스 분석 ({analysis_target} / {alignment_style})", font=dict(size=16)),
    height=850,
    template="plotly_white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

# 축별 디테일 설정
fig.update_yaxes(title_text="지수화 가격 (Log)", type="log", tickvals=[100, 200, 400, 800, 1600, 3200], tickformat="d", gridcolor='rgba(128,128,128,0.2)', row=1, col=1)
fig.update_yaxes(title_text="RSI (심리)", range=[10, 90], gridcolor='rgba(128,128,128,0.2)', row=2, col=1)
fig.update_yaxes(title_text="미 10년물 금리 (%)", gridcolor='rgba(128,128,128,0.2)', row=3, col=1)

x_title = "기준점 대비 경과 (연차: T + n 년)" if alignment_style == "사이클 시작점 기준 (T=0)" else "최고점 대비 상대 위치 (Peak = 0 년)"
fig.update_xaxes(title_text=x_title, gridcolor='rgba(128,128,128,0.2)', row=3, col=1)

st.plotly_chart(fig, use_container_width=True)
