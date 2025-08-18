import sqlite3
import streamlit as st
import secrets
import hashlib

def hash_password(password):
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

# FILE: src/auth/auth.py

def init_db():
    """Initialize database tables, including the new feedback table."""
    conn = sqlite3.connect("data/math.db")
    c = conn.cursor()
    # Create users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            link_code TEXT UNIQUE
        )
    """)
    # Create parent_child_links table
    c.execute("""
        CREATE TABLE IF NOT EXISTS parent_child_links (
            parent_id INTEGER,
            student_id INTEGER,
            FOREIGN KEY (parent_id) REFERENCES users(id),
            FOREIGN KEY (student_id) REFERENCES users(id)
        )
    """)
    # Create student_results table
    c.execute("""
        CREATE TABLE IF NOT EXISTS student_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            nano_topic_id INTEGER,
            question TEXT,
            is_correct BOOLEAN,
            p_learned REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            attempt_completed BOOLEAN,
            hint_used BOOLEAN DEFAULT 0,
            lesson_viewed BOOLEAN DEFAULT 0,
            FOREIGN KEY (student_id) REFERENCES users(id),
            FOREIGN KEY (nano_topic_id) REFERENCES nano_topics(id)
        )
    """)
    
    # --- NEW: Create feedback table ---
    c.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            feedback_text TEXT NOT NULL,
            rating INTEGER,
            context TEXT,
            role TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # --- NEW: Create auth_tokens table ---
    c.execute("""
        CREATE TABLE IF NOT EXISTS auth_tokens (
            token TEXT PRIMARY KEY,
            user_id INTEGER,
            created_at TEXT,
            expires_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Existing migrations...
    c.execute("PRAGMA table_info(student_results)")
    columns = [col[1] for col in c.fetchall()]
    if "nano_topic" in columns:
        # Backup existing data
        c.execute("""
            CREATE TABLE student_results_backup AS SELECT id, student_id, nano_topic, question, is_correct, p_learned, timestamp, attempt_completed
            FROM student_results
        """)
        # Drop the old table
        c.execute("DROP TABLE student_results")
        # Recreate with new schema
        c.execute("""
            CREATE TABLE student_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                nano_topic_id INTEGER,
                question TEXT,
                is_correct BOOLEAN,
                p_learned REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                attempt_completed BOOLEAN,
                hint_used BOOLEAN DEFAULT 0,
                lesson_viewed BOOLEAN DEFAULT 0,
                FOREIGN KEY (student_id) REFERENCES users(id),
                FOREIGN KEY (nano_topic_id) REFERENCES nano_topics(id)
            )
        """)
        # Restore data with nano_topic_id mapping
        c.execute("""
            INSERT INTO student_results (id, student_id, nano_topic_id, question, is_correct, p_learned, timestamp, attempt_completed)
            SELECT id, student_id, (SELECT id FROM nano_topics WHERE name = nano_topic), question, is_correct, p_learned, timestamp, attempt_completed
            FROM student_results_backup
        """)
        # Drop backup table
        c.execute("DROP TABLE student_results_backup")
    elif "nano_topic_id" not in columns:
        c.execute("ALTER TABLE student_results ADD COLUMN nano_topic_id INTEGER")
        c.execute("UPDATE student_results SET nano_topic_id = (SELECT id FROM nano_topics WHERE name = nano_topic)")
        c.execute("ALTER TABLE student_results DROP COLUMN nano_topic")
        # Note: SQLite doesn't support adding FOREIGN KEY via ALTER, so this is handled during table recreation if needed
    # Migrate other columns
    if "timestamp" not in columns:
        c.execute("ALTER TABLE student_results ADD COLUMN timestamp DATETIME DEFAULT CURRENT_TIMESTAMP")
    if "attempt_completed" not in columns:
        c.execute("ALTER TABLE student_results ADD COLUMN attempt_completed BOOLEAN")
        c.execute("UPDATE student_results SET attempt_completed = 1 WHERE is_correct IS NOT NULL")
    if "hint_used" not in columns:
        c.execute("ALTER TABLE student_results ADD COLUMN hint_used BOOLEAN DEFAULT 0")
    if "lesson_viewed" not in columns:
        c.execute("ALTER TABLE student_results ADD COLUMN lesson_viewed BOOLEAN DEFAULT 0")

    c.execute("PRAGMA table_info(questions)")
    columns = [col[1] for col in c.fetchall()]
    if "difficulty" not in columns:
        c.execute("ALTER TABLE questions ADD COLUMN difficulty TEXT DEFAULT 'intermediate'")
    if "style" not in columns:
        c.execute("ALTER TABLE questions ADD COLUMN style TEXT DEFAULT 'mcq'")
    
    conn.commit()
    conn.close()

def register_user(username, password, role):
    """Register a new user."""
    conn = sqlite3.connect("data/math.db")
    c = conn.cursor()
    link_code = secrets.token_hex(3) if role == "student" else None
    try:
        c.execute("INSERT INTO users (username, password, role, link_code) VALUES (?, ?, ?, ?)",
                  (username, hash_password(password), role, link_code))
        conn.commit()
        return link_code
    except sqlite3.IntegrityError:
        st.error("Username already exists.")
        return None
    finally:
        conn.close()

def login_user(username, password):
    """Log in a user and return their role and ID."""
    conn = sqlite3.connect("data/math.db")
    c = conn.cursor()
    c.execute("SELECT id, role, link_code FROM users WHERE username = ? AND password = ?",
              (username, hash_password(password)))
    user = c.fetchone()
    conn.close()
    return user

def link_parent_to_student(parent_id, link_code):
    """Link a parent to a student using the link code."""
    conn = sqlite3.connect("data/math.db")
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE role = 'student' AND link_code = ?", (link_code,))
    student = c.fetchone()
    if student:
        student_id = student[0]
        c.execute("INSERT INTO parent_child_links (parent_id, student_id) VALUES (?, ?)",
                  (parent_id, student_id))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def create_class(teacher_id, name, description, grade_level):
    """Create a new class for a teacher."""
    conn = sqlite3.connect("data/math.db")
    c = conn.cursor()
    class_code = secrets.token_hex(4).upper()  # 8-character code
    try:
        c.execute("""
            INSERT INTO classes (teacher_id, name, description, grade_level, class_code) 
            VALUES (?, ?, ?, ?, ?)
        """, (teacher_id, name, description, grade_level, class_code))
        conn.commit()
        class_id = c.lastrowid
        conn.close()
        return class_id, class_code
    except Exception as e:
        conn.close()
        st.error(f"Error creating class: {str(e)}")
        return None, None

def join_class(student_id, class_code):
    """Allow a student to join a class using the class code."""
    conn = sqlite3.connect("data/math.db")
    c = conn.cursor()
    
    c.execute("SELECT id FROM classes WHERE class_code = ?", (class_code,))
    class_data = c.fetchone()
    
    if class_data:
        class_id = class_data[0]
        try:
            c.execute("INSERT INTO class_students (class_id, student_id) VALUES (?, ?)", (class_id, student_id))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            st.error("You are already enrolled in this class.")
            return False
        finally:
            conn.close()
    else:
        conn.close()
        return False
