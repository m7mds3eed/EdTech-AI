import streamlit as st
import requests
import json
from datetime import datetime
from src.ui.feedback import render_feedback_widget
from src.ui.components import render_question, render_results, render_parent_dashboard
from src.auth.session import restore_session_from_cookie , get_cookie_manager
from src.ui.navigation import render_sidebar
# --- Configuration ---
BACKEND_URL = "http://127.0.0.1:8000"  # Or use os.environ.get for production
# --- ADD THIS BLOCK TO THE TOP OF THE PAGE ---
cookies = get_cookie_manager()


restore_session_from_cookie(BACKEND_URL)
# --- END OF BLOCK ---

# --- Hide default Streamlit navigation ---
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

if st.session_state.role == "parent":
    render_parent_dashboard()
    st.stop()
# Sidebar navigation
# Set current page for navigation
st.session_state.current_page = "quiz"
render_sidebar("quiz", BACKEND_URL)

def clear_quiz_state():
    """Clear all quiz-related session state variables."""
    quiz_keys = [
        "current_question", "question_index", "show_results", "new_question_needed",
        "hint_shown", "hint_used", "lesson_shown", "lesson_viewed", "hint_text", "lesson_text",
        "last_answer_correct", "skips", "attempts", "question_queue",
        # Assignment specific
        "assignment_mode", "assignment_id", "assignment_info", "submission_id",
        "assignment_start_time", "assignment_questions_answered", "assignment_correct_answers",
        "assignment_hints_allowed", "assignment_lessons_allowed"
    ]
    for key in quiz_keys:
        if key in st.session_state:
            del st.session_state[key]

def initialize_quiz_state():
    """Initialize clean quiz state."""
    if "question_index" not in st.session_state:
        st.session_state.question_index = 0
    if "show_results" not in st.session_state:
        st.session_state.show_results = False
    if "points" not in st.session_state:
        st.session_state.points = 0
    if "results" not in st.session_state:
        st.session_state.results = {"strengths": [], "weaknesses": []}
    if "bkt" not in st.session_state:
        st.session_state.bkt = {}

# --- End of Sidebar ---

def get_student_assignments():
    """Get pending assignments via composite API calls."""
    assignments = []
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        resp_classes = requests.get(f"{BACKEND_URL}/classes/my-classes", headers=headers)
        resp_classes.raise_for_status()
        classes = resp_classes.json().get("classes", [])
        
        for cls in classes:
            resp_assign = requests.get(f"{BACKEND_URL}/assignments/class/{cls['id']}", headers=headers)
            if resp_assign.status_code == 200:
                class_assigns = resp_assign.json().get("assignments", [])
                for a in class_assigns:
                    resp_subs = requests.get(f"{BACKEND_URL}/assignments/{a['id']}/submissions", headers=headers)
                    if resp_subs.status_code == 200:
                        subs = resp_subs.json().get("submissions", [])
                        attempts = len(subs)
                        if attempts < a['max_attempts'] and (not a['due_date'] or datetime.fromisoformat(a['due_date']) >= datetime.now()):
                            assignments.append({
                                "id": a['id'],
                                "title": a['title'],
                                "description": a['description'],
                                "due_date": a['due_date'],
                                "min_questions": a['min_questions'],
                                "max_attempts": a['max_attempts'],
                                "show_hints": a['show_hints'],
                                "show_lessons": a['show_lessons'],
                                "class_name": cls['name'],
                                "attempts": attempts,
                                "topic_id": None,  # Placeholder; not in API, default later
                                "subtopic_id": None,
                                "micro_topic_id": a.get('micro_topic_id'),
                                "nano_topic_ids": a.get('nano_topic_ids')
                            })
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching assignments: {e}")
    return assignments

def start_assignment(assignment_id):
    """Start or continue an assignment submission via API."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.post(f"{BACKEND_URL}/assignments/{assignment_id}/submit", headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("submission_id")
    except requests.exceptions.RequestException as e:
        st.error(f"Error starting assignment: {e}")
        return None

def complete_assignment(submission_id, total_questions, correct_answers, time_spent):
    """Complete an assignment submission via API."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        payload = {
            "score": (correct_answers / total_questions * 100) if total_questions > 0 else 0,
            "total_questions": total_questions,
            "correct_answers": correct_answers,
            "skipped_questions": 0  # Placeholder if needed
        }
        response = requests.put(f"{BACKEND_URL}/assignments/submissions/{submission_id}/complete", headers=headers, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        st.error(f"Error completing assignment: {e}")

if "user_id" not in st.session_state or "role" not in st.session_state:
    st.error("Please log in to access the quiz.")
    st.stop()


# Initialize clean quiz state
initialize_quiz_state()

# Check what mode we're in
if st.session_state.get("assignment_mode"):
    # ASSIGNMENT MODE
    st.title("📝 Assignment Quiz")
    
    assignment = st.session_state.assignment_info
    
    # Assignment header with exit option
    col1, col2 = st.columns([4, 1])
    with col1:
        st.subheader(f"Assignment: {assignment['title']}")
        st.caption(f"Class: {assignment['class_name']}")
    with col2:
        if st.button("❌ Exit Assignment", help="Exit this assignment and return to assignments page"):
            clear_quiz_state()
            st.switch_page("pages/student_assignments.py")
    
    # Progress bar (only updates on submit)
    progress = st.session_state.assignment_questions_answered / assignment['min_questions']
    st.progress(min(progress, 1.0))
    st.write(f"Progress: {st.session_state.assignment_questions_answered} / {assignment['min_questions']} questions completed")
    
    # Check if assignment is complete
    if st.session_state.assignment_questions_answered >= assignment['min_questions']:
        time_spent = int((datetime.now() - st.session_state.assignment_start_time).total_seconds())
        complete_assignment(
            st.session_state.submission_id,
            st.session_state.assignment_questions_answered,
            st.session_state.assignment_correct_answers,
            time_spent
        )
        
        # Show results
        st.success("🎉 Assignment Complete!")
        score = (st.session_state.assignment_correct_answers / st.session_state.assignment_questions_answered * 100)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Final Score", f"{score:.1f}%")
        with col2:
            st.metric("Questions Answered", st.session_state.assignment_questions_answered)
        with col3:
            st.metric("Time Spent", f"{time_spent//60}m {time_spent%60}s")
        
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📚 Back to Assignments", type="primary", use_container_width=True):
                clear_quiz_state()
                st.switch_page("pages/student_assignments.py")
        with col2:
            if st.button("🏠 Go Home", use_container_width=True):
                clear_quiz_state()
                st.switch_page("pages/student_assignments.py")
    else:
        # Continue with assignment quiz
        if not st.session_state.get("current_subject") or not st.session_state.get("current_micro_topic"):
            st.error("⚠️ Assignment configuration error. Returning to assignments page.")
            if st.button("Back to Assignments"):
                clear_quiz_state()
                st.switch_page("pages/student_assignments.py")
            st.stop()
        
        # Track answer submission for progress
        if "last_answer_correct" in st.session_state:
            if st.session_state.last_answer_correct:
                st.session_state.assignment_correct_answers += 1
            st.session_state.assignment_questions_answered += 1
            del st.session_state.last_answer_correct
            st.rerun()  # Refresh to update progress bar
        
        # Track skipped questions for progress
        elif "question_skipped" in st.session_state:
            # Get count_skips setting from assignment (default to True if not specified)
            count_skips = assignment.get('count_skips', True)
            if count_skips:
                st.session_state.assignment_questions_answered += 1
                # Skipped questions don't add to correct_answers (count as incorrect)
            del st.session_state.question_skipped
            st.rerun()  # Refresh to update progress bar
        
        # Render the question
        render_question(
            st.session_state.current_subject, 
            st.session_state.current_micro_topic, 
            st.session_state.question_index
        )

elif st.session_state.get("current_subject") and st.session_state.get("current_micro_topic"):
    # PRACTICE MODE
    st.title("🎯 Practice Quiz")
    
    # Practice header with subject info and exit option
    col1, col2 = st.columns([4, 1])
    with col1:
        st.subheader(f"Subject: {st.session_state.current_subject}")
        st.caption(f"Topic: {st.session_state.current_micro_topic}")
    with col2:
        if st.button("❌ Exit Practice", help="Exit practice and return to home"):
            clear_quiz_state()
            st.switch_page("app.py")
    
    # Practice progress
    st.write(f"Questions answered: {st.session_state.question_index} | Points: {st.session_state.points}")
    
    if st.session_state.show_results:
        render_results()
    else:
        render_question(
            st.session_state.current_subject, 
            st.session_state.current_micro_topic, 
            st.session_state.question_index
        )
        
        # End quiz button
        st.divider()
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🏁 End Practice Quiz", use_container_width=True):
                st.session_state.show_results = True
                st.rerun()

else:
    # NO QUIZ ACTIVE - Show options
    st.title("Quiz Center")
    
    # Check for pending assignments first
    if st.session_state.role == "student":
        assignments = get_student_assignments()
        
        if assignments:
            st.subheader("📚 Your Pending Assignments")
            st.info("Complete your assignments first, then practice with custom topics!")
            
            for assignment in assignments[:3]:  # Show first 3 assignments
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"**{assignment['title']}**")
                        st.caption(f"Class: {assignment['class_name']}")
                    with col2:
                        if assignment['due_date']:
                            due = datetime.fromisoformat(assignment['due_date'])
                            days_left = (due.date() - datetime.now().date()).days
                            if days_left == 0:
                                st.warning("Due today!")
                            elif days_left == 1:
                                st.info("Due tomorrow")
                            else:
                                st.info(f"{days_left} days left")
                    with col3:
                        attempts_left = assignment['max_attempts'] - assignment['attempts']
                        if attempts_left > 0:
                            if st.button("Start", key=f"quick_start_{assignment['id']}", type="primary"):
                                # Start assignment with proper setup
                                clear_quiz_state()  # Start fresh
                                st.session_state.assignment_mode = True
                                st.session_state.assignment_id = assignment['id']
                                st.session_state.assignment_info = assignment
                                st.session_state.submission_id = start_assignment(assignment['id'])
                                st.session_state.assignment_start_time = datetime.now()
                                st.session_state.assignment_questions_answered = 0
                                st.session_state.assignment_correct_answers = 0
                                
                                # Set topic based on assignment (default if not set)
                                st.session_state.current_subject = "Numbers and the Number System"  # Default
                                st.session_state.current_micro_topic = "Integer Operations"  # Default
                                if assignment.get('micro_topic_id'):
                                    # Composite: Get name from structure
                                    try:
                                        headers = {"Authorization": f"Bearer {st.session_state.token}"}
                                        resp = requests.get(f"{BACKEND_URL}/topics/structure", headers=headers)
                                        resp.raise_for_status()
                                        curriculum = resp.json().get("curriculum", [])
                                        for top in curriculum:
                                            for sub in top.get("subtopics", []):
                                                for mic in sub.get("micro_topics", []):
                                                    if mic.get("id") == assignment['micro_topic_id']:
                                                        st.session_state.current_subject = top["name"]
                                                        st.session_state.current_micro_topic = mic["name"]
                                                        break
                                                    if st.session_state.current_subject: break
                                                if st.session_state.current_subject: break
                                            if st.session_state.current_subject: break
                                    except requests.exceptions.RequestException:
                                        pass
                                
                                # Set permissions
                                st.session_state.assignment_hints_allowed = assignment.get('show_hints', True)
                                st.session_state.assignment_lessons_allowed = assignment.get('show_lessons', True)
                                
                                st.rerun()
                        else:
                            st.error("No attempts left")
                
                st.divider()
            
            if len(assignments) > 3:
                st.info(f"+ {len(assignments) - 3} more assignments")
                if st.button("📋 View All Assignments"):
                    clear_quiz_state()
                    st.switch_page("pages/student_assignments.py")
        
        # Practice section
        st.divider()
        st.subheader("🎯 Practice Mode")
        st.write("Select a topic to practice on your own:")
        
        # Load subjects and micro-topics from structure
        if "curriculum_structure" not in st.session_state:
            try:
                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                response = requests.get(f"{BACKEND_URL}/topics/structure", headers=headers)
                response.raise_for_status()
                st.session_state.curriculum_structure = response.json().get("curriculum", [])
            except requests.exceptions.RequestException as e:
                st.error(f"Error loading topics: {e}")
                st.session_state.curriculum_structure = []
        
        subjects = [top["name"] for top in st.session_state.curriculum_structure]
        
        subject = st.selectbox("Select a Subject", [""] + subjects, key="practice_subject")
        if subject:
            micro_topics = []
            for top in st.session_state.curriculum_structure:
                if top["name"] == subject:
                    for sub in top.get("subtopics", []):
                        micro_topics.extend([mic["name"] for mic in sub.get("micro_topics", [])])
                    break
            
            micro_topic = st.selectbox("Select a Topic", [""] + micro_topics, key="practice_micro_topic")
            if micro_topic:
                if st.button("🚀 Start Practice Quiz", type="primary"):
                    clear_quiz_state()  # Start fresh
                    st.session_state.current_subject = subject
                    st.session_state.current_micro_topic = micro_topic
                    st.rerun()
        
    else:
        st.error("Please log in as a student to access quizzes.")