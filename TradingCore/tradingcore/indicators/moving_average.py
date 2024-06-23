import pandas as pd
from .base import Indicator

class MovingAverageIndicator(Indicator):
    def __init__(self, window: int):
        self.window = window

    def calculate(self, data: pd.DataFrame):
        data['moving_average'] = data['close'].rolling(window=self.window).mean()
        return data
