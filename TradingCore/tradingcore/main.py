from tradingcore import TimeSeriesData, IchimokuIndicator, Backtester
import numpy as np
import pandas_ta as ta
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def plot_strategy(indicator:IchimokuIndicator, ts:TimeSeriesData, backtest:Backtester):

    # Asegurarse de que no hay NaN en las columnas que se van a plotear
    required_columns = ['Close']
    required_columns += ['Ichimoku_Tenkan', 'Ichimoku_Kijun', 'Ichimoku_SenkouA', 'Ichimoku_SenkouB',
                                'Ichimoku_SenkouA', 'Ichimoku_Chikou', 'Position']

    # Eliminar filas con NaN en columnas requeridas
    data = indicator.components.copy()
    data['Close'] = ts.data['Close']
    data['Position'] = backtest.data['Position']


    # Visualización de resultados con Plotly
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                        row_heights=[1, 1],
                        specs=[[{"secondary_y": True}]] * 2)  # Especificación para todos los subgráficos con secondary_y=True

    # Gráfico de precios y indicador seleccionado
    fig.add_trace(go.Scatter(x=data.index, y=data['Close'], mode='lines', name='Precio de Cierre', line=dict(color='blue')), row=1, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(x=data.index, y=data['Ichimoku_Tenkan'], mode='lines', name='Tenkan-sen', line=dict(color='orange')), row=1, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(x=data.index, y=data['Ichimoku_Kijun'], mode='lines', name='Kijun-sen', line=dict(color='green')), row=1, col=1, secondary_y=False)

    fig.add_trace(go.Scatter(x=data.index, y=data['Ichimoku_SenkouA'], mode='lines', name='Senkou Span A', line=dict(color='green')), row=1, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(x=data.index, y=data['Ichimoku_SenkouA'], mode='lines', name='Senkou Span A (ISA) - Relleno', fill='tonexty', line=dict(color='rgba(0,100,80,0.2)')), row=1, col=1)

    fig.add_trace(go.Scatter(x=data.index, y=data['Ichimoku_SenkouB'], mode='lines', name='Senkou Span B', line=dict(color='red')), row=1, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(x=data.index, y=data['Ichimoku_SenkouB'], mode='lines', name='Senkou Span B (ISB) - Relleno', fill='tonexty', line=dict(color='rgba(100,0,0,0.2)')), row=1, col=1)

    fig.add_trace(go.Scatter(x=data.index, y=data['Ichimoku_Chikou'], mode='lines', name='Chikou Span', line=dict(color='purple')), row=1, col=1, secondary_y=False)

    # Señales de compra y venta para el indicador seleccionado
    if 'Position' in data.columns:
        fig.add_trace(go.Scatter(x=data[data['Position'] == 1].index, y=data['Close'][data['Position'] == 1], mode='markers', marker_symbol='triangle-up', marker_color='green', marker_size=10, name=f'Señal de Compra'), row=1, col=1)
        fig.add_trace(go.Scatter(x=data[data['Position'] == -1].index, y=data['Close'][data['Position'] == -1], mode='markers', marker_symbol='triangle-down', marker_color='red', marker_size=10, name=f'Señal de Venta '), row=1, col=1)


    fig.show()

tickers = ['AAPL','GOOGL','MSFT','NVDA','AMZN','META','TSLA']
strategies = ['Ichimoku','Kumo','KumoChikou','TenkanKijun','TenkanKijunPSAR']
results = pd.DataFrame(columns=['Ticker', 'Strategy', 'Valor final', 'Retorno total', 'Hold perfecto'])
for ticker in tickers:
    ts = TimeSeriesData(symbol=ticker, interval='1d')
    for strategy in strategies:
        indicator = IchimokuIndicator(strategy)
        backtest = Backtester(ts,indicator)
        value, returned, hold = backtest.run_backtest()
        # plot_strategy(indicator, ts, backtest)
        current_result = pd.DataFrame({'Ticker':[ticker], 'Strategy':[strategy], 'Valor final':[value], 'Retorno total':[returned], 'Hold perfecto':[hold]})
        results = pd.concat([results, current_result], ignore_index = True)
print(results)