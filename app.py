import streamlit as st

import yfinance as yf

import pandas as pd

import datetime

import matplotlib.pyplot as plt



# 1. 대시보드 기본 설정

st.set_page_config(page_title="AI 사이클 vs 역사적 버블 정밀 비교", layout="wide")

st.title("📊 역사적 버블 국면 정밀 비교 대시보드 (실제 등락 반영)")

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

        df = yf.download(info['ticker'], start=info['start'], end=info['end'], progress=False)

        if not df.empty:

            df = df[['Close']].copy()

            base_value = df.iloc[0]['Close']

            df['Scaled'] = (df['Close'] / base_value) * 100

            df = df.reset_index()

            df['Years'] = df.index / 252  # 252 영업일 기준 연차 환산

            processed_series[key] = df

            

    return processed_series



# 데이터 로드 (에러 유발 구문 제거)

data_dict = get_all_bubble_data()



ai_data = data_dict['AI_Cycle']

dotcom_data = data_dict['Dotcom']

fang_data = data_dict['FANG']



current_years = ai_data['Years'].iloc[-1]

current_value = ai_data['Scaled'].iloc[-1]



# 3. 상단 메트릭 화면 레이아웃

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(label="현재 AI 사이클 진행 연차", value=f"T + {current_years:.2f} 년")

with col2:

    st.metric(label="시작점 대비 현재 수익률 (Base=100)", value=f"{current_value:.1f} pt", delta=f"{current_value-100:.1f}% 상승 중")

with col3:

    if current_years < 3.0:

        status = "초기 3년 완만한 상승 구간 (역사적 유사성 높은 구간)"

        color = "#10b981"

    elif current_years < 5.0:

        status = "4~5년 차 본격 가속화 변곡점 진입 국면"

        color = "#f59e0b"

    else:

        status = "과거 버블 붕괴 임계점 도달 및 과열 주의"

        color = "#ef4444"

    st.markdown(f"**현재 국면 진단:** <span style='color:{color}; font-size:20px; font-weight:bold;'>{status}</span>", unsafe_allow_html=True)



# 4. 차트 생성

st.write("---")

fig, ax = plt.subplots(figsize=(14, 7))



# 닷컴 버블 등락 (노란색)

ax.plot(dotcom_data['Years'], dotcom_data['Scaled'], label="과거 닷컴 버블 실제 등락 (1995~2002)", color='#fbbf24', alpha=0.6, linewidth=1.5)



# FANG 장세 등락 (빨간색)

ax.plot(fang_data['Years'], fang_data['Scaled'], label="과거 FANG 장세 실제 등락 (2016~2023)", color='#ef4444', alpha=0.6, linewidth=1.5)



# 현재 AI 사이클 실시간 주가 (진한 네이비색 두꺼운 선)

ax.plot(ai_data['Years'], ai_data['Scaled'], label="현재 AI 사이클 실시간 (2023~현재)", color='#0f2042', linewidth=3.5)



# 현재 시점 수직 가이드라인

ax.axvline(x=current_years, color='#0f2042', linestyle=':', alpha=0.8, linewidth=2)

ax.text(current_years + 0.05, 110, f"오늘 시점 (T+{current_years:.2f}Y)", color='#0f2042', fontweight='bold', rotation=90)



# 로그 스케일 차트 스타일링

ax.set_yscale('log')

ax.set_yticks([100, 200, 400, 800])

ax.get_yaxis().set_major_formatter(plt.ScalarFormatter())



ax.set_xlim(0, 7)

ax.set_xlabel("진행 시간 (연차: T + n Year)", fontsize=12)

ax.set_ylabel("지수화된 주가 추이 (Log Scale, 시작점 = 100)", fontsize=12)

ax.set_title("역사적 버블 실제 등락 데이터 vs 현재 AI 사이클 실시간 위치 비교", fontsize=15, pad=15)

ax.grid(True, which="both", ls="--", alpha=0.4)

ax.legend(loc="upper left", fontsize=11)



st.pyplot(fig)