import streamlit as st
import requests
from datetime import datetime

# --- Configuration ---
BACKEND_URL = "http://127.0.0.1:8000"  # Or use os.environ.get for production

def render_feedback_widget(context="general", compact=False):
    """
    Renders a feedback widget that can be used anywhere in the app.
    
    Args:
        context (str): A string to identify where the feedback is coming from (e.g., 'sidebar', 'quiz_results').
        compact (bool): If True, renders the widget inside an expander.
    """
    container = st.expander("💬 Give Feedback") if compact else st
    
    with container:
        if not compact:
            st.subheader("💬 Give Feedback")
            
        feedback = st.text_area(
            "How can we improve the app?",
            placeholder="Share your thoughts, suggestions, or any issues you've encountered...",
            key=f"feedback_text_{context}"
        )
        
        rating = st.slider(
            "How would you rate your experience?",
            min_value=1,
            max_value=10,
            value=7,
            key=f"rating_{context}"
        )

        if st.button("Submit Feedback", key=f"submit_feedback_{context}"):
            if feedback.strip():
                save_feedback(
                    feedback_text=feedback,
                    rating=rating,
                    context=context,
                    role=st.session_state.get("role", "anonymous")
                )
                st.success("Thank you for your feedback! We appreciate you helping us improve.")
                st.balloons()
            else:
                st.warning("Please enter some feedback before submitting.")

def save_feedback(feedback_text, rating, context, role):
    """Saves user feedback via backend API."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        payload = {
            "feedback_text": feedback_text,
            "rating": rating,
            "context": context
        }
        response = requests.post(f"{BACKEND_URL}/feedback/submit", headers=headers, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        st.error(f"Error submitting feedback: {e}")