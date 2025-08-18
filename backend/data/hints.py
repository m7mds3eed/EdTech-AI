# add_hint_tracking.py
# Run this script to add hint tracking to the database

import sqlite3

def add_hint_tracking():
    """Add hint_used and lesson_viewed columns to student_results table."""
    conn = sqlite3.connect("data/math.db")
    c = conn.cursor()
    
    # Check if columns already exist
    c.execute("PRAGMA table_info(student_results)")
    columns = [col[1] for col in c.fetchall()]
    
    # Add hint_used column if it doesn't exist
    if "hint_used" not in columns:
        c.execute("ALTER TABLE student_results ADD COLUMN hint_used BOOLEAN DEFAULT 0")
        print("Added hint_used column to student_results table")
    
    # Add lesson_viewed column if it doesn't exist
    if "lesson_viewed" not in columns:
        c.execute("ALTER TABLE student_results ADD COLUMN lesson_viewed BOOLEAN DEFAULT 0")
        print("Added lesson_viewed column to student_results table")
    
    conn.commit()
    conn.close()
    print("Database migration completed successfully!")

if __name__ == "__main__":
    add_hint_tracking()