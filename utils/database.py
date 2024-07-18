from dotenv import load_dotenv
import os
import pyodbc


load_dotenv()

driver = os.getenv('SQL_DRIVER')
server = os.getenv('SQL_SERVER')
database = os.getenv('SQL_DATABASE')
username = os.getenv('SQL_USERNAME')
password = os.getenv('SQL_PASSWORD')

connection_string = f"DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}"

def get_db_connection():
    try:
        conn = pyodbc.connect(connection_string, timeout=10)
        return conn
    except pyodbc.Error as e:
        raise Exception(f"Database connection error: {str(e)}")