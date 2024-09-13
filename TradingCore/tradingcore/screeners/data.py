from pydantic import BaseModel
from typing import List
from datetime import date

# Define the structure of the incoming JSON payload using Pydantic models
class ScreenerData(BaseModel):
    tickers: List[str]  # List of tickers
    added_date: date    # Date of when tickers were added
    screener_name: str  # Name of the screener