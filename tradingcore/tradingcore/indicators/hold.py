import pandas as pd
import pandas_ta as ta
import numpy as np
from .base import BaseIndicator
import hashlib

class Hold(BaseIndicator):
    POSSIBLE_STRATEGIES = [None, 'Hold']

    def __init__(self, strategy: str = None):
        self.strategy = strategy
        self.components = None
        self.data_hash = None
        self.cache = {}
    
    def calculate(self, data: pd.DataFrame):
        self.components = pd.DataFrame(index=data.index, data={'Hold_Signal': np.append([1], np.zeros(len(data)-1, dtype=int), axis=0)})
        return self.components['Hold_Signal']
    
    def setStrategy(self, strategy: str = None):
        if strategy not in self.POSSIBLE_STRATEGIES:
            raise ValueError(f"Strategy {strategy} is not allowed. Possible strategies: {self.POSSIBLE_STRATEGIES}")
        self.strategy = strategy