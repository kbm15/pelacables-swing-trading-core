import psycopg2
from psycopg2 import sql
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')

def init_database():
    """
    Función para inicializar la base de datos PostgreSQL.
    Si la base de datos ya existe, lo notifica en el log y termina.
    Además, crea la tabla DataTimeSeries si no existe.
    """
    try:
        # Conectarse a la base de datos 'postgres' para ejecutar comandos administrativos
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database="postgres"
        )
        conn.autocommit = True  # Para permitir la creación de bases de datos
        cursor = conn.cursor()
        
        # Crear la base de datos especificada en POSTGRES_DB
        try:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(POSTGRES_DB)))
            logging.info(f"Initialized PostgreSQL database {POSTGRES_DB}")
        except psycopg2.errors.DuplicateDatabase:
            logging.info(f"PostgreSQL database {POSTGRES_DB} already exists")
        
        # Cerrar la conexión a la base de datos 'postgres'
        cursor.close()
        conn.close()

        # Ahora nos conectamos a la base de datos creada/seleccionada para crear la tabla
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB
        )
        cursor = conn.cursor()

        # Crear la tabla DataTimeSeries si no existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS DataTimeSeries (
                date DATE NOT NULL,
                ticker VARCHAR(10) NOT NULL,
                interval VARCHAR(10) NOT NULL,
                open FLOAT NOT NULL,
                high FLOAT NOT NULL,
                low FLOAT NOT NULL,
                close FLOAT NOT NULL,
                volume BIGINT NOT NULL,
                dividends FLOAT DEFAULT 0,
                stock_splits FLOAT DEFAULT 1,
                PRIMARY KEY (date, ticker, interval)
            )
        """)
        logging.info("Table DataTimeSeries is ready.")
        
        # Cerrar la conexión a la base de datos
        cursor.close()
        conn.close()

    except Exception as error:
        logging.error("Failed to initialize PostgreSQL database or create table:", error)
        logging.info("Username: %s", POSTGRES_USER)
        exit(1)
