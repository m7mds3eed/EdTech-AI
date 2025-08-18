import streamlit as st
import openai
from openai import OpenAI
import requests
from datetime import datetime
import json
import os
from dotenv import load_dotenv
from src.auth.session import restore_session_from_cookie, get_cookie_manager
from src.ui.navigation import render_sidebar
# --- Configuration ---
BACKEND_URL = "http://127.0.0.1:8000"  # Or use os.environ.get for production

# Load environment variables
load_dotenv()

# --- ADD THIS BLOCK TO THE TOP OF THE PAGE ---
cookies = get_cookie_manager()


restore_session_from_cookie(BACKEND_URL)
# --- END OF BLOCK ---

# --- Hide default Streamlit navigation ---
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
        
        /* Custom styling for chat interface */
        .chat-message {
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            display: flex;
            flex-direction: column;
        }
        
        .user-message {
            background-color: #f0f2f6;
            align-self: flex-end;
            max-width: 80%;
            margin-left: auto;
        }
        
        .assistant-message {
            background-color: #e8f4fd;
            align-self: flex-start;
            max-width: 80%;
            margin-right: auto;
        }
        
        .timestamp {
            font-size: 0.8rem;
            color: #666;
            margin-top: 0.5rem;
        }
    </style>
""", unsafe_allow_html=True)

# Authentication check
if "user_id" not in st.session_state:
    st.error("Please log in to access the AI Admin Assistant.")
    st.stop()

# Sidebar navigation
# Set current page for navigation
st.session_state.current_page = "ai_admin"
render_sidebar("ai_admin", BACKEND_URL)


# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def get_user_context():
    """Get relevant user context for the AI assistant via APIs."""
    context = {
        "role": st.session_state.role,
        "user_id": st.session_state.user_id
    }
    
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        
        if st.session_state.role == "student":
            # Get student stats from /analytics/student-progress
            response = requests.get(f"{BACKEND_URL}/analytics/student-progress", headers=headers)
            response.raise_for_status()
            data = response.json().get("overall_stats", {})
            context["stats"] = {
                "total_questions": data.get("total_questions", 0),
                "correct_answers": data.get("correct_answers", 0),
                "avg_mastery": data.get("avg_mastery", 0),
                "active_days": 0  # Approximate; no direct
            }
            
            # Get pending assignments (composite count)
            pending = 0
            resp_classes = requests.get(f"{BACKEND_URL}/classes/my-classes", headers=headers)
            if resp_classes.status_code == 200:
                classes = resp_classes.json().get("classes", [])
                for cls in classes:
                    resp_assign = requests.get(f"{BACKEND_URL}/assignments/class/{cls['id']}", headers=headers)
                    if resp_assign.status_code == 200:
                        assigns = resp_assign.json().get("assignments", [])
                        pending += len([a for a in assigns if not a['due_date'] or datetime.fromisoformat(a['due_date']) >= datetime.now()])
            context["pending_assignments"] = pending
            
        elif st.session_state.role == "parent":
            # Get linked children from /analytics/parent-report
            response = requests.get(f"{BACKEND_URL}/analytics/parent-report", headers=headers)
            response.raise_for_status()
            reports = response.json().get("reports", [])
            context["linked_children"] = [r["student_name"] for r in reports]
            
        elif st.session_state.role == "teacher":
            # Get teacher's classes from /classes/my-classes
            response = requests.get(f"{BACKEND_URL}/classes/my-classes", headers=headers)
            response.raise_for_status()
            classes = response.json().get("classes", [])
            context["stats"] = {
                "total_classes": len(classes),
                "total_students": 0  # Approximate
            }
        
    except requests.exceptions.RequestException as e:
        st.error(f"Error getting context: {e}")
    
    return context

if "ai_admin_context" not in st.session_state:
    st.session_state.ai_admin_context = get_user_context()

def get_system_prompt():
    """Generate the system prompt for the AI assistant based on user role and context."""
    
    base_prompt = """You are an AI Admin Assistant for the Learning Gap Identifier app, an IGCSE Mathematics learning platform. 

CORE INSTRUCTIONS:
- You ONLY help with app functionality, navigation, features, and usage
- You do NOT answer mathematics questions or provide academic tutoring
- If asked about math content, redirect users to use the quiz/lesson features in the app
- Always be helpful, friendly, and provide specific step-by-step instructions
- Reference specific page names, button names, and UI elements when giving directions
- Use the user's context to provide personalized assistance

USER CONTEXT:"""
    
    context = st.session_state.ai_admin_context
    role = context["role"]
    
    if role == "student":
        stats = context.get("stats", {})
        base_prompt += f"""
Role: Student
Questions Answered: {stats.get('total_questions', 0)}
Accuracy: {(stats.get('correct_answers', 0) / max(stats.get('total_questions', 1), 1) * 100):.1f}%
Average Mastery: {stats.get('avg_mastery', 0):.1f}%
Active Days: {stats.get('active_days', 0)}
Pending Assignments: {context.get('pending_assignments', 0)}

STUDENT FEATURES YOU CAN HELP WITH:
- Starting quizzes (Home page → Select subject/topic → Start Quiz)
- Completing assignments (My Assignments page → Pending tab → Start Quiz)
- Joining classes (Home page → Join a Class section → Enter 8-char code)
- Understanding progress metrics (My Profile page)
- Finding parent link code (Home page or My Profile)
- Using quiz features (hints, lessons, skip options)
- Navigating between Practice Mode and Assignment Mode
"""
    
    elif role == "parent":
        children = context.get("linked_children", [])
        base_prompt += f"""
Role: Parent
Linked Children: {len(children)} ({', '.join(children) if children else 'None'})

PARENT FEATURES YOU CAN HELP WITH:
- Linking to child accounts (get 6-char code from child)
- Understanding progress reports and metrics
- Interpreting charts and graphs in Parent Dashboard
- Understanding what KPIs mean (accuracy, mastery, consistency)
- Getting actionable recommendations for helping children
- Viewing detailed performance breakdowns
- Understanding strengths and weaknesses reports
"""
    
    elif role == "teacher":
        stats = context.get("stats", {})
        base_prompt += f"""
Role: Teacher
Classes: {stats.get('total_classes', 0)}
Total Students: {stats.get('total_students', 0)}

TEACHER FEATURES YOU CAN HELP WITH:
- Creating and managing classes (generate class codes)
- Creating assignments with various settings
- Adding custom questions
- Managing student enrollment
- Understanding class performance reports
- Interpreting student analytics and KPIs
- Creating announcements
- Using the topic hierarchy system
- Understanding assignment submission data
"""
    
    base_prompt += """

IMPORTANT KNOWLEDGE BASE:

APP STRUCTURE:
- Home page: Role-specific dashboards and quick actions
- Students: Quiz system, assignments, profile with progress tracking
- Parents: Child progress monitoring, detailed reports, recommendations
- Teachers: Class management, assignment creation, performance analytics

KEY METRICS EXPLAINED:
- Accuracy: (Correct Answers / Total Questions) × 100
- Mastery: AI-calculated understanding level using Bayesian Knowledge Tracing
- Study Consistency: (Active Days / Days Since Registration) × 100
- Active Day: Any day with at least one question answered

QUIZ SYSTEM:
- Two modes: Practice (free) and Assignment (teacher-controlled)
- Question types: MCQ, True/False, Short Answer, Exam Style
- Learning aids: Hints, Lessons (may be disabled in assignments)
- Adaptive difficulty based on performance

CLASS SYSTEM:
- Teachers create classes with 8-character codes
- Students join using these codes
- Teachers can create assignments, announcements, custom questions
- Hierarchical topic selection: Topic → Subtopic → Micro-topic → Nano-topics

ASSIGNMENT FEATURES:
- Minimum questions, maximum attempts
- Due dates, difficulty preferences
- Hint/lesson permissions
- Custom teacher questions
- Detailed submission tracking

ALWAYS redirect math questions to app features and be specific about where to find things!
"""
    
    return base_prompt

def log_ai_interaction(user_id, role, question, response, helpful=None):
    """Log AI assistant interactions via feedback API."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        feedback_text = json.dumps({
            "question": question,
            "response": response,
            "helpful": helpful
        })
        payload = {
            "feedback_text": feedback_text,
            "rating": 1 if helpful else 0 if helpful is not None else None,
            "context": "ai_interaction"
        }
        response = requests.post(f"{BACKEND_URL}/feedback/submit", headers=headers, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error logging AI interaction: {e}")

def get_ai_response(user_message, chat_history):
    """Get response from OpenAI based on user message and context."""
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Prepare messages for OpenAI
        messages = [
            {"role": "system", "content": get_system_prompt()}
        ]
        
        # Add recent chat history (last 6 messages to stay within token limits)
        # Skip the current message since we'll add it separately
        for msg in chat_history[-7:-1]:  # Get last 6 messages, excluding the most recent one
            if msg["sender"] == "user":
                messages.append({"role": "user", "content": msg["message"]})
            else:
                messages.append({"role": "assistant", "content": msg["message"]})
        
        # Add current message
        messages.append({"role": "user", "content": user_message})
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        # Log the interaction (only once)
        log_ai_interaction(
            st.session_state.user_id, 
            st.session_state.role, 
            user_message, 
            ai_response
        )
        
        return ai_response
        
    except Exception as e:
        error_response = f"I apologize, but I'm experiencing technical difficulties right now. Please try again in a moment, or you can:\n\n• Check the navigation buttons in the sidebar\n• Use the quick help topics\n• Contact support if the issue persists\n\nError details: {str(e)}"
        
        # Log the error (only once)
        log_ai_interaction(
            st.session_state.user_id, 
            st.session_state.role, 
            user_message, 
            f"ERROR: {str(e)}"
        )
        
        return error_response

# Main interface
st.title("🤖 AI Admin Assistant")
st.markdown("*Your intelligent guide to using the Learning Gap Identifier app*")

# Welcome message based on role
role_welcomes = {
    "student": "Hi! I'm here to help you navigate the app, understand your progress, complete assignments, and make the most of your learning experience.",
    "parent": "Hello! I can help you understand your child's progress, interpret reports, and guide you on how to support their learning journey.",
    "teacher": "Welcome! I'm here to assist with class management, creating assignments, understanding student performance, and using all the teacher tools effectively."
}

st.info(f"👋 {role_welcomes.get(st.session_state.role, 'Hello! I can help you use the Learning Gap Identifier app.')}")

# Handle quick questions from sidebar
if "quick_question" in st.session_state:
    user_input = st.session_state.quick_question
    del st.session_state.quick_question
    
    # Add to chat history
    user_message = {
        "sender": "user",
        "message": user_input,
        "timestamp": datetime.now().strftime("%H:%M")
    }
    st.session_state.chat_history.append(user_message)
    
    # Get AI response
    ai_response = get_ai_response(user_input, st.session_state.chat_history)
    
    # Add AI response to chat history with reference
    ai_message = {
        "sender": "assistant",
        "message": ai_response,
        "timestamp": datetime.now().strftime("%H:%M"),
        "original_question": user_input
    }
    st.session_state.chat_history.append(ai_message)
    
    # Rerun to display the new messages
    st.rerun()

# Chat interface
st.subheader("💬 Chat with AI Assistant")

# Display chat history
if st.session_state.chat_history:
    for i, message in enumerate(st.session_state.chat_history[-10:]):  # Show last 10 messages
        if message["sender"] == "user":
            st.markdown(f"""
            <div class="chat-message user-message">
                <strong>You:</strong> {message["message"]}
                <div class="timestamp">{message["timestamp"]}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="chat-message assistant-message">
                <strong>🤖 AI Assistant:</strong> {message["message"]}
                <div class="timestamp">{message["timestamp"]}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Add feedback buttons for AI responses
            col1, col2, col3 = st.columns([1, 1, 8])
            with col1:
                if st.button("👍", key=f"helpful_{i}", help="This was helpful"):
                    st.success("Thanks for the feedback!")
                    # Log positive feedback
                    log_ai_interaction(
                        st.session_state.user_id, 
                        st.session_state.role, 
                        f"FEEDBACK for: {message.get('original_question', 'Unknown')}", 
                        "HELPFUL: TRUE", 
                        True
                    )
            with col2:
                if st.button("👎", key=f"not_helpful_{i}", help="This wasn't helpful"):
                    st.info("Thanks for the feedback! I'll try to improve.")
                    # Log negative feedback
                    log_ai_interaction(
                        st.session_state.user_id, 
                        st.session_state.role, 
                        f"FEEDBACK for: {message.get('original_question', 'Unknown')}", 
                        "HELPFUL: FALSE", 
                        False
                    )

# Chat input
user_input = st.chat_input("Ask me anything about using the app...")

if user_input:
    # Check if this exact message was just processed to prevent duplication
    if not st.session_state.chat_history or st.session_state.chat_history[-1]["message"] != user_input:
        # Add user message to chat history
        user_message = {
            "sender": "user",
            "message": user_input,
            "timestamp": datetime.now().strftime("%H:%M")
        }
        st.session_state.chat_history.append(user_message)
        
        # Get AI response
        with st.spinner("🤔 Thinking..."):
            ai_response = get_ai_response(user_input, st.session_state.chat_history)
        
        # Add AI response to chat history with reference to original question
        ai_message = {
            "sender": "assistant",
            "message": ai_response,
            "timestamp": datetime.now().strftime("%H:%M"),
            "original_question": user_input  # Store for feedback reference
        }
        st.session_state.chat_history.append(ai_message)
        
        # Rerun to display new messages
        st.rerun()

# Example questions section
st.divider()
st.subheader("💡 Example Questions You Can Ask")

role_examples = {
    "student": [
        "How do I check my progress?",
        "Why can't I see hints in my assignment?",
        "How do I join my teacher's class?",
        "What does my mastery percentage mean?",
        "How do I practice a specific topic?",
        "Where can I see my assignment due dates?"
    ],
    "parent": [
        "How do I link to my child's account?",
        "What does study consistency mean?",
        "How can I help my child with weak areas?",
        "How do I understand the progress charts?",
        "What should I do if my child has low accuracy?",
        "How often should my child practice?"
    ],
    "teacher": [
        "How do I create a new assignment?",
        "How do I see which students need help?",
        "How do I add my own questions?",
        "What do the class performance metrics mean?",
        "How do I remove a student from my class?",
        "How do I create announcements?"
    ]
}

examples = role_examples.get(st.session_state.role, [])
cols = st.columns(2)

for i, example in enumerate(examples):
    col = cols[i % 2]
    with col:
        if st.button(f"📝 {example}", key=f"example_{i}", use_container_width=True):
            st.session_state.quick_question = example
            st.rerun()

# Clear chat button and analytics
col1, col2 = st.columns(2)

with col1:
    if st.button("🗑️ Clear Chat History", type="secondary", use_container_width=True):
        st.session_state.chat_history = []
        st.success("Chat history cleared!")
        st.rerun()

with col2:
    # Show chat statistics
    if st.session_state.chat_history:
        user_messages = [msg for msg in st.session_state.chat_history if msg["sender"] == "user"]
        st.metric("Questions Asked", len(user_messages))

# Usage analytics for current session
if st.session_state.chat_history:
    with st.expander("📊 Session Analytics"):
        total_messages = len(st.session_state.chat_history)
        user_messages = [msg for msg in st.session_state.chat_history if msg["sender"] == "user"]
        ai_messages = [msg for msg in st.session_state.chat_history if msg["sender"] == "assistant"]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Messages", total_messages)
        with col2:
            st.metric("Your Questions", len(user_messages))
        with col3:
            st.metric("AI Responses", len(ai_messages))
        
        # Most recent topics
        if user_messages:
            st.write("**Recent Questions:**")
            for msg in user_messages[-3:]:
                st.write(f"• {msg['message'][:50]}{'...' if len(msg['message']) > 50 else ''}")

# Help section
with st.expander("ℹ️ About this AI Assistant"):
    st.write("""
    **What I can help with:**
    - App navigation and features
    - Understanding your data and metrics
    - Step-by-step instructions for tasks
    - Troubleshooting common issues
    - Explaining how different features work
    
    **What I cannot help with:**
    - Mathematics homework or tutoring
    - Academic content questions
    - Technical issues requiring admin access
    - Account password resets
    
    **Tips for better responses:**
    - Be specific about what you're trying to do
    - Mention which page you're on if relevant
    - Describe any error messages you see
    - Ask follow-up questions if you need clarification
    
    **Privacy & Data:**
    - Your conversations are logged to improve the service
    - No personal academic data is shared with the AI
    - Feedback helps us make the assistant better
    """)

# Emergency help section
st.divider()
st.subheader("🆘 Need Immediate Help?")

emergency_help = {
    "student": {
        "Can't access assignment": "Go to 'My Assignments' → Check 'Pending' tab → Contact teacher if assignment missing",
        "Quiz won't start": "Ensure both subject and topic are selected → Try refreshing page → Check internet connection",
        "Can't find link code": "Home page (top section) or My Profile page → 6-character code to share with parents",
        "Joined wrong class": "Contact your teacher to remove you from the incorrect class"
    },
    "parent": {
        "Can't link to child": "Get 6-character code from child → Use 'Link Account' section → Contact child's teacher if issues",
        "No data showing": "Child must answer questions first → Check if child is actively using the app",
        "Understanding reports": "Green = good performance, Red = needs attention → Focus on 'Areas to Improve' section"
    },
    "teacher": {
        "Students can't join class": "Check 8-character class code → Share exact code with students → Verify class is active",
        "Assignment not visible": "Check class enrollment → Verify assignment settings → Ensure due date is future",
        "Performance data missing": "Students must complete assignments first → Check date ranges in reports"
    }
}

role_help = emergency_help.get(st.session_state.role, {})
for issue, solution in role_help.items():
    with st.expander(f"❗ {issue}"):
        st.write(f"**Quick Solution:** {solution}")
        if st.button(f"Ask AI about: {issue}", key=f"emergency_{issue}"):
            st.session_state.quick_question = f"I'm having trouble with: {issue}. Can you help me?"
            st.rerun()