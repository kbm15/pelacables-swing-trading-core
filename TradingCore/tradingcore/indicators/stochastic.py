import pandas as pd
import pandas_ta as ta
import numpy as np
from .base import BaseIndicator
import hashlib

class StochasticOscillator(BaseIndicator):
    POSSIBLE_STRATEGIES=[None,'Stochastic']
    def __init__(self, strategy: str = None, length: int = 14, smooth_k: int = 3, smooth_d: int = 3):
        self.strategy = strategy
        self.length = length
        self.smooth_k = smooth_k
        self.smooth_d = smooth_d
        self.components = pd.DataFrame(columns=['%K', '%D', 'Stochastic_Signal'])
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
            stoch_result = ta.stoch(data['High'], data['Low'], data['Close'], k=self.length, d=self.smooth_d, smooth_k=self.smooth_k)
            # Assign %K and %D to the DataFrame
            self.components['%K'] = pd.Series([0] * self.length + stoch_result['STOCHk_14_3_3'].tolist())
            self.components['%D'] = pd.Series([0] * self.length + stoch_result['STOCHd_14_3_3'].tolist())
        
        self.components['Stochastic_Signal'] = 0

        # If no strategy return results
        if self.strategy is None:
            return self.components['%K'], self.components['%D']

        # Apply different strategies based on the strategy parameter
        if self.strategy == 'Stochastic':
            # Buy signal: %K crosses above %D
            self.components['Stochastic_Signal'] = np.where(
                (self.components['%K'] > self.components['%D']) & (self.components['%K'].shift(1) <= self.components['%D'].shift(1)),
                1, self.components['Stochastic_Signal'])

            # Sell signal: %K crosses below %D
            self.components['Stochastic_Signal'] = np.where(
                (self.components['%K'] < self.components['%D']) & (self.components['%K'].shift(1) >= self.components['%D'].shift(1)),
                -1, self.components['Stochastic_Signal'])
        
        return self.components['Stochastic_Signal']
