import sqlite3
from datetime import datetime

def fix_database_columns():
    """Fix missing database columns."""
    conn = sqlite3.connect("data/math.db")
    c = conn.cursor()
    
    print("Fixing database columns...")
    
    # Check and add created_at to users table
    c.execute("PRAGMA table_info(users)")
    user_columns = [col[1] for col in c.fetchall()]
    print(f"User columns: {user_columns}")
    
    if "created_at" not in user_columns:
        try:
            c.execute("ALTER TABLE users ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
            print("✅ Added created_at to users table")
        except sqlite3.Error as e:
            print(f"❌ Error adding created_at to users: {e}")
    
    # Update existing users with current timestamp
    c.execute("UPDATE users SET created_at = ? WHERE created_at IS NULL", (datetime.now().isoformat(),))
    print("✅ Updated existing users with creation timestamp")
    
    # Check and add created_at to parent_child_links table
    c.execute("PRAGMA table_info(parent_child_links)")
    pcl_columns = [col[1] for col in c.fetchall()]
    print(f"Parent_child_links columns: {pcl_columns}")
    
    if "created_at" not in pcl_columns:
        try:
            c.execute("ALTER TABLE parent_child_links ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
            print("✅ Added created_at to parent_child_links table")
        except sqlite3.Error as e:
            print(f"❌ Error adding created_at to parent_child_links: {e}")
    
    # Update existing links
    c.execute("UPDATE parent_child_links SET created_at = ? WHERE created_at IS NULL", (datetime.now().isoformat(),))
    print("✅ Updated existing parent_child_links with creation timestamp")
    
    # Check and add columns to assignments table
    c.execute("PRAGMA table_info(assignments)")
    assignment_columns = [col[1] for col in c.fetchall()]
    print(f"Assignment columns: {assignment_columns}")
    
    assignment_new_columns = [
        ("difficulty_preference", "TEXT DEFAULT 'mixed'"),
        ("count_skips", "BOOLEAN DEFAULT 1"),
        ("custom_questions", "TEXT"),
        ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")
    ]
    
    for column_name, column_def in assignment_new_columns:
        if column_name not in assignment_columns:
            try:
                c.execute(f"ALTER TABLE assignments ADD COLUMN {column_name} {column_def}")
                print(f"✅ Added {column_name} to assignments table")
            except sqlite3.Error as e:
                print(f"❌ Error adding {column_name} to assignments: {e}")
    
    # Create teacher_custom_questions table if not exists
    c.execute("""
        CREATE TABLE IF NOT EXISTS teacher_custom_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER,
            question_text TEXT NOT NULL,
            options TEXT,
            correct_answer TEXT NOT NULL,
            difficulty TEXT DEFAULT 'intermediate',
            style TEXT DEFAULT 'mcq',
            nano_topic_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (teacher_id) REFERENCES users(id),
            FOREIGN KEY (nano_topic_id) REFERENCES nano_topics(id)
        )
    """)
    print("✅ Created teacher_custom_questions table")
    
    # Update assignment_submissions if needed
    c.execute("PRAGMA table_info(assignment_submissions)")
    sub_columns = [col[1] for col in c.fetchall()]
    
    if "skipped_questions" not in sub_columns:
        try:
            c.execute("ALTER TABLE assignment_submissions ADD COLUMN skipped_questions INTEGER DEFAULT 0")
            print("✅ Added skipped_questions to assignment_submissions")
        except sqlite3.Error as e:
            print(f"❌ Error adding skipped_questions: {e}")
    
    conn.commit()
    conn.close()
    print("🎉 Database migration completed!")

if __name__ == "__main__":
    fix_database_columns()