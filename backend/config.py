import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    # Database
    DATABASE_PATH = os.path.join("data", "math.db")
    
    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    
    # CORS
    ALLOWED_ORIGINS = [
        "http://localhost:3000",  # React dev server
        "http://localhost:3001",  # Alternative React port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]
    
    # Pagination
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    
    # Quiz settings
    DEFAULT_QUESTIONS_PER_QUIZ = 10
    MIN_QUESTIONS_PER_QUIZ = 5
    MAX_QUESTIONS_PER_QUIZ = 50

settings = Settings()