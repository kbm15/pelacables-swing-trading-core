import pandas as pd
import pandas_ta as ta
import numpy as np

class BaseIndicator:
    def calculate(self, data: pd.DataFrame):        raise NotImplementedError("Should implement calculate()")
