import pandas as pd
import pandas_ta as ta
import numpy as np
from .base import BaseIndicator
import hashlib

class KeltnerChannel(BaseIndicator):
    POSSIBLE_STRATEGIES=[None,'KC']
    def __init__(self, strategy: str = None):
        self.strategy = strategy
        self.components = pd.DataFrame(columns=['KC_Middle', 'KC_Upper', 'KC_Lower', 'KC_Signal'])
        self.data_hash = None
        self.cache = {}

    def _hash_data(self, data):
        return hashlib.sha256(pd.util.hash_pandas_object(data).values).hexdigest()
    
    def setStrategy(self, strategy: str = None):
        if strategy not in self.POSSIBLE_STRATEGIES:
            raise ValueError(f"Strategy {strategy} is not allowed. Possible strategies: {self.POSSIBLE_STRATEGIES}")
        self.strategy = strategy

    def _compare(self, key, series1, series2, op):
        if key not in self.cache:
            self.cache[key] = op(series1, series2)
        return self.cache[key]

    def calculate(self, data: pd.DataFrame):
        data_hash = self._hash_data(data)
        # Check if the data has changed
        if self.data_hash != data_hash:
            # Update the hash
            self.data_hash = data_hash
            kc_result = ta.kc(data['High'], data['Low'], data['Close'], length=20, scalar=2.0)
            # Assign Keltner Channels to the DataFrameD
            self.components['KC_Middle'] = kc_result['KCBe_20_2.0']
            self.components['KC_Upper'] = kc_result['KCUe_20_2.0']
            self.components['KC_Lower'] = kc_result['KCLe_20_2.0']
        
        self.components['KC_Signal'] = 0

        # If no strategy return results
        if self.strategy is None:
            return self.components['KC_Middle'], self.components['KC_Upper'], self.components['KC_Lower']

        # Apply different strategies based on the strategy parameter
        if self.strategy == 'KC':
            # Buy signal: Price crosses above KC Upper
            self.components['KC_Signal'] = np.where(
                (data['Close'] > self.components['KC_Upper']), 
                1, self.components['KC_Signal'])

            # Sell signal: Price crosses below KC Lower
            self.components['KC_Signal'] = np.where(
                (data['Close'] < self.components['KC_Lower']), 
                -1, self.components['KC_Signal'])
        return self.components['KC_Signal']
