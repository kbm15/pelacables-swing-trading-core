import psycopg2
from psycopg2 import sql
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "timeseries_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")


def connect_db():
    """
    Función para conectar a la base de datos PostgreSQL.
    Retorna un objeto de conexión.
    """
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB
        )
        return conn
    except Exception as error:
        logging.error("Failed to connect to PostgreSQL database:", error)
        exit(1)


def init_database():

    try:
        # Usar connect_db para obtener la conexión a la base de datos 'postgres'
        conn = connect_db()
        conn.autocommit = True  # Para permitir la creación de bases de datos
        cursor = conn.cursor()
        
        # Crear la base de datos especificada en POSTGRES_DB si no existe
        try:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(POSTGRES_DB)))
            logging.info(f"Initialized PostgreSQL database {POSTGRES_DB}")
        except psycopg2.errors.DuplicateDatabase:
            logging.info(f"PostgreSQL database {POSTGRES_DB} already exists")
        
        # Cerrar la conexión a la base de datos 'postgres'
        cursor.close()
        conn.close()

        # Ahora nos conectamos a la base de datos creada/seleccionada para crear la tabla
        conn = connect_db()
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
        conn.commit()  # Asegúrate de hacer commit

        # Verifica si la tabla fue creada correctamente
        cursor.execute("""SELECT to_regclass('public.DataTimeSeries');""")
        result = cursor.fetchone()
        if result[0] is None:
            logging.error("Table DataTimeSeries does not exist after creation attempt.")
        else:
            logging.info("Table DataTimeSeries exists.")
        
        # Cerrar la conexión a la base de datos
        cursor.close()
        conn.close()

    except Exception as error:
        logging.error("Failed to initialize PostgreSQL database or create table:", error)
        logging.info("Username: %s", POSTGRES_USER)
        exit(1)
