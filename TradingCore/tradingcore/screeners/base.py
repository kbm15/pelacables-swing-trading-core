from tradingcore.utils.db_connector import DatabaseConnector
import pandas as pd
from datetime import datetime

class BaseScreener:
    def __init__(self, table_name: str):
        # Initialize with database path and table name
        self.table_name = table_name
        self.connection = DatabaseConnector()
        
        # Ensure the table exists
        self.connection.execute(f'''
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                value REAL NOT NULL UNIQUE,
                added TEXT NOT NULL
            )
        ''')
        self.connection.commit()

    def update_table(self, df: pd.DataFrame):
        # Add 'added' column with the current timestamp
        df['added'] = int(datetime.now().timestamp())

        # Fetch current values in the database
        self.connection.execute(f'SELECT value FROM {self.table_name}')
        current_data = self.connection.fetchall()
        current_values = set(row[0] for row in current_data)

        # Identify values to delete (present in the database but not in the DataFrame)
        to_delete = current_values - set(df['Ticker'])

        # Delete rows from the database with values not in the DataFrame
        if to_delete:
            placeholders = ', '.join(['?'] * len(to_delete))
            self.connection.execute(f'''
                DELETE FROM {self.table_name}
                WHERE value IN ({placeholders})
            ''', list(to_delete))

        # Insert new rows if they don't exist in the database
        for _, row in df.iterrows():
            self.connection.execute(f'''
                INSERT OR IGNORE INTO {self.table_name} (value, added)
                VALUES (?, ?)
            ''', (row['Ticker'], row['added']))

        self.connection.commit()

    def get_table_data(self) -> pd.DataFrame:
        # Execute the query using sqlite3
        self.connection.execute(f'SELECT * FROM {self.table_name}')
        
        # Fetch all results from the executed query
        rows = self.connection.fetchall()
        
        # Get the column names from the cursor
        cursor_description = self.connection.description()
        col_names = [description[0] for description in cursor_description]
        
        # Convert the fetched data into a Pandas DataFrame
        df = pd.DataFrame(rows, columns=col_names)
        
        return df

    def close(self):
        # Close the database connection
        self.connection.close()
