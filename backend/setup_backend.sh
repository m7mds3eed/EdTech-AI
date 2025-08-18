#!/bin/bash

# Backend Setup Script for Educational Platform
echo "🎓 Educational Platform Backend Setup"
echo "======================================"

# Check if we're in the backend directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found. Please run this script from the backend directory."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install fastapi==0.104.1
pip install uvicorn[standard]==0.24.0
pip install pydantic==2.5.0
pip install python-multipart==0.0.6
pip install python-dotenv==1.0.0
pip install openai==1.3.0
pip install numpy==1.25.2
pip install python-jose[cryptography]==3.3.0
pip install passlib[bcrypt]==1.7.4

echo "✅ Dependencies installed successfully!"

# Check for .env file
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "⚠️ Please edit .env file and add your OPENAI_API_KEY"
    else
        cat > .env << EOF
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Security
SECRET_KEY=your_secret_key_here_generate_a_random_string

# Database (optional, defaults to data/math.db)
DATABASE_PATH=data/math.db

# Development settings
DEBUG=True
ENVIRONMENT=development

# CORS settings (comma-separated list)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000

# Email settings (for future notifications)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EOF
        echo "⚠️ Created .env file. Please edit it and add your OPENAI_API_KEY"
    fi
fi

# Create data directory
echo "📁 Creating data directory..."
mkdir -p data

# Check if database exists, if not run the data population script
if [ ! -f "data/math.db" ]; then
    echo "🗄️ Database not found. Initializing database..."
    if [ -f "data/data.py" ]; then
        echo "📊 Populating database with curriculum data..."
        python data/data.py
        if [ $? -eq 0 ]; then
            echo "✅ Database initialized successfully!"
        else
            echo "⚠️ Database initialization had issues, but continuing..."
        fi
    else
        echo "⚠️ data/data.py not found. Database will be created on first run."
    fi
fi

# Run database migrations
echo "🔄 Running database migrations..."
if [ -f "data/add_teacher_features.py" ]; then
    python data/add_teacher_features.py
fi

if [ -f "data/add_enhanced_assignment_features.py" ]; then
    python data/add_enhanced_assignment_features.py
fi

if [ -f "data/fix_database_columns.py" ]; then
    python data/fix_database_columns.py
fi

echo "✅ Database migrations completed!"

# Create a simple startup script
cat > start_backend.sh << 'EOF'
#!/bin/bash
echo "🚀 Starting Educational Platform Backend..."

# Activate virtual environment
source venv/bin/activate

# Check if .env file exists and has API key
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create it with your configuration."
    exit 1
fi

if ! grep -q "OPENAI_API_KEY=sk-" .env; then
    echo "⚠️ Warning: OPENAI_API_KEY not set in .env file. AI features may not work."
fi

# Start the server
echo "🌐 Server starting on http://localhost:8000"
echo "📖 API docs available at http://localhost:8000/docs"
echo "🔧 Interactive API at http://localhost:8000/redoc"
echo ""
echo "Press Ctrl+C to stop the server"

uvicorn main:app --reload --host 0.0.0.0 --port 8000
EOF

chmod +x start_backend.sh

echo ""
echo "🎉 Backend setup completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file and add your OPENAI_API_KEY"
echo "2. Run: ./start_backend.sh"
echo "3. Test with: python test_backend.py"
echo ""
echo "🔗 Important URLs:"
echo "   • Backend API: http://localhost:8000"
echo "   • API Documentation: http://localhost:8000/docs"
echo "   • Health Check: http://localhost:8000/health"
echo ""

# Check if OPENAI_API_KEY is set
if grep -q "your_openai_api_key_here" .env 2>/dev/null; then
    echo "⚠️ IMPORTANT: Please set your OPENAI_API_KEY in the .env file before starting!"
fi