import streamlit as st
import sqlite3
import secrets
from datetime import datetime, timedelta

def create_session(user_id):
    """Create a new session token"""
    token = secrets.token_hex(16)
    conn = sqlite3.connect("data/math.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO sessions (user_id, token, created_at, last_activity)
        VALUES (?, ?, ?, ?)
    """, (user_id, token, datetime.now(), datetime.now()))
    conn.commit()
    conn.close()
    return token

def validate_session():
    """Validate current session"""
    if "session_token" not in st.session_state:
        return False
    
    conn = sqlite3.connect("data/math.db")
    c = conn.cursor()
    c.execute("""
        SELECT user_id, last_activity FROM sessions 
        WHERE token = ? AND created_at > ?
    """, (st.session_state.session_token, 
          (datetime.now() - timedelta(days=7)).isoformat()))
    
    result = c.fetchone()
    if result:
        # Update last activity
        c.execute("""
            UPDATE sessions SET last_activity = ? 
            WHERE token = ?
        """, (datetime.now().isoformat(), st.session_state.session_token))
        conn.commit()
    conn.close()
    
    return result is not None