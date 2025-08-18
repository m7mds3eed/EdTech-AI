import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
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
if "user_id" not in st.session_state or st.session_state.role != "teacher":
    st.error("Please log in as a teacher to access this page.")
    st.switch_page("app.py")

# Set current page for navigation
st.session_state.current_page = "teacher_reports"
render_sidebar("teacher_reports", BACKEND_URL)
# --- End of Sidebar ---

# --- Helper Functions (Corrected and Simplified) ---

@st.cache_data(ttl=60) # Cache data for 60 seconds
def get_teacher_classes(token):
    """
    FIX 1: This function now correctly fetches the classes and the student count
    which is already provided by the '/classes/my-classes' endpoint.
    """
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BACKEND_URL}/classes/my-classes", headers=headers)
        response.raise_for_status()
        # The 'student_count' is directly used from the API response.
        return response.json().get("classes", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching classes: {e}")
        return []

@st.cache_data(ttl=60)
def get_class_analytics(class_id, token):
    """
    FIX 2: This is the new, primary function. It calls the powerful
    '/analytics/class/{class_id}' endpoint that provides all the necessary
    data (students, topics, timeline) in a single API call.
    """
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BACKEND_URL}/analytics/class/{class_id}", headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching class analytics: {e}")
        return {"students": [], "topics": [], "timeline": []}


def get_assignment_performance(assignment_id, token):
    """Fetches performance data for a specific assignment."""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        # NOTE: Your backend doesn't have a dedicated endpoint to get single assignment details.
        # We get submissions and infer details from there.
        resp_subs = requests.get(f"{BACKEND_URL}/assignments/{assignment_id}/submissions", headers=headers)
        resp_subs.raise_for_status()
        submissions = resp_subs.json().get("submissions", [])
        return submissions
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching assignment submissions: {e}")
        return []

# --- Main Page ---
st.title("📊 Class Reports")

classes = get_teacher_classes(st.session_state.token)

if not classes:
    st.warning("You have not created any classes yet.")
    if st.button("Go to Dashboard to Create a Class"):
        st.switch_page("pages/teacher_dashboard.py")
else:
    selected_class_name = st.selectbox("Select a Class to View Reports", [c["name"] for c in classes])
    selected_class = next((c for c in classes if c["name"] == selected_class_name), None)

    if selected_class:
        st.write(f"Displaying reports for **{selected_class['name']}** | **{selected_class.get('student_count', 0)} students**")

        # FIX 3: Call the new, functional analytics endpoint.
        analytics_data = get_class_analytics(selected_class["id"], st.session_state.token)
        students = analytics_data.get("students", [])
        topics = analytics_data.get("topics", [])
        timeline = analytics_data.get("timeline", [])

        tab1, tab2, tab3, tab4 = st.tabs(["Class Overview", "Student Performance", "Topic Analysis", "Assignments"])

        # --- TAB 1: Class Overview ---
        with tab1:
            st.header("Class Overview")
            if students:
                # Summary metrics are now accurate based on the API response.
                total_questions = sum(s["total_questions"] for s in students)
                avg_accuracy = sum(s["accuracy"] for s in students) / len(students) if students else 0
                avg_mastery = sum(s["avg_mastery"] for s in students) / len(students) if students else 0
                total_active_days = sum(s["active_days"] for s in students)

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Questions Attempted", f"{total_questions:,}")
                col2.metric("Average Accuracy", f"{avg_accuracy:.1f}%")
                col3.metric("Average Mastery", f"{avg_mastery:.1f}%")
                col4.metric("Total Active Days", total_active_days)
                st.divider()

                # Progress timeline
                st.subheader("Class Activity Timeline")
                if timeline:
                    df_timeline = pd.DataFrame(timeline)
                    df_timeline['date'] = pd.to_datetime(df_timeline['date'])

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=df_timeline['date'], y=df_timeline['questions_answered'], name='Questions Answered', line=dict(color='#1f77b4')))
                    fig.update_layout(title="Daily Questions Answered", xaxis_title="Date", yaxis_title="Count")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No timeline data available for this class yet.")

                # Student ranking
                st.subheader("Student Rankings by Mastery")
                df_students = pd.DataFrame(students).sort_values('avg_mastery', ascending=False)
                df_students['rank'] = range(1, len(df_students) + 1)
                
                display_df = df_students[['rank', 'username', 'avg_mastery', 'accuracy', 'total_questions']].copy()
                display_df.columns = ['Rank', 'Student', 'Mastery %', 'Accuracy %', 'Questions']
                display_df[['Mastery %', 'Accuracy %']] = display_df[['Mastery %', 'Accuracy %']].round(1)
                st.dataframe(display_df, hide_index=True, use_container_width=True)
            else:
                st.info("No student activity has been recorded for this class yet.")

        # --- TAB 2: Individual Student Performance ---
        with tab2:
            st.header("Individual Student Performance")
            if students:
                student_names = [s["username"] for s in students]
                selected_student_name = st.selectbox("Select a Student", student_names)
                selected_student = next((s for s in students if s["username"] == selected_student_name), None)

                if selected_student:
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Avg. Mastery", f"{selected_student['avg_mastery']:.1f}%")
                    col2.metric("Accuracy", f"{selected_student['accuracy']:.1f}%")
                    col3.metric("Questions Attempted", selected_student["total_questions"])
                    col4.metric("Active Days", selected_student["active_days"])
                    st.info("Detailed topic breakdown for individual students is planned for a future update.")
                else:
                    st.warning("Could not find the selected student's data.")
            else:
                st.info("No students in this class have activity to report.")
        
        # --- TAB 3: Topic Analysis ---
        with tab3:
            st.header("Topic Analysis")
            if topics:
                df_topics = pd.DataFrame(topics)
                
                fig = px.bar(df_topics, x='topic_name', y=['accuracy', 'avg_mastery'],
                             title="Class Performance by Topic",
                             labels={'value': 'Percentage', 'variable': 'Metric', 'topic_name': 'Topic'},
                             barmode='group', height=450)
                st.plotly_chart(fig, use_container_width=True)

                st.subheader("Topic Statistics")
                weak_topics = df_topics[df_topics['avg_mastery'] < 50].sort_values('avg_mastery')
                if not weak_topics.empty:
                    st.warning(f"**Attention Needed:** The class is struggling with the following topics:")
                    for _, topic in weak_topics.iterrows():
                        st.write(f"- **{topic['topic_name']}** (Average Mastery: {topic['avg_mastery']:.1f}%)")
            else:
                st.info("No topic performance data is available for this class yet.")
        
        # --- TAB 4: Assignment Reports ---
        with tab4:
            st.header("Assignment Reports")
            try:
                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                resp = requests.get(f"{BACKEND_URL}/assignments/class/{selected_class['id']}", headers=headers)
                resp.raise_for_status()
                assignments = resp.json().get("assignments", [])
            except requests.exceptions.RequestException as e:
                st.error(f"Error fetching assignments: {e}")
                assignments = []

            if assignments:
                assignment_titles = [a['title'] for a in assignments]
                selected_title = st.selectbox("Select an Assignment", assignment_titles)
                selected_assignment = next((a for a in assignments if a['title'] == selected_title), None)

                if selected_assignment:
                    submissions = get_assignment_performance(selected_assignment["id"], st.session_state.token)
                    
                    st.write(f"Due Date: {selected_assignment['due_date'] or 'N/A'}")
                    st.write(f"Max Attempts: {selected_assignment['max_attempts']}")

                    if submissions:
                        df_submissions = pd.DataFrame(submissions)
                        valid_scores = df_submissions['score'].dropna()
                        avg_score = valid_scores.mean() if not valid_scores.empty else 0

                        col1, col2 = st.columns(2)
                        col1.metric("Total Submissions", len(df_submissions))
                        col2.metric("Class Average Score", f"{avg_score:.1f}%")

                        st.subheader("Submission Details")
                        display_df = df_submissions[['student_name', 'attempt_number', 'score', 'correct_answers', 'total_questions', 'completed_at']].copy()
                        display_df.columns = ['Student', 'Attempt #', 'Score %', 'Correct', 'Total Qs', 'Completed At']
                        st.dataframe(display_df, hide_index=True, use_container_width=True)
                    else:
                        st.info("No student submissions for this assignment yet.")
            else:
                st.info("No assignments have been created for this class yet.")