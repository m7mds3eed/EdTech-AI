import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Database Configuration ---
# Path to the SQLite database file
# Path to the SQLite database file
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "math.db")
# --- OpenAI API Configuration ---
# Your OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# The model to use for validation
VALIDATION_MODEL = "gpt-3.5-turbo"

# --- Supervisor Settings ---
# The number of questions to validate in each run
BATCH_SIZE = 10

# Log file for the supervisor's findings
LOG_FILE = os.path.join(os.path.dirname(__file__), "supervisor_log.txt")