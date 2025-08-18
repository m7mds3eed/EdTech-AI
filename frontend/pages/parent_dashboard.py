import streamlit as st
import requests
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
from src.ui.feedback import render_feedback_widget
from src.auth.session import restore_session_from_cookie, get_cookie_manager # <--- IMPORT THE NEW FUNCTION
from src.ui.navigation import render_sidebar
# --- Configuration ---
BACKEND_URL = "http://127.0.0.1:8000"  # Or use os.environ.get for production
# --- ADD THIS BLOCK TO THE TOP OF THE PAGE ---
# cookies = EncryptedCookieManager(prefix="eduapp_", password="some_secure_password_min_32_chars_long")
# if not cookies.ready():
#     st.stop()

cookies = get_cookie_manager()

restore_session_from_cookie(BACKEND_URL)
# --- END OF BLOCK ---

# --- Authentication and Sidebar ---
if "user_id" not in st.session_state or st.session_state.role != "parent":
    st.error("Please log in as a parent to access this page.")
    st.switch_page("app.py")

# Sidebar navigation
# Set current page for navigation
st.session_state.current_page = "parent_dashboard"
render_sidebar("parent_dashboard", BACKEND_URL)

# --- Hide default Streamlit navigation ---
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

def get_linked_students():
    """Get students linked to parent with real IDs and data."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.get(f"{BACKEND_URL}/parent/linked-students", headers=headers)
        response.raise_for_status()
        return response.json().get("students", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching students: {e}")
        return []

def get_student_summary(student_name, time_range_days=None):
    """Get comprehensive student summary with real data (keeping original function name)."""
    # First, find the student ID by name from linked students
    linked_students = get_linked_students()
    student_data = next((s for s in linked_students if s["username"] == student_name), None)
    
    if not student_data:
        return None
    
    student_id = student_data["id"]
    
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.get(f"{BACKEND_URL}/parent/student-analytics/{student_id}", headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("has_data", False):
            return {
                "overall": (0, 0, 0, 0, 0, 0, 0),
                "account_created": data.get("account_created", datetime.now().isoformat()),
                "strengths": [],
                "weaknesses": [],
                "activity": []
            }
        
        overall_stats = data["overall_stats"]
        topic_progress = data["topic_progress"]
        daily_activity = data["daily_activity"]
        
        # Filter daily activity by time range if specified
        if time_range_days and daily_activity:
            cutoff_date = (datetime.now() - timedelta(days=time_range_days)).date()
            daily_activity = [
                activity for activity in daily_activity 
                if datetime.fromisoformat(activity["date"]).date() >= cutoff_date
            ]
        
        # Process strengths and weaknesses
        strengths = [
            tp["topic"] for tp in topic_progress 
            if tp["mastery_level"] > 70 and tp["questions_answered"] >= 3
        ]
        
        weaknesses = [
            {"topic": tp["topic"], "mastery": tp["mastery_level"]}
            for tp in topic_progress 
            if tp["mastery_level"] < 50 and tp["questions_answered"] >= 2
        ]
        
        # Convert to format expected by existing code
        overall = (
            overall_stats["total_questions"],
            overall_stats["correct_answers"],
            overall_stats["avg_mastery"],
            overall_stats["topics_attempted"],
            overall_stats["hints_used"],
            overall_stats["lessons_viewed"],
            overall_stats["active_days"]
        )
        
        return {
            "overall": overall,
            "account_created": data["account_created"],
            "strengths": strengths,
            "weaknesses": weaknesses,
            "activity": daily_activity
        }
        
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching student summary: {e}")
        return None

# Main dashboard
st.title("👨‍👩‍👧‍👦 Parent Dashboard")

linked_students = get_linked_students()

if not linked_students:
    st.warning("👋 Welcome! Let's connect you to your child's account.")
    
    with st.container():
        st.subheader("🔗 Link to Your Child's Account")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            link_code = st.text_input("Enter your child's link code", placeholder="e.g., abc123")
            st.caption("Ask your child for their 6-character link code from their profile.")
        with col2:
            st.write("")  # Spacing
            st.write("")  # Spacing
            if st.button("🔗 Link Account", type="primary"):
                if link_code.strip():
                    try:
                        headers = {"Authorization": f"Bearer {st.session_state.token}"}
                        response = requests.post(f"{BACKEND_URL}/auth/link-parent", headers=headers, json={"link_code": link_code.strip()})
                        response.raise_for_status()
                        st.success("✅ Successfully linked to your child's account!")
                        st.rerun()
                    except requests.exceptions.RequestException as e:
                        st.error("❌ Invalid link code. Please check with your child.")
                else:
                    st.error("Please enter a link code.")
    
    st.info("💡 Once linked, you'll see your child's learning progress, strengths, and areas that need attention.")

else:
    # Student selector
    st.subheader("📊 Select Your Child")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        student = st.selectbox("", [s["username"] for s in linked_students], 
                              format_func=lambda x: f"👤 {x}")
    with col2:
        time_range = st.selectbox("Time Period", ["Last 7 Days", "Last 30 Days", "All Time"])
        time_range_days = {"Last 7 Days": 7, "Last 30 Days": 30, "All Time": None}[time_range]
    
    if student:
        summary = get_student_summary(student, time_range_days)
        
        if summary and summary["overall"][0] > 0:  # Has data
            total_questions = summary["overall"][0]
            correct_answers = summary["overall"][1]
            avg_mastery = summary["overall"][2] or 0
            active_days = summary["overall"][6]
            hints_used = summary["overall"][4]
            lessons_viewed = summary["overall"][5]
            
            accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
            
            # Calculate consistency
            consistency = 0
            if summary["account_created"]:
                created_date = datetime.fromisoformat(summary["account_created"])
                days_since_creation = (datetime.now() - created_date).days + 1
                consistency = (active_days / days_since_creation * 100) if days_since_creation > 0 else 0
            
            # Key metrics
            st.subheader(f"📈 {student}'s Progress Summary")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Questions Answered", total_questions)
            with col2:
                st.metric("Accuracy", f"{accuracy:.0f}%", delta=f"{accuracy-70:.0f}%" if accuracy > 0 else None)
            with col3:
                st.metric("Average Mastery", f"{avg_mastery:.0f}%", delta=f"{avg_mastery-75:.0f}%" if avg_mastery > 0 else None)
            with col4:
                st.metric("Study Consistency", f"{consistency:.0f}%", 
                         help=f"Active {active_days} out of {days_since_creation if summary['account_created'] else '?'} days")
            
            # Activity chart
            if summary["activity"]:
                st.subheader("📊 Daily Activity")
                df_activity = pd.DataFrame(summary["activity"])
                df_activity['date'] = pd.to_datetime(df_activity['date'])
                
                fig = px.bar(df_activity, x='date', y='questions_answered',  # Changed from 'questions' to 'questions_answered'
                            title=f"Questions Answered in {time_range}",
                            color='accuracy', 
                            color_continuous_scale='RdYlGn',
                            range_color=[0, 100])
                fig.update_layout(showlegend=False, height=300)
                st.plotly_chart(fig, use_container_width=True)
            
            # Insights section
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🌟 What They're Good At")
                if summary["strengths"]:
                    strength_message = "Your child is excelling in:\n"
                    for i, strength in enumerate(summary["strengths"], 1):
                        strength_message += f"{i}. **{strength}**\n"
                    strength_message += "\n✅ Keep encouraging practice in these areas!"
                    st.success(strength_message)
                else:
                    st.info("🎯 Your child is building foundational skills. Strengths will appear as they practice more!")
            
            with col2:
                st.subheader("📚 Areas to Focus On")
                if summary["weaknesses"]:
                    weakness_message = "Consider helping with:\n"
                    for i, weakness in enumerate(summary["weaknesses"], 1):
                        weakness_message += f"{i}. **{weakness['topic']}** ({weakness['mastery']:.0f}% mastery)\n"
                    weakness_message += "\n💡 Focus on one topic at a time for best results!"
                    st.warning(weakness_message)
                else:
                    st.success("🎉 No major weak areas identified! Your child is doing great!")
            
            # Help usage insights
            if hints_used > 0 or lessons_viewed > 0:
                st.subheader("🆘 Learning Support Usage")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    hint_rate = (hints_used / total_questions * 100) if total_questions > 0 else 0
                    st.metric("Hint Usage", f"{hint_rate:.0f}%", help=f"Used hints {hints_used} times")
                
                with col2:
                    lesson_rate = (lessons_viewed / total_questions * 100) if total_questions > 0 else 0
                    st.metric("Lesson Views", f"{lesson_rate:.0f}%", help=f"Viewed lessons {lessons_viewed} times")
                
                with col3:
                    if hint_rate > 30:
                        st.warning("High hint usage - may need more foundational practice")
                    elif hint_rate > 15:
                        st.info("Moderate hint usage - shows good help-seeking behavior")
                    else:
                        st.success("Low hint usage - shows strong independent problem-solving")
            
            # Action items
            st.subheader("💡 Recommended Actions")
            
            action_items = []
            
            if accuracy < 60:
                action_items.append("🔴 **Priority:** Schedule daily 15-minute practice sessions")
            elif accuracy < 75:
                action_items.append("🟡 **Focus:** Review incorrect answers together")
            else:
                action_items.append("🟢 **Maintain:** Keep up the excellent work!")
            
            if consistency < 50:
                action_items.append("📅 **Consistency:** Help establish a regular study routine")
            
            if len(summary["weaknesses"]) > 2:
                action_items.append("🎯 **Focus Areas:** Work on one weak topic at a time")
            
            if hints_used / total_questions > 0.4 if total_questions > 0 else False:
                action_items.append("🤝 **Support:** Consider reviewing concepts together before quiz time")
            
            for item in action_items:
                st.write(item)
            
            # Specific action steps from report
            if summary["weaknesses"]:
                st.subheader("🎯 Specific Help for Weakest Area")
                weakest_topic = summary["weaknesses"][0]["topic"]
                weakest_mastery = summary["weaknesses"][0]["mastery"] / 100
                
                with st.expander(f"📖 How to help with {weakest_topic}"):
                    if "actionable_steps" not in st.session_state:
                        st.session_state.actionable_steps = {}
                    
                    if weakest_topic not in st.session_state.actionable_steps:
                        if st.button(f"Get Specific Tips for {weakest_topic}", key=f"steps_{weakest_topic}"):
                            with st.spinner("Generating personalized tips..."):
                                # Use from report; approximate if not per-topic
                                st.session_state.actionable_steps[weakest_topic] = "Steps from report: " + "\n".join(summary.get("actionable_steps", [{}])[0].get("steps", "No steps available"))
                    
                    if weakest_topic in st.session_state.actionable_steps:
                        st.write(st.session_state.actionable_steps[weakest_topic])
        
        else:
            # No data yet
            st.info(f"👋 {student} hasn't started practicing yet! Encourage them to take their first quiz.")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Getting Started Tips:**")
                st.write("• Help them log in and explore the quiz section")
                st.write("• Start with topics they feel confident about")
                st.write("• Encourage daily 10-15 minute practice sessions")
            
            with col2:
                st.write("**What You'll See Here:**")
                st.write("• Daily progress and activity")
                st.write("• Strengths and areas needing work")
                st.write("• Personalized recommendations")

    # Add another child section
    st.divider()
    with st.expander("➕ Link Another Child"):
        link_code = st.text_input("Enter another child's link code", key="additional_link")
        if st.button("Link Additional Child"):
            if link_code.strip():
                try:
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    response = requests.post(f"{BACKEND_URL}/auth/link-parent", headers=headers, json={"link_code": link_code.strip()})
                    response.raise_for_status()
                    st.success("Successfully linked another child!")
                    st.rerun()
                except requests.exceptions.RequestException as e:
                    st.error("Invalid link code.")
            else:
                st.error("Please enter a link code.")