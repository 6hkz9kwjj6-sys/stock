import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 대시보드 기본 설정
st.set_page_config(page_title="AI vs Historical Bubble Dashboard v2", layout="wide")

st.title("📊 역사적 버블 국면 정밀 비교 및 매크로 진단 대시보드")
st.subheader("실제 주가 등락(Log Scale)과 펀더멘털 / 심리 / 매크로 유동성 지표 크로스 체크")

# 사이드바 컨트롤러
st.sidebar.header("⚙️ 대시보드 옵션 변경")
analysis_target = st.sidebar.radio("1. 분석 타겟 선택", ["시장 지수 기준", "주도 대장주 기준"])
alignment_style = st.sidebar.radio("2. 시계열 정렬 기준", ["사이클 시작점 기준 (T=0)", "역사적 최고점 기준 (Peak=0)"])

# 2. 데이터 수집 및 지표 계산 함수
@st.cache_data(ttl=3600)
def get_extended_bubble_data(target="시장 지수 기준", align_mode="사이클 시작점 기준 (T=0)"):
    if target == "시장 지수 기준":
        tickers = {
            'AI_Cycle': {'ticker': '^NDX', 'start': '2023-01-03', 'end': datetime.date.today().strftime("%Y-%m-%d")},
            'Dotcom': {'ticker': '^NDX', 'start': '1995-01-03', 'end': '2002-01-03'},
            'FANG': {'ticker': '^NDX', 'start': '2016-07-01', 'end': '2023-07-01'}
        }
    else:
        tickers = {
            'AI_Cycle': {'ticker': 'NVDA', 'start': '2023-01-03', 'end': datetime.date.today().strftime("%Y-%m-%d")},
            'Dotcom': {'ticker': 'CSCO', 'start': '1995-01-03', 'end': '2002-01-03'},
            'FANG': {'ticker': 'AAPL', 'start': '2016-07-01', 'end': '2023-07-01'}
        }
        
    macro_ticker = '^TNX'  # 미국 10년물 국채 금리
    processed_series = {}
    
    for key, info in tickers.items():
        try:
            # 주가 데이터 로드
            df = yf.download(info['ticker'], start=info['start'], end=info['end'], progress=False)
            # 매크로 금리 데이터 로드
            df_macro = yf.download(macro_ticker, start=info['start'], end=info['end'], progress=False)
            
            # [수정] MultiIndex 컬럼 구조 안전하게 해제 (단일 차원 변환)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if isinstance(df_macro.columns, pd.MultiIndex):
                df_macro.columns = df_macro.columns.get_level_values(0)
            
            if not df.empty:
                # 데이터 정제 및 동기화 부모 프레임 생성
                df = df[['Close']].rename(columns={'Close': 'Price'}).dropna()
                df_macro = df_macro[['Close']].rename(columns={'Close': 'Macro_Yield'})
                
                # [수정] 주가 날짜 기준으로 금리 데이터를 안전하게 병합 (날짜 어긋남 방지)
                df = df.join(df_macro, how='left')
                df['Macro_Yield'] = df['Macro_Yield'].bfill().ffill()
                
                # 100포인트 스케일링 계산 기본값 설정
                base_value = float(df['Price'].iloc[0])
                df['Scaled'] = (df['Price'] / base_value) * 100
                
                # --- RSI (14일) 계산 ---
                delta = df['Price'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                loss = loss.replace(0, 0.00001)
                rs = gain / loss
                df['RSI'] = 100 - (100 / (1 + rs))
                # ----------------------
                
                df = df.reset_index()
                
                # 시계열 정렬 기준 계산
                if align_mode == "역사적 최고점 기준 (Peak=0)":
                    peak_idx = df['Scaled'].idxmax()
                    df['Years'] = (df.index - peak_idx) / 252
                else:
                    df['Years'] = df.index / 252
                    
                processed_series[key] = df
        except Exception as e:
            st.sidebar.error(f"⚠️ {key} ({info['ticker']}) 로드 실패: {str(e)}")
            
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

# 데이터 로드 실행
data_dict = get_extended_bubble_data(target=analysis_target, align_mode=alignment_style)

# 데이터 검증 및 방어선
required_keys = ['AI_Cycle', 'Dotcom', 'FANG']
missing_keys = [k for k in required_keys if k not in data_dict]

if missing_keys:
    st.error(f"🚨 **데이터 동기화 실패:** {missing_keys} 데이터를 가져오지 못했습니다.")
    st.stop()

ai_data = data_dict['AI_Cycle']
dotcom_data = data_dict['Dotcom']
fang_data = data_dict['FANG']

current_years = ai_data['Years'].iloc[-1]
current_value = ai_data['Scaled'].iloc[-1]
current_pct = current_value - 100

dotcom_max_value = dotcom_data['Scaled'].max()
dotcom_max_pct = dotcom_max_value - 100

current_rsi = ai_data['RSI'].dropna().iloc[-1] if not ai_data['RSI'].dropna().empty else 50
ai_fwd_per = get_fundamental_metrics()

# 3. 상단 메트릭 배치
m1, m2, m3, m4 = st.columns(4)
time_prefix = "Peak " if alignment_style == "역사적 최고점 기준 (Peak=0)" else "T + "
m1.metric("현재 AI 사이클 위치", f"{time_prefix}{current_years:.2f}년")
m2.metric("시작점 대비 수익률 (현재 / 과거 최고)", f"{current_value:.1f} / {dotcom_max_value:.1f} pt", f"{current_pct:.1f}% / {dotcom_max_pct:.1f}%")

per_delta = "닷컴 최고점 시스코(131배) 대비 안전" if ai_fwd_per < 50 else "밸류에이션 과열 주의"
m3.metric("AI 대장주 Avg Forward PER", f"{ai_fwd_per:.1f}배", per_delta)

rsi_status = "과열(매도 주의)" if current_rsi > 70 else ("침체(매수 기회)" if current_rsi < 30 else "보통")
m4.metric("현재 AI 사이클 RSI (심리)", f"{current_rsi:.1f}", rsi_status)

st.write("---")
if ai_fwd_per > 40 and current_rsi > 70:
    st.error(f"🚨 **종합 진단:** 현재 시장은 **실적 대비 고평가(PER {ai_fwd_per:.1f}배)** 상태이며, **투자 심리(RSI {current_rsi:.1f}) 또한 극도의 과열 구간**에 진입했습니다.")
else:
    st.success(f"✅ **종합 진단:** **실적 성장세(PER {ai_fwd_per:.1f}배)**가 주가를 지지하고 있으며 심리적 광기(RSI)도 통제 범위 내에 있습니다.")

# 4. 3층 구조 서브플롯 차트 생성
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.06, row_heights=[0.5, 0.25, 0.25])

# [1층] 메인 주가 스케일링 차트
fig.add_trace(go.Scatter(x=dotcom_data['Years'], y=dotcom_data['Scaled'], name="과거 닷컴 버블 (1995~2002)", line=dict(color='#fbbf24', width=1.5, dash='dot'), opacity=0.5), row=1, col=1)
fig.add_trace(go.Scatter(x=fang_data['Years'], y=fang_data['Scaled'], name="과거 FANG 장세 (2016~2023)", line=dict(color='#ef4444', width=1.5), opacity=0.5), row=1, col=1)
fig.add_trace(go.Scatter(x=ai_data['Years'], y=ai_data['Scaled'], name="현재 AI 사이클 (2023~현재)", line=dict(color='#00ff66', width=4)), row=1, col=1)

fig.add_vline(x=current_years, line_width=1.5, line_dash="dash", line_color="#7f8c8d")

# [2층] 보조 지표 RSI 차트
fig.add_trace(go.Scatter(x=dotcom_data['Years'], y=dotcom_data['RSI'], name="닷컴 RSI", line=dict(color='#fbbf24', width=1, dash='dot'), opacity=0.4), row=2, col=1)
fig.add_trace(go.Scatter(x=fang_data['Years'], y=fang_data['RSI'], name="FANG RSI", line=dict(color='#ef4444', width=1), opacity=0.4), row=2, col=1)
fig.add_trace(go.Scatter(x=ai_data['Years'], y=ai_data['RSI'], name="현재 AI RSI", line=dict(color='#00ff66', width=2)), row=2, col=1)

fig.add_hline(y=70, line_width=1, line_dash="dash", line_color="rgba(239, 68, 68, 0.5)", row=2, col=1)
fig.add_hline(y=30, line_width=1, line_dash="dash", line_color="rgba(16, 185, 129, 0.5)", row=2, col=1)

# [3층] 매크로 금리 차트
fig.add_trace(go.Scatter(x=dotcom_data['Years'], y=dotcom_data['Macro_Yield'], name="닷컴 당시 금리", line=dict(color='#fbbf24', width=1, dash='dot'), opacity=0.6), row=3, col=1)
fig.add_trace(go.Scatter(x=fang_data['Years'], y=fang_data['Macro_Yield'], name="FANG 당시 금리", line=dict(color='#ef4444', width=1), opacity=0.6), row=3, col=1)
fig.add_trace(go.Scatter(x=ai_data['Years'], y=ai_data['Macro_Yield'], name="현재 국채 금리", line=dict(color='#00ff66', width=2.5)), row=3, col=1)

# 레이아웃 설정
fig.update_layout(
    title=dict(text=f"역사적 국면 정밀 크로스 분석 ({analysis_target} / {alignment_style})", font=dict(size=16)),
    height=850,
    template="plotly_white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

fig.update_yaxes(title_text="지수화 가격 (Log Scale)", type="log", tickvals=[100, 200, 400, 800, 1600, 3200], tickformat="d", gridcolor='rgba(128,128,128,0.2)', row=1, col=1)
fig.update_yaxes(title_text="RSI (심리 강도)", range=[10, 90], gridcolor='rgba(128,128,128,0.2)', row=2, col=1)
fig.update_yaxes(title_text="미 10년물 금리 (%)", gridcolor='rgba(128,128,128,0.2)', row=3, col=1)

x_title = "기준점 대비 경과 (연차: T + n 년)" if alignment_style == "사이클 시작점 기준 (T=0)" else "최고점 대비 상대 위치 (Peak = 0 년)"
fig.update_xaxes(title_text=x_title, gridcolor='rgba(128,128,128,0.2)', row=3, col=1)

st.plotly_chart(fig, use_container_width=True)
