# In backend/data/database_setup.py

import sqlite3
import os

# Define the path to the database relative to the backend folder
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'math.db')

def setup_database():
    """
    Creates and sets up the entire database schema from scratch.
    This single script ensures the database structure is always correct and complete.
    It is idempotent, meaning it can be run multiple times without causing errors.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    print("--- 🚀 Starting Full Database Schema Setup ---")

    # --- 1. Core Curriculum Tables ---
    print("   -> Creating curriculum tables (topics, subtopics, etc.)...")
    c.execute("""
    CREATE TABLE IF NOT EXISTS topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT, subject TEXT NOT NULL,
        name TEXT NOT NULL, description TEXT
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS subtopics (
        id INTEGER PRIMARY KEY AUTOINCREMENT, topic_id INTEGER, name TEXT NOT NULL,
        description TEXT, FOREIGN KEY (topic_id) REFERENCES topics(id)
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS micro_topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT, subtopic_id INTEGER, name TEXT NOT NULL,
        description TEXT, FOREIGN KEY (subtopic_id) REFERENCES subtopics(id)
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS nano_topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT, micro_topic_id INTEGER, name TEXT NOT NULL,
        description TEXT, keywords TEXT,
        FOREIGN KEY (micro_topic_id) REFERENCES micro_topics(id)
    )""")

    # --- 2. Users and Authentication Tables ---
    print("   -> Creating user and authentication tables...")
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL, role TEXT NOT NULL, link_code TEXT UNIQUE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS parent_child_links (
        parent_id INTEGER, student_id INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (parent_id, student_id),
        FOREIGN KEY (parent_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    # --- 3. Questions and Results Tables ---
    print("   -> Creating questions and student results tables...")
    c.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nano_topic_id INTEGER,
        question TEXT NOT NULL, options TEXT NOT NULL, answer TEXT NOT NULL,
        difficulty TEXT, style TEXT, is_approved INTEGER DEFAULT 0,
        rejection_reason TEXT,
        FOREIGN KEY (nano_topic_id) REFERENCES nano_topics(id)
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS student_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER, nano_topic_id INTEGER,
        question TEXT, is_correct BOOLEAN, p_learned REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, attempt_completed BOOLEAN,
        hint_used BOOLEAN DEFAULT 0, lesson_viewed BOOLEAN DEFAULT 0,
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (nano_topic_id) REFERENCES nano_topics(id)
    )""")

    # --- 4. Teacher, Class, and Assignment Tables ---
    print("   -> Creating teacher, class, and assignment tables...")
    c.execute("""
    CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, teacher_id INTEGER, name TEXT NOT NULL,
        description TEXT, grade_level TEXT, class_code TEXT UNIQUE NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (teacher_id) REFERENCES users(id)
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS student_classes (
        student_id INTEGER NOT NULL, class_id INTEGER NOT NULL,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (student_id, class_id),
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT, class_id INTEGER, title TEXT NOT NULL,
        description TEXT, due_date DATETIME, min_questions INTEGER DEFAULT 10,
        max_attempts INTEGER DEFAULT 1, show_hints BOOLEAN DEFAULT 1,
        show_lessons BOOLEAN DEFAULT 1, micro_topic_id INTEGER, nano_topic_ids TEXT,
        difficulty_preference TEXT DEFAULT 'mixed', count_skips BOOLEAN DEFAULT 1,
        custom_questions TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS assignment_submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, assignment_id INTEGER, student_id INTEGER,
        attempt_number INTEGER NOT NULL, score REAL,
        started_at DATETIME DEFAULT CURRENT_TIMESTAMP, completed_at DATETIME,
        total_questions INTEGER, correct_answers INTEGER, time_spent INTEGER,
        skipped_questions INTEGER DEFAULT 0,
        FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT, class_id INTEGER, teacher_id INTEGER,
        content TEXT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
        FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS teacher_custom_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, teacher_id INTEGER, question_text TEXT NOT NULL,
        options TEXT, correct_answer TEXT NOT NULL, difficulty TEXT DEFAULT 'intermediate',
        style TEXT DEFAULT 'mcq', nano_topic_id INTEGER, created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (teacher_id) REFERENCES users(id),
        FOREIGN KEY (nano_topic_id) REFERENCES nano_topics(id)
    )""")

    # --- 5. Feedback and Interaction Tables ---
    print("   -> Creating feedback and interaction tables...")
    c.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, feedback_text TEXT NOT NULL,
        rating INTEGER, context TEXT, role TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS ai_interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, role TEXT,
        question TEXT, response TEXT, helpful BOOLEAN,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    # --- 6. Indexes for Performance ---
    print("   -> Creating indexes for faster queries...")
    c.execute("CREATE INDEX IF NOT EXISTS idx_nano_topic_id ON questions(nano_topic_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_student_results_student_id ON student_results(student_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_assignments_class_id ON assignments(class_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_assignment_submissions_student_id ON assignment_submissions(student_id)")

    conn.commit()
    conn.close()
    print("--- ✅ Database Schema Setup Complete ---")

if __name__ == "__main__":
    # This allows the script to be run directly from the command line
    setup_database()