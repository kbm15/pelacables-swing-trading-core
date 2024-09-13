from pydantic import BaseModel
from datetime import date

# Define the structure of the incoming JSON payload using Pydantic models
class ScreenerData(BaseModel):
    tickers: list[str] = []  # List of tickers
    added_date: str    # Date of when tickers were added
    screener_name: str  # Name of the screener