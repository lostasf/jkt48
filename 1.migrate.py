import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return psycopg2.connect(os.environ.get("NEON_DB_URL"))

def run_sql_file(filename):
    if not os.path.exists(filename):
        print(f"Error: {filename} not found.")
        return

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            with open(filename, 'r') as file:
                sql = file.read()
                cur.execute(sql)
        conn.commit()

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "up"
    
    if action == "up":
        print("Running schema.sql...")
        run_sql_file("schema.sql")
        print("Database schema created or verified.")
    elif action == "down":
        print("Running drop_schema.sql...")
        run_sql_file("drop_schema.sql")
        print("Database schema dropped.")
    else:
        print("Invalid argument. Use 'up' or 'down'.")