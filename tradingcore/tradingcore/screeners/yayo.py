import pandas as pd
from decouple import config
from tradingcore.screeners import BaseScreener



class YayoScreener(BaseScreener):
    def __init__(self, table_name: str):
        super().__init__(table_name)

    def generate_dataframe(self) -> pd.DataFrame:

        # Read the table from the URL    
        dfs = pd.read_html(config('PORTFOLIO_URL'))

        # Select the desired DataFrame
        original_df = dfs[0]
        current_tickers_df = original_df.iloc[3:, 4:9]
        current_tickers_df.columns = original_df.iloc[2, 4:9]
        row_index_with_nan = current_tickers_df.index[current_tickers_df.iloc[:, 0].isna()].tolist()[0] - current_tickers_df.index[0]
        current_tickers_df = current_tickers_df.iloc[:row_index_with_nan]

        return current_tickers_df

    def update_table_with_custom_data(self):
        # Generate the DataFrame with custom data
        df = self.generate_dataframe()
        df['Screener'] = 'Yayo'

        # Use the update_table method from the BaseScreener class to update the table
        self.update_table(df)

# Usage
if __name__ == "__main__":
    # Create an instance of YayoScreener with a specific table name
    screener = YayoScreener("screener")

    # Update the table with custom data
    screener.update_table_with_custom_data()

    # Optionally, retrieve and print the table data to verify the update
    df = screener.get_table_data()
    print(df)

    # Close the connection when done
    screener.close()
