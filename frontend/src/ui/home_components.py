# FILE: src/ui/home_components.py

import streamlit as st
import requests
from datetime import datetime
from typing import List, Tuple, Dict, Optional
from src.auth.auth_handlers import AuthenticationError


class HomeComponents:
    """Reusable components and API handlers for home pages."""
    
    def __init__(self, backend_url: str):
        self.backend_url = backend_url
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests."""
        token = st.session_state.get("token")
        if not token:
            raise AuthenticationError("No authentication token found")
        return {"Authorization": f"Bearer {token}"}
    
    def load_subjects_and_micro_topics(self) -> Tuple[List[str], Dict[str, List[str]]]:
        """
        Load subjects and micro topics from curriculum structure.
        
        Returns:
            Tuple of (subjects list, micro_topics dict)
        """
        try:
            response = requests.get(f"{self.backend_url}/topics/structure", timeout=10)
            response.raise_for_status()
            curriculum = response.json().get("curriculum", [])
            
            subjects = [topic['name'] for topic in curriculum]
            micro_topics = {}
            
            for topic in curriculum:
                micros = set()
                for sub in topic.get('subtopics', []):
                    for micro in sub.get('micro_topics', []):
                        micros.add(micro['name'])
                micro_topics[topic['name']] = list(micros)
            
            return subjects, micro_topics
        except requests.exceptions.RequestException:
            return [], {}

    def get_pending_assignments(self) -> List[Tuple]:
        """
        Get ALL incomplete assignments for the student (including overdue ones).
        
        Returns:
            List of tuples: (title, due_date, class_name, attempts_left, assignment_id)
        """
        try:
            headers = self._get_auth_headers()
            
            # First get all classes the student is enrolled in
            classes_response = requests.get(
                f"{self.backend_url}/classes/my-classes",
                headers=headers,
                timeout=10
            )
            classes_response.raise_for_status()
            student_classes = classes_response.json().get("classes", [])
            
            all_assignments = []
            
            # For each class, get all assignments
            for class_info in student_classes:
                class_id = class_info["id"]
                class_name = class_info["name"]
                
                # Get assignments for this class
                assignments_response = requests.get(
                    f"{self.backend_url}/assignments/class/{class_id}",
                    headers=headers,
                    timeout=10
                )
                assignments_response.raise_for_status()
                assignments = assignments_response.json().get("assignments", [])
                
                # For each assignment, check if student has completed it
                for assignment in assignments:
                    assignment_id = assignment["id"]
                    
                    # Get student's submissions for this assignment
                    submissions_response = requests.get(
                        f"{self.backend_url}/assignments/{assignment_id}/submissions",
                        headers=headers,
                        timeout=10
                    )
                    
                    if submissions_response.status_code == 200:
                        submissions = submissions_response.json().get("submissions", [])
                        
                        # Check if any submission is completed
                        completed_submissions = [s for s in submissions if s.get("completed_at")]
                        
                        # If no completed submissions, this assignment is pending
                        if not completed_submissions:
                            attempts_used = len(submissions)
                            attempts_left = max(0, assignment["max_attempts"] - attempts_used)
                            
                            all_assignments.append((
                                assignment["title"],
                                assignment.get("due_date"),
                                class_name,
                                attempts_left,
                                assignment_id
                            ))
            
            # Sort by due date (overdue first, then by due date)
            def sort_key(assignment):
                due_date = assignment[1]
                if not due_date:
                    return (1, datetime.max)  # No due date = lowest priority
                
                due = datetime.fromisoformat(due_date)
                now = datetime.now()
                
                if due < now:
                    return (0, due)  # Overdue = highest priority
                else:
                    return (1, due)  # Future due dates
            
            all_assignments.sort(key=sort_key)
            return all_assignments
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching assignments: {e}")
            return []

    def get_class_announcements(self) -> List[Dict]:
        """
        Get announcements from all classes the student is enrolled in.
        
        Returns:
            List of announcement dictionaries with title, content, teacher_name, class_name
        """
        try:
            headers = self._get_auth_headers()
            
            # First get all classes the student is enrolled in
            classes_response = requests.get(
                f"{self.backend_url}/classes/my-classes",
                headers=headers,
                timeout=10
            )
            classes_response.raise_for_status()
            student_classes = classes_response.json().get("classes", [])
            
            all_announcements = []
            
            # For each class, get announcements
            for class_info in student_classes:
                class_id = class_info["id"]
                class_name = class_info["name"]
                
                announcements_response = requests.get(
                    f"{self.backend_url}/announcements/class/{class_id}",
                    headers=headers,
                    timeout=10
                )
                
                if announcements_response.status_code == 200:
                    announcements = announcements_response.json().get("announcements", [])
                    
                    # Add class name to each announcement and format for display
                    for announcement in announcements:
                        all_announcements.append({
                            "title": f"📢 Announcement",  # Generic title since backend doesn't provide one
                            "content": announcement["content"],
                            "teacher_name": announcement["teacher_name"],
                            "class_name": class_name,
                            "created_at": announcement["created_at"]
                        })
            
            # Sort by creation date (newest first)
            all_announcements.sort(
                key=lambda x: datetime.fromisoformat(x["created_at"]), 
                reverse=True
            )
            
            return all_announcements
        except requests.exceptions.RequestException as e:
            print(f"Error fetching announcements: {e}")
            return []

    def get_student_stats(self) -> Optional[Tuple[int, float, float]]:
        """
        Get student statistics.
        
        Returns:
            Tuple of (total_questions, accuracy, consistency) or None
        """
        try:
            headers = self._get_auth_headers()
            response = requests.get(
                f"{self.backend_url}/analytics/student-progress", 
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            overall = response.json().get("overall_stats", {})
            return (
                overall.get("total_questions", 0),
                overall.get("accuracy", 0),
                overall.get("consistency", 0)  # Now using backend-provided consistency
            )
        except requests.exceptions.RequestException:
            return None
  
    def join_class(self, class_code: str) -> Tuple[bool, str]:
        """
        Join a class using the class code.
        
        Args:
            class_code: The class code to join
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            headers = self._get_auth_headers()
            response = requests.post(
                f"{self.backend_url}/classes/join",
                headers=headers,
                json={"class_code": class_code},
                timeout=10
            )
            
            if response.status_code == 200:
                return True, "Successfully joined class!"
            elif response.status_code == 404:
                return False, "Invalid class code. Please check with your teacher."
            elif response.status_code == 400:
                return False, "You are already enrolled in this class."
            else:
                return False, f"Error joining class: {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            return False, f"Connection error: {str(e)}"

    def link_parent_to_student(self, link_code: str) -> bool:
        """
        Link parent to student account.
        
        Args:
            link_code: Student's link code
            
        Returns:
            bool: Success status
        """
        try:
            headers = self._get_auth_headers()
            response = requests.post(
                f"{self.backend_url}/auth/link-parent",
                headers=headers,
                json={"link_code": link_code},
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            return False
    
    def get_teacher_classes(self) -> List[Dict]:
        """
        Get classes for the current teacher.
        
        Returns:
            List of class dictionaries
        """
        try:
            headers = self._get_auth_headers()
            response = requests.get(
                f"{self.backend_url}/classes/my-classes", 
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json().get("classes", [])
        except requests.exceptions.RequestException:
            return []
    
    def get_student_privacy_info(self, student_id: int) -> Tuple[List[Dict], List[Dict]]:
        """
        Get privacy information for a student.
        
        Args:
            student_id: The student's ID
            
        Returns:
            Tuple of (parents list, teachers list)
        """
        # Placeholder implementation - would need backend endpoint
        return [], []

    def handle_session_expired(self):
        """Handle expired session by clearing session state"""
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Redirect to auth page
        st.switch_page("pages/auth.py")


# Utility functions for common UI patterns
def render_metric_card(title: str, value: str, delta: Optional[str] = None):
    """Render a styled metric card."""
    with st.container():
        if delta:
            st.metric(title, value, delta)
        else:
            st.metric(title, value)


def render_assignment_card(assignment: Tuple[str, str, str, int]):
    """Render an assignment card with consistent styling."""
    title, due_date, class_name, attempts_left = assignment
    
    with st.container():
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.write(f"**{title}**")
            st.caption(f"📚 Class: {class_name}")
        
        with col2:
            if due_date:
                due = datetime.fromisoformat(due_date)
                days_left = (due.date() - datetime.now().date()).days
                if days_left == 0:
                    st.warning("⏰ Due today!")
                elif days_left == 1:
                    st.info("📅 Due tomorrow")
                elif days_left < 0:
                    st.error("🚨 Overdue!")
                else:
                    st.info(f"📅 {days_left} days left")
        
        with col3:
            st.caption(f"🔄 {attempts_left} attempts left")


def render_announcement_card(announcement: Dict):
    """Render an announcement card with consistent styling."""
    with st.container():
        st.write(f"**{announcement['title']}**")
        st.caption(f"👩‍🏫 {announcement['teacher_name']} • {announcement['class_name']}")
        
        # Format creation date
        try:
            created_date = datetime.fromisoformat(announcement['created_at'])
            time_ago = datetime.now() - created_date
            if time_ago.days == 0:
                st.caption("📅 Today")
            elif time_ago.days == 1:
                st.caption("📅 Yesterday")
            else:
                st.caption(f"📅 {time_ago.days} days ago")
        except:
            pass
        
        with st.expander("Read more"):
            st.write(announcement['content'])