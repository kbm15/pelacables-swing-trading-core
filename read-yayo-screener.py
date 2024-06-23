import os
import sys
import pandas as pd
from decouple import config
import datetime

# Function to save to log
def save_to_log(message):
    log_file = "yayo_screener/screener.log"
    print(message)
    if not os.path.exists(log_file):
        with open(log_file, "w") as f:
            f.write("Initializing log file.\n")
            print("Initializing log file.")

    with open(log_file, "a") as f:
        f.write(message + "\n")


# Function to print initializing screener string
def print_initializing_screener():
    print("Welcome to Yayo Screener!")
    print("This seems to be your first time running the program.")
    save_to_log(message="Initializing the screener...")

# Function to create yayo_screener folder
def create_yayo_screener_folder():
    os.makedirs("yayo_screener")

# Function to check if the yayo_screener folder exists
def yayo_screener_folder_exists():
    return os.path.exists("yayo_screener")

# Function to load current_tickers_df from current_tickers.pkl
def load_current_tickers_df():
    return pd.read_pickle("yayo_screener/current_tickers.pkl")

# Function to save current_tickers_df to current_tickers.pkl
def save_current_tickers_df(current_tickers_df):
    current_tickers_df.to_pickle("yayo_screener/current_tickers.pkl")

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

    # Save the trimmed DataFrame to current_tickers.pkl
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

    # Check if current_tickers.pkl exists
    if os.path.exists("yayo_screener/current_tickers.pkl"):
        # Load current_tickers_df from current_tickers.pkl
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
                save_to_log(diff_message)

            # Update current tickers
            current_tickers_df = new_tickers_df
    else:
        # Run update method
        print("Running initial update...")
        current_tickers_df = update_current_tickers_df(url)

    # Display current_tickers_df
    print("current_tickers_df:")
    print(current_tickers_df)
    print("Copy friendly list")
    print(current_tickers_df['Ticker'].tolist())

# Entry point of the program
if __name__ == "__main__":
    main()
