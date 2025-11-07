#!/bin/bash

# NBA RAG System Complete Setup Script
# This script sets up the entire RAG system for NBA statistics analysis

echo "🏀 NBA RAG System Complete Setup"
echo "================================="

# Check if we're in the right directory
if [ ! -f "nba-backend/requirements.txt" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Step 1: Install Python dependencies
echo "📦 Installing Python dependencies..."
cd nba-backend
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Python dependencies"
    exit 1
fi

echo "✅ Python dependencies installed"

# Step 2: Check environment variables
echo "🔧 Checking environment variables..."
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating template..."
    cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key_here
MONGODB_URI=mongodb://localhost:27017/
BALLDONTLIE_API_KEY=your_balldontlie_api_key_here
EOF
    echo "📝 Please edit .env file with your actual API keys"
    echo "   Then run this script again"
    exit 1
fi

# Check if API keys are set
if grep -q "your_openai_api_key_here" .env; then
    echo "⚠️  Please update .env file with your actual API keys"
    exit 1
fi

echo "✅ Environment variables configured"

# Step 3: Check MongoDB connection
echo "🗄️  Checking MongoDB connection..."
python -c "
from pymongo import MongoClient
import os
from dotenv import load_dotenv
load_dotenv()
try:
    client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
    client.admin.command('ping')
    print('✅ MongoDB connection successful')
except Exception as e:
    print(f'❌ MongoDB connection failed: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ MongoDB connection failed. Please ensure MongoDB is running"
    exit 1
fi

# Step 4: Check if data exists
echo "📊 Checking data availability..."
python -c "
from pymongo import MongoClient
import os
from dotenv import load_dotenv
load_dotenv()
client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
db = client['nba_stats']
collections = ['teams', 'players', 'games', 'coaches']
total_docs = 0
for collection in collections:
    count = db[collection].count_documents({})
    total_docs += count
    print(f'   {collection}: {count} documents')
if total_docs == 0:
    print('⚠️  No data found. Please run: python scraper.py')
    exit(1)
else:
    print(f'✅ Total documents: {total_docs}')
"

if [ $? -ne 0 ]; then
    echo "❌ No data found. Please run the scraper first:"
    echo "   cd nba-backend && python scraper.py"
    exit 1
fi

# Step 5: Initialize RAG system
echo "🚀 Initializing RAG system..."
python setup_rag.py

if [ $? -ne 0 ]; then
    echo "❌ RAG system initialization failed"
    exit 1
fi

echo "✅ RAG system initialized successfully"

# Step 6: Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd ../nba-frontend
npm install

if [ $? -ne 0 ]; then
    echo "❌ Failed to install frontend dependencies"
    exit 1
fi

echo "✅ Frontend dependencies installed"

# Step 7: Create startup scripts
echo "📝 Creating startup scripts..."

# Backend startup script
cat > ../start_backend.sh << 'EOF'
#!/bin/bash
cd nba-backend
echo "🚀 Starting NBA RAG Backend..."
python app.py
EOF

# Frontend startup script
cat > ../start_frontend.sh << 'EOF'
#!/bin/bash
cd nba-frontend
echo "🚀 Starting NBA RAG Frontend..."
npm start
EOF

# Make scripts executable
chmod +x ../start_backend.sh
chmod +x ../start_frontend.sh

echo "✅ Startup scripts created"

# Step 8: Final instructions
echo ""
echo "🎉 NBA RAG System Setup Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Start the backend server:"
echo "   ./start_backend.sh"
echo "   (or: cd nba-backend && python app.py)"
echo ""
echo "2. In a new terminal, start the frontend:"
echo "   ./start_frontend.sh"
echo "   (or: cd nba-frontend && npm start)"
echo ""
echo "3. Open your browser to:"
echo "   http://localhost:3000"
echo ""
echo "4. Use the 'RAG Analysis' tab to ask questions like:"
echo "   - 'Who are the top 5 teams with most championships?'"
echo "   - 'What are LeBron James' career statistics?'"
echo "   - 'Compare the Warriors and Celtics performance'"
echo ""
echo "📚 For more information, see RAG_README.md"
echo ""
echo "Happy analyzing! 🏀"
