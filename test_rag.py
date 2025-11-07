#!/usr/bin/env python3
"""
Quick RAG System Test Script

This script tests if your RAG system is working properly.
Run this to verify everything is set up correctly.
"""

import os
import sys
from dotenv import load_dotenv

def test_imports():
    """Test if all required packages can be imported"""
    print("🔍 Testing imports...")
    
    try:
        import openai
        print("✅ OpenAI imported successfully")
    except ImportError as e:
        print(f"❌ OpenAI import failed: {e}")
        return False
    
    try:
        import pymongo
        print("✅ PyMongo imported successfully")
    except ImportError as e:
        print(f"❌ PyMongo import failed: {e}")
        return False
    
    try:
        import sentence_transformers
        print("✅ Sentence Transformers imported successfully")
    except ImportError as e:
        print(f"❌ Sentence Transformers import failed: {e}")
        return False
    
    try:
        import faiss
        print("✅ FAISS imported successfully")
    except ImportError as e:
        print(f"❌ FAISS import failed: {e}")
        return False
    
    try:
        import numpy
        print("✅ NumPy imported successfully")
    except ImportError as e:
        print(f"❌ NumPy import failed: {e}")
        return False
    
    return True

def test_environment():
    """Test environment variables"""
    print("\n🔧 Testing environment variables...")
    
    load_dotenv()
    
    openai_key = os.getenv("OPENAI_API_KEY")
    mongodb_uri = os.getenv("MONGODB_URI")
    
    if not openai_key or openai_key == "your_openai_api_key_here":
        print("❌ OPENAI_API_KEY not set or using placeholder")
        return False
    else:
        print("✅ OPENAI_API_KEY is set")
    
    if not mongodb_uri:
        print("❌ MONGODB_URI not set")
        return False
    else:
        print(f"✅ MONGODB_URI is set: {mongodb_uri}")
    
    return True

def test_mongodb():
    """Test MongoDB connection and data"""
    print("\n🗄️  Testing MongoDB connection...")
    
    try:
        from pymongo import MongoClient
        load_dotenv()
        
        mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        client = MongoClient(mongo_uri)
        
        # Test connection
        client.admin.command('ping')
        print("✅ MongoDB connection successful")
        
        # Check data
        db = client["nba_stats"]
        collections = ['teams', 'players', 'games', 'coaches']
        
        total_docs = 0
        for collection_name in collections:
            count = db[collection_name].count_documents({})
            total_docs += count
            status = "✅" if count > 0 else "❌"
            print(f"   {status} {collection_name}: {count} documents")
        
        if total_docs == 0:
            print("❌ No data found in MongoDB")
            return False
        else:
            print(f"✅ Total documents: {total_docs}")
            return True
            
    except Exception as e:
        print(f"❌ MongoDB test failed: {e}")
        return False

def test_rag_system():
    """Test the RAG system"""
    print("\n🚀 Testing RAG system...")
    
    try:
        # Import the RAG system
        sys.path.append('nba-backend')
        from rag_system import NBARAGAgent
        
        # Initialize
        load_dotenv()
        mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        print("   Initializing RAG agent...")
        rag_agent = NBARAGAgent(mongo_uri, openai_key)
        
        print("   Building vector store (this may take a moment)...")
        rag_agent.initialize()
        
        print("✅ RAG system initialized successfully")
        
        # Test a simple query
        print("   Testing with sample query...")
        test_query = "How many teams are in the NBA?"
        result = rag_agent.analyze(test_query)
        
        if result and 'analysis' in result:
            print(f"✅ Query test successful!")
            print(f"   Query: {test_query}")
            print(f"   Response: {result['analysis'][:100]}...")
            print(f"   Sources used: {len(result['sources'])}")
            return True
        else:
            print("❌ Query test failed - no analysis returned")
            return False
            
    except Exception as e:
        print(f"❌ RAG system test failed: {e}")
        return False

def test_api_endpoint():
    """Test the Flask API endpoint"""
    print("\n🌐 Testing API endpoint...")
    
    try:
        import requests
        import time
        
        # Start the Flask app in background (simplified test)
        print("   Note: Make sure Flask app is running on port 8000")
        print("   You can start it with: cd nba-backend && python app.py")
        
        # Test the endpoint
        try:
            response = requests.post(
                'http://localhost:8000/api/rag-analyze',
                json={'query': 'How many teams are in the NBA?'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print("✅ API endpoint working!")
                print(f"   Response: {data.get('analysis', 'No analysis')[:100]}...")
                return True
            else:
                print(f"❌ API returned status code: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            print("⚠️  API not running - start Flask app first")
            return False
            
    except ImportError:
        print("❌ Requests library not available")
        return False
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🏀 NBA RAG System Test Suite")
    print("=" * 40)
    
    tests = [
        ("Import Test", test_imports),
        ("Environment Test", test_environment),
        ("MongoDB Test", test_mongodb),
        ("RAG System Test", test_rag_system),
        ("API Endpoint Test", test_api_endpoint)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your RAG system is working!")
    elif passed >= 3:
        print("⚠️  Most tests passed, but there are some issues to fix")
    else:
        print("❌ Multiple tests failed. Check the errors above.")
    
    print("\n💡 Next steps:")
    if passed >= 3:
        print("1. Start the Flask app: cd nba-backend && python app.py")
        print("2. Start the frontend: cd nba-frontend && npm start")
        print("3. Open http://localhost:3000 and try the RAG Analysis tab")
    else:
        print("1. Fix the failing tests above")
        print("2. Make sure all dependencies are installed")
        print("3. Check your .env file configuration")

if __name__ == "__main__":
    main()

