# ============================================================================
# FILE: pages/teacher_home.py

import streamlit as st
import requests
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
    """Teacher home page."""
    st.set_page_config(
        page_title="Teacher Home - Learning Gap Identifier",
        page_icon="👩‍🏫",
        layout="wide"
    )
    
    # Check authentication
    if not st.session_state.get("user_id") or st.session_state.get("role") != "teacher":
        st.error("❌ Access denied. Please log in as a teacher.")
        st.switch_page("pages/auth.py")
    
    # Initialize components
    home_components = HomeComponents(BACKEND_URL)
    
    # Render sidebar
    render_sidebar("app", BACKEND_URL)
    
    # Main content
    st.title("🎓 Learning Gap Identifier")
    st.header("👩‍🏫 Teacher Dashboard")
    st.write("Manage your classes, create assignments, and track student progress.")
    
    st.divider()
    
    # Class Dashboard Section
    st.subheader("🏫 Your Classes")
    
    try:
        classes = home_components.get_teacher_classes()
        
        if not classes:
            st.info("You haven't created any classes yet. Use the sidebar to go to 'Manage Classes' to create one!")
        else:
            # Calculate and display aggregate stats
            num_classes = len(classes)
            total_students = sum(c.get('student_count', 0) for c in classes)
            
            stat_col1, stat_col2 = st.columns(2)
            stat_col1.metric("Total Classes", num_classes)
            stat_col2.metric("Total Students Enrolled", total_students)
            
            st.divider()
            
            # Display individual class details
            for cls in classes:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.subheader(cls.get("name", "Unnamed Class"))
                        student_count = cls.get("student_count", 0)
                        st.caption(f"👥 {student_count} student(s) enrolled")
                    with col2:
                        st.write("**Class Code:**")
                        st.code(cls.get("class_code", "N/A"))
                    with col3:
                        if st.button("View Details", key=f"details_{cls.get('id')}", use_container_width=True):
                            st.session_state.selected_class_id = cls.get('id')
                            st.info(f"Navigate to details for class ID: {cls.get('id')}")
                            # Example navigation: st.switch_page("pages/teacher_class_details.py")
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            st.error("🚨 Your session has expired. Please log out and log in again.")
            if st.button("Logout to Refresh Session", key="teacher_logout_btn"):
                home_components.handle_session_expired()
        else:
            st.error(f"Could not load your classes: {e}")
    except requests.exceptions.RequestException as e:
        st.error(f"A connection error occurred while fetching classes: {e}")


if __name__ == "__main__":
    main()