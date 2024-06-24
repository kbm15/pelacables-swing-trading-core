import pandas as pd
import pandas_ta as ta
import numpy as np
from .base import Indicator
import hashlib

class MAIndicator(Indicator):
    POSSIBLE_STRATEGIES=[None,'MA']
    def __init__(self, strategy: str = None, length: int = 50, ma_type: str = 'sma'):
        self.strategy = strategy
        self.length = length
        self.ma_type = ma_type
        self.components = pd.DataFrame(columns=['MA', 'MA_Signal'])
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
            if self.ma_type == 'sma':
                ma_result = ta.sma(data['Close'], length=self.length)
            elif self.ma_type == 'ema':
                ma_result = ta.ema(data['Close'], length=self.length)
            else:
                raise ValueError("Unsupported MA type")
            # Assign MA to the DataFrame
            self.components['MA'] = ma_result

        self.components['MA_Signal'] = 0

        # If no strategy return results
        if self.strategy is None:
            return self.components['MA']

        # Apply different strategies based on the strategy parameter
        if self.strategy == 'MA':
            # Buy signal: price crosses above MA
            self.components['MA_Signal'] = np.where(
                (data['Close'] > self.components['MA']), 
                1, self.components['MA_Signal'])

            # Sell signal: price crosses below MA
            self.components['MA_Signal'] = np.where(
                (data['Close'] < self.components['MA']), 
                -1, self.components['MA_Signal'])
        return self.components['MA_Signal']
