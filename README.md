# Learning Gap Identifier

This is a full-stack educational application designed to help students, parents, and teachers identify and address learning gaps in Mathematics. The application features a Streamlit frontend for an interactive user experience and a FastAPI backend to handle the business logic, data storage, and AI-powered features.

-----

## Features

### Frontend (Streamlit)

  * **User-friendly interface:** A clean and intuitive UI for a seamless user experience.
  * **Role-based access control:** Separate dashboards and functionalities for students, parents, and teachers.
  * **Interactive quizzes:** Engaging quizzes with multiple question types.
  * **Personalized learning:** AI-powered hints and mini-lessons to help students understand concepts.
  * **Progress tracking:** Detailed analytics and visualizations for students to monitor their progress.
  * **Parental monitoring:** Parents can track their children's performance and get actionable insights.
  * **Teacher tools:** Teachers can create and manage classes, assign quizzes, and monitor student performance.

### Backend (FastAPI)

* **RESTful API:** A robust and scalable API engineered to handle all application requests, from user authentication to complex data queries.
* **Adaptive Learning Engine:** Implements a **Bayesian Knowledge Tracing (BKT)** model to dynamically track student mastery in real-time and deliver personalized, adaptive learning paths.
* **AI Content Generation:** Integrates with OpenAI to dynamically generate a rich variety of quiz questions, contextual hints, and comprehensive mini-lessons, ensuring a constantly evolving content library.
* **Supervisor AI:** An autonomous AI-powered system that validates the quality and mathematical correctness of all quiz questions, guaranteeing high educational standards and accuracy.
* **Role-Based Analytics Engine:** Provides detailed, aggregated analytics endpoints tailored specifically for students, parents, and teachers, transforming raw data into actionable insights.
* **Secure Authentication:** Manages secure user registration, login, and session handling with role-based access control for all user types.
* **Database Management:** Utilizes an SQLite database to efficiently store and manage all application data, including user profiles, class structures, assignments, and granular student results.

-----

## Tech Stack

  * **Frontend:** Streamlit
  * **Backend:** FastAPI, Python 3.9
  * **Database:** SQLite
  * **AI:** OpenAI GPT-3.5 Turbo
  * **Other Libraries:** Pandas, Plotly Express

-----

## Getting Started

### Prerequisites

  * Python 3.9 or higher
  * pip (Python package installer)
  * A virtual environment tool (e.g., `venv`)

### Backend Setup

1.  **Navigate to the `backend` directory:**

    ```sh
    cd backend
    ```

2.  **Run the setup script:**
    This will create a virtual environment, install the required dependencies, and set up the database.

    ```sh
    bash setup_backend.sh
    ```

3.  **Configure your environment variables:**
    Open the `.env` file and add your OpenAI API key.

4.  **Start the backend server:**

    ```sh
    bash start_backend.sh
    ```

    The backend server will be running at `http://localhost:8000`.

### Frontend Setup

1.  **Navigate to the `frontend` directory:**

    ```sh
    cd frontend
    ```

2.  **Install the required dependencies:**

    ```sh
    pip install -r requirements.txt
    ```

3.  **Run the Streamlit application:**

    ```sh
    streamlit run app.py
    ```

    The Streamlit application will be running at `http://localhost:8501`.

-----

## Usage

Once both the backend and frontend servers are running, you can access the application by navigating to `http://localhost:8501` in your web browser. You can register as a student, parent, or teacher and start using the application.

-----

## Testing

To run the backend tests, navigate to the `backend` directory and run the following command:

```sh
python test_backend.py
```
