from tradingcore import TimeSeriesData, IchimokuIndicator
import numpy as np
import pandas_ta as ta

ts = TimeSeriesData(symbol='AAPL', interval='1d')
ts_data = ts.data.copy()

ts_data['Position']=IchimokuIndicator('TenkanKijunPSAR').calculate(ts_data)

print(ts_data)