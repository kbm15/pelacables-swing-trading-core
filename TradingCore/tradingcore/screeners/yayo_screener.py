import os
import sys
import pandas as pd
from decouple import config
import datetime

# Function to print initializing screener string
def print_initializing_screener():
    print("Welcome to Yayo Screener!")
    print("This seems to be your first time running the program.")

# Function to create yayo_screener folder
def create_yayo_screener_folder():
    os.makedirs("cache")

# Function to check if the yayo_screener folder exists
def yayo_screener_folder_exists():
    return os.path.exists("cache")

# Function to load current_tickers_df from yayo_screener.pkl
def load_current_tickers_df():
    return pd.read_pickle("cache/yayo_screener.pkl")

# Function to save current_tickers_df to yayo_screener.pkl
def save_current_tickers_df(current_tickers_df):
    current_tickers_df.to_pickle("cache/yayo_screener.pkl")

# Function to check if an update is needed based on the last update date
def update_needed(current_tickers_df, force_update=False):
    # Check if force-update argument is provided
    if force_update:
        return True
    
    # Check if the column names start with a date older than 2 weeks
    first_column_date = pd.to_datetime(current_tickers_df.columns[3].split()[0], errors='coerce')
    if isinstance(first_column_date, pd.Timestamp):
        if (datetime.datetime.now() - first_column_date) > datetime.timedelta(weeks=2):
            return True
    return False

# Function to update current_tickers_df
def update_current_tickers_df(url):
    # Read the table from the URL    
    dfs = pd.read_html(url)

    # Select the desired DataFrame (assuming it's the first one in the list)
    original_df = dfs[0]

    # Select the desired rows and columns, starting from the fourth row (index 3)
    current_tickers_df = original_df.iloc[3:, 4:9]

    # Assign column names from the third row (index 2) of the original DataFrame
    current_tickers_df.columns = original_df.iloc[2, 4:9]

    # Find the index of the first row where the value in column 2 is NaN
    row_index_with_nan = current_tickers_df.index[current_tickers_df.iloc[:, 0].isna()].tolist()[0] - current_tickers_df.index[0]

    # Trim the DataFrame to include only the rows before the first row with NaN in column 2
    current_tickers_df = current_tickers_df.iloc[:row_index_with_nan]

    # Save the trimmed DataFrame to yayo_screener.pkl
    save_current_tickers_df(current_tickers_df)


    return current_tickers_df

# Main functio

def main():
    # Check if the "force-update" argument is provided
    force_update = False
    if "force-update" in sys.argv:
        force_update = True
        print("Force update is enabled.")

    # Get the URL variable
    url = config('PORTFOLIO_URL')
    
    # Check if yayo_screener folder exists
    if not yayo_screener_folder_exists():
        print_initializing_screener()
        create_yayo_screener_folder()

    # Check if yayo_screener.pkl exists
    if os.path.exists("cache/yayo_screener.pkl"):
        # Load current_tickers_df from yayo_screener.pkl
        current_tickers_df = load_current_tickers_df()

        # Check if an update is needed
        if update_needed(current_tickers_df, force_update):
            print("Updating current_tickers_df...")
            new_tickers_df = update_current_tickers_df(url)

            # Calculate diff between new and current tickers
            added_tickers = new_tickers_df.iloc[:, 0][~new_tickers_df.iloc[:, 0].isin(current_tickers_df.iloc[:, 0])].tolist()
            removed_tickers = current_tickers_df.iloc[:, 0][~current_tickers_df.iloc[:, 0].isin(new_tickers_df.iloc[:, 0])].tolist()
            # Check if there are added or removed values
            if len(added_tickers) > 0 or len(removed_tickers) > 0:  

                # Save diff to log
                diff_message = f"On {new_tickers_df.columns[3].split()[0]} Added tickers: {', '.join(added_tickers)}. Removed tickers: {', '.join(removed_tickers)}"

            # Update current tickers
            current_tickers_df = new_tickers_df
    else:
        # Run update method
        print("Running initial update...")
        current_tickers_df = update_current_tickers_df(url)

    # Display current_tickers_df
    print("current_tickers_df:")
    print(current_tickers_df)
    ticker_list=current_tickers_df['Ticker'].tolist()
    print("Copy friendly list")
    print(ticker_list)
    current_tickers_df['Ticker'].to_pickle("input/yayo_screener.pkl")
    print(f"Data successfully pickled to input/yayo_screener.pkl")

# Entry point of the program
if __name__ == "__main__":
    main()
