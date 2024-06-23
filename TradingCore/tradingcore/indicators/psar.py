import pandas as pd
import pandas_ta as ta
import numpy as np
from .base import Indicator
import hashlib

class PSARIndicator(Indicator):
    def __init__(self, strategy: str = None ):
        self.strategy = strategy
        self.components = pd.DataFrame(columns=['PSAR_Long','PSAR_Short','PSAR_Signal'])
        self.data_hash = None

    def _hash_data(self, data):
        return hashlib.sha256(pd.util.hash_pandas_object(data).values).hexdigest()

    def _compare(self, key, series1, series2, op):
        if key not in self.cache:
            self.cache[key] = op(series1, series2)
        return self.cache[key]

    def calculate(self, data: pd.DataFrame):
        data_hash = self._hash_data(data)
        # Check if the data has changed
        if self.data_hash != data_hash:
            #print("Data has changed. Recalculating PSAR parameters.")
            # Update the hash
            self.data_hash = data_hash      
            psar_result = ta.psar(data['High'], data['Low'], data['Close'], af0=0.02, af=0.02, max_af=0.2)        
            # Assign PSAR components to the DataFrame
            self.components['PSAR_Long'] = psar_result['PSARl_0.02_0.2']
            self.components['PSAR_Short'] = psar_result['PSARs_0.02_0.2']
        
        self.components['PSAR_Signal'] = 0

        # If no strategy return results
        if self.strategy is None:
            return psar_result['PSARl_0.02_0.2'], psar_result['PSARs_0.02_0.2']

        # Apply different strategies based on the strategy parameter
        if self.strategy == 'PSAR':
            # Buy signal: price > PSAR
            self.components['PSAR_Signal'] = np.where(
                (data['Close'] > self.components['PSAR_Long']), 
                1, self.components['PSAR_Signal'])

            # Sell signal: price < PSAR
            self.components['PSAR_Signal'] = np.where(
                (data['Close'] < self.components['PSAR_Short']), 
                -1, self.components['PSAR_Signal'])
        return self.components['PSAR_Signal']
