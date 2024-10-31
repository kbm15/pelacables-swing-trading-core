import pandas as pd
import pandas_ta as ta
import numpy as np
from .base import BaseIndicator
import hashlib

class RSI(BaseIndicator):
    POSSIBLE_STRATEGIES=[None,'RSI','RSI_Falling','RSI_Divergence','RSI_Cross']
    def __init__(self, strategy: str = None, length: int = 14):
        self.strategy = strategy
        self.length = length
        self.components = pd.DataFrame(columns=['RSI_Slow', 'RSI_Fast', 'RSI_Signal', 'RSI_Bullish_Divergence', 'RSI_Bearish_Divergence'])
        self.data_hash = None
        self.cache = {}

    def _hash_data(self, data):
        return hashlib.sha256(pd.util.hash_pandas_object(data).values).hexdigest()
    
    def setStrategy(self, strategy: str = None):
        if strategy not in self.POSSIBLE_STRATEGIES:
            raise ValueError(f"Strategy {strategy} is not allowed. Possible strategies: {self.POSSIBLE_STRATEGIES}")
        self.strategy = strategy

    def _find_divergences(self, data, rsi):
        bullish_divergence = np.zeros(len(data))
        bearish_divergence = np.zeros(len(data))
        
        for i in range(2, len(data)):
            # Bullish Divergence: Price makes lower low, RSI makes higher low
            if data['Low'].iloc[i] < data['Low'].iloc[i-1] and rsi.iloc[i] > rsi.iloc[i-1]:
                bullish_divergence[i] = 1
            # Bearish Divergence: Price makes higher high, RSI makes lower high
            if data['High'].iloc[i] > data['High'].iloc[i-1] and rsi.iloc[i] < rsi.iloc[i-1]:
                bearish_divergence[i] = 1
        
        return bullish_divergence, bearish_divergence

    def calculate(self, data: pd.DataFrame):
        data_hash = self._hash_data(data)
        # Check if the data has changed
        if self.data_hash != data_hash:
            # Update the hash
            self.data_hash = data_hash
            # Calculate RSI components
            data['RSI_Slow'] = ta.rsi(data['Close'], length=14)
            data['RSI_Fast'] = ta.rsi(data['Close'], length=5)
            self.components['RSI_Slow'] = data['RSI_Slow']
            self.components['RSI_Fast'] = data['RSI_Fast']
            # Calculate divergences
            bullish_divergence, bearish_divergence = self._find_divergences(data, self.components['RSI_Slow'])
            self.components['RSI_Bullish_Divergence'] = bullish_divergence
            self.components['RSI_Bearish_Divergence'] = bearish_divergence

        self.components['RSI_Signal'] = 0

        # If no strategy return results
        if self.strategy is None:
            return self.components['RSI_Slow'], self.components['RSI_Fast']       

        # Apply different strategies based on the strategy parameter
        if self.strategy == 'RSI':
            # Buy signal: RSI < 30 (oversold)
            self.components['RSI_Signal'] = np.where(
                self.components['RSI_Slow'] < 30, 
                1, self.components['RSI_Signal'])

            # Sell signal: RSI > 70 (overbought)
            self.components['RSI_Signal'] = np.where(
                self.components['RSI_Slow'] > 70, 
                -1, self.components['RSI_Signal'])
            
        if self.strategy == 'RSI_Falling':
            # Buy signal: RSI < 30 (oversold)
            self.components['RSI_Signal'] = np.where(
                self.components['RSI_Slow'] < 30, 
                1, self.components['RSI_Signal'])

            # Sell signal: RSI > 70 (overbought)
            self.components['RSI_Signal'] = np.where(
                (self.components['RSI_Slow'].shift(1) >= 70) &
                (self.components['RSI_Slow'] > 70), 
                -1, self.components['RSI_Signal'])
        
        elif self.strategy == 'RSI_Cross':
            # Buy signal: RSI_Fast crosses above RSI_Slow
            self.components['RSI_Signal'] = np.where(
                (self.components['RSI_Fast'] > self.components['RSI_Slow']) &
                (self.components['RSI_Fast'].shift(1) <= self.components['RSI_Slow'].shift(1)),
                1, self.components['RSI_Signal'])

            # Sell signal: RSI_Fast crosses below RSI_Slow
            self.components['RSI_Signal'] = np.where(
                (self.components['RSI_Fast'] < self.components['RSI_Slow']) &
                (self.components['RSI_Fast'].shift(1) >= self.components['RSI_Slow'].shift(1)),
                -1, self.components['RSI_Signal'])
        
        # Combine divergence signals with RSI strategy signals
        elif self.strategy == 'RSI_Divergence':
            self.components['RSI_Signal'] = np.where(
                (self.components['RSI_Bullish_Divergence'] == 1) &
                (self.components['RSI_Slow'] < 30), 
                1, self.components['RSI_Signal'])

            self.components['RSI_Signal'] = np.where(
                (self.components['RSI_Bearish_Divergence'] == 1) &
                (self.components['RSI_Slow'] > 70), 
                -1, self.components['RSI_Signal'])
        
        return self.components['RSI_Signal']
