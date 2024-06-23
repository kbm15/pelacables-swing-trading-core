import pandas as pd
import pandas_ta as ta
import numpy as np

class Indicator:
    def calculate(self, data: pd.DataFrame):        raise NotImplementedError("Should implement calculate()")
