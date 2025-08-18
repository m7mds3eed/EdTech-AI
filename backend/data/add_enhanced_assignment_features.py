import sqlite3
from datetime import datetime

def add_enhanced_assignment_features():
    """Add enhanced assignment features to the database."""
    conn = sqlite3.connect("data/math.db")
    c = conn.cursor()
    
    # Check current schema
    c.execute("PRAGMA table_info(assignments)")
    existing_columns = [col[1] for col in c.fetchall()]
    print(f"Existing assignment columns: {existing_columns}")
    
    # Add new columns for enhanced assignment features
    new_columns = [
        ("difficulty_preference", "TEXT DEFAULT 'mixed'"),  # beginner, intermediate, advanced, mixed
        ("count_skips", "BOOLEAN DEFAULT 1"),  # Whether to count skips against student
        ("custom_questions", "TEXT"),  # JSON array of teacher-provided questions
        ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")  # When assignment was created
    ]
    
    for column_name, column_def in new_columns:
        if column_name not in existing_columns:
            try:
                c.execute(f"ALTER TABLE assignments ADD COLUMN {column_name} {column_def}")
                print(f"Added column: {column_name}")
            except sqlite3.Error as e:
                print(f"Error adding {column_name}: {e}")
    
    # Add user creation timestamps if not exists
    c.execute("PRAGMA table_info(users)")
    user_columns = [col[1] for col in c.fetchall()]
    
    if "created_at" not in user_columns:
        try:
            c.execute("ALTER TABLE users ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
            print("Added created_at to users table")
            
            # Update existing users with current timestamp
            c.execute("UPDATE users SET created_at = ? WHERE created_at IS NULL", (datetime.now().isoformat(),))
            print("Updated existing users with creation timestamp")
        except sqlite3.Error as e:
            print(f"Error adding created_at to users: {e}")
    
    # Add parent_child_links creation timestamp
    c.execute("PRAGMA table_info(parent_child_links)")
    pcl_columns = [col[1] for col in c.fetchall()]
    
    if "created_at" not in pcl_columns:
        try:
            c.execute("ALTER TABLE parent_child_links ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
            print("Added created_at to parent_child_links table")
            
            # Update existing links
            c.execute("UPDATE parent_child_links SET created_at = ? WHERE created_at IS NULL", (datetime.now().isoformat(),))
        except sqlite3.Error as e:
            print(f"Error adding created_at to parent_child_links: {e}")
    
    # Create teacher custom questions table
    c.execute("""
        CREATE TABLE IF NOT EXISTS teacher_custom_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER,
            question_text TEXT NOT NULL,
            options TEXT,  -- JSON array for MCQ options
            correct_answer TEXT NOT NULL,
            difficulty TEXT DEFAULT 'intermediate',
            style TEXT DEFAULT 'mcq',
            nano_topic_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (teacher_id) REFERENCES users(id),
            FOREIGN KEY (nano_topic_id) REFERENCES nano_topics(id)
        )
    """)
    print("Created teacher_custom_questions table")
    
    # Update assignment_submissions to track skips properly
    c.execute("PRAGMA table_info(assignment_submissions)")
    sub_columns = [col[1] for col in c.fetchall()]
    
    if "skipped_questions" not in sub_columns:
        try:
            c.execute("ALTER TABLE assignment_submissions ADD COLUMN skipped_questions INTEGER DEFAULT 0")
            print("Added skipped_questions to assignment_submissions")
        except sqlite3.Error as e:
            print(f"Error adding skipped_questions: {e}")
    
    conn.commit()
    conn.close()
    print("Enhanced assignment features migration completed!")

if __name__ == "__main__":
    add_enhanced_assignment_features()