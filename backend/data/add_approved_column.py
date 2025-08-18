import sqlite3
import os

DATABASE_PATH = os.path.join("data", "math.db")

def add_approval_column():
    """
    Adds an 'is_approved' column to the questions table.
    It defaults to 0 (False), so all existing questions will need re-validation.
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()

        print("Adding 'is_approved' column to the questions table...")
        
        # Add the column with a default value of 0 (not approved)
        c.execute("ALTER TABLE questions ADD COLUMN is_approved INTEGER DEFAULT 0")
        
        conn.commit()
        print("Successfully added the 'is_approved' column.")

    except sqlite3.OperationalError as e:
        # This will happen if you run the script more than once
        if "duplicate column name" in str(e):
            print("Column 'is_approved' already exists.")
        else:
            raise e
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    add_approval_column()