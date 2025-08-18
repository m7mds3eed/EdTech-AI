#!/bin/bash
echo "🚀 Starting Educational Platform Backend..."

# --- 1. PRE-FLIGHT CHECKS ---
# Check if running from the correct directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found. Please run this script from the backend directory."
    exit 1
fi

# Check for .env file and create a default one if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 .env file not found. Creating a default .env file..."
    cat > .env << 'EOF'
# OpenAI API Configuration
OPENAI_API_KEY="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

# Security
SECRET_KEY="generate_a_long_random_string_for_this"

# Database Path
DATABASE_PATH="data/math.db"
EOF
    echo "⚠️ IMPORTANT: Please open the .env file and add your real OPENAI_API_KEY."
    exit 1
fi

# --- 2. VIRTUAL ENVIRONMENT ---
# Create venv if it doesn't exist, and activate it
if [ ! -d "venv" ]; then
    echo "🐍 Virtual environment not found. Creating one..."
    python -m venv venv
    echo "✅ Virtual environment created. Please run 'source venv/bin/activate' and 'pip install -r requirements.txt', then start this script again."
    exit 1
fi
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# --- 3. DATABASE SETUP & POPULATION ---
# Create data directory if it doesn't exist
mkdir -p data

DB_FILE="data/math.db"
DB_EXISTS=true
if [ ! -f "$DB_FILE" ]; then
    DB_EXISTS=false
fi

# Step 3a: Always run the setup script to ensure the schema is up-to-date
echo "🗄️ Verifying database schema..."
python data/database_setup.py

# Step 3b: If the database was just created, populate it with initial data
if [ "$DB_EXISTS" = false ] ; then
    echo "🌱 New database created. Populating with initial data..."
    python data/data.py
    echo "✅ Database populated."
else
    echo "👍 Database schema checked and is up to date."
fi

# --- 4. START THE SERVER ---
echo "🌐 Server starting on http://localhost:8000"
echo "📖 API docs available at http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"

uvicorn main:app --reload --host 0.0.0.0 --port 8000