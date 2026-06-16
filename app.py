import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import plotly.graph_objects as go

st.set_page_config(page_title="AI vs Historical Bubble Comparison", layout="wide")
st.title("📊 역사적 버블 국면 정밀 비교 (실제 등락 반영)")
st.subheader("과거 실제 주가 데이터 기반 Base = 100, Log Scale 비교")

@st.cache_data(ttl=3600)
def get_all_bubble_data():
    tickers = {
        'AI_Cycle': {'ticker': '^NDX', 'start': '2023-01-03', 'end': datetime.date.today().strftime("%Y-%m-%d")},
        'Dotcom': {'ticker': '^NDX', 'start': '1995-01-03', 'end': '2002-01-03'},
        'FANG': {'ticker': '^NDX', 'start': '2016-07-01', 'end': '2023-07-01'}
    }
    processed_series = {}
    for key, info in tickers.items():
        df = yf.download(info['ticker'], start=info['start'], end=info['end'], progress=False)
        if not df.empty:
            df = df[['Close']].copy()
            base_value = df.iloc[0]['Close']
            df['Scaled'] = (df['Close'] / base_value) * 100
            df = df.reset_index()
            df['Years'] = df.index / 252
            processed_series[key] = df
    return processed_series

data_dict = get_all_bubble_data()
ai_data, dotcom_data, fang_data = data_dict['AI_Cycle'], data_dict['Dotcom'], data_dict['FANG']
current_years = ai_data['Years'].iloc[-1]
current_value = ai_data['Scaled'].iloc[-1]

# 메트릭 섹션
c1, c2, c3 = st.columns(3)
c1.metric("현재 AI 사이클 연차", f"T + {current_years:.2f}년")
c2.metric("시작점 대비 수익률", f"{current_value:.1f} pt", f"{current_value-100:.1f}%")
status = "초기 성장 구간" if current_years < 3 else "가속화 변곡점"
c3.info(f"현재 국면 진단: {status}")

# Plotly 차트 (글자 깨짐 없음)
fig = go.Figure()
fig.add_trace(go.Scatter(x=dotcom_data['Years'], y=dotcom_data['Scaled'], name="닷컴 버블 (1995-02)", line=dict(color='orange', width=1, dash='dot')))
fig.add_trace(go.Scatter(x=fang_data['Years'], y=fang_data['Scaled'], name="FANG 장세 (2016-23)", line=dict(color='red', width=1)))
fig.add_trace(go.Scatter(x=ai_data['Years'], y=ai_data['Scaled'], name="현재 AI 사이클", line=dict(color='#0f2042', width=4)))

fig.update_layout(
    title="역사적 버블 vs AI 사이클 (Log Scale)",
    xaxis_title="진행 시간 (연차)", yaxis_title="지수화 주가 (Base 100)",
    yaxis_type="log", height=600, template="plotly_white"
)
st.plotly_chart(fig, use_container_width=True)
