# FILE: pages/parent_home.py

import streamlit as st
from src.ui.navigation import render_sidebar
from src.ui.home_components import HomeComponents
from src.auth.session import get_cookie_manager

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
    """Parent home page."""
    st.set_page_config(
        page_title="Parent Home - Learning Gap Identifier",
        page_icon="👨‍👩‍👧‍👦",
        layout="wide"
    )
    
    # Check authentication
    if not st.session_state.get("user_id") or st.session_state.get("role") != "parent":
        st.error("❌ Access denied. Please log in as a parent.")
        st.switch_page("pages/auth.py")
    
    # Initialize components
    home_components = HomeComponents(BACKEND_URL)
    
    # Render sidebar
    render_sidebar("app", BACKEND_URL)
    
    # Main content
    st.title("🎓 Learning Gap Identifier")
    st.header("👨‍👩‍👧‍👦 Parent Zone")
    st.write("Monitor your child's learning progress and get insights into their strengths and areas for improvement.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 View Detailed Reports", type="primary", use_container_width=True):
            st.switch_page("pages/parent_dashboard.py")
    
    with col2:
        with st.expander("🔗 Link to a Student Account"):
            link_code = st.text_input("Enter your child's link code")
            if st.button("Link Account"):
                if home_components.link_parent_to_student(link_code):
                    st.success("Successfully linked to student account!")
                    st.rerun()
                else:
                    st.error("Invalid link code or student not found.")


if __name__ == "__main__":
    main()


