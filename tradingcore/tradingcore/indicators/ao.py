import pandas as pd
import pandas_ta as ta
import numpy as np
from .base import BaseIndicator
import hashlib

class AwesomeOscillator:
    POSSIBLE_STRATEGIES = [None,'SMA_Crossover']

    def __init__(self, strategy: str = None):
        self.strategy = strategy
        self.components = pd.DataFrame(columns=['AO', 'AO_Signal'])
        self.data_hash = None

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
            self.data_hash = data_hash
            # Calculate short and long SMA
            short_sma = ta.sma(data['Close'], length=5)
            long_sma = ta.sma(data['Close'], length=34)

            # Calculate Awesome Oscillator (AO)
            ao = short_sma - long_sma

            # AO_Signal: AO crossover
            self.components['AO_Signal'] = 0
            

            # Store results in components DataFrame
            self.components['AO'] = ao

        # If no strategy is specified, return the Ichimoku components
        if self.strategy is None:
            return self.components['AO']
        
        if self.strategy == 'SMA_Crossover':
            # Additional logic for SMA crossover strategy
            self.components['AO_Signal'] = self.components['AO'].apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))

        return self.components['AO_Signal']