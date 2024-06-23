import pandas as pd

class Indicator:
    def calculate(self, data: pd.DataFrame):
        raise NotImplementedError("Should implement calculate()")
