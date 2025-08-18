# FILE: main.py

from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import sqlite3
import json
import hashlib
import secrets
from datetime import datetime, timedelta
import os
import sys
import pandas as pd
# DATABASE_PATH = os.path.join(os.path.dirname(__file__), "data", "math.db")
from fastapi.responses import JSONResponse
# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.auth.auth import hash_password, init_db
from src.quiz.data import load_nano_topics, get_questions, get_unanswered_questions
from src.quiz.bkt import BKT, select_next_module
from src.quiz.openai_client import (
    generate_question, generate_explanation, generate_hint, 
    generate_mini_lesson, generate_parent_report, generate_actionable_steps
)
from src.supervisor.supervisor import run_full_database_check

# Initialize FastAPI app
app = FastAPI(
    title="Educational Platform API",
    description="Backend API for the educational quiz platform",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Database path
DATABASE_PATH = os.path.join("data", "math.db")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()

# Pydantic models
class UserCreate(BaseModel):
    username: str
    password: str
    role: str = Field(..., pattern="^(student|parent|teacher|admin)$")

class UserLogin(BaseModel):
    username: str
    password: str

class LinkParent(BaseModel):
    link_code: str

class ClassCreate(BaseModel):
    name: str
    description: Optional[str] = None
    grade_level: Optional[str] = None

class JoinClass(BaseModel):
    class_code: str

class AssignmentCreate(BaseModel):
    class_id: int
    title: str
    description: Optional[str] = None
    due_date: Optional[str] = None
    min_questions: int = 10
    max_attempts: int = 1
    show_hints: bool = True
    show_lessons: bool = True
    micro_topic_id: Optional[int] = None
    nano_topic_ids: Optional[List[int]] = None
    difficulty_preference: str = "mixed"
    count_skips: bool = True
    custom_questions: Optional[List[Dict]] = None

class QuestionAnswer(BaseModel):
    question: str
    answer: str
    nano_topic: str
    hint_used: bool = False
    lesson_viewed: bool = False

class FeedbackCreate(BaseModel):
    feedback_text: str
    rating: Optional[int] = None
    context: Optional[str] = None

class CustomQuestionCreate(BaseModel):
    question_text: str
    options: Optional[List[str]] = None
    correct_answer: str
    difficulty: str = "intermediate"
    style: str = "mcq"
    nano_topic_id: Optional[int] = None

class AnnouncementCreate(BaseModel):
    class_id: int
    content: str

# Utility functions
def get_db_connection():
    """Get database connection"""
    return sqlite3.connect(DATABASE_PATH)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token (simplified for this example)"""
    # In production, implement proper JWT verification
    token = credentials.credentials
    # For now, just check if token exists and is not empty
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from a token"""
    token = credentials.credentials
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    token_data = c.execute(
        "SELECT user_id, expires_at FROM auth_tokens WHERE token = ?",
        (token,)
    ).fetchone()
    
    if not token_data or datetime.fromisoformat(token_data["expires_at"]) < datetime.now():
        conn.close()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    
    user_id = token_data["user_id"]
    
    user = c.execute(
        "SELECT id, username, role, link_code FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    
    conn.close()
    
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "link_code": user["link_code"]
    }

# Authentication endpoints
@app.post("/auth/register")
async def register(user: UserCreate):
    """Register a new user"""
    # This function is mostly correct, no major changes needed.
    # The original logic for registration is sound.
    conn = get_db_connection()
    c = conn.cursor()
    
    link_code = secrets.token_hex(3).upper() if user.role == "student" else None
    
    try:
        c.execute(
            "INSERT INTO users (username, password, role, link_code, created_at) VALUES (?, ?, ?, ?, ?)",
            (user.username, hash_password(user.password), user.role, link_code, datetime.now().isoformat())
        )
        conn.commit()
        user_id = c.lastrowid
        
        # We don't generate a token on register, user must log in.
        return {
            "message": "User registered successfully",
            "user_id": user_id,
            "link_code": link_code
        }
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")
    finally:
        conn.close()

@app.post("/auth/login")
async def login(user: UserLogin):
    """Login user and return a token"""
    conn = get_db_connection()
    # Set row_factory to access columns by name
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    db_user = c.execute(
        "SELECT id, role, link_code FROM users WHERE username = ? AND password = ?",
        (user.username, hash_password(user.password))
    ).fetchone()
    
    if not db_user:
        conn.close()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    # Create a simple token and store it
    token = secrets.token_hex(16)
    now = datetime.now()
    expires = now + timedelta(days=7)
    c.execute(
        "INSERT INTO auth_tokens (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (token, db_user["id"], now.isoformat(), expires.isoformat())
    )
    conn.commit()
    conn.close()
    
    return {
        "token": token,
        "user_id": db_user["id"],
        "role": db_user["role"],
        "link_code": db_user["link_code"]
    }

# In main.py, add this new endpoint

@app.get("/auth/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """
    Validates a token and returns the current user's information.
    This is used by the frontend to restore a session on page refresh.
    """
    # The get_current_user dependency already gives us id, username, and role.
    # We just need to add the link_code for students.
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    user_info = dict(current_user) # Make a mutable copy

    if user_info["role"] == "student":
        link_code_result = conn.execute(
            "SELECT link_code FROM users WHERE id = ?",
            (user_info["id"],)
        ).fetchone()
        user_info["link_code"] = link_code_result["link_code"] if link_code_result else None

    conn.close()
    return user_info

@app.post("/auth/link-parent")
async def link_parent(link_data: LinkParent, current_user: dict = Depends(get_current_user)):
    """Link parent to student"""
    if current_user["role"] != "parent":
        raise HTTPException(status_code=403, detail="Only parents can link to students")
    
    # The rest of this function was already correct!
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("SELECT id FROM users WHERE role = 'student' AND link_code = ?", (link_data.link_code,))
    student = c.fetchone()
    
    if not student:
        raise HTTPException(status_code=404, detail="Invalid link code")
    
    try:
        c.execute(
            "INSERT INTO parent_child_links (parent_id, student_id, created_at) VALUES (?, ?, ?)",
            (current_user["id"], student[0], datetime.now().isoformat())
        )
        conn.commit()
        return {"message": "Successfully linked to student"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Already linked to this student")
    finally:
        conn.close()

# Quiz endpoints
@app.get("/quiz/nano-topics/{subject}")
async def get_nano_topics(subject: str, micro_topic: Optional[str] = None):
    """Get nano topics for a subject"""
    topics = load_nano_topics(subject, micro_topic)
    return {"nano_topics": topics}

@app.get("/quiz/questions/{nano_topic}")
async def get_topic_questions(nano_topic: str, current_user: dict = Depends(get_current_user)):
    """Get questions for a nano topic"""
    if current_user["role"] == "student":
        questions = get_unanswered_questions(current_user["id"], nano_topic)
    else:
        questions = get_questions(nano_topic)
    return {"questions": questions}


# In main.py, replace the ENTIRE submit_answer function with this one:

@app.get("/quiz/hint")
async def get_hint(question: str, nano_topic: str, assignment_id: Optional[int] = None, current_user: dict = Depends(get_current_user)):
    """Get hint for a question (handles both regular and custom questions)"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if this is from an assignment with custom questions
    if assignment_id:
        c.execute("SELECT custom_questions FROM assignments WHERE id = ?", (assignment_id,))
        assignment = c.fetchone()
        
        if assignment and assignment[0]:  # Has custom questions
            # For custom questions, generate a generic hint since we don't store hints
            hint = generate_hint(question, [], "See the answer choices for clues", nano_topic)
            conn.close()
            return {"hint": hint}
    
    # Regular question logic
    c.execute("""
        SELECT options, answer FROM questions q
        JOIN nano_topics n ON q.nano_topic_id = n.id
        WHERE q.question = ? AND n.name = ? AND q.is_approved = 1
    """, (question, nano_topic))
    
    result = c.fetchone()
    conn.close()
    
    if not result:
        # Fallback for custom questions or missing questions
        hint = generate_hint(question, [], "Think about the key concepts involved", nano_topic)
        return {"hint": hint}
    
    options = json.loads(result[0]) if result[0] else []
    answer = result[1]
    
    hint = generate_hint(question, options, answer, nano_topic)
    return {"hint": hint}

@app.get("/quiz/lesson")
async def get_mini_lesson(question: str, nano_topic: str, assignment_id: Optional[int] = None, current_user: dict = Depends(get_current_user)):
    """Get mini lesson for a topic (handles both regular and custom questions)"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if this is from an assignment with custom questions
    if assignment_id:
        c.execute("SELECT custom_questions FROM assignments WHERE id = ?", (assignment_id,))
        assignment = c.fetchone()
        
        if assignment and assignment[0]:  # Has custom questions
            # For custom questions, generate a generic lesson
            lesson = generate_mini_lesson(nano_topic, question, "General explanation")
            conn.close()
            return {"lesson": lesson}
    
    # Regular question logic
    c.execute("""
        SELECT answer FROM questions q
        JOIN nano_topics n ON q.nano_topic_id = n.id
        WHERE q.question = ? AND n.name = ? AND q.is_approved = 1
    """, (question, nano_topic))
    
    result = c.fetchone()
    conn.close()
    
    if not result:
        # Fallback for custom questions
        lesson = generate_mini_lesson(nano_topic, question, "General explanation")
        return {"lesson": lesson}
    
    lesson = generate_mini_lesson(nano_topic, question, result[0])
    return {"lesson": lesson}

@app.post("/quiz/submit-answer")
async def submit_answer(answer_data: QuestionAnswer, assignment_id: Optional[int] = None, current_user: dict = Depends(get_current_user)):
    """Submit answer and update BKT model (handles both regular and custom questions)"""
    print("\n--- DEBUG: Entering /quiz/submit-answer ---")
    conn = None
    try:
        if current_user.get("role") != "student":
            print("--- DEBUG: FAILED - User is not a student ---")
            raise HTTPException(status_code=403, detail="Only students can submit answers")

        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # First, try to find the question in regular questions table
        nano_topic_result = c.execute("SELECT id FROM nano_topics WHERE name = ?", (answer_data.nano_topic,)).fetchone()
        
        correct_answer = None
        is_correct = False
        
        if nano_topic_result:
            nano_topic_id = nano_topic_result["id"]
            
            # Try regular questions first
            question_result = c.execute(
                "SELECT answer FROM questions WHERE nano_topic_id = ? AND question = ? AND is_approved = 1",
                (nano_topic_id, answer_data.question)
            ).fetchone()
            
            if question_result:
                correct_answer = question_result["answer"]
            else:
                # Try custom questions if assignment_id is provided
                if assignment_id:
                    custom_question_result = c.execute("""
                        SELECT tcq.correct_answer 
                        FROM teacher_custom_questions tcq
                        WHERE tcq.question_text = ? AND tcq.nano_topic_id = ?
                    """, (answer_data.question, nano_topic_id)).fetchone()
                    
                    if custom_question_result:
                        correct_answer = custom_question_result["correct_answer"]
        
        if not correct_answer:
            # If we still can't find it, try to find any custom question with this text
            custom_result = c.execute(
                "SELECT correct_answer FROM teacher_custom_questions WHERE question_text = ?",
                (answer_data.question,)
            ).fetchone()
            
            if custom_result:
                correct_answer = custom_result["correct_answer"]
                # Use a default nano_topic_id or create one for custom questions
                if not nano_topic_result:
                    nano_topic_id = 1  # Default fallback
            else:
                print("--- DEBUG: FAILED - Question not found in any table ---")
                raise HTTPException(status_code=404, detail="Question not found")

        is_correct = answer_data.answer.strip().lower() == correct_answer.strip().lower()
        print(f"--- DEBUG: User's answer is_correct: {is_correct} ---")

        # Update BKT model
        bkt = BKT()
        last_result = c.execute(
            "SELECT p_learned FROM student_results WHERE student_id = ? AND nano_topic_id = ? ORDER BY timestamp DESC LIMIT 1",
            (current_user["id"], nano_topic_id)
        ).fetchone()
        
        if last_result:
            bkt.p_learned = last_result["p_learned"]

        new_p_learned = bkt.update(is_correct)

        # Save result
        c.execute("""
            INSERT INTO student_results 
            (student_id, nano_topic_id, question, is_correct, p_learned, hint_used, lesson_viewed, attempt_completed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (current_user["id"], nano_topic_id, answer_data.question, is_correct, new_p_learned, 
              answer_data.hint_used, answer_data.lesson_viewed, True))
        conn.commit()

        response = {
            "is_correct": is_correct,
            "correct_answer": correct_answer,
            "p_learned": new_p_learned
        }

        if not is_correct:
            try:
                explanation = generate_explanation(answer_data.question, answer_data.answer, correct_answer)
                response["explanation"] = explanation
            except Exception as e:
                response["explanation"] = "Sorry, an explanation could not be generated at this time."
        
        return response

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        import traceback
        print("--- DEBUG: FAILED - An unexpected error occurred! ---")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="An internal error occurred while submitting the answer.")
    finally:
        if conn:
            conn.close()


@app.get("/quiz/next-topic")
async def get_next_topic(current_user: dict = Depends(get_current_user)):
    """Get next topic based on BKT scores"""
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can get next topic")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get latest p_learned for each nano topic
    c.execute("""
        SELECT n.name, sr.p_learned
        FROM (
            SELECT nano_topic_id, MAX(timestamp) as latest_timestamp
            FROM student_results
            WHERE student_id = ?
            GROUP BY nano_topic_id
        ) latest
        JOIN student_results sr ON sr.nano_topic_id = latest.nano_topic_id 
                                AND sr.timestamp = latest.latest_timestamp
                                AND sr.student_id = ?
        JOIN nano_topics n ON n.id = sr.nano_topic_id
    """, (current_user["id"], current_user["id"]))
    
    results = c.fetchall()
    conn.close()
    
    if not results:
        # Return first available topic if no progress yet
        topics = load_nano_topics("Numbers and the Number System")
        return {"next_topic": topics[0]["name"] if topics else None}
    
    # Create BKT dictionary
    bkt_dict = {}
    for topic_name, p_learned in results:
        bkt = BKT()
        bkt.p_learned = p_learned
        bkt_dict[topic_name] = bkt
    
    next_topic = select_next_module(bkt_dict)
    return {"next_topic": next_topic}

# Teacher/Class Management endpoints
@app.post("/classes/create")
async def create_class(class_data: ClassCreate, current_user: dict = Depends(get_current_user)):
    """Create a new class"""
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can create classes")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    class_code = secrets.token_hex(4).upper()
    
    try:
        c.execute("""
            INSERT INTO classes (teacher_id, name, description, class_code, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (current_user["id"], class_data.name, class_data.description, 
              class_code, datetime.now().isoformat()))
        
        conn.commit()
        class_id = c.lastrowid
        
        return {
            "class_id": class_id,
            "class_code": class_code,
            "message": "Class created successfully"
        }
    finally:
        conn.close()

@app.post("/classes/join")
async def join_class(join_data: JoinClass, current_user: dict = Depends(get_current_user)):
    """Join a class"""
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can join classes")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if class exists
    c.execute("SELECT id FROM classes WHERE class_code = ?", (join_data.class_code,))
    class_result = c.fetchone()
    
    if not class_result:
        raise HTTPException(status_code=404, detail="Invalid class code")
    
    class_id = class_result[0]
    
    try:
        c.execute("""
            INSERT INTO student_classes (student_id, class_id, joined_at)
            VALUES (?, ?, ?)
        """, (current_user["id"], class_id, datetime.now().isoformat()))
        
        conn.commit()
        return {"message": "Successfully joined class"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Already enrolled in this class")
    finally:
        conn.close()

# FIXED: This function now standardizes the response for all roles.
@app.get("/classes/my-classes")
async def get_my_classes(current_user: dict = Depends(get_current_user)):
    """
    Get classes for the current user.
    The response is standardized to include a 'date' key for both roles.
    - For teachers, 'date' is the class creation date.
    - For students, 'date' is the date they joined the class.
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    classes = []
    
    if current_user["role"] == "teacher":
        # Query for classes and count of students for each class.
        c.execute("""
            SELECT 
                c.id, c.name, c.description, c.class_code, c.created_at,
                COUNT(sc.student_id) as student_count
            FROM classes c
            LEFT JOIN student_classes sc ON c.id = sc.class_id
            WHERE c.teacher_id = ?
            GROUP BY c.id
            ORDER BY c.created_at DESC
        """, (current_user["id"],))
        
        rows = c.fetchall()
        for row in rows:
            class_data = dict(row)
            # Standardize the date key for the frontend.
            class_data['date'] = class_data.pop('created_at')
            classes.append(class_data)

    elif current_user["role"] == "student":
        # Query for classes the student is enrolled in.
        c.execute("""
            SELECT c.id, c.name, c.description, c.class_code, sc.joined_at
            FROM classes c
            JOIN student_classes sc ON c.id = sc.class_id
            WHERE sc.student_id = ?
            ORDER BY sc.joined_at DESC
        """, (current_user["id"],))
        
        rows = c.fetchall()
        for row in rows:
            class_data = dict(row)
            # Standardize the date key for the frontend.
            class_data['date'] = class_data.pop('joined_at')
            classes.append(class_data)

    conn.close()
    return {"classes": classes}


@app.post("/assignments/create")
async def create_assignment(assignment: AssignmentCreate, current_user: dict = Depends(get_current_user)):
    """Create a new assignment"""
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can create assignments")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Verify teacher owns the class
    c.execute("SELECT teacher_id FROM classes WHERE id = ?", (assignment.class_id,))
    class_result = c.fetchone()
    
    if not class_result or class_result[0] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized for this class")
    
    try:
        c.execute("""
            INSERT INTO assignments 
            (class_id, title, description, due_date, min_questions, max_attempts, 
             show_hints, show_lessons, micro_topic_id, nano_topic_ids, 
             difficulty_preference, count_skips, custom_questions, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            assignment.class_id, assignment.title, assignment.description,
            assignment.due_date, assignment.min_questions, assignment.max_attempts,
            assignment.show_hints, assignment.show_lessons, assignment.micro_topic_id,
            json.dumps(assignment.nano_topic_ids) if assignment.nano_topic_ids else None,
            assignment.difficulty_preference, assignment.count_skips,
            json.dumps(assignment.custom_questions) if assignment.custom_questions else None,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        assignment_id = c.lastrowid
        
        return {
            "assignment_id": assignment_id,
            "message": "Assignment created successfully"
        }
    finally:
        conn.close()

@app.get("/assignments/class/{class_id}")
async def get_class_assignments(class_id: int, current_user: dict = Depends(get_current_user)):
    """Get assignments for a class"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check access
    if current_user["role"] == "teacher":
        c.execute("SELECT teacher_id FROM classes WHERE id = ?", (class_id,))
        teacher_result = c.fetchone()
        if not teacher_result or teacher_result[0] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not authorized")
    elif current_user["role"] == "student":
        c.execute("SELECT student_id FROM student_classes WHERE class_id = ? AND student_id = ?", 
                 (class_id, current_user["id"]))
        if not c.fetchone():
            raise HTTPException(status_code=403, detail="Not enrolled in this class")
    
    c.execute("""
        SELECT id, title, description, due_date, min_questions, max_attempts,
               show_hints, show_lessons, created_at
        FROM assignments
        WHERE class_id = ?
        ORDER BY created_at DESC
    """, (class_id,))
    
    assignments = [
        {
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "due_date": row[3],
            "min_questions": row[4],
            "max_attempts": row[5],
            "show_hints": row[6],
            "show_lessons": row[7],
            "created_at": row[8]
        }
        for row in c.fetchall()
    ]
    
    conn.close()
    return {"assignments": assignments}

# Analytics endpoints
# REPLACE the existing /analytics/student-progress endpoint in main.py with this updated version:

@app.get("/analytics/student-progress")
async def get_student_progress(current_user: dict = Depends(get_current_user)):
    """Get student progress analytics with complete KPI data"""
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can view their progress")
    
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get user account creation date
    user_data = c.execute(
        "SELECT created_at FROM users WHERE id = ?", 
        (current_user["id"],)
    ).fetchone()
    
    account_created = user_data["created_at"] if user_data else datetime.now().isoformat()
    
    # Get overall statistics including hints and lessons
    c.execute("""
        SELECT 
            COUNT(*) as total_questions,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct_answers,
            AVG(p_learned) as avg_mastery,
            COUNT(DISTINCT nano_topic_id) as topics_attempted,
            SUM(CASE WHEN hint_used THEN 1 ELSE 0 END) as hints_used,
            SUM(CASE WHEN lesson_viewed THEN 1 ELSE 0 END) as lessons_viewed,
            COUNT(DISTINCT DATE(timestamp)) as active_days
        FROM student_results
        WHERE student_id = ?
    """, (current_user["id"],))
    
    stats = c.fetchone()
    
    # Get topic-wise progress
    c.execute("""
        SELECT 
            n.name,
            COUNT(*) as questions_answered,
            SUM(CASE WHEN sr.is_correct THEN 1 ELSE 0 END) as correct_answers,
            MAX(sr.p_learned) as mastery_level,
            MAX(sr.timestamp) as last_attempt
        FROM student_results sr
        JOIN nano_topics n ON sr.nano_topic_id = n.id
        WHERE sr.student_id = ?
        GROUP BY n.name
        ORDER BY mastery_level ASC
    """, (current_user["id"],))
    
    topic_progress = [
        {
            "topic": row["name"],
            "questions_answered": row["questions_answered"],
            "correct_answers": row["correct_answers"],
            "accuracy": (row["correct_answers"] / row["questions_answered"]) * 100 if row["questions_answered"] > 0 else 0,
            "mastery_level": row["mastery_level"] * 100 if row["mastery_level"] else 0,
            "last_attempt": row["last_attempt"]
        }
        for row in c.fetchall()
    ]
    
    conn.close()
    
    # Calculate consistency based on actual account creation
    if stats and stats["active_days"]:
        created_date = datetime.fromisoformat(account_created)
        days_since_creation = (datetime.now() - created_date).days + 1
        consistency = (stats["active_days"] / days_since_creation * 100) if days_since_creation > 0 else 0
    else:
        consistency = 0
    
    return {
        "overall_stats": {
            "total_questions": stats["total_questions"] or 0,
            "correct_answers": stats["correct_answers"] or 0,
            "accuracy": (stats["correct_answers"] / stats["total_questions"]) * 100 if stats["total_questions"] and stats["total_questions"] > 0 else 0,
            "avg_mastery": stats["avg_mastery"] * 100 if stats["avg_mastery"] else 0,
            "topics_attempted": stats["topics_attempted"] or 0,
            "hints_used": stats["hints_used"] or 0,
            "lessons_viewed": stats["lessons_viewed"] or 0,
            "active_days": stats["active_days"] or 0,
            "consistency": consistency
        },
        "topic_progress": topic_progress,
        "account_created": account_created
    }

@app.get("/analytics/parent-report")
async def get_parent_report(current_user: dict = Depends(get_current_user)):
    """Get parent report for linked students"""
    if current_user["role"] != "parent":
        raise HTTPException(status_code=403, detail="Only parents can view reports")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get linked students
    c.execute("""
        SELECT u.id, u.username
        FROM users u
        JOIN parent_child_links pcl ON u.id = pcl.student_id
        WHERE pcl.parent_id = ?
    """, (current_user["id"],))
    
    students = c.fetchall()
    reports = []
    
    for student_id, student_name in students:
        # Get student progress
        c.execute("""
            SELECT 
                n.name,
                sr.is_correct,
                sr.p_learned,
                sr.timestamp
            FROM student_results sr
            JOIN nano_topics n ON sr.nano_topic_id = n.id
            WHERE sr.student_id = ? AND sr.timestamp >= date('now', '-7 days')
            ORDER BY sr.timestamp DESC
        """, (student_id,))
        
        recent_results = c.fetchall()
        
        # Analyze strengths and weaknesses
        topic_performance = {}
        for topic, is_correct, p_learned, timestamp in recent_results:
            if topic not in topic_performance:
                topic_performance[topic] = {"correct": 0, "total": 0, "mastery": p_learned}
            topic_performance[topic]["total"] += 1
            if is_correct:
                topic_performance[topic]["correct"] += 1
        
        strengths = [topic for topic, perf in topic_performance.items() 
                    if perf["correct"] / perf["total"] >= 0.8]
        weaknesses = [{"topic": topic, "mastery": perf["mastery"]} 
                     for topic, perf in topic_performance.items() 
                     if perf["correct"] / perf["total"] < 0.6]
        
        # Generate actionable steps for weak topics
        actionable_steps = []
        for weakness in weaknesses[:3]:  # Top 3 weaknesses
            steps = generate_actionable_steps(weakness["topic"], weakness["mastery"])
            actionable_steps.append({
                "topic": weakness["topic"],
                "steps": steps
            })
        
        reports.append({
            "student_name": student_name,
            "strengths": strengths,
            "weaknesses": [w["topic"] for w in weaknesses],
            "actionable_steps": actionable_steps,
            "total_questions": len(recent_results),
            "accuracy": sum(1 for _, is_correct, _, _ in recent_results if is_correct) / len(recent_results) * 100 if recent_results else 0
        })
    
    conn.close()
    return {"reports": reports}

# Feedback endpoints
@app.post("/feedback/submit")
async def submit_feedback(feedback: FeedbackCreate, current_user: dict = Depends(get_current_user)):
    """Submit user feedback"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute("""
            INSERT INTO feedback (user_id, feedback_text, rating, context, role, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (current_user["id"], feedback.feedback_text, feedback.rating, 
              feedback.context, current_user["role"], datetime.now().isoformat()))
        
        conn.commit()
        return {"message": "Feedback submitted successfully"}
    finally:
        conn.close()

# Admin endpoints
@app.post("/admin/run-supervisor")
async def run_supervisor(background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    """Run the supervisor AI to validate questions"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can run supervisor")
    
    background_tasks.add_task(run_full_database_check)
    return {"message": "Supervisor validation started in background"}

@app.get("/admin/question-stats")
async def get_question_stats(current_user: dict = Depends(get_current_user)):
    """Get question validation statistics"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view question stats")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("""
        SELECT 
            COUNT(*) as total_questions,
            SUM(CASE WHEN is_approved = 1 THEN 1 ELSE 0 END) as approved_questions,
            SUM(CASE WHEN is_approved = 0 THEN 1 ELSE 0 END) as rejected_questions,
            SUM(CASE WHEN is_approved IS NULL THEN 1 ELSE 0 END) as pending_questions
        FROM questions
    """)
    
    stats = c.fetchone()
    conn.close()
    
    return {
        "total_questions": stats[0],
        "approved_questions": stats[1],
        "rejected_questions": stats[2],
        "pending_questions": stats[3]
    }

@app.get("/admin/rejected-questions")
async def get_rejected_questions(current_user: dict = Depends(get_current_user)):
    """Get rejected questions with reasons"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view rejected questions")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("""
        SELECT q.id, q.question, q.answer, q.rejection_reason, n.name as nano_topic
        FROM questions q
        JOIN nano_topics n ON q.nano_topic_id = n.id
        WHERE q.is_approved = 0 AND q.rejection_reason IS NOT NULL
        ORDER BY q.id DESC
        LIMIT 50
    """)
    
    rejected_questions = [
        {
            "id": row[0],
            "question": row[1],
            "answer": row[2],
            "rejection_reason": row[3],
            "nano_topic": row[4]
        }
        for row in c.fetchall()
    ]
    
    conn.close()
    return {"rejected_questions": rejected_questions}

# Custom Questions for Teachers
@app.post("/teacher/custom-questions")
async def create_custom_question(question: CustomQuestionCreate, current_user: dict = Depends(get_current_user)):
    """Create a custom question for teachers"""
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can create custom questions")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute("""
            INSERT INTO teacher_custom_questions 
            (teacher_id, question_text, options, correct_answer, difficulty, style, nano_topic_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            current_user["id"], question.question_text, 
            json.dumps(question.options) if question.options else None,
            question.correct_answer, question.difficulty, question.style,
            question.nano_topic_id, datetime.now().isoformat()
        ))
        
        conn.commit()
        question_id = c.lastrowid
        
        return {
            "question_id": question_id,
            "message": "Custom question created successfully"
        }
    finally:
        conn.close()

@app.get("/teacher/custom-questions")
async def get_custom_questions(current_user: dict = Depends(get_current_user)):
    """Get custom questions created by teacher"""
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can view custom questions")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("""
        SELECT tcq.id, tcq.question_text, tcq.options, tcq.correct_answer, 
               tcq.difficulty, tcq.style, n.name as nano_topic, tcq.created_at
        FROM teacher_custom_questions tcq
        LEFT JOIN nano_topics n ON tcq.nano_topic_id = n.id
        WHERE tcq.teacher_id = ?
        ORDER BY tcq.created_at DESC
    """, (current_user["id"],))
    
    questions = [
        {
            "id": row[0],
            "question_text": row[1],
            "options": json.loads(row[2]) if row[2] else [],
            "correct_answer": row[3],
            "difficulty": row[4],
            "style": row[5],
            "nano_topic": row[6],
            "created_at": row[7]
        }
        for row in c.fetchall()
    ]
    
    conn.close()
    return {"custom_questions": questions}

@app.delete("/teacher/custom-questions/{question_id}")
async def delete_custom_question(question_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a custom question"""
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can delete custom questions")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Verify ownership
    c.execute("SELECT teacher_id FROM teacher_custom_questions WHERE id = ?", (question_id,))
    result = c.fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Question not found")
    
    if result[0] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this question")
    
    c.execute("DELETE FROM teacher_custom_questions WHERE id = ?", (question_id,))
    conn.commit()
    conn.close()
    
    return {"message": "Question deleted successfully"}

# Announcements
@app.post("/announcements/create")
async def create_announcement(announcement: AnnouncementCreate, current_user: dict = Depends(get_current_user)):
    """Create a class announcement"""
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can create announcements")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Verify teacher owns the class
    c.execute("SELECT teacher_id FROM classes WHERE id = ?", (announcement.class_id,))
    class_result = c.fetchone()
    
    if not class_result or class_result[0] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized for this class")
    
    try:
        c.execute("""
            INSERT INTO announcements (class_id, teacher_id, content, created_at)
            VALUES (?, ?, ?, ?)
        """, (announcement.class_id, current_user["id"], announcement.content, datetime.now().isoformat()))
        
        conn.commit()
        announcement_id = c.lastrowid
        
        return {
            "announcement_id": announcement_id,
            "message": "Announcement created successfully"
        }
    finally:
        conn.close()

@app.get("/announcements/class/{class_id}")
async def get_class_announcements(class_id: int, current_user: dict = Depends(get_current_user)):
    """Get announcements for a class"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check access
    if current_user["role"] == "teacher":
        c.execute("SELECT teacher_id FROM classes WHERE id = ?", (class_id,))
        teacher_result = c.fetchone()
        if not teacher_result or teacher_result[0] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not authorized")
    elif current_user["role"] == "student":
        c.execute("SELECT student_id FROM student_classes WHERE class_id = ? AND student_id = ?", 
                 (class_id, current_user["id"]))
        if not c.fetchone():
            raise HTTPException(status_code=403, detail="Not enrolled in this class")
    
    c.execute("""
        SELECT a.id, a.content, a.created_at, u.username as teacher_name
        FROM announcements a
        JOIN users u ON a.teacher_id = u.id
        WHERE a.class_id = ?
        ORDER BY a.created_at DESC
    """, (class_id,))
    
    announcements = [
        {
            "id": row[0],
            "content": row[1],
            "created_at": row[2],
            "teacher_name": row[3]
        }
        for row in c.fetchall()
    ]
    
    conn.close()
    return {"announcements": announcements}

# Assignment Submissions
@app.post("/assignments/{assignment_id}/submit")
async def submit_assignment(assignment_id: int, current_user: dict = Depends(get_current_user)):
    """Submit/start an assignment"""
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can submit assignments")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Verify student is enrolled in the class
    c.execute("""
        SELECT a.class_id, a.max_attempts
        FROM assignments a
        WHERE a.id = ?
    """, (assignment_id,))
    
    assignment_result = c.fetchone()
    if not assignment_result:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    class_id, max_attempts = assignment_result
    
    c.execute("SELECT student_id FROM student_classes WHERE class_id = ? AND student_id = ?", 
             (class_id, current_user["id"]))
    if not c.fetchone():
        raise HTTPException(status_code=403, detail="Not enrolled in this class")
    
    # Check existing attempts
    c.execute("""
        SELECT COUNT(*) FROM assignment_submissions 
        WHERE assignment_id = ? AND student_id = ?
    """, (assignment_id, current_user["id"]))
    
    current_attempts = c.fetchone()[0]
    if current_attempts >= max_attempts:
        raise HTTPException(status_code=400, detail="Maximum attempts exceeded")
    
    # Create new submission
    attempt_number = current_attempts + 1
    
    try:
        c.execute("""
            INSERT INTO assignment_submissions 
            (assignment_id, student_id, attempt_number, started_at)
            VALUES (?, ?, ?, ?)
        """, (assignment_id, current_user["id"], attempt_number, datetime.now().isoformat()))
        
        conn.commit()
        submission_id = c.lastrowid
        
        return {
            "submission_id": submission_id,
            "attempt_number": attempt_number,
            "message": "Assignment started successfully"
        }
    finally:
        conn.close()

class AssignmentComplete(BaseModel):
    score: float
    total_questions: int
    correct_answers: int
    skipped_questions: int = 0

@app.put("/assignments/submissions/{submission_id}/complete")
async def complete_assignment(
    submission_id: int,
    assignment_data: AssignmentComplete,
    current_user: dict = Depends(get_current_user)
):
    """Complete an assignment submission"""
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can complete assignments")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Verify ownership
    c.execute("SELECT student_id FROM assignment_submissions WHERE id = ?", (submission_id,))
    result = c.fetchone()
    
    if not result or result[0] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        c.execute(""" 
            UPDATE assignment_submissions 
            SET completed_at = ?, score = ?, total_questions = ?, 
                correct_answers = ?, skipped_questions = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), assignment_data.score, assignment_data.total_questions, 
              assignment_data.correct_answers, assignment_data.skipped_questions, submission_id))
        
        conn.commit()
        return {"message": "Assignment completed successfully"}
    finally:
        conn.close()

@app.get("/assignments/{assignment_id}/submissions")
async def get_assignment_submissions(assignment_id: int, current_user: dict = Depends(get_current_user)):
    """Get submissions for an assignment"""
    conn = get_db_connection()
    c = conn.cursor()
    
    if current_user["role"] == "teacher":
        # Verify teacher owns the assignment
        c.execute("""
            SELECT c.teacher_id FROM assignments a
            JOIN classes c ON a.class_id = c.id
            WHERE a.id = ?
        """, (assignment_id,))
        teacher_result = c.fetchone()
        
        if not teacher_result or teacher_result[0] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Get all submissions for this assignment
        c.execute("""
            SELECT asub.id, asub.student_id, u.username, asub.attempt_number,
                   asub.score, asub.total_questions, asub.correct_answers,
                   asub.started_at, asub.completed_at, asub.skipped_questions
            FROM assignment_submissions asub
            JOIN users u ON asub.student_id = u.id
            WHERE asub.assignment_id = ?
            ORDER BY u.username, asub.attempt_number
        """, (assignment_id,))
        
        submissions = [
            {
                "id": row[0],
                "student_id": row[1],
                "student_name": row[2],
                "attempt_number": row[3],
                "score": row[4],
                "total_questions": row[5],
                "correct_answers": row[6],
                "started_at": row[7],
                "completed_at": row[8],
                "skipped_questions": row[9]
            }
            for row in c.fetchall()
        ]
        
    elif current_user["role"] == "student":
        # Get only current student's submissions
        c.execute("""
            SELECT id, attempt_number, score, total_questions, correct_answers,
                   started_at, completed_at, skipped_questions
            FROM assignment_submissions
            WHERE assignment_id = ? AND student_id = ?
            ORDER BY attempt_number
        """, (assignment_id, current_user["id"]))
        
        submissions = [
            {
                "id": row[0],
                "attempt_number": row[1],
                "score": row[2],
                "total_questions": row[3],
                "correct_answers": row[4],
                "started_at": row[5],
                "completed_at": row[6],
                "skipped_questions": row[7]
            }
            for row in c.fetchall()
        ]
    else:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    conn.close()
    return {"submissions": submissions}

# Additional utility endpoints
@app.get("/topics/structure")
async def get_curriculum_structure():
    """Get the complete curriculum structure"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("""
        SELECT t.id, t.name, t.description,
               s.id, s.name, s.description,
               m.id, m.name, m.description,
               n.id, n.name, n.keywords
        FROM topics t
        LEFT JOIN subtopics s ON t.id = s.topic_id
        LEFT JOIN micro_topics m ON s.id = m.subtopic_id
        LEFT JOIN nano_topics n ON m.id = n.micro_topic_id
        ORDER BY t.id, s.id, m.id, n.id
    """)
    
    results = c.fetchall()
    conn.close()
    
    # Structure the data
    curriculum = {}
    
    for row in results:
        topic_id, topic_name, topic_desc = row[0], row[1], row[2]
        subtopic_id, subtopic_name, subtopic_desc = row[3], row[4], row[5]
        micro_id, micro_name, micro_desc = row[6], row[7], row[8]
        nano_id, nano_name, nano_keywords = row[9], row[10], row[11]
        
        if topic_id not in curriculum:
            curriculum[topic_id] = {
                "id": topic_id,
                "name": topic_name,
                "description": topic_desc,
                "subtopics": {}
            }
        
        if subtopic_id and subtopic_id not in curriculum[topic_id]["subtopics"]:
            curriculum[topic_id]["subtopics"][subtopic_id] = {
                "id": subtopic_id,
                "name": subtopic_name,
                "description": subtopic_desc,
                "micro_topics": {}
            }
        
        if micro_id and micro_id not in curriculum[topic_id]["subtopics"][subtopic_id]["micro_topics"]:
            curriculum[topic_id]["subtopics"][subtopic_id]["micro_topics"][micro_id] = {
                "id": micro_id,
                "name": micro_name,
                "description": micro_desc,
                "nano_topics": {}
            }
        
        if nano_id:
            curriculum[topic_id]["subtopics"][subtopic_id]["micro_topics"][micro_id]["nano_topics"][nano_id] = {
                "id": nano_id,
                "name": nano_name,
                "keywords": nano_keywords.split(",") if nano_keywords else []
            }
    
    # Convert to list format
    structured_curriculum = []
    for topic in curriculum.values():
        topic["subtopics"] = list(topic["subtopics"].values())
        for subtopic in topic["subtopics"]:
            subtopic["micro_topics"] = list(subtopic["micro_topics"].values())
            for micro_topic in subtopic["micro_topics"]:
                micro_topic["nano_topics"] = list(micro_topic["nano_topics"].values())
        structured_curriculum.append(topic)
    
    return {"curriculum": structured_curriculum}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Educational Platform API",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

# Error handlers
# CORRECTED Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

# Add this new endpoint in main.py

@app.get("/classes/{class_id}/students")
async def get_class_students(class_id: int, current_user: dict = Depends(get_current_user)):
    """Get all students enrolled in a specific class."""
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can view class students")

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Verify teacher owns the class
    owner = c.execute("SELECT teacher_id FROM classes WHERE id = ?", (class_id,)).fetchone()
    if not owner or owner["teacher_id"] != current_user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Not authorized to view this class")

    # Get students in the class
    c.execute("""
        SELECT
            u.id,
            u.username,
            sc.joined_at
        FROM users u
        JOIN student_classes sc ON u.id = sc.student_id
        WHERE sc.class_id = ?
        ORDER BY u.username
    """, (class_id,))

    students = [dict(row) for row in c.fetchall()]
    conn.close()

    return {"students": students}


@app.get("/analytics/class/{class_id}")
async def get_class_analytics(class_id: int, current_user: dict = Depends(get_current_user)):
    """Get aggregated analytics for all students in a class."""
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can view class reports")

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Verify teacher owns the class
    owner = c.execute("SELECT teacher_id FROM classes WHERE id = ?", (class_id,)).fetchone()
    if not owner or owner["teacher_id"] != current_user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Not authorized to view this class")

    # Fetch all results for all students in the class
    c.execute("""
        SELECT
            u.id as student_id,
            u.username,
            sr.p_learned,
            sr.is_correct,
            sr.timestamp,
            n.name as topic_name
        FROM student_results sr
        JOIN users u ON sr.student_id = u.id
        JOIN student_classes sc ON u.id = sc.student_id
        JOIN nano_topics n ON sr.nano_topic_id = n.id
        WHERE sc.class_id = ?
    """, (class_id,))
    
    all_results = c.fetchall()
    conn.close()

    if not all_results:
        return {"students": [], "topics": [], "timeline": []}

    # Process data with Pandas
    df = pd.DataFrame([dict(row) for row in all_results])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['date'] = df['timestamp'].dt.date

    # 1. Per-student performance
    student_performance = df.groupby('student_id').agg(
        username=('username', 'first'),
        total_questions=('student_id', 'size'),
        correct_answers=('is_correct', lambda x: x.sum()),
        avg_mastery=('p_learned', 'mean'),
        active_days=('date', 'nunique')
    ).reset_index()
    student_performance['accuracy'] = (student_performance['correct_answers'] / student_performance['total_questions']) * 100
    student_performance['avg_mastery'] *= 100 # Convert to percentage

    # 2. Per-topic performance
    topic_performance = df.groupby('topic_name').agg(
        total_attempts=('topic_name', 'size'),
        correct_answers=('is_correct', lambda x: x.sum()),
        avg_mastery=('p_learned', 'mean')
    ).reset_index()
    topic_performance['accuracy'] = (topic_performance['correct_answers'] / topic_performance['total_attempts']) * 100
    topic_performance['avg_mastery'] *= 100

    # 3. Timeline
    timeline = df.groupby('date').agg(
        questions_answered=('date', 'size'),
        avg_mastery=('p_learned', 'mean')
    ).reset_index()
    timeline['avg_mastery'] *= 100
    
    return {
        "students": student_performance.to_dict('records'),
        "topics": topic_performance.to_dict('records'),
        "timeline": timeline.to_dict('records')
    }

@app.get("/assignments/{assignment_id}/questions")
async def get_assignment_questions(assignment_id: int, current_user: dict = Depends(get_current_user)):
    """Get questions for a specific assignment (handles both AI and custom questions)"""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get assignment details
    c.execute("""
        SELECT a.custom_questions, a.micro_topic_id, a.nano_topic_ids, a.class_id
        FROM assignments a
        WHERE a.id = ?
    """, (assignment_id,))
    
    assignment = c.fetchone()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    # Check access
    if current_user["role"] == "student":
        c.execute("SELECT student_id FROM student_classes WHERE class_id = ? AND student_id = ?", 
                 (assignment["class_id"], current_user["id"]))
        if not c.fetchone():
            raise HTTPException(status_code=403, detail="Not enrolled in this class")
    elif current_user["role"] == "teacher":
        c.execute("SELECT teacher_id FROM classes WHERE id = ?", (assignment["class_id"],))
        class_result = c.fetchone()
        if not class_result or class_result["teacher_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    questions = []
    
    # Handle custom questions
    if assignment["custom_questions"]:
        custom_question_data = json.loads(assignment["custom_questions"])
        custom_question_ids = [q["id"] for q in custom_question_data]
        
        if custom_question_ids:
            placeholders = ",".join("?" * len(custom_question_ids))
            c.execute(f"""
                SELECT tcq.question_text as question, tcq.options, tcq.correct_answer as answer, 
                       tcq.style, n.name as nano_topic
                FROM teacher_custom_questions tcq
                LEFT JOIN nano_topics n ON tcq.nano_topic_id = n.id
                WHERE tcq.id IN ({placeholders})
            """, custom_question_ids)
            
            for row in c.fetchall():
                questions.append({
                    "question": row["question"],
                    "options": json.loads(row["options"]) if row["options"] else [],
                    "answer": row["answer"],
                    "style": row["style"],
                    "nano_topic": row["nano_topic"] or "Custom Question"
                })
    
    # Handle AI-generated questions
    if assignment["micro_topic_id"]:
        # Get nano topics for this micro topic
        if assignment["nano_topic_ids"]:
            # Specific nano topics were selected
            nano_topic_ids = json.loads(assignment["nano_topic_ids"])
            if nano_topic_ids:
                placeholders = ",".join("?" * len(nano_topic_ids))
                c.execute(f"""
                    SELECT n.name
                    FROM nano_topics n
                    WHERE n.id IN ({placeholders})
                """, nano_topic_ids)
            else:
                # Empty list means no specific nano topics
                c.execute("""
                    SELECT n.name
                    FROM nano_topics n
                    WHERE n.micro_topic_id = ?
                """, (assignment["micro_topic_id"],))
        else:
            # No nano_topic_ids specified, get all nano topics for the micro topic
            c.execute("""
                SELECT n.name
                FROM nano_topics n
                WHERE n.micro_topic_id = ?
            """, (assignment["micro_topic_id"],))
        
        nano_topics = [row["name"] for row in c.fetchall()]
        
        # Get questions from each nano topic
        for nano_topic in nano_topics:
            c.execute("""
                SELECT q.question, q.options, q.answer, q.style
                FROM questions q
                JOIN nano_topics n ON q.nano_topic_id = n.id
                WHERE n.name = ? AND q.is_approved = 1
            """, (nano_topic,))
            
            for row in c.fetchall():
                questions.append({
                    "question": row["question"],
                    "options": json.loads(row["options"]) if row["options"] else [],
                    "answer": row["answer"],
                    "style": row["style"],
                    "nano_topic": nano_topic
                })
    
    conn.close()
    return {"questions": questions}

# ADD these new endpoints to main.py for proper parent data retrieval:

@app.get("/parent/linked-students")
async def get_linked_students(current_user: dict = Depends(get_current_user)):
    """Get actual linked students with real IDs"""
    if current_user["role"] != "parent":
        raise HTTPException(status_code=403, detail="Only parents can view linked students")
    
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("""
        SELECT u.id, u.username, u.created_at, pcl.created_at as linked_at
        FROM users u
        JOIN parent_child_links pcl ON u.id = pcl.student_id
        WHERE pcl.parent_id = ?
    """, (current_user["id"],))
    
    students = [
        {
            "id": row["id"],
            "username": row["username"], 
            "created_at": row["created_at"],
            "linked_at": row["linked_at"]
        }
        for row in c.fetchall()
    ]
    
    conn.close()
    return {"students": students}

@app.get("/parent/student-analytics/{student_id}")
async def get_student_analytics_for_parent(
    student_id: int, 
    current_user: dict = Depends(get_current_user)
):
    """Get detailed analytics for a specific student (parent access)"""
    if current_user["role"] != "parent":
        raise HTTPException(status_code=403, detail="Only parents can view student analytics")
    
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Verify parent is linked to this student
    link_check = c.execute("""
        SELECT 1 FROM parent_child_links 
        WHERE parent_id = ? AND student_id = ?
    """, (current_user["id"], student_id)).fetchone()
    
    if not link_check:
        raise HTTPException(status_code=403, detail="Not authorized to view this student's data")
    
    # Get comprehensive student data (same as student analytics but for parent access)
    # Overall statistics including hints and lessons
    stats = c.execute("""
        SELECT 
            COUNT(*) as total_questions,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct_answers,
            AVG(p_learned) as avg_mastery,
            COUNT(DISTINCT nano_topic_id) as topics_attempted,
            SUM(CASE WHEN hint_used THEN 1 ELSE 0 END) as hints_used,
            SUM(CASE WHEN lesson_viewed THEN 1 ELSE 0 END) as lessons_viewed,
            COUNT(DISTINCT DATE(timestamp)) as active_days,
            MIN(DATE(timestamp)) as first_activity,
            MAX(DATE(timestamp)) as last_activity
        FROM student_results
        WHERE student_id = ?
    """, (student_id,)).fetchone()
    
    # Topic-wise progress
    topic_progress = c.execute("""
        SELECT 
            n.name as topic,
            COUNT(*) as questions_answered,
            SUM(CASE WHEN sr.is_correct THEN 1 ELSE 0 END) as correct_answers,
            MAX(sr.p_learned) as mastery_level,
            MAX(sr.timestamp) as last_attempt
        FROM student_results sr
        JOIN nano_topics n ON sr.nano_topic_id = n.id
        WHERE sr.student_id = ?
        GROUP BY n.name
        ORDER BY mastery_level ASC
    """, (student_id,)).fetchall()
    
    # Recent daily activity (last 30 days)
    daily_activity = c.execute("""
        SELECT 
            DATE(timestamp) as date,
            COUNT(*) as questions_answered,
            AVG(CASE WHEN is_correct THEN 100.0 ELSE 0.0 END) as accuracy
        FROM student_results
        WHERE student_id = ? 
        AND timestamp >= date('now', '-30 days')
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
    """, (student_id,)).fetchall()
    
    # Get user creation date
    user_data = c.execute(
        "SELECT created_at FROM users WHERE id = ?", 
        (student_id,)
    ).fetchone()
    
    conn.close()
    
    if not stats or not stats["total_questions"]:
        return {
            "has_data": False,
            "account_created": user_data["created_at"] if user_data else None
        }
    
    # Calculate consistency
    account_created = user_data["created_at"] if user_data else None
    consistency = 0
    if account_created and stats["active_days"]:
        created_date = datetime.fromisoformat(account_created)
        days_since_creation = (datetime.now() - created_date).days + 1
        consistency = (stats["active_days"] / days_since_creation * 100) if days_since_creation > 0 else 0
    
    return {
        "has_data": True,
        "overall_stats": {
            "total_questions": stats["total_questions"],
            "correct_answers": stats["correct_answers"], 
            "accuracy": (stats["correct_answers"] / stats["total_questions"]) * 100,
            "avg_mastery": stats["avg_mastery"] * 100 if stats["avg_mastery"] else 0,
            "topics_attempted": stats["topics_attempted"],
            "hints_used": stats["hints_used"],
            "lessons_viewed": stats["lessons_viewed"],
            "active_days": stats["active_days"],
            "consistency": consistency
        },
        "topic_progress": [
            {
                "topic": row["topic"],
                "questions_answered": row["questions_answered"],
                "correct_answers": row["correct_answers"],
                "accuracy": (row["correct_answers"] / row["questions_answered"]) * 100,
                "mastery_level": row["mastery_level"] * 100 if row["mastery_level"] else 0,
                "last_attempt": row["last_attempt"]
            }
            for row in topic_progress
        ],
        "daily_activity": [
            {
                "date": row["date"],
                "questions_answered": row["questions_answered"],
                "accuracy": row["accuracy"]
            }
            for row in daily_activity
        ],
        "account_created": account_created
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)