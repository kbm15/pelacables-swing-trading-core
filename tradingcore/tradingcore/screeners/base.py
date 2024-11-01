import pandas as pd
from datetime import datetime

class BaseScreener:
    def __init__(self, table_name: str):
        self.name = 'screener'