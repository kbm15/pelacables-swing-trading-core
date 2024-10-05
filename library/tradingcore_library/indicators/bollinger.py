import pandas as pd
import pandas_ta as ta
import numpy as np
from .base import BaseIndicator
import hashlib

class BollingerBands(BaseIndicator):
    POSSIBLE_STRATEGIES=[None,'Bollinger']
    def __init__(self, strategy: str = None ):
        self.strategy = strategy
        self.components = pd.DataFrame(columns=['Bollinger_Upper', 'Bollinger_Middle', 'Bollinger_Lower', 'Bollinger_width', 'Bollinger_std', 'Bollinger_Signal'])
        self.data_hash = None

    def _hash_data(self, data):
        return hashlib.sha256(pd.util.hash_pandas_object(data).values).hexdigest()

    def _compare(self, key, series1, series2, op):
        if key not in self.cache:
            self.cache[key] = op(series1, series2)
        return self.cache[key]
    
    def setStrategy(self, strategy: str = None):
        if strategy not in self.POSSIBLE_STRATEGIES:
            raise ValueError(f"Strategy {strategy} is not allowed. Possible strategies: {self.POSSIBLE_STRATEGIES}")
        self.strategy = strategy

    def calculate(self, data: pd.DataFrame):
        data_hash = self._hash_data(data)
        # Check if the data has changed
        if self.data_hash != data_hash:
            # print(f"Data has changed, old hash {self.data_hash} vs new hash {data_hash}. Recalculating Bollinger parameters.")
            # Update the hash
            self.data_hash = data_hash

            # Calcular Bandas de Bollinger
            bbands_result = ta.bbands(data['Close'], length=20, std=2)

            # Asignar las columnas al DataFrame 'data' según sea necesario
            self.components['Bollinger_Upper'] = bbands_result['BBU_20_2.0']
            self.components['Bollinger_Middle'] = bbands_result['BBM_20_2.0']
            self.components['Bollinger_Lower'] = bbands_result['BBL_20_2.0']

            # Opcionalmente, si necesitas otras columnas como el ancho y la desviación estándar
            self.components['Bollinger_width'] = bbands_result['BBB_20_2.0']
            self.components['Bollinger_std'] = bbands_result['BBP_20_2.0']
        
        self.components['Bollinger_Signal'] = 0
         
        # If no strategy is specified, return the Ichimoku components
        if self.strategy is None:            
            return self.components['Bollinger_Upper'], self.components['Bollinger_Middle'], self.components['Bollinger_Lower']
        
        # Apply different strategies based on the strategy parameter
        if self.strategy == 'Bollinger':
            self.components['Bollinger_Signal'] = np.where(data['Close'] < self.components['Bollinger_Lower'], 1, self.components['Bollinger_Signal'])  # Señal de compra
            self.components['Bollinger_Signal'] = np.where(data['Close'] > self.components['Bollinger_Upper'], -1, self.components['Bollinger_Signal'])  # Señal de venta
        
        return self.components['Bollinger_Signal']
