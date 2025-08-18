import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from src.ui.feedback import render_feedback_widget
from src.auth.session import restore_session_from_cookie, get_cookie_manager
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

# --- Authentication and Sidebar ---
if "user_id" not in st.session_state or st.session_state.role != "student":
    st.error("Please log in as a student to access this page.")
    st.switch_page("app.py")

# Sidebar navigation
# Set current page for navigation
st.session_state.current_page = "student_assignments"
render_sidebar("student_assignments", BACKEND_URL)
# --- End of Sidebar ---

# Ensure user is logged in and is a student
if "user_id" not in st.session_state or st.session_state.role != "student":
    st.error("Please log in as a student to view assignments.")
    st.stop()

st.title("My Assignments")

def get_student_assignments_detailed():
    """Get all assignments with details via composite API calls."""
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
                        
                        # FIX: Only count COMPLETED submissions as attempts
                        completed_subs = [s for s in subs if s.get('completed_at')]
                        completed_attempts = len(completed_subs)
                        
                        # Check for incomplete/started submissions
                        incomplete_subs = [s for s in subs if not s.get('completed_at')]
                        has_incomplete = len(incomplete_subs) > 0
                        
                        best_score = max([s.get('score', 0) for s in completed_subs] or [None])
                        
                        assignments.append({
                            "id": a['id'],
                            "title": a['title'],
                            "description": a['description'],
                            "due_date": a['due_date'],
                            "min_questions": a['min_questions'],
                            "max_attempts": a['max_attempts'],
                            "class_name": cls['name'],
                            "teacher_name": "Your Teacher",  # Placeholder; no API field
                            "completed_attempts": completed_attempts,  # Only completed attempts count
                            "has_incomplete": has_incomplete,  # Track if there's an incomplete attempt
                            "best_score": best_score,
                            "assigned_date": a['created_at'],
                            "topic_id": None,  # Placeholder
                            "subtopic_id": None,
                            "micro_topic_id": a.get('micro_topic_id'),
                            "nano_topic_ids": a.get('nano_topic_ids'),
                            "show_hints": a['show_hints'],
                            "show_lessons": a['show_lessons']
                        })
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching assignments: {e}")
    return assignments

def get_submission_history(assignment_id):
    """Get submission history via API."""
    submissions = []
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.get(f"{BACKEND_URL}/assignments/{assignment_id}/submissions", headers=headers)
        response.raise_for_status()
        subs = response.json().get("submissions", [])
        for s in subs:
            time_spent = None
            if s.get('started_at') and s.get('completed_at'):
                start = datetime.fromisoformat(s['started_at'])
                end = datetime.fromisoformat(s['completed_at'])
                time_spent = int((end - start).total_seconds())
            submissions.append({
                "attempt": s['attempt_number'],
                "started": s.get('started_at'),
                "completed": s.get('completed_at'),
                "score": s.get('score'),
                "total_questions": s.get('total_questions'),
                "correct_answers": s.get('correct_answers'),
                "time_spent": time_spent,
                "is_completed": bool(s.get('completed_at'))
            })
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching history: {e}")
    return submissions

def start_assignment_from_assignments_page(assignment):
    """Set up session state for starting an assignment."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        
        # Check if there's already an incomplete submission
        submissions_resp = requests.get(f"{BACKEND_URL}/assignments/{assignment['id']}/submissions", headers=headers)
        submissions_resp.raise_for_status()
        submissions = submissions_resp.json().get("submissions", [])
        
        incomplete_submission = None
        for sub in submissions:
            if not sub.get('completed_at'):
                incomplete_submission = sub
                break
        
        if incomplete_submission:
            # Resume existing submission instead of creating new one
            st.info(f"📝 Resuming previous attempt (Attempt #{incomplete_submission['attempt_number']})")
            submission_id = incomplete_submission['id']
        else:
            # Create new submission
            response = requests.post(f"{BACKEND_URL}/assignments/{assignment['id']}/submit", headers=headers)
            
            if response.status_code == 400:
                error_detail = response.json()
                if "Maximum attempts exceeded" in error_detail.get('detail', ''):
                    st.error(f"❌ You have used all {assignment['max_attempts']} attempts for this assignment.")
                    return False
                else:
                    st.error(f"❌ Error: {error_detail.get('detail', 'Unknown error')}")
                    return False
            
            response.raise_for_status()
            data = response.json()
            submission_id = data.get("submission_id")
            
            if not submission_id:
                st.error("❌ Failed to create submission. Please try again.")
                return False
        
        # Set assignment mode session variables
        st.session_state.assignment_mode = True
        st.session_state.assignment_id = assignment["id"]
        st.session_state.assignment_info = assignment
        st.session_state.submission_id = submission_id
        st.session_state.assignment_start_time = datetime.now()
        st.session_state.assignment_questions_answered = 0
        st.session_state.assignment_correct_answers = 0
        
        # Set topic filters based on assignment (default or from structure)
        st.session_state.current_subject = "Numbers and the Number System"  # Default
        st.session_state.current_micro_topic = "Integer Operations"  # Default
        if assignment.get('micro_topic_id'):
            # Composite: Get name from structure (cache if possible)
            if "curriculum_structure" not in st.session_state:
                try:
                    resp = requests.get(f"{BACKEND_URL}/topics/structure", headers=headers)
                    resp.raise_for_status()
                    st.session_state.curriculum_structure = resp.json().get("curriculum", [])
                except:
                    pass
            curriculum = st.session_state.get("curriculum_structure", [])
            for top in curriculum:
                for sub in top.get("subtopics", []):
                    for mic in sub.get("micro_topics", []):
                        if mic.get("id") == assignment['micro_topic_id']:
                            st.session_state.current_subject = top["name"]
                            st.session_state.current_micro_topic = mic["name"]
                            break
                    if st.session_state.current_subject: break
                if st.session_state.current_subject: break
        
        # Set hint/lesson permissions
        st.session_state.assignment_hints_allowed = assignment.get("show_hints", True)
        st.session_state.assignment_lessons_allowed = assignment.get("show_lessons", True)
        
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to start assignment: {e}")
        return False

# Get assignments
assignments = get_student_assignments_detailed()

# Separate by status
pending_assignments = []
completed_assignments = []
overdue_assignments = []

for assignment in assignments:
    # Logic: If user has completed at least once, it goes to completed tab
    # Otherwise, it stays in pending (regardless of due date, unless overdue with no completions)
    
    if assignment['completed_attempts'] > 0:
        # Has at least one completed attempt - goes to completed tab
        completed_assignments.append(assignment)
    elif assignment['due_date']:
        due_date = datetime.fromisoformat(assignment['due_date'])
        # Check if it's past the due date and never completed
        if due_date.date() < datetime.now().date():
            overdue_assignments.append(assignment)
        else:
            pending_assignments.append(assignment)
    else:
        # No due date and no completions - stays pending
        pending_assignments.append(assignment)

# Display assignments by category
tab1, tab2, tab3 = st.tabs([
    f"📝 Pending ({len(pending_assignments)})", 
    f"✅ Completed ({len(completed_assignments)})", 
    f"⏰ Overdue ({len(overdue_assignments)})"
])

with tab1:
    if pending_assignments:
        for assignment in pending_assignments:
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.subheader(assignment['title'])
                    st.write(f"**Class:** {assignment['class_name']} | **Teacher:** {assignment['teacher_name']}")
                    if assignment['description']:
                        st.write(assignment['description'])
                    st.write(f"📝 {assignment['min_questions']} questions required")
                
                with col2:
                    if assignment['due_date']:
                        due = datetime.fromisoformat(assignment['due_date'])
                        days_left = (due.date() - datetime.now().date()).days
                        if days_left == 0:
                            st.warning("⏰ Due today!")
                        elif days_left == 1:
                            st.info("📅 Due tomorrow")
                        elif days_left > 1:
                            st.info(f"📅 {days_left} days left")
                        st.caption(due.strftime("%b %d, %Y"))
                    else:
                        st.info("No due date")
                
                with col3:
                    attempts_left = assignment['max_attempts'] - assignment['completed_attempts']
                    st.metric("Attempts Left", attempts_left)
                    
                    # Show incomplete attempt warning if exists
                    if assignment['has_incomplete']:
                        st.warning("⏳ Incomplete attempt exists")
                    
                    # Show previous attempts if any
                    if assignment['completed_attempts'] > 0:
                        best_score = assignment['best_score']
                        if best_score is not None:
                            st.caption(f"Best score: {best_score:.1f}%")
                        else:
                            st.caption("Previous attempts exist")
                    
                    if attempts_left > 0:
                        if assignment['has_incomplete']:
                            button_text = "Resume Quiz"
                        elif assignment['completed_attempts'] > 0:
                            button_text = "Try Again"
                        else:
                            button_text = "Start Quiz"
                        
                        if st.button(button_text, key=f"start_{assignment['id']}", type="primary"):
                            if start_assignment_from_assignments_page(assignment):
                                st.switch_page("pages/quiz.py")
                    else:
                        st.error("No attempts left")
                
                st.divider()
    else:
        st.info("No pending assignments. Great job staying on top of your work!")

with tab2:
    if completed_assignments:
        for assignment in completed_assignments:
            best_score_display = f"{assignment['best_score']:.1f}%" if assignment['best_score'] is not None else "No score"
            with st.expander(f"{assignment['title']} - Best Score: {best_score_display}"):
                st.write(f"**Class:** {assignment['class_name']} | **Teacher:** {assignment['teacher_name']}")
                
                # Get submission history
                submissions = get_submission_history(assignment['id'])
                
                if submissions:
                    st.subheader("Submission History")
                    
                    for sub in submissions:
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            if sub['is_completed']:
                                score_display = f"{sub['score']:.1f}%" if sub['score'] is not None else "N/A"
                                st.metric(f"Attempt {sub['attempt']}", score_display)
                            else:
                                st.metric(f"Attempt {sub['attempt']}", "Incomplete")
                        with col2:
                            if sub['is_completed']:
                                correct_answers = sub['correct_answers'] if sub['correct_answers'] is not None else 0
                                total_questions = sub['total_questions'] if sub['total_questions'] is not None else 0
                                st.write(f"**Questions:** {correct_answers}/{total_questions}")
                            else:
                                st.write("**Status:** In progress")
                        with col3:
                            if sub['time_spent']:
                                st.write(f"**Time:** {sub['time_spent']//60}m {sub['time_spent']%60}s")
                            else:
                                st.write("**Time:** N/A")
                        with col4:
                            if sub['completed']:
                                completed_date = datetime.fromisoformat(sub['completed'])
                                st.write(f"**Date:** {completed_date.strftime('%b %d')}")
                            else:
                                st.write("**Status:** Started")
                
                # Show if attempts are available for retrying
                attempts_left = assignment['max_attempts'] - assignment['completed_attempts']
                if attempts_left > 0:
                    st.success(f"✨ {attempts_left} more attempts available")
                else:
                    st.info("🏁 All attempts completed")
    else:
        st.info("No completed assignments yet.")

with tab3:
    if overdue_assignments:
        st.warning("These assignments are past their due date and haven't been completed yet!")
        
        for assignment in overdue_assignments:
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.subheader(f"❌ {assignment['title']}")
                    st.write(f"**Class:** {assignment['class_name']}")
                    if assignment['due_date']:
                        due = datetime.fromisoformat(assignment['due_date'])
                        days_overdue = (datetime.now().date() - due.date()).days
                        st.error(f"Overdue by {days_overdue} days (was due {due.strftime('%b %d, %Y')})")
                
                with col2:
                    attempts_left = assignment['max_attempts'] - assignment['completed_attempts']
                    if attempts_left > 0:
                        if st.button("Complete Now", key=f"overdue_{assignment['id']}", type="primary"):
                            if start_assignment_from_assignments_page(assignment):
                                st.switch_page("pages/quiz.py")
                    else:
                        st.error("No attempts left")
                
                st.divider()
    else:
        st.success("No overdue assignments. Keep up the good work!")

# Summary statistics
st.sidebar.header("Assignment Summary")
total_assignments = len(assignments)
completion_rate = (len(completed_assignments) / total_assignments * 100) if total_assignments > 0 else 0

# Calculate average score properly handling None values
completed_scores = [a['best_score'] for a in completed_assignments if a['best_score'] is not None]
avg_score = sum(completed_scores) / len(completed_scores) if completed_scores else 0

st.sidebar.metric("Total Assignments", total_assignments)
st.sidebar.metric("Completion Rate", f"{completion_rate:.1f}%")
if completed_scores:
    st.sidebar.metric("Average Best Score", f"{avg_score:.1f}%")
else:
    st.sidebar.metric("Average Best Score", "N/A")

# Navigation
st.sidebar.divider()
if st.sidebar.button("Back to Home"):
    st.switch_page("app.py")
if st.sidebar.button("Practice Mode"):
    st.switch_page("pages/quiz.py")