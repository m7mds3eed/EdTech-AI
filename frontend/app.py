# FILE: app.py (New streamlined version)

import streamlit as st
from src.auth.session import restore_session_from_cookie, get_cookie_manager
from src.auth.auth_handlers import initialize_session_state
from src.ui.navigation import render_sidebar
from src.auth.auth_handlers import clear_user_session

# --- Configuration ---
BACKEND_URL = "http://127.0.0.1:8000"  # Or use os.environ.get for production

def main():
    """Main application entry point and router."""
    
    # Page configuration
    st.set_page_config(
        page_title="Learning Gap Identifier",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Hide default Streamlit navigation
    _hide_streamlit_nav()
    
    # Initialize cookie manager
    cookies = get_cookie_manager()
    
    # Initialize session state
    initialize_session_state()
    
    # Restore session from cookie if available
    restore_session_from_cookie(BACKEND_URL)
    
    # Route to appropriate page based on authentication status
    if not st.session_state.get("user_id"):
        # User not logged in - redirect to auth page
        st.switch_page("pages/auth.py")
    else:
        # User logged in - show role-specific home page
        _render_authenticated_app()


def _hide_streamlit_nav():
    """Hide default Streamlit navigation elements."""
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)


def _render_authenticated_app():
    """Render the main application for authenticated users."""
    # Set current page for navigation highlighting
    st.session_state.current_page = "app"
    
    # Render sidebar navigation
    render_sidebar("app", BACKEND_URL)
    
    # Route to role-specific home page
    user_role = st.session_state.role
    
    if user_role == "student":
        st.switch_page("pages/student_home.py")
    elif user_role == "parent":
        st.switch_page("pages/parent_home.py")
    elif user_role == "teacher":
        st.switch_page("pages/teacher_home.py")
    else:
        # Handle unknown role
        st.error(f"❌ Unknown user role: {user_role}")
        st.info("Please contact support or try logging in again.")
        
        if st.button("🚪 Logout and Try Again"):
            cookies = get_cookie_manager()


if __name__ == "__main__":
    main()