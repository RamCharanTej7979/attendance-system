import mysql.connector
from mysql.connector import Error
from config import Config

def get_db_connection():
    """
    Creates a new connection to the MySQL database.
    """
    try:
        connection = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL Database: {e}")
    return None

def init_db():
    """
    Executes the schema.sql file to make sure DB and tables exist.
    """
    try:
        # First connect without specifying a DB to create it if it doesn't exist
        connection = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
        cursor = connection.cursor()
        
        # Read and execute schema
        import os
        schema_path = os.path.join(Config.BASE_DIR, 'sql', 'schema.sql')
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                sql_statements = f.read().split(';')
                for statement in sql_statements:
                    if statement.strip():
                        cursor.execute(statement)
            connection.commit()
            print("Database initialized successfully.")
        
        cursor.close()
        connection.close()
    except Exception as e:
        print(f"Failed to initialize database: {e}")
