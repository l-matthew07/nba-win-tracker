"""
NBA Statistics RAG (Retrieval-Augmented Generation) System

This module implements a RAG system for analyzing NBA statistics data.
It combines vector similarity search with LLM generation to provide
intelligent analysis of basketball statistics.
"""

import os
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
from dataclasses import dataclass
from openai import OpenAI
from pymongo import MongoClient
from dotenv import load_dotenv
import pickle
import hashlib
from sentence_transformers import SentenceTransformer
import faiss
import re

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Document:
    """Represents a document in the vector database"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None

class NBAVectorStore:
    """Vector store for NBA statistics data using FAISS"""
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        self.documents = {}
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
    def add_documents(self, documents: List[Document]):
        """Add documents to the vector store"""
        embeddings = []
        doc_ids = []
        
        for doc in documents:
            if doc.embedding is None:
                doc.embedding = self.embedding_model.encode(doc.content)
            
            embeddings.append(doc.embedding)
            doc_ids.append(doc.id)
            self.documents[doc.id] = doc
            
        if embeddings:
            embeddings_array = np.array(embeddings).astype('float32')
            self.index.add(embeddings_array)
            logger.info(f"Added {len(documents)} documents to vector store")
    
    def search(self, query: str, k: int = 5) -> List[Tuple[Document, float]]:
        """Search for similar documents"""
        query_embedding = self.embedding_model.encode([query])
        query_embedding = query_embedding.astype('float32')
        
        scores, indices = self.index.search(query_embedding, k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.documents):
                doc_id = list(self.documents.keys())[idx]
                doc = self.documents[doc_id]
                results.append((doc, float(score)))
        
        return results

class NBADataProcessor:
    """Processes NBA data from MongoDB into text chunks for RAG"""
    
    def __init__(self, mongo_uri: str):
        self.client = MongoClient(mongo_uri)
        self.db = self.client["nba_stats"]
        
    def process_teams_data(self) -> List[Document]:
        """Convert teams data to text documents"""
        documents = []
        teams = self.db.teams.find()
        
        for team in teams:
            content = f"""
            Team: {team.get('name', 'Unknown')}
            City: {team.get('city', 'Unknown')}
            Founded: {team.get('founded_year', 'Unknown')}
            League: {team.get('league', 'Unknown')}
            Total Games: {team.get('games', 'Unknown')}
            Total Wins: {team.get('wins', 'Unknown')}
            Total Losses: {team.get('losses', 'Unknown')}
            Win Percentage: {team.get('win_loss_pct', 'Unknown')}
            Playoff Appearances: {team.get('years_playoffs', 'Unknown')}
            Division Championships: {team.get('years_div_champs', 'Unknown')}
            Conference Championships: {team.get('years_conf_champs', 'Unknown')}
            League Championships: {team.get('years_league_champs', 'Unknown')}
            Years Active: {team.get('year_min', 'Unknown')} - {team.get('year_max', 'Unknown')}
            """
            
            doc_id = f"team_{team.get('abbreviation', 'unknown')}"
            metadata = {
                'type': 'team',
                'team_name': team.get('name'),
                'abbreviation': team.get('abbreviation'),
                'founded_year': team.get('founded_year')
            }
            
            documents.append(Document(
                id=doc_id,
                content=content.strip(),
                metadata=metadata
            ))
        
        return documents
    
    def process_players_data(self) -> List[Document]:
        """Convert players data to text documents"""
        documents = []
        players = self.db.players.find()
        
        for player in players:
            # Basic player info
            content = f"""
            Player: {player.get('first_name', '')} {player.get('last_name', '')}
            Birth Date: {player.get('birth_date', 'Unknown')}
            """
            
            # Add detailed stats if available
            if 'details' in player and player['details']:
                details = player['details']
                
                # Add bio information
                if 'bio' in details and details['bio']:
                    for key, value in details['bio'].items():
                        content += f"\n{key}: {value}"
                
                # Add statistics tables
                if 'stats' in details and details['stats']:
                    for table_id, table_data in details['stats'].items():
                        if table_data and 'headers' in table_data and 'rows' in table_data:
                            content += f"\n\n{table_id.replace('_', ' ').title()} Statistics:"
                            if table_data['headers']:
                                content += f"\nHeaders: {', '.join(table_data['headers'])}"
                            if table_data['rows'] and len(table_data['rows']) > 0:
                                # Add first few rows as examples
                                for i, row in enumerate(table_data['rows'][:3]):
                                    if any(cell for cell in row if cell):
                                        content += f"\nRow {i+1}: {', '.join(str(cell) if cell else 'N/A' for cell in row)}"
            
            doc_id = f"player_{player.get('_id')}"
            metadata = {
                'type': 'player',
                'first_name': player.get('first_name'),
                'last_name': player.get('last_name'),
                'birth_date': player.get('birth_date')
            }
            
            documents.append(Document(
                id=doc_id,
                content=content.strip(),
                metadata=metadata
            ))
        
        return documents
    
    def process_games_data(self) -> List[Document]:
        """Convert games data to text documents (grouped by season)"""
        documents = []
        
        # Group games by season
        pipeline = [
            {"$group": {
                "_id": "$season",
                "games": {"$push": "$$ROOT"},
                "total_games": {"$sum": 1}
            }},
            {"$sort": {"_id": -1}}
        ]
        
        seasons = list(self.db.games.aggregate(pipeline))
        
        for season_data in seasons:
            season = season_data['_id']
            games = season_data['games']
            
            # Calculate season statistics
            total_games = len(games)
            completed_games = [g for g in games if g.get('away_score') is not None and g.get('home_score') is not None]
            
            # Team performance summary
            team_stats = {}
            for game in completed_games:
                home_team = game.get('home_team')
                away_team = game.get('away_team')
                home_score = game.get('home_score', 0)
                away_score = game.get('away_score', 0)
                
                if home_team not in team_stats:
                    team_stats[home_team] = {'wins': 0, 'losses': 0, 'points_for': 0, 'points_against': 0}
                if away_team not in team_stats:
                    team_stats[away_team] = {'wins': 0, 'losses': 0, 'points_for': 0, 'points_against': 0}
                
                if home_score > away_score:
                    team_stats[home_team]['wins'] += 1
                    team_stats[away_team]['losses'] += 1
                else:
                    team_stats[away_team]['wins'] += 1
                    team_stats[home_team]['losses'] += 1
                
                team_stats[home_team]['points_for'] += home_score
                team_stats[home_team]['points_against'] += away_score
                team_stats[away_team]['points_for'] += away_score
                team_stats[away_team]['points_against'] += home_score
            
            # Create content
            content = f"""
            NBA Season {season} Statistics:
            Total Games: {total_games}
            Completed Games: {len(completed_games)}
            League: {games[0].get('league', 'NBA') if games else 'Unknown'}
            
            Team Performance Summary:
            """
            
            # Add top teams by wins
            sorted_teams = sorted(team_stats.items(), key=lambda x: x[1]['wins'], reverse=True)
            for team, stats in sorted_teams[:10]:  # Top 10 teams
                win_pct = stats['wins'] / (stats['wins'] + stats['losses']) if (stats['wins'] + stats['losses']) > 0 else 0
                content += f"""
            {team}: {stats['wins']}W-{stats['losses']}L ({win_pct:.3f}), 
            Points For: {stats['points_for']}, Points Against: {stats['points_against']}
            """
            
            doc_id = f"season_{season}"
            metadata = {
                'type': 'season',
                'season': season,
                'total_games': total_games,
                'completed_games': len(completed_games)
            }
            
            documents.append(Document(
                id=doc_id,
                content=content.strip(),
                metadata=metadata
            ))
        
        return documents
    
    def process_coaches_data(self) -> List[Document]:
        """Convert coaches data to text documents"""
        documents = []
        coaches = self.db.coaches.find()
        
        for coach in coaches:
            content = f"""
            Coach: {coach.get('full_name', 'Unknown')}
            """
            
            # Add bio information
            if 'bio' in coach and coach['bio']:
                for key, value in coach['bio'].items():
                    content += f"\n{key}: {value}"
            
            # Add coaching statistics
            if 'stats' in coach and coach['stats']:
                for table_id, table_data in coach['stats'].items():
                    if table_data and 'headers' in table_data and 'rows' in table_data:
                        content += f"\n\n{table_id.replace('_', ' ').title()} Statistics:"
                        if table_data['headers']:
                            content += f"\nHeaders: {', '.join(table_data['headers'])}"
                        if table_data['rows'] and len(table_data['rows']) > 0:
                            for i, row in enumerate(table_data['rows'][:5]):  # First 5 rows
                                if any(cell for cell in row if cell):
                                    content += f"\nRow {i+1}: {', '.join(str(cell) if cell else 'N/A' for cell in row)}"
            
            doc_id = f"coach_{coach.get('_id')}"
            metadata = {
                'type': 'coach',
                'full_name': coach.get('full_name')
            }
            
            documents.append(Document(
                id=doc_id,
                content=content.strip(),
                metadata=metadata
            ))
        
        return documents

class NBARAGAgent:
    """Main RAG agent for NBA statistics analysis"""
    
    def __init__(self, mongo_uri: str, openai_api_key: str):
        self.mongo_uri = mongo_uri
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.vector_store = NBAVectorStore()
        self.data_processor = NBADataProcessor(mongo_uri)
        self.is_initialized = False
        
    def initialize(self, force_rebuild: bool = False):
        """Initialize the RAG system by processing data and building vector store"""
        if self.is_initialized and not force_rebuild:
            logger.info("RAG system already initialized")
            return
        
        logger.info("Initializing NBA RAG system...")
        
        # Process all data types
        all_documents = []
        
        logger.info("Processing teams data...")
        all_documents.extend(self.data_processor.process_teams_data())
        
        logger.info("Processing players data...")
        all_documents.extend(self.data_processor.process_players_data())
        
        logger.info("Processing games data...")
        all_documents.extend(self.data_processor.process_games_data())
        
        logger.info("Processing coaches data...")
        all_documents.extend(self.data_processor.process_coaches_data())
        
        # Add to vector store
        logger.info(f"Adding {len(all_documents)} documents to vector store...")
        self.vector_store.add_documents(all_documents)
        
        self.is_initialized = True
        logger.info("RAG system initialization complete!")
    
    def search_relevant_documents(self, query: str, k: int = 5) -> List[Tuple[Document, float]]:
        """Search for relevant documents based on query"""
        if not self.is_initialized:
            raise ValueError("RAG system not initialized. Call initialize() first.")
        
        return self.vector_store.search(query, k)
    
    def generate_response(self, query: str, context_documents: List[Document]) -> str:
        """Generate response using OpenAI with retrieved context"""
        
        # Prepare context from retrieved documents
        context = "\n\n".join([
            f"Document {i+1} ({doc.metadata.get('type', 'unknown')}):\n{doc.content}"
            for i, doc in enumerate(context_documents)
        ])
        
        prompt = f"""
        You are an expert NBA analyst with access to comprehensive basketball statistics data. 
        Use the provided context to answer the user's question about NBA statistics, players, teams, games, or coaches.
        
        Context Data:
        {context}
        
        User Question: {query}
        
        Instructions:
        1. Provide accurate, data-driven analysis based on the context
        2. If specific data is not available in the context, mention this limitation
        3. Use statistics and numbers to support your analysis
        4. Be specific about time periods, teams, and players when relevant
        5. If comparing teams or players, provide concrete numbers
        6. Keep responses informative but concise
        
        Analysis:
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"I apologize, but I encountered an error while generating the analysis: {str(e)}"
    
    def analyze(self, query: str, k: int = 5) -> Dict[str, Any]:
        """Main method to analyze NBA statistics using RAG"""
        if not self.is_initialized:
            self.initialize()
        
        # Search for relevant documents
        relevant_docs = self.search_relevant_documents(query, k)
        
        # Generate response
        analysis = self.generate_response(query, [doc for doc, score in relevant_docs])
        
        # Prepare response
        return {
            "query": query,
            "analysis": analysis,
            "sources": [
                {
                    "type": doc.metadata.get('type', 'unknown'),
                    "id": doc.id,
                    "relevance_score": float(score),
                    "metadata": doc.metadata
                }
                for doc, score in relevant_docs
            ],
            "timestamp": datetime.now().isoformat()
        }

# Example usage and testing
if __name__ == "__main__":
    # Initialize the RAG agent
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    rag_agent = NBARAGAgent(mongo_uri, openai_api_key)
    
    # Initialize the system
    rag_agent.initialize()
    
    # Example queries
    test_queries = [
        "Who are the top 5 teams with the most championships?",
        "What are LeBron James' career statistics?",
        "How did the Lakers perform in the 2020 season?",
        "Which teams had the best win percentage in recent years?",
        "Compare the performance of the Warriors and Celtics in the 2020s"
    ]
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"Query: {query}")
        print(f"{'='*50}")
        
        result = rag_agent.analyze(query)
        print(f"Analysis: {result['analysis']}")
        print(f"\nSources used: {len(result['sources'])} documents")
