import sqlite3
import psycopg2

class DatabaseConnector:
    def __init__(self, db_type="sqlite", **kwargs):
        self.db_type = db_type
        self.connection = None
        
        if db_type == "sqlite":
            self.connection = sqlite3.connect(database="local.db")
        elif db_type == "postgresql":
            self.connection = psycopg2.connect(
                dbname=kwargs.get('dbname'),
                user=kwargs.get('user'),
                password=kwargs.get('password'),
                host=kwargs.get('host', 'localhost'),
                port=kwargs.get('port', 5432)
            )
        else:
            raise ValueError("Unsupported database type")

        self.cursor = self.connection.cursor()
        
    def execute(self, query, params=None):
        self.cursor.execute(query, params or ())

    def commit(self):
        self.connection.commit()

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    def close(self):
        self.cursor.close()
        self.connection.close()

    def description(self):
        return self.cursor.description
