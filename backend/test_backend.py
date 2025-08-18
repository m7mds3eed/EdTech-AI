#!/usr/bin/env python3
"""
Comprehensive Backend Testing Script
Tests all FastAPI endpoints and functionality
"""

import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USER_DATA = {
    "student": {"username": "test_student", "password": "test123", "role": "student"},
    "parent": {"username": "test_parent", "password": "test123", "role": "parent"},
    "teacher": {"username": "test_teacher", "password": "test123", "role": "teacher"},
    "admin": {"username": "test_admin", "password": "test123", "role": "admin"}
}

class BackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.tokens = {}
        self.users = {}
        self.test_results = []
        ## MODIFICATION ##: Add a place to store real questions fetched from the API
        self.available_questions = []

    def log_test(self, test_name, success, message="", response_data=None):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        self.test_results.append({
            "test": test_name, "success": success,
            "message": message, "data": response_data
        })

    def get_auth_headers(self, role):
        """Get authorization headers for a role"""
        if role in self.tokens:
            return {"Authorization": f"Bearer {self.tokens[role]}"}
        return {}

    # --- Test Functions ---

    def test_health_check(self):
        # ... (This function is correct, no changes needed)
        try:
            response = self.session.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                data = response.json()
                self.log_test("Health Check", True, f"Server is healthy - {data.get('status')}")
                return True
            else:
                self.log_test("Health Check", False, f"Health check failed with status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Health Check", False, f"Connection failed: {str(e)}")
            return False

    def test_root_endpoint(self):
        # ... (This function is correct, no changes needed)
        try:
            response = self.session.get(f"{BASE_URL}/")
            if response.status_code == 200:
                data = response.json()
                self.log_test("Root Endpoint", True, f"API Info: {data.get('message')}")
                return True
            else:
                self.log_test("Root Endpoint", False, f"Root endpoint failed with status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Root Endpoint", False, f"Error: {str(e)}")
            return False

    def test_user_registration(self):
        # ... (This function is correct, no changes needed)
        success_count = 0
        for role, user_data in TEST_USER_DATA.items():
            try:
                response = self.session.post(f"{BASE_URL}/auth/register", json=user_data)
                if response.status_code == 200:
                    data = response.json()
                    self.users[role] = data
                    self.log_test(f"Register {role.title()}", True, f"User ID: {data.get('user_id')}")
                    success_count += 1
                else:
                    error_msg = response.json().get('detail', f'Status {response.status_code}')
                    self.log_test(f"Register {role.title()}", False, error_msg)
            except Exception as e:
                self.log_test(f"Register {role.title()}", False, str(e))
        return success_count == len(TEST_USER_DATA)

    def test_user_login(self):
        # ... (This function is correct, no changes needed)
        success_count = 0
        for role, user_data in TEST_USER_DATA.items():
            try:
                login_data = {"username": user_data["username"], "password": user_data["password"]}
                response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
                if response.status_code == 200:
                    data = response.json()
                    self.tokens[role] = data.get("token")
                    self.log_test(f"Login {role.title()}", True, f"Token received")
                    success_count += 1
                else:
                    error_msg = response.json().get('detail', f'Status {response.status_code}')
                    self.log_test(f"Login {role.title()}", False, error_msg)
            except Exception as e:
                self.log_test(f"Login {role.title()}", False, str(e))
        return success_count == len(TEST_USER_DATA)

    def test_curriculum_structure(self):
        # ... (This function is correct, no changes needed)
        try:
            response = self.session.get(f"{BASE_URL}/topics/structure")
            if response.status_code == 200:
                data = response.json()
                curriculum = data.get("curriculum", [])
                self.log_test("Curriculum Structure", True, f"Found {len(curriculum)} topics")
                return True
            else:
                self.log_test("Curriculum Structure", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Curriculum Structure", False, str(e))
            return False

    def test_nano_topics(self):
        # ... (This function is correct, no changes needed)
        try:
            response = self.session.get(f"{BASE_URL}/quiz/nano-topics/Numbers and the Number System")
            if response.status_code == 200:
                data = response.json()
                topics = data.get("nano_topics", [])
                self.log_test("Nano Topics", True, f"Found {len(topics)} nano topics")
                return True
            else:
                self.log_test("Nano Topics", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Nano Topics", False, str(e))
            return False

    ## MODIFICATION ##: This function now saves the questions it finds.
    def test_get_questions(self):
        """Test getting questions and save them for the submit test."""
        try:
            headers = self.get_auth_headers("student")
            response = self.session.get(f"{BASE_URL}/quiz/questions/Addition and Subtraction", headers=headers)
            if response.status_code == 200:
                data = response.json()
                questions = data.get("questions", [])
                self.log_test("Get Questions", True, f"Found {len(questions)} questions")
                if questions:
                    # Save the fetched questions to be used by the next test
                    self.available_questions = questions
                return True
            else:
                self.log_test("Get Questions", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Get Questions", False, str(e))
            return False

    ## MODIFICATION ##: This function is now dynamic and robust.
    def test_submit_answer(self):
        """Test submitting an answer using a real question fetched from the API."""
        # Check if the previous test found any questions
        if not self.available_questions:
            self.log_test("Submit Answer", False, "Skipping test: No questions were available to answer.")
            return False

        try:
            headers = self.get_auth_headers("student")
            # Use the first question that was fetched in the test_get_questions step
            question_to_answer = self.available_questions[0]

            answer_data = {
                "question": question_to_answer["question"],
                "answer": "a_test_answer",  # The actual answer doesn't matter, just that it's valid
                "nano_topic": "Addition and Subtraction",
                "hint_used": False,
                "lesson_viewed": False
            }
            response = self.session.post(f"{BASE_URL}/quiz/submit-answer", json=answer_data, headers=headers)
            
            # A successful submission will return a 200 status and a JSON body
            if response.status_code == 200 and "is_correct" in response.json():
                self.log_test("Submit Answer", True, "Answer submitted, received valid response.")
                return True
            else:
                # Try to get a detailed error message from the JSON response
                error_msg = response.json().get('detail', f'Status {response.status_code}')
                self.log_test("Submit Answer", False, error_msg)
                return False
        except Exception as e:
            self.log_test("Submit Answer", False, str(e))
            return False

    # ... (All other test functions like test_teacher_class_creation, etc., are correct and need no changes)
    def test_teacher_class_creation(self):
        try:
            headers = self.get_auth_headers("teacher")
            class_data = {"name": "Test Math Class", "description": "A test class for backend testing"}
            response = self.session.post(f"{BASE_URL}/classes/create", json=class_data, headers=headers)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Create Class", True, f"Class code: {data.get('class_code')}")
                return data.get('class_code')
            else:
                error_msg = response.json().get('detail', f'Status {response.status_code}')
                self.log_test("Create Class", False, error_msg)
                return None
        except Exception as e:
            self.log_test("Create Class", False, str(e))
            return None
    
    def test_student_join_class(self, class_code):
        if not class_code:
            self.log_test("Join Class", False, "No class code available")
            return False
        try:
            headers = self.get_auth_headers("student")
            join_data = {"class_code": class_code}
            response = self.session.post(f"{BASE_URL}/classes/join", json=join_data, headers=headers)
            if response.status_code == 200:
                self.log_test("Join Class", True, "Student joined class successfully")
                return True
            else:
                error_msg = response.json().get('detail', f'Status {response.status_code}')
                self.log_test("Join Class", False, error_msg)
                return False
        except Exception as e:
            self.log_test("Join Class", False, str(e))
            return False
    
    def test_parent_link_student(self):
        try:
            headers = self.get_auth_headers("parent")
            student_data = self.users.get("student", {})
            link_code = student_data.get("link_code")
            if not link_code:
                self.log_test("Parent Link Student", False, "No student link code available")
                return False
            link_data = {"link_code": link_code}
            response = self.session.post(f"{BASE_URL}/auth/link-parent", json=link_data, headers=headers)
            if response.status_code == 200:
                self.log_test("Parent Link Student", True, "Parent linked to student successfully")
                return True
            else:
                error_msg = response.json().get('detail', f'Status {response.status_code}')
                self.log_test("Parent Link Student", False, error_msg)
                return False
        except Exception as e:
            self.log_test("Parent Link Student", False, str(e))
            return False

    def test_student_analytics(self):
        try:
            headers = self.get_auth_headers("student")
            response = self.session.get(f"{BASE_URL}/analytics/student-progress", headers=headers)
            if response.status_code == 200:
                data = response.json()
                stats = data.get("overall_stats", {})
                self.log_test("Student Analytics", True, f"Questions: {stats.get('total_questions', 0)}")
                return True
            else:
                error_msg = response.json().get('detail', f'Status {response.status_code}')
                self.log_test("Student Analytics", False, error_msg)
                return False
        except Exception as e:
            self.log_test("Student Analytics", False, str(e))
            return False
    
    def test_parent_reports(self):
        try:
            headers = self.get_auth_headers("parent")
            response = self.session.get(f"{BASE_URL}/analytics/parent-report", headers=headers)
            if response.status_code == 200:
                data = response.json()
                reports = data.get("reports", [])
                self.log_test("Parent Reports", True, f"Found {len(reports)} student reports")
                return True
            else:
                error_msg = response.json().get('detail', f'Status {response.status_code}')
                self.log_test("Parent Reports", False, error_msg)
                return False
        except Exception as e:
            self.log_test("Parent Reports", False, str(e))
            return False
    
    def test_feedback_submission(self):
        try:
            headers = self.get_auth_headers("student")
            feedback_data = {"feedback_text": "This is a test feedback", "rating": 5, "context": "testing"}
            response = self.session.post(f"{BASE_URL}/feedback/submit", json=feedback_data, headers=headers)
            if response.status_code == 200:
                self.log_test("Submit Feedback", True, "Feedback submitted successfully")
                return True
            else:
                error_msg = response.json().get('detail', f'Status {response.status_code}')
                self.log_test("Submit Feedback", False, error_msg)
                return False
        except Exception as e:
            self.log_test("Submit Feedback", False, str(e))
            return False
    
    def test_admin_features(self):
        try:
            headers = self.get_auth_headers("admin")
            # Test question stats
            response = self.session.get(f"{BASE_URL}/admin/question-stats", headers=headers)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Admin Question Stats", True, f"Total questions: {data.get('total_questions', 0)}")
            else:
                self.log_test("Admin Question Stats", False, f"Status {response.status_code}")
            # Test rejected questions
            response = self.session.get(f"{BASE_URL}/admin/rejected-questions", headers=headers)
            if response.status_code == 200:
                data = response.json()
                rejected = data.get("rejected_questions", [])
                self.log_test("Admin Rejected Questions", True, f"Found {len(rejected)} rejected questions")
            else:
                self.log_test("Admin Rejected Questions", False, f"Status {response.status_code}")
            return True
        except Exception as e:
            self.log_test("Admin Features", False, str(e))
            return False

    def run_all_tests(self):
        """Run comprehensive backend tests"""
        print("🚀 Starting Backend Testing...")
        print("=" * 50)
        
        if not self.test_health_check():
            print("❌ Health check failed. Is the server running on port 8000?")
            return False
        
        self.test_root_endpoint()
        self.test_curriculum_structure()
        self.test_nano_topics()
        
        if not self.test_user_registration():
            print("❌ User registration failed. Database issues?")
            return False
        
        if not self.test_user_login():
            print("❌ User login failed. Authentication issues?")
            return False
        
        ## MODIFICATION ##: The order of these two tests is now critical.
        # We must get the questions first, so we have something to submit.
        self.test_get_questions()
        self.test_submit_answer()
        
        self.test_student_analytics()
        
        class_code = self.test_teacher_class_creation()
        self.test_student_join_class(class_code)
        
        self.test_parent_link_student()
        self.test_parent_reports()
        
        self.test_feedback_submission()
        self.test_admin_features()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        print(f"Total Tests: {total}\nPassed: {passed}\nFailed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if passed < total:
            print("\n⚠️ Failed tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        return passed == total

def main():
    """Main testing function"""
    print("🧪 FastAPI Backend Testing Tool")
    print("Ensure your backend server is running on http://localhost:8000")
    print("Press Enter to continue or Ctrl+C to exit...")
    try:
        input()
    except KeyboardInterrupt:
        print("\nTesting cancelled.")
        return
    
    tester = BackendTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 ALL TESTS PASSED! Backend is ready for frontend integration.")
    else:
        print("\n❌ Backend testing found issues. Please fix the issues before proceeding.")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()