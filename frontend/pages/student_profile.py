import streamlit as st
import requests
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
from src.ui.feedback import render_feedback_widget
from src.auth.session import restore_session_from_cookie,get_cookie_manager
from src.ui.navigation import render_sidebar

# --- Configuration ---
BACKEND_URL = "http://127.0.0.1:8000"  # Or use os.environ.get for production
# --- ADD THIS BLOCK TO THE TOP OF THE PAGE ---
cookies = get_cookie_manager()


restore_session_from_cookie( BACKEND_URL)
# --- END OF BLOCK ---

# --- Hide default Streamlit navigation ---
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)




if "user_id" not in st.session_state or st.session_state.role != "student":
    st.error("Please log in as a student to access your profile.")
    st.stop()

# --- Authentication and Sidebar ---
# Set current page for navigation
st.session_state.current_page = "student_profile"
render_sidebar("student_profile", BACKEND_URL)

# REPLACE the get_student_insights() function in student_profile.py with this:

def get_student_insights():
    """Get comprehensive student insights via backend."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.get(f"{BACKEND_URL}/analytics/student-progress", headers=headers)
        response.raise_for_status()
        data = response.json()
        
        overall_stats = data.get("overall_stats", {})
        topic_progress = data.get("topic_progress", [])
        account_created = data.get("account_created", datetime.now().isoformat())
        
        # --- Data Processing ---
        
        # Strengths: mastery > 70%, attempts >= 3
        strengths = sorted(
            [
                {
                    "topic": tp["topic"],
                    "mastery": tp["mastery_level"],
                    "attempts": tp["questions_answered"]
                }
                for tp in topic_progress if tp.get("mastery_level", 0) > 70 and tp.get("questions_answered", 0) >= 3
            ],
            key=lambda x: x["mastery"], reverse=True
        )[:5]
        
        # Weaknesses: mastery < 50%, attempts >= 2
        weaknesses = sorted(
            [
                {
                    "topic": tp["topic"],
                    "mastery": tp["mastery_level"],
                    "attempts": tp["questions_answered"],
                    "wrong": tp.get("questions_answered", 0) - tp.get("correct_answers", 0)
                }
                for tp in topic_progress if tp.get("mastery_level", 0) < 50 and tp.get("questions_answered", 0) >= 2
            ],
            key=lambda x: x["mastery"]
        )[:5]

        # --- Activity and Consistency Calculation (now from backend) ---
        recent_activity = []
        if topic_progress:
            df = pd.DataFrame(topic_progress)
            # Gracefully handle any invalid date formats
            df['date'] = pd.to_datetime(df['last_attempt'], errors='coerce')
            df.dropna(subset=['date'], inplace=True)
            
            # Only proceed if there are valid dates left after cleaning
            if not df.empty:
                recent_activity = df.groupby(df['date'].dt.date).agg(
                    questions_answered=('questions_answered', 'sum'),
                    accuracy=('accuracy', 'mean')
                ).reset_index().to_dict('records')

        # --- Final Data Assembly (now using backend data) ---
        overall = (
            overall_stats.get("total_questions", 0),
            overall_stats.get("correct_answers", 0),
            overall_stats.get("avg_mastery", 0),
            overall_stats.get("topics_attempted", 0),
            overall_stats.get("hints_used", 0),  # Now correctly from backend
            overall_stats.get("lessons_viewed", 0),  # Now correctly from backend
            overall_stats.get("active_days", 0)
        )
        
        return {
            "overall": overall,
            "account_created": account_created,  # Now actual creation date
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recent_activity": recent_activity,
            "consistency": overall_stats.get("consistency", 0)  # Now from backend
        }

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching insights: {e}")
        return {
            "overall": (0, 0, 0, 0, 0, 0, 0),
            "account_created": datetime.now().isoformat(),
            "strengths": [],
            "weaknesses": [],
            "recent_activity": [],
            "consistency": 0
        }

# Main dashboard
st.title("📊 Your Learning Dashboard")

# Display link code from session
if "link_code" in st.session_state:
    st.info(f"👨‍👩‍👧‍👦 **Your Parent Link Code:** `{st.session_state.link_code}` (Share this with your parents)")
else:
    st.warning("Link code not available. Please log in again.")

insights = get_student_insights()

# Overall performance metrics
st.subheader("🎯 Your Progress Overview")

if insights["overall"][0] > 0:  # Has answered questions
    col1, col2, col3, col4 = st.columns(4)
    
    total_questions = insights["overall"][0]
    correct_answers = insights["overall"][1]
    avg_mastery = insights["overall"][2] or 0
    topics_attempted = insights["overall"][3]
    hints_used = insights["overall"][4]
    lessons_viewed = insights["overall"][5]
    active_days = insights["overall"][6]
    
    accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    
    with col1:
        st.metric("Questions Answered", total_questions)
    with col2:
        st.metric("Accuracy", f"{accuracy:.1f}%")
    with col3:
        st.metric("Average Mastery", f"{avg_mastery:.1f}%")
    with col4:
        st.metric("Topics Explored", topics_attempted)
    
    # Calculate consistency based on approximated account creation
    if insights["account_created"]:
        created_date = datetime.fromisoformat(insights["account_created"])
        days_since_creation = (datetime.now() - created_date).days + 1
        consistency = (active_days / days_since_creation * 100) if days_since_creation > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Study Consistency", f"{consistency:.0f}%", 
                     help=f"You've been active {active_days} out of {days_since_creation} days since joining")
        with col2:
            st.metric("Hints Used", hints_used)
        with col3:
            st.metric("Lessons Viewed", lessons_viewed)
    
    # Recent activity chart
    if insights["recent_activity"]:
        st.subheader("📈 Your Activity This Week")
        df_activity = pd.DataFrame(insights["recent_activity"])
        df_activity['date'] = pd.to_datetime(df_activity['date'])
        
        fig = px.bar(df_activity, x='date', y='questions_answered', 
                     title="Questions Answered Per Day",
                     color='accuracy', 
                     color_continuous_scale='RdYlGn',
                     range_color=[0, 100])
        fig.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    # Strengths and weaknesses
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🌟 Your Strengths")
        if insights["strengths"]:
            strength_summary = f"You're doing great in {len(insights['strengths'])} topics! "
            if len(insights["strengths"]) >= 3:
                strength_summary += "Keep up the excellent work! 🎉"
            else:
                strength_summary += "Practice more to unlock additional strengths! 💪"
            
            st.success(strength_summary)
            
            for strength in insights["strengths"][:3]:  # Show top 3
                st.write(f"**{strength['topic']}** - {strength['mastery']:.1f}% mastery ({strength['attempts']} questions)")
                
            if len(insights["strengths"]) > 3:
                with st.expander(f"View {len(insights['strengths']) - 3} more strengths"):
                    for strength in insights["strengths"][3:]:
                        st.write(f"**{strength['topic']}** - {strength['mastery']:.1f}% mastery")
        else:
            st.info("💡 Keep practicing to identify your strengths! Answer at least 3 questions per topic.")
    
    with col2:
        st.subheader("📚 Areas to Improve")
        if insights["weaknesses"]:
            weakness_summary = f"Focus on {len(insights['weaknesses'])} topics to boost your overall performance. "
            if len(insights['weaknesses']) <= 2:
                weakness_summary += "You're almost there! 🚀"
            else:
                weakness_summary += "Start with the lowest mastery topics first. 📖"
            
            st.warning(weakness_summary)
            
            for weakness in insights["weaknesses"][:3]:  # Show top 3 to improve
                st.write(f"**{weakness['topic']}** - {weakness['mastery']:.1f}% mastery")
                st.caption(f"Got {weakness['wrong']} wrong out of {weakness['attempts']} attempts")
                
            if len(insights["weaknesses"]) > 3:
                with st.expander(f"View {len(insights['weaknesses']) - 3} more areas to improve"):
                    for weakness in insights["weaknesses"][3:]:
                        st.write(f"**{weakness['topic']}** - {weakness['mastery']:.1f}% mastery")
        else:
            st.success("🎉 No major weak areas identified! You're doing great!")
    
    # Action buttons
    st.divider()
    st.subheader("🚀 What's Next?")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📝 Practice Weak Areas", type="primary", use_container_width=True):
            if insights["weaknesses"]:
                # Get the weakest topic
                weakest_topic = insights["weaknesses"][0]["topic"]
                
                # Composite: Get structure to find subject/micro
                try:
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    response = requests.get(f"{BACKEND_URL}/topics/structure", headers=headers)
                    response.raise_for_status()
                    curriculum = response.json().get("curriculum", [])
                    
                    subject = None
                    micro_topic = None
                    for top in curriculum:
                        for sub in top.get("subtopics", []):
                            for mic in sub.get("micro_topics", []):
                                for nan in mic.get("nano_topics", []):
                                    if nan["name"] == weakest_topic:
                                        subject = top["name"]
                                        micro_topic = mic["name"]
                                        break
                                if subject: break
                            if subject: break
                        if subject: break
                    
                    if subject and micro_topic:
                        st.session_state.current_subject = subject
                        st.session_state.current_micro_topic = micro_topic
                        st.switch_page("pages/quiz.py")
                    else:
                        st.error("Could not find topic details. Starting general quiz.")
                        st.switch_page("pages/quiz.py")
                except requests.exceptions.RequestException as e:
                    st.error(f"Error finding topic: {e}")
                    st.switch_page("pages/quiz.py")
            else:
                st.switch_page("pages/quiz.py")
    
    with col2:
        if st.button("📋 Check Assignments", use_container_width=True):
            st.switch_page("pages/student_assignments.py")
    
    with col3:
        if st.button("🎯 Free Practice", use_container_width=True):
            st.switch_page("pages/quiz.py")

else:
    # No activity yet
    st.info("👋 Welcome! Start your first quiz to see your personalized dashboard.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Start Your First Quiz", type="primary", use_container_width=True):
            st.switch_page("pages/quiz.py")
    with col2:
        if st.button("📋 Check for Assignments", use_container_width=True):
            st.switch_page("pages/student_assignments.py")