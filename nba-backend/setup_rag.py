#!/usr/bin/env python3
"""
Setup script for NBA RAG System

This script helps you set up and test the RAG system for NBA statistics analysis.
"""

import os
import sys
from dotenv import load_dotenv
from rag_system import NBARAGAgent
import time

def check_environment():
    """Check if all required environment variables are set"""
    load_dotenv()
    
    required_vars = ['OPENAI_API_KEY', 'MONGODB_URI']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these in your .env file or environment.")
        return False
    
    print("✅ All required environment variables are set")
    return True

def test_mongodb_connection():
    """Test MongoDB connection"""
    try:
        from pymongo import MongoClient
        mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        client = MongoClient(mongo_uri)
        client.admin.command('ping')
        print("✅ MongoDB connection successful")
        return True
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return False

def check_data_availability():
    """Check if NBA data is available in MongoDB"""
    try:
        from pymongo import MongoClient
        mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        client = MongoClient(mongo_uri)
        db = client["nba_stats"]
        
        collections = {
            'teams': db.teams.count_documents({}),
            'players': db.players.count_documents({}),
            'games': db.games.count_documents({}),
            'coaches': db.coaches.count_documents({})
        }
        
        print("📊 Data availability in MongoDB:")
        for collection, count in collections.items():
            status = "✅" if count > 0 else "❌"
            print(f"   {status} {collection}: {count} documents")
        
        total_docs = sum(collections.values())
        if total_docs == 0:
            print("\n⚠️  No data found in MongoDB. Please run the scraper first.")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking data: {e}")
        return False

def initialize_rag_system():
    """Initialize the RAG system"""
    try:
        print("\n🚀 Initializing RAG system...")
        mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        
        rag_agent = NBARAGAgent(mongo_uri, openai_api_key)
        
        print("   Processing data and building vector store...")
        start_time = time.time()
        rag_agent.initialize()
        end_time = time.time()
        
        print(f"✅ RAG system initialized successfully in {end_time - start_time:.2f} seconds")
        return rag_agent
        
    except Exception as e:
        print(f"❌ Error initializing RAG system: {e}")
        return None

def test_rag_queries(rag_agent):
    """Test the RAG system with sample queries"""
    if not rag_agent:
        return
    
    test_queries = [
        "How many teams are in the NBA?",
        "Who are the top 5 teams with most championships?",
        "What are the Lakers' recent performance?",
        "Which players have the most points in their career?",
        "Compare the Warriors and Celtics performance"
    ]
    
    print("\n🧪 Testing RAG system with sample queries...")
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Test Query {i} ---")
        print(f"Q: {query}")
        
        try:
            result = rag_agent.analyze(query)
            print(f"A: {result['analysis'][:200]}...")
            print(f"   Sources: {len(result['sources'])} documents")
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    """Main setup function"""
    print("🏀 NBA RAG System Setup")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Test MongoDB connection
    if not test_mongodb_connection():
        sys.exit(1)
    
    # Check data availability
    if not check_data_availability():
        print("\n💡 To populate data, run: python scraper.py")
        sys.exit(1)
    
    # Initialize RAG system
    rag_agent = initialize_rag_system()
    if not rag_agent:
        sys.exit(1)
    
    # Test with sample queries
    test_rag_queries(rag_agent)
    
    print("\n🎉 RAG system setup complete!")
    print("\nNext steps:")
    print("1. Start the Flask server: python app.py")
    print("2. Start the React frontend: cd nba-frontend && npm start")
    print("3. Open http://localhost:3000 and try the RAG Analysis tab")

if __name__ == "__main__":
    main()

