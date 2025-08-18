# FILE: src/auth/session.py

import streamlit as st
import requests
from streamlit_cookies_manager import EncryptedCookieManager

def get_cookie_manager():
    """
    Returns a singleton instance of the EncryptedCookieManager.
    """
    # Check if the cookie manager is already in session_state
    if 'cookie_manager' not in st.session_state:
        # If not, create a new instance and store it
        st.session_state.cookie_manager = EncryptedCookieManager(
            prefix="eduapp_",
            password="some_secure_password_min_32_chars_long"
        )
    # Return the existing instance
    return st.session_state.cookie_manager

def restore_session_from_cookie(backend_url):
    """
    Checks for an auth token in cookies and validates it with the backend.
    """
    print("--- CHECKPOINT 1: restore_session_from_cookie() CALLED ---")
    cookies = get_cookie_manager()
    
    if not cookies.ready():
        # If not ready, exit the function and wait for the next rerun.
        # The component will set the cookie value then trigger a rerun.
        return

    token = cookies.get("auth_token")

    if token and "user_id" not in st.session_state:
        if st.session_state.get("user_id") is None:
            print("--- CHECKPOINT 2: User not logged in, checking for cookie. ---")
            token = cookies.get("auth_token")

            if token:
                print(f"--- CHECKPOINT 3: Found token in cookie: {token[:10]}... ---")
                try:
                    headers = {"Authorization": f"Bearer {token}"}
                    print("--- CHECKPOINT 4: Calling backend at /auth/me to validate. ---")
                    response = requests.get(f"{backend_url}/auth/me", headers=headers)
                    print(f"--- CHECKPOINT 5: Backend responded with Status Code: {response.status_code} ---")

                    if response.status_code == 200:
                        print("--- CHECKPOINT 6: Token is VALID. Populating session state. ---")
                        user_data = response.json()
                        st.session_state.user_id = user_data["id"]
                        st.session_state.role = user_data["role"]
                        st.session_state.token = token
                        st.session_state.link_code = user_data.get("link_code")
                        print(f"--- CHECKPOINT 7: Session state populated for user_id: {st.session_state.user_id} ---")
                    else:
                        print("--- CHECKPOINT 8: Token INVALID. Deleting cookie. ---")
                        del cookies["auth_token"]
                except requests.exceptions.RequestException as e:
                    print(f"--- CHECKPOINT 9: API call FAILED. Error: {e} ---")
                    del cookies["auth_token"]
            else:
                print("--- CHECKPOINT 10: No auth_token cookie found. ---")
        else:
            print(f"--- CHECKPOINT 11: Session already active for user_id: {st.session_state.get('user_id')}. No action needed. ---")

