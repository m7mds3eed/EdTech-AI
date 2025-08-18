import streamlit as st
import requests
import random

# --- Configuration ---
BACKEND_URL = "http://127.0.0.1:8000"  # Or use os.environ.get for production

def render_question(subject, micro_topic, question_index):
    """Render a single question for the quiz with skip, hint, and lesson functionality."""
    # Initialize session state variables if not present
    if "current_question" not in st.session_state:
        st.session_state.current_question = None
    if "skips" not in st.session_state:
        st.session_state.skips = 0
    if "attempts" not in st.session_state:
        st.session_state.attempts = 0
    if "new_question_needed" not in st.session_state:
        st.session_state.new_question_needed = True
    if "hint_shown" not in st.session_state:
        st.session_state.hint_shown = False
    if "hint_used" not in st.session_state:
        st.session_state.hint_used = False
    if "lesson_shown" not in st.session_state:
        st.session_state.lesson_shown = False
    if "lesson_viewed" not in st.session_state:
        st.session_state.lesson_viewed = False
    if "bkt" not in st.session_state:  # Minimal BKT state; backend handles most
        st.session_state.bkt = {}

    # Ensure token exists (from login)
    if "token" not in st.session_state:
        st.error("Session expired. Please log in again.")
        st.switch_page("app.py")

    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    # Generate new question if needed
    if st.session_state.get("new_question_needed", True):
        # Reset hint and lesson states for new question
        st.session_state.hint_shown = False
        st.session_state.hint_used = False
        st.session_state.lesson_shown = False
        st.session_state.lesson_viewed = False
        
        # Check if we're in assignment mode and handle accordingly
        if st.session_state.get("assignment_mode") and st.session_state.get("assignment_id"):
            # ASSIGNMENT MODE - Get questions from assignment
            assignment_id = st.session_state.assignment_id
            
            # Initialize assignment question pool if not exists
            if "assignment_questions" not in st.session_state:
                try:
                    response = requests.get(f"{BACKEND_URL}/assignments/{assignment_id}/questions", headers=headers)
                    response.raise_for_status()
                    assignment_questions = response.json().get("questions", [])
                    
                    if not assignment_questions:
                        st.error("⚠️ No questions available for this assignment.")
                        st.info("Please contact your teacher - this assignment may not be properly configured.")
                        if st.button("⬅️ Back to Assignments"):
                            st.switch_page("pages/student_assignments.py")
                        st.stop()
                    
                    # Shuffle questions for variety
                    random.shuffle(assignment_questions)
                    st.session_state.assignment_questions = assignment_questions
                    st.session_state.assignment_question_index = 0
                except requests.exceptions.RequestException as e:
                    st.error(f"Error fetching assignment questions: {e}")
                    st.stop()
            
            # Get next question from assignment pool
            if st.session_state.assignment_question_index >= len(st.session_state.assignment_questions):
                # Reshuffle and start over if we've used all questions
                random.shuffle(st.session_state.assignment_questions)
                st.session_state.assignment_question_index = 0
            
            question_data = st.session_state.assignment_questions[st.session_state.assignment_question_index]
            st.session_state.assignment_question_index += 1
            
            st.session_state.current_question = {
                "id": question_index + 1,
                "question": question_data["question"],
                "options": question_data.get("options", []),
                "answer": question_data["answer"],
                "topic": question_data.get("nano_topic", "Assignment Question"),
                "style": question_data.get("style", "mcq")
            }
        else:
            # PRACTICE MODE - Use existing logic
            # Fetch nano topics for the micro topic (cache in session)
            if f"nano_topics_{subject}_{micro_topic}" not in st.session_state:
                try:
                    response = requests.get(f"{BACKEND_URL}/quiz/nano-topics/{subject}?micro_topic={micro_topic}", headers=headers)
                    response.raise_for_status()
                    st.session_state[f"nano_topics_{subject}_{micro_topic}"] = response.json().get("nano_topics", [])
                except requests.exceptions.RequestException as e:
                    st.error(f"Error fetching topics: {e}")
                    st.stop()
            
            nano_topics = st.session_state[f"nano_topics_{subject}_{micro_topic}"]
            if not nano_topics:
                st.error(f"No nano-topics found for subject: {subject}, micro-topic: {micro_topic}.")
                st.stop()

            # Select next topic via backend (based on BKT)
            try:
                response = requests.get(f"{BACKEND_URL}/quiz/next-topic", headers=headers)
                response.raise_for_status()
                next_topic = response.json().get("next_topic")
                if not next_topic or next_topic not in [n["name"] for n in nano_topics]:
                    next_topic = random.choice([n["name"] for n in nano_topics])  # Fallback
            except requests.exceptions.RequestException:
                next_topic = random.choice([n["name"] for n in nano_topics])  # Fallback on error

            # Get questions for the selected nano-topic
            try:
                response = requests.get(f"{BACKEND_URL}/quiz/questions/{next_topic}", headers=headers)
                response.raise_for_status()
                questions = response.json().get("questions", [])
            except requests.exceptions.RequestException as e:
                st.error(f"Error fetching questions: {e}")
                questions = []

            if not questions:
                st.warning("⚠️ We're sorry, there are no approved questions available for this topic yet.")
                st.info("Our supervisors are working on it. Please select another topic or check back later.")
                if st.button("⬅️ Back to Home"):
                    st.switch_page("app.py")
                st.stop()

            # Select question based on current mastery (approximate locally or from backend response)
            question_data = random.choice(questions)  # Backend can filter; here random for simplicity

            st.session_state.current_question = {
                "id": question_index + 1,
                "question": question_data["question"],
                "options": question_data.get("options", []),
                "answer": question_data["answer"],
                "topic": next_topic,
                "style": question_data.get("style", "mcq")
            }
        
        st.session_state.new_question_needed = False

    question = st.session_state.current_question
    
    # Display question
    st.write(f"**Question {question_index + 1}**: {question['question']}")
    
    # Display hint if requested
    if st.session_state.hint_shown:
        st.info(f"💡 **Hint**: {st.session_state.hint_text}")
    
    # Display lesson if requested
    if st.session_state.lesson_shown:
        with st.expander("📚 Mini-Lesson", expanded=True):
            st.markdown(st.session_state.lesson_text)
    
    # Question input based on style
    answer = None
    if question["style"] == "mcq":
        if question["options"]:
            answer = st.radio("Select your answer:", question["options"], key=f"q{question['id']}")
        else:
            st.error("This multiple-choice question has no options.")
    elif question["style"] == "true_false":
        answer = st.radio("Select your answer:", ["True", "False"], key=f"q{question['id']}")
    elif question["style"] == "short_answer":
        answer = st.text_input("Your answer:", key=f"q{question['id']}")
    elif question["style"] == "exam_style":
        st.write("Provide your step-by-step solution below:")
        answer = st.text_area("Your answer:", key=f"q{question['id']}")
    else:
        st.error(f"Unsupported question style: {question['style']}")
    
    # Action buttons
    col1, col2, col3, col4 = st.columns(4)
    
    # Check permissions for hints/lessons (assume from session; set in quiz start)
    hints_allowed = st.session_state.get("assignment_hints_allowed", True)
    lessons_allowed = st.session_state.get("assignment_lessons_allowed", True)
    
    with col1:
        if hints_allowed:
            if st.button("💡 Hint", help="Get a helpful hint", key=f"hint_{question['id']}"):
                if not st.session_state.hint_shown:
                    try:
                        # Add assignment_id parameter if in assignment mode
                        url = f"{BACKEND_URL}/quiz/hint?question={question['question']}&nano_topic={question['topic']}"
                        if st.session_state.get("assignment_mode") and st.session_state.get("assignment_id"):
                            url += f"&assignment_id={st.session_state.assignment_id}"
                        
                        response = requests.get(url, headers=headers)
                        response.raise_for_status()
                        st.session_state.hint_text = response.json().get("hint")
                        st.session_state.hint_shown = True
                        st.session_state.hint_used = True
                        st.rerun()
                    except requests.exceptions.RequestException as e:
                        st.error(f"Error getting hint: {e}")
        else:
            st.button("💡 Hint", disabled=True, help="Hints disabled for this assignment", key=f"hint_disabled_{question['id']}")
    
    with col2:
        if lessons_allowed:
            if st.button("📚 Lesson", help="View a mini-lesson", key=f"lesson_{question['id']}"):
                if not st.session_state.lesson_shown:
                    try:
                        # Add assignment_id parameter if in assignment mode
                        url = f"{BACKEND_URL}/quiz/lesson?question={question['question']}&nano_topic={question['topic']}"
                        if st.session_state.get("assignment_mode") and st.session_state.get("assignment_id"):
                            url += f"&assignment_id={st.session_state.assignment_id}"
                        
                        response = requests.get(url, headers=headers)
                        response.raise_for_status()
                        st.session_state.lesson_text = response.json().get("lesson")
                        st.session_state.lesson_shown = True
                        st.session_state.lesson_viewed = True
                        st.rerun()
                    except requests.exceptions.RequestException as e:
                        st.error(f"Error getting lesson: {e}")
        else:
            st.button("📚 Lesson", disabled=True, help="Lessons disabled for this assignment", key=f"lesson_disabled_{question['id']}")
    
    with col3:
        if st.button("⏭️ Skip", help="Skip this question", key=f"skip_{question['id']}"):
            _handle_skip(question, subject, micro_topic)
            st.rerun()
    
    with col4:
        # Enable submit only if answer is provided
        submit_disabled = False
        if question["style"] in ["mcq", "true_false"]:
            submit_disabled = answer is None
        else:
            submit_disabled = not answer or not answer.strip()
            
        if st.button("✅ Submit", disabled=submit_disabled, type="primary", key=f"submit_{question['id']}"):
            _handle_submit(answer, question, subject, micro_topic)
            st.rerun()

def _handle_submit(answer, question, subject, micro_topic):
    """Handle submitting an answer via backend."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        payload = {
            "question": question["question"],
            "answer": answer,
            "nano_topic": question["topic"],
            "hint_used": st.session_state.hint_used,
            "lesson_viewed": st.session_state.lesson_viewed
        }
        
        # Add assignment_id if in assignment mode
        url = f"{BACKEND_URL}/quiz/submit-answer"
        if st.session_state.get("assignment_mode") and st.session_state.get("assignment_id"):
            url += f"?assignment_id={st.session_state.assignment_id}"
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        resp_data = response.json()
        
        correct = resp_data.get("is_correct", False)
        p_learned = resp_data.get("p_learned", 0.0)
        
        st.session_state.attempts += 1
        st.session_state.points += 10 if correct else 0
        
        # Update local BKT minimally (full in backend)
        topic = question["topic"]
        if subject not in st.session_state.bkt:
            st.session_state.bkt[subject] = {}
        if micro_topic not in st.session_state.bkt[subject]:
            st.session_state.bkt[subject][micro_topic] = {}
        st.session_state.bkt[subject][micro_topic][topic] = {"p_learned": p_learned}
        
        # Update results
        if correct:
            st.session_state.results["strengths"].append(question["question"])
        else:
            st.session_state.results["weaknesses"].append({"question": question["question"]})
        
        # Check mastery for badge (approximate)
        mastery = all(t.get("p_learned", 0) > 0.8 for t in st.session_state.bkt.get(subject, {}).get(micro_topic, {}).values())
        st.session_state.badge = f"{subject.capitalize()} Star" if mastery else None
        
        st.session_state.last_answer_correct = correct
        st.session_state.question_index += 1
        st.session_state.new_question_needed = True
    except requests.exceptions.RequestException as e:
        st.error(f"Error submitting answer: {e}")

def _handle_skip(question, subject, micro_topic):
    """Handle skipping a question via backend submit (as incorrect/null)."""
    st.session_state.attempts += 1
    st.session_state.skips += 1
    
    # Log skip via backend (treat as not correct)
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        payload = {
            "question": question["question"],
            "answer": "",  # Empty for skip
            "nano_topic": question["topic"],
            "hint_used": st.session_state.hint_used,
            "lesson_viewed": st.session_state.lesson_viewed
        }
        
        # Add assignment_id if in assignment mode
        url = f"{BACKEND_URL}/quiz/submit-answer"
        if st.session_state.get("assignment_mode") and st.session_state.get("assignment_id"):
            url += f"?assignment_id={st.session_state.assignment_id}"
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        # Update local state if needed from response (e.g., p_learned)
        
        # Set session state to indicate this was a skip for assignment progress tracking
        st.session_state.last_answer_correct = False  # Skips count as incorrect
        
    except requests.exceptions.RequestException as e:
        st.error(f"Error logging skip: {e}")
    
    # Move to next question
    st.session_state.question_index += 1
    st.session_state.new_question_needed = True

def render_results():
    """Render quiz results for students."""
    st.header("🎉 Quiz Complete!")
    
    total_questions = st.session_state.question_index
    # Handle division by zero if no questions were answered
    answered_questions = len(st.session_state.results["strengths"]) + len(st.session_state.results["weaknesses"])
    max_points = answered_questions * 10
    accuracy = (st.session_state.points / max_points * 100) if max_points > 0 else 0
    
    # Results summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Questions Answered", answered_questions)
    with col2:
        st.metric("Points Earned", f"{st.session_state.points}/{max_points}")
    with col3:
        st.metric("Accuracy", f"{accuracy:.1f}%")
    
    # Progress bar
    if max_points > 0:
        st.progress(st.session_state.points / max_points)
    
    # Strengths and weaknesses
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("✅ Strengths")
        if st.session_state.results["strengths"]:
            for s in st.session_state.results["strengths"]:
                st.write(f"- {s}")
        else:
            st.info("No strengths identified yet. Keep practicing!")
    
    with col2:
        st.subheader("📚 Areas to Improve")
        if st.session_state.results["weaknesses"]:
            for w in st.session_state.results["weaknesses"]:
                st.write(f"- {w['question']}")
        else:
            st.success("Great job! No weak areas identified.")
    
    # Badge
    if st.session_state.badge:
        st.success(f"🏆 Badge Earned: {st.session_state.badge}")
    
    # Action buttons
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 View Profile", use_container_width=True):
            st.switch_page("pages/student_profile.py")
    
    with col2:
        if st.button("🔄 Practice Again", use_container_width=True, type="primary"):
            # Reset for new practice session
            st.session_state.question_index = 0
            st.session_state.show_results = False
            st.session_state.results = {"strengths": [], "weaknesses": []}
            st.session_state.points = 0
            st.session_state.badge = None
            st.session_state.skips = 0
            st.session_state.attempts = 0
            st.session_state.new_question_needed = True
            st.rerun()
    
    with col3:
        if st.button("🏠 Back to Home", use_container_width=True):
            # Clear everything and go home
            keys_to_clear = [
                "question_index", "current_subject", "current_micro_topic", "show_results", 
                "results", "points", "badge", "skips", "attempts", "current_question",
                "new_question_needed", "hint_shown", "lesson_shown", "last_answer_correct",
                "assignment_questions", "assignment_question_index"
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.switch_page("app.py")

def render_parent_dashboard():
    """Redirect to parent dashboard for parents."""
    if st.session_state.role == "parent":
        st.switch_page("pages/parent_dashboard.py")
    else:
        st.write("Parent dashboard is only available for parent accounts.")