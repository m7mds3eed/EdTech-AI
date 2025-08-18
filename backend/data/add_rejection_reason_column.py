import sqlite3
import os

DATABASE_PATH = os.path.join("data", "math.db")

def add_rejection_column():
    """Adds a 'rejection_reason' column to the questions table."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()
        print("Adding 'rejection_reason' column to the questions table...")
        c.execute("ALTER TABLE questions ADD COLUMN rejection_reason TEXT")
        conn.commit()
        print("Successfully added the 'rejection_reason' column.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'rejection_reason' already exists.")
        else:
            raise e
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    add_rejection_column()