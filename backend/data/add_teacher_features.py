import sqlite3

def add_teacher_features():
    """
    Add tables for teacher/admin functionality.
    This script is idempotent, meaning it can be run multiple times without
    creating duplicate tables. It will create the tables if they do not exist.
    """
    conn = sqlite3.connect("data/math.db")
    c = conn.cursor()

    print("Creating teacher-related tables if they don't exist...")

    # Table for classes created by teachers
    c.execute("""
    CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        class_code TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (teacher_id) REFERENCES users(id)
    );
    """)

    # This is the missing table that caused the error.
    # It links students to the classes they have joined.
    c.execute("""
    CREATE TABLE IF NOT EXISTS student_classes (
        student_id INTEGER NOT NULL,
        class_id INTEGER NOT NULL,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (student_id, class_id),
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
    );
    """)

    # Table for assignments created by teachers
    c.execute("""
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        due_date TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        min_questions INTEGER DEFAULT 10,
        max_attempts INTEGER DEFAULT 1,
        show_hints BOOLEAN DEFAULT TRUE,
        show_lessons BOOLEAN DEFAULT TRUE,
        micro_topic_id INTEGER,
        nano_topic_ids TEXT, -- Storing as JSON
        FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
    );
    """)
    
    # Table for assignment submissions by students
    c.execute("""
    CREATE TABLE IF NOT EXISTS assignment_submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        attempt_number INTEGER NOT NULL,
        score REAL,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        total_questions INTEGER,
        correct_answers INTEGER,
        time_spent INTEGER, -- in seconds
        FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # Table for announcements made by teachers
    c.execute("""
    CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_id INTEGER NOT NULL,
        teacher_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
        FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()
    print("Database schema checked and updated successfully.")

if __name__ == '__main__':
    add_teacher_features()