import streamlit as st
import requests
from src.ui.feedback import render_feedback_widget
# from streamlit_cookies_manager import EncryptedCookieManager
from src.auth.session import get_cookie_manager

def render_sidebar(current_page="app", backend_url="http://127.0.0.1:8000"):
    """
    Universal sidebar navigation component for all pages.
    
    Args:
        current_page (str): The current page identifier (e.g., "app", "quiz", "student_profile")
        backend_url (str): Backend URL for API calls
    """
    
    # Define navigation structure for each role
    navigation_config = {
        "student": [
            {"label": "🏠 Home", "page": "app", "file": "app.py"},
            {"label": "📚 Start Quiz", "page": "quiz", "file": "pages/quiz.py", "primary": True},
            {"label": "📋 My Assignments", "page": "student_assignments", "file": "pages/student_assignments.py"},
            {"label": "👤 My Profile", "page": "student_profile", "file": "pages/student_profile.py"}
        ],
        "parent": [
            {"label": "🏠 Home", "page": "app", "file": "app.py"},
            {"label": "📊 Parent Dashboard", "page": "parent_dashboard", "file": "pages/parent_dashboard.py", "primary": True}
        ],
        "teacher": [
            {"label": "🏠 Home", "page": "app", "file": "app.py"},
            {"label": "👩‍🏫 Manage Classes", "page": "teacher_dashboard", "file": "pages/teacher_dashboard.py", "primary": True},
            {"label": "📈 Class Reports", "page": "teacher_reports", "file": "pages/teacher_reports.py"}
        ]
    }
    
    with st.sidebar:
        st.header("🧭 Navigation")
        
        # Check if user is logged in
        if not st.session_state.get("user_id") or not st.session_state.get("role"):
            st.error("Please log in to access navigation.")
            return
            
        st.success(f"👋 Welcome, {st.session_state.role.capitalize()}!")

        # Render role-based navigation buttons
        user_role = st.session_state.role
        if user_role in navigation_config:
            for nav_item in navigation_config[user_role]:
                # Determine if this button should be highlighted (current page)
                is_current = nav_item["page"] == current_page
                button_type = "primary" if nav_item.get("primary", False) and not is_current else "secondary" if is_current else "tertiary"
                
                # Create unique key for each button
                button_key = f"nav_{nav_item['page']}_{current_page}"
                
                if st.button(
                    nav_item["label"], 
                    use_container_width=True, 
                    type=button_type,
                    key=button_key,
                    disabled=is_current  # Disable current page button to show it's active
                ):
                    # Clear quiz-related state when navigating away from quiz
                    if current_page == "quiz" and nav_item["page"] != "quiz":
                        _clear_quiz_state()
                    
                    st.switch_page(nav_item["file"])

        st.divider()

        # AI Assistant - Available to all roles
        ai_button_key = f"ai_assistant_{current_page}"
        is_ai_page = current_page == "ai_admin"
        
        if st.button(
            "🤖 AI Assistant", 
            use_container_width=True, 
            type="primary" if not is_ai_page else "secondary",
            key=ai_button_key,
            disabled=is_ai_page
        ):
            st.switch_page("pages/ai_admin.py")

        st.caption("💡 Need help? Ask our AI Assistant!")
        
        # Student-specific privacy section
        if user_role == "student":
            _render_student_privacy_section(backend_url)
        
        # Universal feedback widget
        render_feedback_widget(context=f"sidebar_{current_page}", compact=True)
        
        st.divider()
        
        # Logout button
        logout_key = f"logout_{current_page}"
        if st.button("🚪 Logout", type="secondary", use_container_width=True, key=logout_key):
            _handle_logout()

def _clear_quiz_state():
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

def _render_student_privacy_section(backend_url):
    """Render privacy information section for students."""
    with st.expander("🔒 Privacy & Access"):
        # This function would need to be implemented or moved from your existing code
        try:
            parents, teachers = _get_student_privacy_info(st.session_state.user_id, backend_url)
            
            st.write("**Who can see your data:**")
            if parents:
                st.write("👨‍👩‍👧‍👦 **Parents:**")
                for parent in parents:
                    st.write(f"• {parent['username']}")
            else:
                st.write("👨‍👩‍👧‍👦 **Parents:** None linked")
            
            if teachers:
                st.write("👩‍🏫 **Teachers:**")
                for teacher in teachers:
                    st.write(f"• {teacher['username']} ({teacher['class']})")
            else:
                st.write("👩‍🏫 **Teachers:** None")
        except Exception as e:
            st.caption("Privacy info temporarily unavailable")

def _get_student_privacy_info(student_id, backend_url):
    """Get privacy information for student. Placeholder implementation."""
    # This should be implemented based on your backend API
    # For now, returning empty lists as in your original code
    return [], []

def _handle_logout():
    """Handle user logout process."""
    # Clear cookies if available
    try:
        cookies = get_cookie_manager()
        if cookies.ready() and "auth_token" in cookies:
            del cookies["auth_token"]
            cookies.save()
    except ImportError:
        pass  # Cookie manager not available
    
    # Clear all session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
    st.rerun()