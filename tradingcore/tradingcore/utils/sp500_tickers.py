import pandas as pd

def get_sp500_tickers() -> list:
    """
    Fetches the list of S&P 500 tickers from Wikipedia.

    Returns:
        A list of ticker symbols.
    """
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    try:
        tables = pd.read_html(url)
        df = tables[0]
        tickers = df['Symbol'].tolist()
        # Some tickers have dots instead of dashes (e.g., BRK.B), replace with appropriate format
        tickers = [ticker.replace('.', '-') for ticker in tickers]
        return tickers
    except Exception as e:
        print(f"Error fetching S&P 500 tickers: {e}")
        return []

# Example usage:
if __name__ == "__main__":
    sp500_tickers = get_sp500_tickers()
    print(sp500_tickers)