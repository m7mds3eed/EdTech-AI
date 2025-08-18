# FILE: pages/student_home.py

import streamlit as st
import requests
from datetime import datetime
from src.ui.navigation import render_sidebar
from src.ui.home_components import HomeComponents

# Configuration
BACKEND_URL = "http://127.0.0.1:8000"
# --- Hide default Streamlit navigation ---
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)
def main():
    """Student home page."""
    st.set_page_config(
        page_title="Student Home - Learning Gap Identifier",
        page_icon="🎓",
        layout="wide"
    )
    
    # Check authentication
    if not st.session_state.get("user_id") or st.session_state.get("role") != "student":
        st.error("❌ Access denied. Please log in as a student.")
        st.switch_page("pages/auth.py")
    
    # Initialize home components
    home_components = HomeComponents(BACKEND_URL)
    
    # Render sidebar
    render_sidebar("app", BACKEND_URL)
    
    # Main content
    st.title("🎓 Learning Gap Identifier")
    st.header("👋 Welcome back!")
    
    # Quick start quiz section
    _render_quick_start_section(home_components)
    
    st.divider()
    
    # Two-column layout for main content
    col1, col2 = st.columns([2, 1], gap="large")
    
    with col1:
        _render_assignments_section(home_components)
        _render_class_joining_section(home_components)
    
    with col2:
        _render_announcements_section(home_components)
        _render_quick_stats_section(home_components)
        _render_parent_link_section()


def _render_quick_start_section(home_components: HomeComponents):
    """Render the quick start quiz section."""
    st.subheader("🎯 Start Learning")
    
    subjects, micro_topics_data = home_components.load_subjects_and_micro_topics()
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        subject = st.selectbox(
            "📖 Subject", 
            [""] + subjects, 
            key="home_subject", 
            placeholder="Choose a subject..."
        )
    
    with col2:
        if subject:
            available_topics = micro_topics_data.get(subject, [])
            micro_topic = st.selectbox(
                "📝 Topic", 
                [""] + available_topics, 
                key="home_micro_topic", 
                placeholder="Choose a topic..."
            )
        else:
            micro_topic = st.selectbox(
                "📝 Topic", 
                [""], 
                key="home_micro_topic", 
                placeholder="Select subject first", 
                disabled=True
            )
    
    with col3:
        st.write("")  # For alignment
        st.write("")  # For alignment
        if st.button("🚀 Start Quiz Now!", type="primary", use_container_width=True):
            selected_subject = st.session_state.get("home_subject")
            selected_topic = st.session_state.get("home_micro_topic")
            if selected_subject and selected_topic:
                st.session_state.current_subject = selected_subject
                st.session_state.current_micro_topic = selected_topic
                st.switch_page("pages/quiz.py")
            else:
                st.error("Please select both a subject and a topic!")

def _render_assignments_section(home_components: HomeComponents):
    """Render the assignments section."""
    st.subheader("📋 Your Assignments")
    
    try:
        pending_assignments = home_components.get_pending_assignments()
        
        if pending_assignments:
            # Validate assignments have questions available
            validated_assignments = []
            problematic_assignments = 0
            
            for assignment in pending_assignments:
                try:
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    resp = requests.get(f"{BACKEND_URL}/assignments/{assignment[4]}/questions", headers=headers)  # assignment[4] is assignment_id
                    if resp.status_code == 200:
                        questions = resp.json().get("questions", [])
                        if questions:
                            validated_assignments.append(assignment)
                        else:
                            problematic_assignments += 1
                    else:
                        problematic_assignments += 1
                except:
                    problematic_assignments += 1
            
            # Show warning if some assignments have issues
            if problematic_assignments > 0:
                st.warning(f"⚠️ {problematic_assignments} assignment(s) may not be properly configured. Contact your teacher if you can't access them.")
            
            # Display validated assignments
            for assignment in validated_assignments[:5]:  # Limit to 5 most recent
                with st.container():
                    col_a, col_b, col_c = st.columns([2, 1, 1])
                    with col_a:
                        st.write(f"**{assignment[0]}**")
                        st.caption(f"📚 Class: {assignment[2]}")
                    with col_b:
                        if assignment[1]:
                            due = datetime.fromisoformat(assignment[1])
                            days_left = (due.date() - datetime.now().date()).days
                            if days_left == 0:
                                st.warning("⏰ Due today!")
                            elif days_left == 1:
                                st.info("📅 Due tomorrow")
                            else:
                                st.info(f"📅 {days_left} days left")
                    with col_c:
                        st.caption(f"🔄 {assignment[3]} attempts left")
            
            if validated_assignments:
                if st.button("📋 View All Assignments", use_container_width=True):
                    # Clear any existing quiz state to avoid conflicts
                    if "assignment_mode" in st.session_state:
                        del st.session_state.assignment_mode
                    if "assignment_questions" in st.session_state:
                        del st.session_state.assignment_questions
                    st.switch_page("pages/student_assignments.py")
            else:
                st.info("🎉 No available assignments! Perfect time to practice with custom topics.")
                if st.button("🎯 Start Practice Quiz", use_container_width=True, type="primary"):
                    st.switch_page("pages/quiz.py")
        else:
            st.info("🎉 No pending assignments! Perfect time to practice with custom topics.")
            if st.button("🎯 Start Practice Quiz", use_container_width=True, type="primary"):
                st.switch_page("pages/quiz.py")
                
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            st.error("🚨 Your session has expired. Please log out and log in again.")
            if st.button("Logout to Refresh Session"):
                home_components.handle_session_expired()
        else:
            st.error(f"Error loading assignments: {e}")
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {e}")

def _render_class_joining_section(home_components: HomeComponents):
    """Render the class joining section."""
    st.divider()
    st.subheader("🏫 Join a Class")
    
    with st.form("join_class_form"):
        st.write("**Enter the class code your teacher gave you:**")
        col_x, col_y = st.columns([2, 1])
        with col_x:
            class_code = st.text_input(
                "Class Code", 
                placeholder="e.g., ABC123XY", 
                max_chars=8
            )
        with col_y:
            st.write("")  # Spacing
            join_submitted = st.form_submit_button(
                "🚪 Join Class", 
                type="primary", 
                use_container_width=True
            )
        
        if join_submitted and class_code:
            success, message = home_components.join_class(class_code.upper())
            if success:
                st.success(f"🎉 {message} Code: {class_code.upper()}!")
                st.balloons()
                st.rerun()
            else:
                st.error(f"❌ {message}")
        elif join_submitted:
            st.error("Please enter a class code.")


def _render_announcements_section(home_components: HomeComponents):
    """Render the announcements section."""
    st.subheader("📢 Announcements")
    
    try:
        announcements = home_components.get_class_announcements()
        
        if announcements:
            for announcement in announcements[:3]:  # Show top 3
                with st.container():
                    st.write(f"**{announcement['title']}**")
                    st.caption(f"👩‍🏫 {announcement['teacher_name']} • {announcement['class_name']}")
                    with st.expander("Read more"):
                        st.write(announcement['content'])
                    st.divider()
        else:
            st.info("📭 No new announcements")
    except Exception as e:
        st.error("Unable to load announcements")


def _render_quick_stats_section(home_components: HomeComponents):
    """Render the quick stats section."""
    st.subheader("📊 Quick Stats")
    
    try:
        stats = home_components.get_student_stats()
        
        if stats and stats[0] > 0:
            st.metric("Questions Answered", stats[0])
            st.metric("Average Accuracy", f"{stats[1]:.1f}%")
            st.metric("Study Consistency", f"{stats[2]:.0f}%")
        else:
            st.info("🚀 Start your first quiz to see stats!")
            if st.button("▶️ Begin", use_container_width=True, type="primary"):
                st.switch_page("pages/quiz.py")
    except Exception as e:
        st.info("📊 Stats will appear after your first quiz")


def _render_parent_link_section():
    """Render the parent link section."""
    st.divider()
    st.subheader("👨‍👩‍👧‍👦 Parent Link")
    
    if st.session_state.get("link_code"):
        st.code(st.session_state.link_code, language=None)
        st.caption("📤 Share this code with your parents")
    else:
        st.info("Link code not available")


if __name__ == "__main__":
    main()