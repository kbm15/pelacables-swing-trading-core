from library import TimeSeriesData, Backtester, ScreenerData, AwesomeOscillator,BollingerBands,IchimokuCloud,KeltnerChannel,MovingAverage,MACD,PSAR,RSI,StochasticOscillator,VolumeIndicator
from library.utils.yahoo_finance import check_tickers_exist     
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def plot_strategy(indicator:IchimokuCloud, ts:TimeSeriesData, backtest:Backtester):

    # Asegurarse de que no hay NaN en las columnas que se van a plotear
    required_columns = ['Close']
    required_columns += ['Ichimoku_Tenkan','Ichimoku_Kijun','Ichimoku_SenkouA','Ichimoku_SenkouB',
                                'Ichimoku_SenkouA','Ichimoku_Chikou','Position']

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

def backtest_ticker(ticker, ts, indicators_strategies):
    results = pd.DataFrame(columns=['Ticker', 'BaseIndicator', 'Strategy', 'Valor final', 'Retorno total', 'Hold perfecto'])
    for indicator_name, strategies in indicators_strategies.items():
        # Dynamically create an instance of the indicator
        indicator = globals()[indicator_name]()        
        backtest = Backtester(ts, indicator)

        for strategy in strategies:
            indicator.setStrategy(strategy)
            value, returned = backtest.run_backtest()
            
            results.loc[len(results)]={
                'Ticker': ticker, 
                'Indicator': indicator_name, 
                'Strategy': strategy, 
                'Valor final': value, 
                'Retorno total': returned
            }
            # plot_strategy(indicator, ts, backtest)
    
        returned = (ts.data['Close'].iloc[-1] - ts.data['Close'].iloc[0]) / ts.data['Close'].iloc[0] * 100    
        value = backtest.initial_capital * (returned/100 +1)
        results.loc[len(results)]={
                'Ticker': ticker, 
                'Indicator': indicator_name, 
                'Strategy': 'Hold', 
                'Valor final': value, 
                'Retorno total': returned
            }
    
    return results

# Worker thread that runs and processes tasks from the queue
def worker():
    logging.info("Worker thread started and waiting for tasks...")
    while True:
        # Get a task from the queue
        ticker = task_queue.get()
        
        if ticker is None:
            logging.info("None received, worker is exiting...")
            break  # Exit loop if None is received
        
        logging.info(f"Processing ticker: {ticker}")
        
        try:
            ts = TimeSeriesData(ticker=ticker, interval='1h')
            logging.info(f"TimeSeriesData created for ticker: {ticker}")
            
            # Submit the task to the executor for processing
            executor.submit(backtest_ticker, ticker, ts, indicators_strategies)
            logging.info(f"Task submitted for backtesting: {ticker}")
        except Exception as e:
            logging.error(f"Error while processing ticker {ticker}: {str(e)}")
        
        task_queue.task_done()
        logging.info(f"Task completed for ticker: {ticker}")

    logging.info("Worker thread has been stopped.")
def threaded_backtest(tickers, indicators_strategies):
    with ThreadPoolExecutor() as executor:
        futures = []
        results = []
        for ticker in tickers:
            ts = TimeSeriesData(ticker=ticker, interval='1h')
            futures.append(executor.submit(backtest_ticker, ticker, ts, indicators_strategies))
        
        for future in as_completed(futures):
            result = future.result()
            if len(results) == 0:
                results =[result]
            else:
                results.append(result)
    results_df = pd.concat(results,axis=0, ignore_index=True)
    return results_df

mag7_tickers = ['AAPL','GOOGL','MSFT','NVDA','AMZN','META','TSLA']
nasdaq_100_tickers = ['AAPL','MSFT','AMZN','GOOGL','GOOG','META','TSLA','NVDA','PYPL','ADBE','CMCSA','NFLX','INTC','PEP',
                      'CSCO','AVGO','COST','TMUS','TXN','QCOM','CHTR','SBUX','AMGN','MDLZ','ISRG','BKNG','GILD',
                      'ADP','ADI','LRCX','MU','INTU','AMAT','ILMN','ADSK','VRTX','REGN','JD','BIIB','KDP','MNST','CSX',
                      'MELI','MAR','CTSH','LULU','DOCU','TEAM','AEP','XEL','WDAY','SNPS','ASML','MRVL','KLAC','ORLY','IDXX',
                      'CRWD','EBAY','DXCM','ROST','ALGN','CPRT','ODFL','CDNS','ZS','NXPI','ANSS','PAYX','VRSK','PCAR','BMRN',
                      'SWKS','WDAY','FAST','MTCH','EXC','WBA','CHKP','CTAS','VRSN','INCY','OKTA','DOCU','FTNT','CDW','SIRI',
                      'LBTYA','LBTYK','QRVO','TTWO','LILA'
                      ] 

yayo_tickers = ['AMX','APEI','ATEN','BGC','ERO','EYE','F','FBP','HBI','HNST','HRTG','IMMR','KTOS','MITK','ORN','OSBC','PAGS','PK','SILV','VIRC','XHR']

hist_yayo_tickers = [
    'ALTM', 'ARCO', 'CMPO', 'FSM', 'IAG', 'ILPT', 'INTR', 'IONQ', 'KGC', 'PAYO', 'HMST', 'PAGS', 'TTI', 'WT', 'AMTX', 'ARIS', 
    'COTY', 'DH', 'OSW', 'PAYS', 'DESP', 'HNST', 'IMMR', 'TSQ', 'NOTV', 'OUT', 'PTLO', 'TFPM', 'AMAL', 'CMPO', 'CRGY', 'FDUS', 
    'GDRX', 'INTR', 'PBPB', 'USAP', 'BDTX', 'HEAR', 'HLMN', 'LAC', 'ONB', 'TZOO', 'CTLP', 'DB', 'HLLY', 'INTR', 'MWA', 'NSSC', 
    'SILV', 'WT', 'EGO', 'GT', 'LPRO', 'ROOT', 'VRE', 'ACEL', 'BHC', 'EQX', 'GDRX', 'MNTX', 'NWL', 'OSW', 'AGNC', 'BWB', 'INTR', 
    'PAGS', 'RRGB', 'UTI', 'ABR', 'ARCO', 'EHTH', 'GTES', 'NU', 'PK', 'ARAY', 'HAFC', 'HEAR', 'MASS', 'MITK', 'ULBI', 'AGI', 
    'CHWY', 'PBPB', 'RLAY', 'SEAT', 'AEO', 'AM', 'ARIS', 'BHC', 'HRTG', 'LSEA', 'ORN', 'TRIP', 'AHH', 'ARAY', 'ECVT', 'HLLY', 
    'PSEC', 'SKT', 'TCMD', 'ABR', 'BHC', 'LYTS', 'NXE', 'OPRT', 'PSTL', 'PTEN', 'CMRE', 'FTI', 'JBI', 'MITK', 'NINE', 'PBPB', 
    'RWT', 'UTI', 'ARIS', 'FREY', 'KGC', 'LFVN', 'ONB', 'OSW', 'QUAD', 'ASRT', 'KLXE', 'NABL', 'NMFC', 'SCYX', 'SLM', 'ARCO', 
    'CLS', 'ESRT', 'EXAI', 'GLAD', 'HLLY', 'MEC', 'PAGS', 'RRGB', 'ULBI', 'AAOI', 'CNHI', 'WT', 'BHC', 'DAKT', 'MRTN', 'QUAD', 
    'SHO', 'ALDX', 'MAG', 'SIRI', 'TUSK', 'OSW', 'RYAM', 'GSL', 'CINT', 'III', 'KGC', 'STNE', 'AAOI', 'RMTI', 'ARIS', 'DB', 
    'ECVT', 'WTTR', 'IBCP', 'SURG', 'PLYA', 'FSM', 'DLO', 'ETRN', 'CSWC', 'DAKT', 'PLTK', 'ARCO', 'KLXE', 'WT', 'PBPB', 'HNRG', 
    'NOA', 'OPAL', 'RITM', 'XP', 'BWEN', 'DB', 'IBCP', 'PAGS', 'ASRT', 'AGI', 'AMPL', 'STNE', 'COTY', 'DAKT', 'NINE', 'OSG', 
    'AMCR', 'AM', 'BWB', 'EEX', 'HTGC', 'PAAS', 'PANL', 'NAPA', 'UTI', 'CLS', 'RLAY', 'FREY', 'KLXE', 'PSTL', 'STGW', 'TUSK', 
    'LYTS', 'AKR', 'MEC', 'RITM', 'AMPL', 'ATEN', 'PANL', 'VRT', 'JAKK', 'BTG', 'FCF', 'FNB', 'NOA', 'ARCO', 'AE', 'BWEN', 'CLVT', 
    'EXPI', 'FBRT', 'ARHS', 'CSWC', 'GDYN', 'SPNS', 'AM', 'VTNR', 'BWB', 'CNX', 'FCF', 'KRG', 'OI', 'PBPB', 'BZH', 'SRAD', 'SLM', 
    'SPNS', 'AMPL', 'BNL', 'FMNB', 'GPK', 'HBM', 'PRMW', 'ASB', 'ATEN', 'BIVI', 'BRBR', 'CHX', 'FREY', 'GDS', 'GNE', 'IRWD', 'MRC'
]

etf = ['QQQ','SPY']

# Define a thread-safe queue to store incoming tasks
task_queue = queue.Queue()

# Define a ThreadPoolExecutor with a fixed number of threads
executor = ThreadPoolExecutor(max_workers=5)

# Define the FastAPI app with a lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the worker thread during the startup
    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()
    
    # Yield control back to FastAPI (app runs here)
    yield
    
    # Optionally, cleanup during shutdown
    task_queue.put(None)  # Signal the worker to exit
    worker_thread.join()  # Ensure the worker thread finishes

app = FastAPI(lifespan=lifespan)

indicators_strategies = {
  "AwesomeOscillator": ['SMA_Crossover'],
   "BollingerBands": ['Bollinger'],  
   "IchimokuCloud": ['Ichimoku', 'Kumo', 'KumoChikou', 'Kijun', 'KijunPSAR', 'TenkanKijun', 'KumoTenkanKijun', 'TenkanKijunPSAR', 'KumoTenkanKijunPSAR', 'KumoKiyunPSAR', 'KumoChikouPSAR', 'KumoKiyunChikouPSAR'],
   "KeltnerChannel": ['KC'],
   "MovingAverage": ['MA'],
   "MACD": ['MACD'],
   "PSAR": ['PSAR'],
   "RSI": ['RSI', 'RSI_Falling', 'RSI_Divergence', 'RSI_Cross'],
  "VolumeIndicator": ['Volume']
}



# Define an API endpoint to receive the data
@app.post("/add-screener/")
async def add_screener(data: ScreenerData):

    # Extract the ticker list from the received data
    tickers, trash = check_tickers_exist(data.tickers)
    logging.info(f"Loading tickers {tickers}, discarded {trash}")

    # Add the incoming data to the task queue
    task_queue.put(tickers)
    
    # Return a response
    return {
        "received_tickers": tickers
    }

# Define an API endpoint to receive the data
@app.post("/add-ticker/")
async def add_ticker(data):

    # Extract the ticker list from the received data
    json_data = json.loads(data)
    ticker = json_data['ticker']
    
    tickers, trash = check_tickers_exist([ticker])
    logging.info(f"Loading tickers {tickers}, discarded {trash}")

    if len(tickers) == 1:
        logging.info(f"Loading single ticker {ticker}")
        ts = TimeSeriesData(ticker=ticker, interval='1h')
        result = backtest_ticker(ticker=ticker, ts=ts, indicators_strategies=indicators_strategies)
        return result.to_json(orient="records")

    else:
        logging.error(f"Failed to load ticker from json {json_data}")
        return {
            "message": "Invalid ticker data"
        }
    
    


# Running the app using Uvicorn server (optional, useful when running locally)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# OLD 

""" results = threaded_backtest(ticker_list, indicators_strategies)

results.to_csv('result.csv', index=False)

# Calculate the average Retorno total per Strategy
average_ret_per_strategy = results.groupby('Strategy')['Retorno total'].mean().reset_index()
average_ret_per_strategy.columns = ['Strategy','Average Retorno total']
average_ret_per_strategy = average_ret_per_strategy.sort_values(by='Average Retorno total', ascending=False)

# Calculate the max Retorno total Strategy per Ticker
max_ret_per_ticker = results.loc[results.groupby('Ticker')['Retorno total'].idxmax()]
max_ret_per_ticker = max_ret_per_ticker[['Ticker','Strategy','Valor final','Retorno total']].reset_index(drop=True)
max_ret_per_ticker.columns = ['Ticker','Max Strategy','Max Valor final','Max Retorno total']
max_ret_per_ticker = max_ret_per_ticker.sort_values(by='Max Valor final', ascending=False)


print("Average Retorno total per Strategy (sorted):")
print(average_ret_per_strategy)
print("\nMax Retorno total Strategy per Ticker (sorted):")
print(max_ret_per_ticker)

logging.info(f"Finished batch") """