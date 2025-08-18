import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from src.ui.feedback import render_feedback_widget
from src.auth.session import restore_session_from_cookie, get_cookie_manager
from src.ui.navigation import render_sidebar

# --- Configuration ---
BACKEND_URL = "http://127.0.0.1:8000"  # Or use os.environ.get for production
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
    </style>
""", unsafe_allow_html=True)

# Ensure user is logged in and is a teacher
if "user_id" not in st.session_state or st.session_state.role != "teacher":
    st.error("Please log in as a teacher to access the dashboard.")
    st.switch_page("app.py")  # ← ADD THIS LINE TO REDIRECT TO LOGIN

# Set current page for navigation
st.session_state.current_page = "teacher_dashboard"
render_sidebar("teacher_dashboard", BACKEND_URL)

st.title("👩‍🏫 Teacher Dashboard")

# Helper functions
def get_teacher_classes():
    """Get all classes for a teacher via API."""
    classes = []
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.get(f"{BACKEND_URL}/classes/my-classes", headers=headers)
        response.raise_for_status()
        api_classes = response.json().get("classes", [])
        for c in api_classes:
            classes.append({
                "id": c["id"],
                "name": c["name"],
                "description": c["description"],
                "grade_level": "N/A",  # Placeholder; not in API
                "class_code": c["class_code"],
                "created_at": c["date"],  # API has "date"
                # FIX: Use the student_count from the API
                "student_count": c.get("student_count", 0)
            })
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching classes: {e}")
    return classes

def create_enhanced_assignment(class_id, title, description, topic_id, subtopic_id, 
                              micro_topic_id, nano_topic_ids, due_date, min_questions, 
                              max_attempts, show_hints, show_lessons, difficulty_preference, 
                              custom_questions=None):
    """Create a new assignment via API."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        payload = {
            "class_id": class_id,
            "title": title,
            "description": description,
            "due_date": due_date.isoformat() if due_date else None,
            "min_questions": min_questions,
            "max_attempts": max_attempts,
            "show_hints": show_hints,
            "show_lessons": show_lessons,
            "micro_topic_id": micro_topic_id,
            "nano_topic_ids": nano_topic_ids,
            "difficulty_preference": difficulty_preference,
            "count_skips": True,  # Always count skips now
            "custom_questions": custom_questions
        }
        response = requests.post(f"{BACKEND_URL}/assignments/create", headers=headers, json=payload)
        response.raise_for_status()
        return response.json().get("assignment_id")
    except requests.exceptions.RequestException as e:
        st.error(f"Error creating assignment: {e}")
        return None

def save_custom_question(question_text, options, correct_answer, difficulty, style, nano_topic_id):
    """Save a custom question via API."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        payload = {
            "question_text": question_text,
            "options": options,
            "correct_answer": correct_answer,
            "difficulty": difficulty,
            "style": style,
            "nano_topic_id": nano_topic_id
        }
        response = requests.post(f"{BACKEND_URL}/teacher/custom-questions", headers=headers, json=payload)
        response.raise_for_status()
        return response.json().get("question_id")
    except requests.exceptions.RequestException as e:
        st.error(f"Error saving question: {e}")
        return None

# Main dashboard
tab1, tab2, tab3, tab4 = st.tabs(["📚 My Classes", "📝 Create Assignment", "❓ Custom Questions", "📢 Announcements"])

with tab1:
    st.header("My Classes")
    
    # Create new class
    with st.expander("➕ Create New Class"):
        col1, col2 = st.columns(2)
        with col1:
            class_name = st.text_input("Class Name", placeholder="e.g., Grade 10 Mathematics")
            grade_level = st.selectbox("Grade Level", ["Grade 5", "Grade 6", "Grade 7", 
                                                       "Grade 8", "Grade 9", "Grade 10", 
                                                       "Grade 11", "Grade 12"])
        with col2:
            class_description = st.text_area("Description", placeholder="Brief description of the class")
        
        if st.button("Create Class", type="primary"):
            if class_name:
                try:
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    payload = {
                        "name": class_name,
                        "description": class_description,
                        "grade_level": grade_level
                    }
                    response = requests.post(f"{BACKEND_URL}/classes/create", headers=headers, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    class_id = data.get("class_id")
                    class_code = data.get("class_code")
                    if class_id:
                        st.success(f"✅ Class created! Class code: **{class_code}**")
                        st.info("📤 Share this code with your students so they can join the class.")
                        st.rerun()
                except requests.exceptions.RequestException as e:
                    st.error(f"Error creating class: {e}")
            else:
                st.error("Please enter a class name.")
    
    # Display existing classes
    classes = get_teacher_classes()
    
    if classes:
        for class_info in classes:
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.subheader(class_info["name"])
                    st.write(f"📊 {class_info['grade_level']} | 👥 {class_info['student_count']} students")
                    if class_info["description"]:
                        st.caption(class_info["description"])
                with col2:
                    st.write(f"**Class Code:**")
                    st.code(class_info["class_code"])
                with col3:
                    if st.button("👀 View Details", key=f"view_{class_info['id']}"):
                        st.session_state.selected_class_id = class_info["id"]
                        st.session_state.selected_class_name = class_info["name"]
                
                # Show class details if selected
                if st.session_state.get("selected_class_id") == class_info["id"]:
                    st.divider()
                    
                    # FIX: Call the new endpoint to get the list of students
                    students = []
                    try:
                        headers = {"Authorization": f"Bearer {st.session_state.token}"}
                        response = requests.get(f"{BACKEND_URL}/classes/{class_info['id']}/students", headers=headers)
                        response.raise_for_status()
                        students = response.json().get("students", [])
                    except requests.exceptions.RequestException as e:
                        st.error(f"Could not load students: {e}")

                    st.write("**📊 Class Roster:**")
                    if students:
                        # Note: The original dataframe had placeholder columns like "Avg Mastery".
                        # The new endpoint provides basics; a more advanced endpoint would be needed for full analytics.
                        df_students = pd.DataFrame(students)
                        df_students["joined_at"] = pd.to_datetime(df_students["joined_at"]).dt.strftime("%Y-%m-%d")
                        st.dataframe(df_students[["username", "joined_at"]],
                                column_config={"username": "Student Name", "joined_at": "Date Joined"},
                                hide_index=True, use_container_width=True)
                    else:
                        st.info("No students enrolled yet. Share the class code with your students.")
                                    
                    # Get assignments for this class
                    assignments = []
                    try:
                        headers = {"Authorization": f"Bearer {st.session_state.token}"}
                        resp = requests.get(f"{BACKEND_URL}/assignments/class/{class_info['id']}", headers=headers)
                        resp.raise_for_status()
                        assignments = resp.json().get("assignments", [])
                    except requests.exceptions.RequestException:
                        pass
                    
                    st.write("**📝 Recent Assignments:**")
                    if assignments:
                        for assign in assignments[:5]:  # Show last 5
                            col1, col2, col3 = st.columns([3, 1, 1])
                            with col1:
                                st.write(f"📋 **{assign['title']}**")
                            with col2:
                                if assign['due_date']:
                                    due_date = datetime.fromisoformat(assign['due_date'])
                                    st.caption(f"Due: {due_date.strftime('%m/%d/%Y')}")
                                else:
                                    st.caption("No due date")
                            with col3:
                                # Submissions count (composite via /assignments/{id}/submissions)
                                subs_count = 0
                                try:
                                    resp_subs = requests.get(f"{BACKEND_URL}/assignments/{assign['id']}/submissions", headers=headers)
                                    resp_subs.raise_for_status()
                                    subs_count = len(resp_subs.json().get("submissions", []))
                                except:
                                    pass
                                st.caption(f"Submissions: {subs_count}")
                    else:
                        st.info("No assignments created yet.")
                    
                    # Delete class option (no API; placeholder)
                    st.divider()
                    st.warning("Class deletion not supported yet. Contact admin if needed.")
                
                st.divider()
    else:
        st.info("📚 No classes created yet. Create your first class above!")

with tab2:
    st.header("Create Assignment")
    
    classes = get_teacher_classes()
    if not classes:
        st.warning("⚠️ Please create a class first before creating assignments.")
    else:
        if "selected_custom_questions" not in st.session_state:
            st.session_state.selected_custom_questions = []

        # --- LOAD CURRICULUM STRUCTURE (outside form for dynamic updates) ---
        if "curriculum_structure" not in st.session_state:
            try:
                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                response = requests.get(f"{BACKEND_URL}/topics/structure", headers=headers)
                response.raise_for_status()
                st.session_state.curriculum_structure = response.json().get("curriculum", [])
            except requests.exceptions.RequestException as e:
                st.error(f"Error loading topics: {e}")
                st.session_state.curriculum_structure = []

        curriculum = st.session_state.curriculum_structure

        # --- BASIC ASSIGNMENT DETAILS ---
        st.subheader("📋 Assignment Details")
        
        # Select class
        class_names = [c["name"] for c in classes]
        selected_class_name = st.selectbox("📚 Select Class", class_names, key="assignment_class_select")
        selected_class_id = next(c["id"] for c in classes if c["name"] == selected_class_name)

        assignment_title = st.text_input("📝 Assignment Title", placeholder="e.g., Week 1 Practice")
        assignment_description = st.text_area("📄 Instructions", placeholder="Instructions for students")
        due_date = st.date_input("📅 Due Date", min_value=datetime.now().date())
        
        # Advanced settings
        st.subheader("⚙️ Assignment Settings")
        col1, col2, col3 = st.columns(3)
        with col1:
            min_questions = st.number_input("📊 Minimum Questions", min_value=5, max_value=50, value=10)
            max_attempts = st.number_input("🔄 Maximum Attempts", min_value=1, max_value=10, value=3)
        with col2:
            difficulty_preference = st.selectbox("🎯 Difficulty Level", ["mixed", "beginner", "intermediate", "advanced"])
            # Remove count_skips checkbox - always count skips
            # st.info("📉 Skips will always count toward progress and be monitored")
        with col3:
            show_hints = st.checkbox("💡 Allow hints", value=True)
            show_lessons = st.checkbox("📚 Allow lessons", value=True)

        # Question source
        st.subheader("📖 Question Source")
        use_ai = st.checkbox("Use AI-generated questions", value=True, key="assignment_use_ai")
        use_custom = st.checkbox("Use Custom Questions", value=False, key="assignment_use_custom")

        # --- HIERARCHICAL TOPIC SELECTION (always show, filter for custom questions) ---
        st.subheader("📚 Select Topic Hierarchy")
        
        selected_micro_topic_obj = None
        nano_topic_ids = []
        selected_topic_hierarchy = None

        # Get custom questions if using custom mode for filtering
        custom_questions = []
        if use_custom:
            try:
                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                response = requests.get(f"{BACKEND_URL}/teacher/custom-questions", headers=headers)
                response.raise_for_status()
                custom_questions = response.json().get("custom_questions", [])
            except requests.exceptions.RequestException as e:
                st.error(f"Error loading custom questions: {e}")

        if curriculum:
            # Filter curriculum based on available custom questions
            if use_custom:
                # Get all nano-topics that have custom questions
                available_nano_topics = list(set([q.get("nano_topic") for q in custom_questions if q.get("nano_topic")]))
                
                # Filter curriculum to only show hierarchy paths that lead to available nano-topics
                filtered_curriculum = []
                for subject in curriculum:
                    filtered_subject = {"name": subject["name"], "subtopics": []}
                    
                    for subtopic in subject.get("subtopics", []):
                        filtered_subtopic = {"name": subtopic["name"], "micro_topics": []}
                        
                        for micro_topic in subtopic.get("micro_topics", []):
                            # Check if this micro-topic has any nano-topics with custom questions
                            has_available_nanos = any(
                                nano["name"] in available_nano_topics 
                                for nano in micro_topic.get("nano_topics", [])
                            )
                            
                            if has_available_nanos:
                                # Filter nano-topics to only show those with custom questions
                                filtered_nano_topics = [
                                    nano for nano in micro_topic.get("nano_topics", [])
                                    if nano["name"] in available_nano_topics
                                ]
                                filtered_micro = {
                                    "name": micro_topic["name"],
                                    "id": micro_topic["id"],
                                    "nano_topics": filtered_nano_topics
                                }
                                filtered_subtopic["micro_topics"].append(filtered_micro)
                        
                        if filtered_subtopic["micro_topics"]:
                            filtered_subject["subtopics"].append(filtered_subtopic)
                    
                    if filtered_subject["subtopics"]:
                        filtered_curriculum.append(filtered_subject)
                
                active_curriculum = filtered_curriculum
            else:
                active_curriculum = curriculum

            if active_curriculum:
                # Level 1: Subjects (filtered if using custom questions)
                subject_names = [t["name"] for t in active_curriculum]
                if subject_names:
                    selected_subject = st.selectbox("📚 Subject", subject_names, key="assignment_subject_select")
                    selected_subject_obj = next((t for t in active_curriculum if t["name"] == selected_subject), None)

                    if selected_subject_obj and selected_subject_obj.get("subtopics"):
                        # Level 2: Topics (filtered if using custom questions)
                        subtopic_names = [s["name"] for s in selected_subject_obj["subtopics"]]
                        if subtopic_names:
                            selected_topic = st.selectbox("📑 Topic", subtopic_names, key="assignment_topic_select")
                            selected_topic_obj = next((s for s in selected_subject_obj["subtopics"] if s["name"] == selected_topic), None)

                            if selected_topic_obj and selected_topic_obj.get("micro_topics"):
                                # Level 3: Micro-topics (filtered if using custom questions)
                                micro_topic_names = [m["name"] for m in selected_topic_obj["micro_topics"]]
                                if micro_topic_names:
                                    selected_micro_topic = st.selectbox("📝 Micro-topic", micro_topic_names, key="assignment_micro_select")
                                    selected_micro_topic_obj = next((m for m in selected_topic_obj["micro_topics"] if m["name"] == selected_micro_topic), None)

                                    if selected_micro_topic_obj and selected_micro_topic_obj.get("nano_topics"):
                                        # Level 4: Nano-topics (already filtered if using custom questions)
                                        nano_topic_names = [n["name"] for n in selected_micro_topic_obj["nano_topics"]]
                                        if nano_topic_names:
                                            if use_custom:
                                                # For custom questions, all shown nano-topics have questions available
                                                selected_nano_topics = st.multiselect(
                                                    "🔬 Nano-topics (all have custom questions available)", 
                                                    nano_topic_names, 
                                                    key="assignment_nano_select"
                                                )
                                                nano_topic_ids = [n["id"] for n in selected_micro_topic_obj["nano_topics"] if n["name"] in selected_nano_topics]
                                                
                                                # Show available questions for selected nano-topics
                                                if selected_nano_topics:
                                                    st.write("**Available Custom Questions:**")
                                                    for nano_name in selected_nano_topics:
                                                        questions_for_nano = [q for q in custom_questions if q.get("nano_topic") == nano_name]
                                                        if questions_for_nano:
                                                            with st.expander(f"🔬 {nano_name} ({len(questions_for_nano)} questions)"):
                                                                for q in questions_for_nano:
                                                                    st.write(f"• {q['question_text'][:100]}{'...' if len(q['question_text']) > 100 else ''}")
                                                                    st.caption(f"Type: {q['style'].upper()} | Difficulty: {q['difficulty'].title()}")
                                            else:
                                                # For AI questions, show all nano-topics as multiselect (optional)
                                                selected_nano_topics = st.multiselect("🔬 Specific Nano-topics (optional)", nano_topic_names, key="assignment_nano_select")
                                                nano_topic_ids = [n["id"] for n in selected_micro_topic_obj["nano_topics"] if n["name"] in selected_nano_topics]
                                            
                                            # Display selected hierarchy
                                            if selected_micro_topic_obj:
                                                selected_topic_hierarchy = f"{selected_subject} → {selected_topic} → {selected_micro_topic}"
                                                if selected_nano_topics:
                                                    selected_topic_hierarchy += f" → {', '.join(selected_nano_topics)}"
                                                st.success(f"✅ Selected: {selected_topic_hierarchy}")
                                        else:
                                            st.info("No nano-topics available for this micro-topic.")
                                            if selected_micro_topic_obj:
                                                selected_topic_hierarchy = f"{selected_subject} → {selected_topic} → {selected_micro_topic}"
                                                st.success(f"✅ Selected: {selected_topic_hierarchy}")
                                else:
                                    st.info("No micro-topics available for this topic.")
                        else:
                            st.info("No topics available for this subject.")
                else:
                    if use_custom:
                        st.warning("⚠️ No subjects have custom questions available.")
                        st.info("💡 Create custom questions first, or switch to AI-generated questions.")
                    else:
                        st.warning("No subjects available in the curriculum.")
            else:
                if use_custom:
                    st.warning("⚠️ No custom questions available in any topic.")
                    st.info("💡 Create custom questions first, or switch to AI-generated questions.")
                else:
                    st.warning("No subjects available in the curriculum.")
        else:
            st.error("Unable to load curriculum structure.")

        # --- ASSIGNMENT CREATION FORM ---
        with st.form("create_assignment"):
            # Display selected topic info within form
            if selected_topic_hierarchy:
                if use_ai:
                    st.info(f"📍 AI questions will be generated from: **{selected_topic_hierarchy}**")
                elif use_custom:
                    st.info(f"📍 Custom questions will be selected from: **{selected_topic_hierarchy}**")
            else:
                if use_ai:
                    st.warning("⚠️ Please select a complete topic hierarchy above for AI questions.")
                elif use_custom:
                    st.warning("⚠️ Please select topic hierarchy and nano-topics with available custom questions.")

            if st.form_submit_button("🚀 Create Assignment", type="primary", use_container_width=True):
                if assignment_title:
                    # Validate based on question type
                    if use_ai and not selected_micro_topic_obj:
                        st.error("❌ Please select at least up to Micro-topic for AI-generated questions.")
                    elif use_custom and not nano_topic_ids:
                        st.error("❌ Please select nano-topics with available custom questions.")
                    else:
                        # Get custom question IDs if using custom questions
                        custom_question_ids = None
                        if use_custom and nano_topic_ids:
                            try:
                                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                                response = requests.get(f"{BACKEND_URL}/teacher/custom-questions", headers=headers)
                                response.raise_for_status()
                                custom_questions = response.json().get("custom_questions", [])
                                
                                # Get all custom question IDs from selected nano-topics
                                selected_nano_names = [n["name"] for n in selected_micro_topic_obj["nano_topics"] if n["id"] in nano_topic_ids]
                                custom_question_ids = [q["id"] for q in custom_questions if q.get("nano_topic") in selected_nano_names]
                                
                                if not custom_question_ids:
                                    st.error("❌ No custom questions found for selected nano-topics.")
                                    st.stop()
                            except requests.exceptions.RequestException as e:
                                st.error(f"Error loading custom questions: {e}")
                                st.stop()
                        
                        assignment_id = create_enhanced_assignment(
                            selected_class_id,
                            assignment_title,
                            assignment_description,
                            None,
                            None,
                            selected_micro_topic_obj["id"] if selected_micro_topic_obj else None,
                            nano_topic_ids if use_ai else [],
                            due_date,
                            min_questions if use_ai else len(custom_question_ids) if custom_question_ids else min_questions,
                            max_attempts,
                            show_hints,
                            show_lessons,
                            difficulty_preference,
                            custom_questions=[{"id": qid} for qid in custom_question_ids] if use_custom and custom_question_ids else None
                        )
                        if assignment_id:
                            st.success(f"✅ Assignment '{assignment_title}' created successfully!")
                            if use_custom:
                                st.info(f"📊 Assignment includes {len(custom_question_ids)} custom questions.")
                            st.session_state.selected_custom_questions = []
                            st.rerun()
                else:
                    st.error("❌ Please enter a title.")

with tab3:
    st.header("Custom Questions")
    st.info("💡 Organize and create questions for your classes.")

    # --- SEARCH & FILTERS ---
    with st.expander("🔍 Search & Filters"):
        search_query = st.text_input("Search questions...")
        filter_difficulty = st.multiselect("Filter by Difficulty", ["beginner", "intermediate", "advanced"])
        filter_type = st.multiselect("Filter by Type", ["mcq", "short_answer", "true_false"])

    # --- FETCH QUESTION BANK ---
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.get(f"{BACKEND_URL}/teacher/custom-questions", headers=headers)
        response.raise_for_status()
        custom_questions = response.json().get("custom_questions", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching questions: {e}")
        custom_questions = []

    # --- LOAD CURRICULUM FOR HIERARCHY ---
    if "curriculum_structure" not in st.session_state:
        try:
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            resp = requests.get(f"{BACKEND_URL}/topics/structure", headers=headers)
            resp.raise_for_status()
            st.session_state.curriculum_structure = resp.json().get("curriculum", [])
        except requests.exceptions.RequestException as e:
            st.error(f"Error loading topics: {e}")
            st.session_state.curriculum_structure = []

    curriculum = st.session_state.curriculum_structure

    # --- GROUP QUESTIONS BY SUBJECT > TOPIC > MICRO > NANO ---
    grouped_questions = {}
    for q in custom_questions:
        nano = q.get("nano_topic") or "No Nano-topic"
        micro = "No Micro-topic"
        topic = "No Topic"
        subject = "No Subject"
        
        # Find the hierarchy for this nano topic
        for sub in curriculum:
            for subtopic in sub.get("subtopics", []):
                for micro_t in subtopic.get("micro_topics", []):
                    for nano_t in micro_t.get("nano_topics", []):
                        if nano_t["name"] == nano:
                            subject = sub["name"]
                            topic = subtopic["name"]
                            micro = micro_t["name"]
                            break
                    if micro != "No Micro-topic":
                        break
                if topic != "No Topic":
                    break
            if subject != "No Subject":
                break
        
        grouped_questions.setdefault(subject, {}).setdefault(topic, {}).setdefault(micro, {}).setdefault(nano, []).append(q)

    # --- DISPLAY QUESTION BANK ---
    st.subheader("📚 Your Question Bank")
    if grouped_questions:
        for subject, topics in grouped_questions.items():
            with st.expander(f"📘 {subject}"):
                for topic, micros in topics.items():
                    with st.expander(f"📑 {topic}"):
                        for micro, nanos in micros.items():
                            with st.expander(f"📝 {micro}"):
                                for nano, questions in nanos.items():
                                    st.markdown(f"### 🔬 {nano}")
                                    for q in questions:
                                        if (not search_query or search_query.lower() in q['question_text'].lower()) and \
                                           (not filter_difficulty or q['difficulty'] in filter_difficulty) and \
                                           (not filter_type or q['style'] in filter_type):
                                            with st.container():
                                                st.write(f"**Q:** {q['question_text']}")
                                                st.caption(f"Type: {q['style'].upper()} | Difficulty: {q['difficulty'].title()}")
                                                st.caption(f"Correct Answer: {q['correct_answer']}")
                                                col1, col2 = st.columns([1,1])
                                                with col1:
                                                    if st.button("🗑️ Delete", key=f"del_{q['id']}"):
                                                        try:
                                                            del_resp = requests.delete(f"{BACKEND_URL}/teacher/custom-questions/{q['id']}", headers=headers)
                                                            del_resp.raise_for_status()
                                                            st.success("Question deleted!")
                                                            st.rerun()
                                                        except requests.exceptions.RequestException as e:
                                                            st.error(f"Error deleting: {e}")
                                                with col2:
                                                    if st.button("✏️ Edit", key=f"edit_{q['id']}"):
                                                        st.session_state.edit_question = q
                                                        st.rerun()
                                                st.divider()
    else:
        st.info("📭 No custom questions created yet.")

    # --- CREATE NEW QUESTION ---
    st.subheader("➕ Add New Question")

    # Initialize options state
    if "options" not in st.session_state:
        st.session_state.options = ["",""]
    if "question_type" not in st.session_state:
        st.session_state.question_type = "mcq"

    # Step 1: Select question type OUTSIDE form for dynamic refresh
    st.session_state.question_type = st.radio("📋 Question Type", ["mcq", "short_answer", "true_false"], index=["mcq","short_answer","true_false"].index(st.session_state.question_type), key="q_type_select")

    # Dynamic MCQ option controls (outside form)
    if st.session_state.question_type == "mcq":
        st.write("### Manage Options")
        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("➕ Add Option", key="add_option"):
                st.session_state.options.append("")
                st.rerun()
        with col2:
            if len(st.session_state.options) > 2 and st.button("➖ Remove Last Option", key="remove_option"):
                st.session_state.options.pop()
                st.rerun()

    # Step 2: Topic Selection (OUTSIDE form for dynamic updates)
    st.subheader("📚 Select Topic Hierarchy")
    
    # Cascading Subject → Topic → Micro → Nano selection
    nano_topic_id = None
    selected_nano_topic_name = None
    
    if curriculum:
        # Level 1: Subjects (topics in the API structure)
        subject_names = [t["name"] for t in curriculum]
        if subject_names:
            selected_subject = st.selectbox("📚 Subject", subject_names, key="subject_select")
            selected_subject_obj = next((t for t in curriculum if t["name"] == selected_subject), None)

            if selected_subject_obj and selected_subject_obj.get("subtopics"):
                # Level 2: Topics (subtopics in the API structure)
                subtopic_names = [s["name"] for s in selected_subject_obj["subtopics"]]
                if subtopic_names:
                    selected_topic = st.selectbox("📑 Topic", subtopic_names, key="topic_select")
                    selected_topic_obj = next((s for s in selected_subject_obj["subtopics"] if s["name"] == selected_topic), None)

                    if selected_topic_obj and selected_topic_obj.get("micro_topics"):
                        # Level 3: Micro-topics
                        micro_topic_names = [m["name"] for m in selected_topic_obj["micro_topics"]]
                        if micro_topic_names:
                            selected_micro_topic = st.selectbox("📝 Micro-topic", micro_topic_names, key="micro_select")
                            selected_micro_topic_obj = next((m for m in selected_topic_obj["micro_topics"] if m["name"] == selected_micro_topic), None)

                            if selected_micro_topic_obj and selected_micro_topic_obj.get("nano_topics"):
                                # Level 4: Nano-topics
                                nano_topic_names = [n["name"] for n in selected_micro_topic_obj["nano_topics"]]
                                if nano_topic_names:
                                    selected_nano_topic = st.selectbox("🔬 Nano-topic", nano_topic_names, key="nano_select")
                                    if selected_nano_topic:
                                        nano_topic_id = next((n["id"] for n in selected_micro_topic_obj["nano_topics"] if n["name"] == selected_nano_topic), None)
                                        selected_nano_topic_name = selected_nano_topic
                                        st.success(f"✅ Selected: {selected_subject} → {selected_topic} → {selected_micro_topic} → {selected_nano_topic}")
                                else:
                                    st.info("No nano-topics available for this micro-topic.")
                        else:
                            st.info("No micro-topics available for this topic.")
                else:
                    st.info("No topics available for this subject.")
        else:
            st.warning("No subjects available in the curriculum.")
    else:
        st.error("Unable to load curriculum structure.")

    # Step 3: Question Form (with topic hierarchy already selected)
    with st.form("custom_question"):
        question_text = st.text_area("❓ Question", placeholder="Enter your question here...")
        difficulty = st.selectbox("🎯 Difficulty", ["beginner", "intermediate", "advanced"])
        question_type = st.session_state.question_type

        if question_type == "mcq":
            st.write("### Options (Select the correct one):")
            if "correct_answer_index" not in st.session_state:
                st.session_state.correct_answer_index = 0  # Default to first option

            # Render radio for selecting the correct option
            st.session_state.correct_answer_index = st.radio(
                "Select the correct answer:",
                options=list(range(len(st.session_state.options))),
                format_func=lambda x: f"Option {chr(65+x)}",
                index=st.session_state.correct_answer_index,
                key="correct_option_selector"
            )

            # Render text inputs for each option
            for i in range(len(st.session_state.options)):
                st.session_state.options[i] = st.text_input(f"Option {chr(65+i)}", value=st.session_state.options[i], key=f"new_option_{i}")

            # Set the correct answer value based on selected index
            correct_answer = st.session_state.options[st.session_state.correct_answer_index] if st.session_state.options[st.session_state.correct_answer_index].strip() else ""

        elif question_type == "true_false":
            st.session_state.options = ["True","False"]
            correct_answer = st.selectbox("✅ Correct Answer", st.session_state.options)
        else:
            correct_answer = st.text_input("✅ Correct Answer", placeholder="Expected answer")

        # Display selected topic info
        if selected_nano_topic_name:
            st.info(f"📍 This question will be saved to: **{selected_nano_topic_name}**")
        else:
            st.warning("⚠️ Please select a complete topic hierarchy above before saving.")

        if st.form_submit_button("💾 Save Question", type="primary"):
            if question_text and correct_answer and nano_topic_id:
                payload = {
                    "question_text": question_text,
                    "options": st.session_state.options if question_type == "mcq" else None,
                    "correct_answer": correct_answer,
                    "difficulty": difficulty,
                    "style": question_type,
                    "nano_topic_id": nano_topic_id
                }
                try:
                    save_resp = requests.post(f"{BACKEND_URL}/teacher/custom-questions", headers=headers, json=payload)
                    save_resp.raise_for_status()
                    st.success("Question saved!")
                    st.session_state.options = ["",""]
                    st.rerun()
                except requests.exceptions.RequestException as e:
                    st.error(f"Error saving: {e}")
            else:
                st.error("❌ Please fill in question text, correct answer, and select a complete topic hierarchy.")

with tab4:
    st.header("Announcements")
    
    classes = get_teacher_classes()
    if not classes:
        st.warning("⚠️ Please create a class first before posting announcements.")
    else:
        # Create announcement
        with st.expander("📢 Post New Announcement"):
            with st.form("new_announcement"):
                class_names = [c["name"] for c in classes]
                selected_class_for_announcement = st.selectbox("📚 Select Class", class_names)
                selected_class_id = next(c["id"] for c in classes if c["name"] == selected_class_for_announcement)
                
                announcement_title = st.text_input("📌 Title", placeholder="e.g., Homework Reminder")
                announcement_content = st.text_area("📝 Content", placeholder="Write your announcement here...")
                
                if st.form_submit_button("📤 Post Announcement", type="primary"):
                    if announcement_title and announcement_content:
                        try:
                            headers = {"Authorization": f"Bearer {st.session_state.token}"}
                            payload = {
                                "class_id": selected_class_id,
                                "content": f"{announcement_title}\n\n{announcement_content}"  # Combine since API has content
                            }
                            response = requests.post(f"{BACKEND_URL}/announcements/create", headers=headers, json=payload)
                            response.raise_for_status()
                            st.success("✅ Announcement posted successfully!")
                            st.rerun()
                        except requests.exceptions.RequestException as e:
                            st.error(f"Error posting announcement: {e}")
                    else:
                        st.error("❌ Please fill in both title and content.")
        
        # Display recent announcements (composite)
        st.subheader("📋 Recent Announcements")
        
        announcements = []
        try:
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            for cls in classes:
                resp = requests.get(f"{BACKEND_URL}/announcements/class/{cls['id']}", headers=headers)
                if resp.status_code == 200:
                    class_anns = resp.json().get("announcements", [])
                    for a in class_anns:
                        announcements.append({
                            "id": a["id"],
                            "title": "Announcement",  # Placeholder; API has no title
                            "content": a["content"],
                            "created_at": a["created_at"],
                            "class_name": cls["name"]
                        })
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching announcements: {e}")
        
        if announcements:
            for ann in announcements[:10]:  # Limit 10
                with st.container():
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"**{ann['title']}**")
                        st.write(ann["content"])
                    with col2:
                        st.caption(f"📚 {ann['class_name']}")
                        created = datetime.fromisoformat(ann['created_at'])
                        st.caption(f"📅 {created.strftime('%m/%d/%Y %H:%M')}")
                    st.divider()
        else:
            st.info("📭 No announcements posted yet.")