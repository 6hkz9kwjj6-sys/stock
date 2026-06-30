# [수정된 데이터 수집 함수]
@st.cache_data(ttl=3600)
def get_extended_bubble_data(target="시장 지수 기준"):
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
        
    macro_ticker = '^TNX'
    processed_series = {}
    
    for key, info in tickers.items():
        try:
            # 주가 및 금리 데이터 다운로드
            df = yf.download(info['ticker'], start=info['start'], end=info['end'], progress=False)
            df_macro = yf.download(macro_ticker, start=info['start'], end=info['end'], progress=False)
            
            # yfinance 다운로드 실패 혹은 빈 데이터프레임 방어
            if df.empty or len(df) < 5:
                # 당일 데이터가 없는 경우를 위해 end 날짜를 하루 늘려서 재시도
                extended_end = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                df = yf.download(info['ticker'], start=info['start'], end=extended_end, progress=False)
                df_macro = yf.download(macro_ticker, start=info['start'], end=extended_end, progress=False)
            
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                if isinstance(df_macro.columns, pd.MultiIndex):
                    df_macro.columns = df_macro.columns.get_level_values(0)
                
                df = df.dropna(subset=['Close']).copy()
                df_macro = df_macro.dropna(subset=['Close']).copy()
                
                df['Macro_Yield'] = df_macro['Close']
                df['Macro_Yield'] = df['Macro_Yield'].bfill().ffill()
                
                close_series = pd.Series(df['Close'].values.flatten(), index=df.index)
                base_value = float(close_series.iloc[0])
                df['Scaled'] = (close_series / base_value) * 100
                
                delta = close_series.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                loss = loss.replace(0, 0.00001)
                rs = gain / loss
                df['RSI'] = 100 - (100 / (1 + rs))
                
                df = df.reset_index()
                
                if alignment_style == "역사적 최고점 기준 (Peak=0)":
                    peak_idx = df['Scaled'].idxmax()
                    df['Years'] = (df.index - peak_idx) / 252
                else:
                    df['Years'] = df.index / 252
                    
                processed_series[key] = df
        except Exception as e:
            st.sidebar.error(f"⚠️ {key} ({info['ticker']}) 데이터 로드 실패: {str(e)}")
            
    return processed_series

# ----------------------------------------------------
# [데이터 로드 및 방어 코드 적용 부분]
data_dict = get_extended_bubble_data(target=analysis_target)

# 중요 키가 없는 경우 사용자에게 친절하게 경고하고 실행을 멈춤
required_keys = ['AI_Cycle', 'Dotcom', 'FANG']
missing_keys = [k for k in required_keys if k not in data_dict]

if missing_keys:
    st.error(f"🚨 **야후 파이낸스 API에서 데이터를 가져오지 못했습니다.** 누락된 항목: {missing_keys}")
    st.info("💡 잠시 후 다시 새로고침(R)을 하거나, 주말/휴일인 경우 대시보드 옵션에서 분석 타겟을 변경해 보세요.")
    st.stop() # 에러로 앱이 터지지 않고 여기서 안전하게 중단됨

# 정상적으로 데이터가 있을 때만 아래 로직 실행
ai_data = data_dict['AI_Cycle']
dotcom_data = data_dict['Dotcom']
fang_data = data_dict['FANG']
# ----------------------------------------------------
