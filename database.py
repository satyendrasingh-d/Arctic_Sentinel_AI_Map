
import sqlite3
import os

# Define the database file name
DB_FILE = "database.db"

def init_db():
    # Initialize the SQLite database and create tables if they do not exist
    # check_same_thread=False is used to prevent issues with FastAPI's async workers
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    
    # Create the route_logs table to store user search history and risk data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS route_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_location TEXT,
            end_location TEXT,
            avg_risk_percentage REAL,
            max_risk_category TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized and 'route_logs' table is ready.")

def insert_route_log(start_loc: str, end_loc: str, avg_risk: float, max_category: str):
    # Insert a new record into the route_logs table
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO route_logs (start_location, end_location, avg_risk_percentage, max_risk_category)
            VALUES (?, ?, ?, ?)
        ''', (start_loc, end_loc, avg_risk, max_category))
        conn.commit()
    except Exception as e:
        print(f"Database Insertion Error: {e}")
    finally:
        conn.close()

def fetch_recent_logs(limit: int = 50):
    # Retrieve the most recent route search logs for the admin panel
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM route_logs ORDER BY timestamp DESC LIMIT ?', (limit,))
        rows = cursor.fetchall()
        
        # Format the data into a list of dictionaries for the API response
        logs = []
        for row in rows:
            logs.append({
                "id": row[0],
                "start": row[1],
                "end": row[2],
                "avg_risk": row[3],
                "category": row[4],
                "time": row[5]
            })
        return logs
    except Exception as e:
        print(f"Database Fetch Error: {e}")
        return []
    finally:
        conn.close()
