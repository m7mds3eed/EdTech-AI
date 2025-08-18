import streamlit as st
from functools import wraps

def require_role(allowed_roles):
    """Decorator to check if user has required role"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if "role" not in st.session_state:
                st.error("Please log in to access this page.")
                st.stop()
            if st.session_state.role not in allowed_roles:
                st.error(f"Access denied. This page is only for {', '.join(allowed_roles)}s.")
                st.stop()
            return func(*args, **kwargs)
        return wrapper
    return decorator

def check_permission(allowed_roles):
    """Check if current user has permission"""
    if "role" not in st.session_state:
        return False
    return st.session_state.role in allowed_roles