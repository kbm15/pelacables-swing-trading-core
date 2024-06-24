import pandas as pd
import pandas_ta as ta
import numpy as np
from .base import Indicator
import hashlib

class MACDIndicator(Indicator):
    POSSIBLE_STRATEGIES=[None,'MACD']
    def __init__(self, strategy: str = None, fast: int = 12, slow: int = 26, signal: int = 9):
        self.strategy = strategy
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.components = pd.DataFrame(columns=['MACD', 'MACD_Signal', 'MACD_Hist', 'MACD_Strategy_Signal'])
        self.data_hash = None
        self.cache = {}

    def _hash_data(self, data):
        return hashlib.sha256(pd.util.hash_pandas_object(data).values).hexdigest()
    
    def setStrategy(self, strategy: str = None):
        if strategy not in self.POSSIBLE_STRATEGIES:
            raise ValueError(f"Strategy {strategy} is not allowed. Possible strategies: {self.POSSIBLE_STRATEGIES}")
        self.strategy = strategy

    def calculate(self, data: pd.DataFrame):
        data_hash = self._hash_data(data)
        # Check if the data has changed
        if self.data_hash != data_hash:
            # Update the hash
            self.data_hash = data_hash
            macd_result = ta.macd(data['Close'], fast=self.fast, slow=self.slow, signal=self.signal)
            # Assign MACD components to the DataFrame
            self.components['MACD'] = macd_result['MACD_12_26_9']
            self.components['MACD_Signal'] = macd_result['MACDs_12_26_9']
            self.components['MACD_Hist'] = macd_result['MACDh_12_26_9']

        self.components['MACD_Strategy_Signal'] = 0

        # If no strategy return results
        if self.strategy is None:
            return self.components['MACD'], self.components['MACD_Signal'], self.components['MACD_Hist']

        # Apply different strategies based on the strategy parameter
        if self.strategy == 'MACD':
            # Buy signal: MACD line crosses above Signal line
            self.components['MACD_Strategy_Signal'] = np.where(
                (self.components['MACD'] > self.components['MACD_Signal']), 
                1, self.components['MACD_Strategy_Signal'])

            # Sell signal: MACD line crosses below Signal line
            self.components['MACD_Strategy_Signal'] = np.where(
                (self.components['MACD'] < self.components['MACD_Signal']), 
                -1, self.components['MACD_Strategy_Signal'])
        return self.components['MACD_Strategy_Signal']
