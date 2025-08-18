# FILE: pages/auth.py

import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager
from src.auth.auth_handlers import AuthHandlers, AuthenticationError, save_user_session

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
    """Main authentication page."""
    st.set_page_config(
        page_title="Learning Gap Identifier - Login",
        page_icon="🎓",
        layout="centered"
    )
    
    # Initialize cookie manager
    cookies = EncryptedCookieManager(
        prefix="eduapp_", 
        password="some_secure_password_min_32_chars_long"
    )
    if not cookies.ready():
        st.stop()
    
    # Initialize auth handler
    auth_handler = AuthHandlers(BACKEND_URL)
    
    # Check if already logged in
    if st.session_state.get("user_id"):
        st.success("✅ You are already logged in!")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🏠 Go to Home", type="primary", use_container_width=True):
                st.switch_page("app.py")
        with col2:
            if st.button("🚪 Logout", use_container_width=True):
                _handle_logout(cookies)
                st.rerun()
        st.stop()
    
    # Main authentication UI
    _render_auth_header()
    _render_auth_tabs(auth_handler, cookies)
    _render_auth_footer()


def _render_auth_header():
    """Render the authentication page header."""
    st.title("🎓 Learning Gap Identifier")
    st.subheader("Welcome! Please login or register to continue")
    st.markdown("---")


def _render_auth_tabs(auth_handler: AuthHandlers, cookies):
    """Render login and registration tabs."""
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])
    
    with tab1:
        _render_login_form(auth_handler, cookies)
    
    with tab2:
        _render_register_form(auth_handler, cookies)


def _render_login_form(auth_handler: AuthHandlers, cookies):
    """Render the login form."""
    with st.form("login_form", clear_on_submit=False):
        st.write("**Login to your account**")
        
        # Input fields
        username = st.text_input(
            "Username", 
            placeholder="Enter your username",
            key="login_username"
        )
        password = st.text_input(
            "Password", 
            type="password",
            placeholder="Enter your password", 
            key="login_password"
        )
        role = st.selectbox(
            "I am a:", 
            ["student", "parent", "teacher"],
            key="login_role"
        )
        
        # Submit button
        submitted = st.form_submit_button(
            "🚀 Login", 
            type="primary", 
            use_container_width=True
        )
        
        if submitted:
            _handle_login(auth_handler, username, password, role, cookies)


def _render_register_form(auth_handler: AuthHandlers, cookies):
    """Render the registration form."""
    with st.form("register_form", clear_on_submit=False):
        st.write("**Create a new account**")
        
        # Input fields
        username = st.text_input(
            "Choose a username",
            placeholder="Enter a unique username",
            key="register_username"
        )
        password = st.text_input(
            "Choose a password",
            type="password",
            placeholder="Enter a secure password",
            key="register_password"
        )
        confirm_password = st.text_input(
            "Confirm password",
            type="password",
            placeholder="Re-enter your password",
            key="register_confirm_password"
        )
        role = st.selectbox(
            "I am a:",
            ["student", "parent", "teacher"],
            key="register_role"
        )
        
        # Submit button
        submitted = st.form_submit_button(
            "✨ Create Account", 
            type="primary", 
            use_container_width=True
        )
        
        if submitted:
            _handle_register(
                auth_handler, username, password, confirm_password, role, cookies
            )


def _render_auth_footer():
    """Render authentication page footer."""
    st.markdown("---")
    
    with st.expander("ℹ️ Need Help?"):
        st.write("**First time here?**")
        st.write("• **Students**: Register with your name and create a password")
        st.write("• **Parents**: Register to monitor your child's progress")
        st.write("• **Teachers**: Register to create classes and assignments")
        
        st.write("**Forgot your password?**")
        st.write("Contact your teacher or administrator for assistance.")


def _handle_login(auth_handler: AuthHandlers, username: str, password: str, role: str, cookies):
    """Handle login form submission."""
    # Validation
    if not username.strip():
        st.error("❌ Please enter your username.")
        return
    
    if not password.strip():
        st.error("❌ Please enter your password.")
        return
    
    # Attempt login
    try:
        with st.spinner("🔄 Logging in..."):
            user_data = auth_handler.login_user(username, password)
            
            # Verify role matches
            if user_data.get("role") != role:
                st.error("❌ Invalid credentials or wrong role selected.")
                return
            
            # Save session and redirect
            save_user_session(user_data, cookies)
            st.success("✅ Logged in successfully!")
            st.balloons()
            
            # Small delay to show success message
            import time
            time.sleep(1)
            st.switch_page("app.py")
            
    except AuthenticationError as e:
        st.error(f"❌ {str(e)}")
    except Exception as e:
        st.error("❌ An unexpected error occurred. Please try again.")
        st.exception(e)  # For debugging


def _handle_register(auth_handler: AuthHandlers, username: str, password: str, 
                    confirm_password: str, role: str, cookies):
    """Handle registration form submission."""
    # Validation
    if not username.strip():
        st.error("❌ Username cannot be empty!")
        return
    
    if len(username) < 3:
        st.error("❌ Username must be at least 3 characters long!")
        return
    
    if len(password) < 4:
        st.error("❌ Password must be at least 4 characters long!")
        return
    
    if password != confirm_password:
        st.error("❌ Passwords don't match!")
        return
    
    # Attempt registration
    try:
        with st.spinner("🔄 Creating account..."):
            link_code = auth_handler.register_user(username, password, role)
            
            # Show success message with link code for students
            if role == "student" and link_code:
                st.success("✅ Account created successfully!")
                st.info(f"📝 Your student link code: **{link_code}**")
                st.info("💡 Share this code with your parents so they can monitor your progress!")
            else:
                st.success("✅ Account created successfully!")
            
            # Auto-login after successful registration
            user_data = auth_handler.login_user(username, password)
            save_user_session(user_data, cookies)
            
            st.success("🔄 Automatically logged in!")
            st.balloons()
            
            # Small delay to show success message
            import time
            time.sleep(1)
            st.switch_page("app.py")
            
    except AuthenticationError as e:
        st.error(f"❌ {str(e)}")
    except Exception as e:
        st.error("❌ An unexpected error occurred. Please try again.")
        st.exception(e)  # For debugging


def _handle_logout(cookies):
    """Handle user logout."""
    from src.auth.auth_handlers import clear_user_session
    clear_user_session(cookies)
    st.success("👋 Logged out successfully!")


if __name__ == "__main__":
    main()