import sqlite3
import os
from src.database import get_db_connection

def main():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        print("Connected successfully!")
        
        cursor.execute("SELECT COUNT(*) FROM users")
        print("Users count:", cursor.fetchone()[0])
        
        cursor.execute("INSERT INTO users (email, password_hash, role, name, phone, created_at) VALUES ('test_dummy@hiresense.ai', 'hash', 'candidate', 'Dummy', '123', '2026-07-15')")
        conn.commit()
        print("Inserted successfully!")
        
        cursor.execute("DELETE FROM users WHERE email = 'test_dummy@hiresense.ai'")
        conn.commit()
        print("Deleted successfully!")
        
        conn.close()
        print("Closed successfully!")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()
