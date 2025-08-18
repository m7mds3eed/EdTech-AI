#!/usr/bin/env python3
"""
Startup script for the Educational Platform API
"""

import uvicorn
import os
import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

# Ensure data directory exists
data_dir = current_dir / "data"
data_dir.mkdir(exist_ok=True)

def main():
    """Main function to run the server"""
    print("🚀 Starting Educational Platform API...")
    print("📚 Initializing database...")
    
    # Import and initialize
    from main import app
    from src.auth.auth import init_db
    
    # Initialize database
    init_db()
    print("✅ Database initialized successfully!")
    
    print("🌐 Starting server on http://localhost:8000")
    print("📖 API documentation available at http://localhost:8000/docs")
    print("🔧 Interactive API at http://localhost:8000/redoc")
    
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload for development
        log_level="info"
    )

if __name__ == "__main__":
    main()