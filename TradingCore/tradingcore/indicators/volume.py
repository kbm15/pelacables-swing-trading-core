import pandas as pd
import numpy as np
from .base import BaseIndicator
import hashlib

class VolumeIndicator(BaseIndicator):
    POSSIBLE_STRATEGIES = [None, 'Volume']

    def __init__(self, strategy: str = None):
        self.strategy = strategy
        self.components = pd.DataFrame(columns=['Volume_Signal'])
        self.data_hash = None
        self.cache = {}

    def _hash_data(self, data):
        return hashlib.sha256(pd.util.hash_pandas_object(data).values).hexdigest()

    def calculate(self, data: pd.DataFrame):
        data_hash = self._hash_data(data)
        # Check if the data has changed
        if self.data_hash != data_hash:
            # Update the hash
            self.data_hash = data_hash
            # Volume components (can be more complex, like volume moving averages)
            self.components['Volume'] = data['Volume']
        
        self.components['Volume_Signal'] = 0

        # If no strategy return results
        if self.strategy is None:
            return self.components['Volume']

        # Apply different strategies based on the strategy parameter
        if self.strategy == 'Volume':
            # Example strategy: Buy signal if the current volume is higher than the average volume of the past 20 periods
            average_volume = self.components['Volume'].rolling(window=20).mean()
            self.components['Volume_Signal'] = np.where(
                self.components['Volume'] > average_volume,
                1, self.components['Volume_Signal'])
            self.components['Volume_Signal'] = np.where(
                self.components['Volume'] < average_volume,
                -1, self.components['Volume_Signal'])
            
        return self.components['Volume_Signal']

    def setStrategy(self, strategy: str = None):
        if strategy not in self.POSSIBLE_STRATEGIES:
            raise ValueError(f"Strategy {strategy} is not allowed. Possible strategies: {self.POSSIBLE_STRATEGIES}")
        self.strategy = strategy
