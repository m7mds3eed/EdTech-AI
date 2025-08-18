# FILE: src/auth/auth_handlers.py

import streamlit as st
import requests
from datetime import datetime


class AuthenticationError(Exception):
    """Custom exception for authentication-related errors."""
    pass


class AuthHandlers:
    """Centralized authentication API handlers."""
    
    def __init__(self, backend_url: str):
        self.backend_url = backend_url
    
    def login_user(self, username: str, password: str) -> dict:
        """
        Authenticate user against the backend.
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            dict: User data including user_id, role, link_code, token
            
        Raises:
            AuthenticationError: If login fails
        """
        try:
            response = requests.post(
                f"{self.backend_url}/auth/login",
                json={"username": username, "password": password},
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid username or password")
            elif e.response.status_code == 403:
                raise AuthenticationError("Account is disabled or suspended")
            else:
                raise AuthenticationError(f"Login failed: {e}")
        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"Connection error: Unable to reach server")
    
    def register_user(self, username: str, password: str, role: str) -> str:
        """
        Register a new user via the backend.
        
        Args:
            username: Desired username
            password: User's password
            role: User role (student, parent, teacher)
            
        Returns:
            str: Link code for students, None for other roles
            
        Raises:
            AuthenticationError: If registration fails
        """
        try:
            response = requests.post(
                f"{self.backend_url}/auth/register",
                json={"username": username, "password": password, "role": role},
                timeout=10
            )
            response.raise_for_status()
            return response.json().get("link_code")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:
                raise AuthenticationError("Username already exists. Please choose a different one.")
            elif e.response.status_code == 400:
                error_detail = e.response.json().get("detail", "Invalid registration data")
                raise AuthenticationError(f"Registration failed: {error_detail}")
            else:
                raise AuthenticationError(f"Registration failed: {e}")
        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"Connection error: Unable to reach server")
    
    def validate_token(self, token: str) -> dict:
        """
        Validate an authentication token with the backend.
        
        Args:
            token: JWT authentication token
            
        Returns:
            dict: User data if token is valid
            
        Raises:
            AuthenticationError: If token is invalid
        """
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                f"{self.backend_url}/auth/me",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Session expired. Please log in again.")
            else:
                raise AuthenticationError(f"Token validation failed: {e}")
        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"Connection error: Unable to validate session")
    
    def link_parent_to_student(self, link_code: str, token: str) -> bool:
        """
        Link parent to student via backend.
        
        Args:
            link_code: Student's unique link code
            token: Parent's authentication token
            
        Returns:
            bool: True if linking successful
            
        Raises:
            AuthenticationError: If linking fails
        """
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.post(
                f"{self.backend_url}/auth/link-parent",
                headers=headers,
                json={"link_code": link_code},
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise AuthenticationError("Invalid link code. Please check with your child.")
            elif e.response.status_code == 409:
                raise AuthenticationError("Already linked to this student.")
            else:
                raise AuthenticationError(f"Linking failed: {e}")
        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"Connection error: Unable to link accounts")
    
    def join_class(self, class_code: str, token: str) -> tuple[bool, str]:
        """
        Join a class using class code.
        
        Args:
            class_code: Teacher's class code
            token: Student's authentication token
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.post(
                f"{self.backend_url}/classes/join",
                headers=headers,
                json={"class_code": class_code},
                timeout=10
            )
            
            if response.status_code == 200:
                return True, "Successfully joined class!"
            elif response.status_code == 400:
                return False, "Already enrolled in this class. Check with teacher."
            elif response.status_code == 404:
                return False, "Invalid class code. Please check with your teacher."
            else:
                detail = response.json().get('detail', 'Unknown error')
                return False, f"Error joining: {detail}"
                
        except requests.exceptions.RequestException as e:
            return False, f"Connection error: {e}"


# Utility functions for session management
def save_user_session(user_data: dict, cookies) -> None:
    """Save user session data."""
    if not cookies.ready():
        # Show a spinner and stop execution until the component is ready
        st.spinner("Initializing session...") 
        st.stop()
    st.session_state.user_id = user_data["user_id"]
    st.session_state.role = user_data["role"]
    st.session_state.link_code = user_data.get("link_code")
    st.session_state.token = user_data["token"]
    
    # Save to cookies for persistence
    cookies["auth_token"] = user_data["token"]
    cookies.save()


def clear_user_session(cookies) -> None:
    """Clear user session data."""
    # Clear session state
    session_keys = [
        "user_id", "role", "link_code", "token", "points", "results", 
        "bkt", "badge", "current_subject", "current_micro_topic", 
        "question_queue"
    ]
    
    for key in session_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    # Clear cookies
    if "auth_token" in cookies:
        del cookies["auth_token"]
        cookies.save()


def initialize_session_state() -> None:
    """Initialize all required session state variables."""
    defaults = {
        "user_id": None,
        "role": None,
        "points": 0,
        "results": {"strengths": [], "weaknesses": []},
        "bkt": {},
        "badge": None,
        "current_subject": None,
        "current_micro_topic": None,
        "question_queue": [],
        "link_code": None,
        "token": None
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value