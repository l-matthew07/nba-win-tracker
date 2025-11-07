# NBA Statistics RAG (Retrieval-Augmented Generation) System

This project implements a RAG system for analyzing NBA statistics using your scraped data from Basketball Reference. The system combines vector similarity search with LLM generation to provide intelligent analysis of basketball statistics.

## 🏗️ Architecture

### Components

1. **Data Processing Pipeline** (`rag_system.py`)
   - Converts MongoDB data into text chunks
   - Processes teams, players, games, and coaches data
   - Creates structured documents for vector search

2. **Vector Store** (`NBAVectorStore`)
   - Uses FAISS for efficient similarity search
   - Employs sentence-transformers for embeddings
   - Stores document embeddings and metadata

3. **RAG Agent** (`NBARAGAgent`)
   - Combines retrieval with generation
   - Uses OpenAI GPT-4 for analysis
   - Provides context-aware responses

4. **API Integration** (`app.py`)
   - Flask endpoint for RAG analysis
   - Integrates with existing team wins analysis

5. **Frontend Interface** (`App.js`)
   - Tabbed interface for different analysis types
   - RAG analysis with source attribution
   - Real-time query processing

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd nba-backend
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create a `.env` file in the `nba-backend` directory:

```env
OPENAI_API_KEY=your_openai_api_key_here
MONGODB_URI=mongodb://localhost:27017/
BALLDONTLIE_API_KEY=your_balldontlie_api_key_here
```

### 3. Ensure Data is Available

Make sure your MongoDB contains NBA data:

```bash
python scraper.py
```

### 4. Set Up RAG System

```bash
python setup_rag.py
```

This will:
- Check environment variables
- Test MongoDB connection
- Verify data availability
- Initialize the RAG system
- Run test queries

### 5. Start the Application

Backend:
```bash
python app.py
```

Frontend:
```bash
cd nba-frontend
npm start
```

Visit `http://localhost:3000` and use the "RAG Analysis" tab.

## 📊 Data Sources

The RAG system processes four types of data:

### Teams Data
- Team names, cities, founding years
- Win/loss records and percentages
- Championship history
- Playoff appearances

### Players Data
- Player biographical information
- Career statistics from all tables
- Performance metrics across seasons
- Awards and achievements

### Games Data
- Game schedules and results
- Team performance by season
- Score differentials and trends
- Historical game data (1947-present)

### Coaches Data
- Coach biographical information
- Coaching statistics and records
- Team performance under coaches
- Career achievements

## 🔍 How It Works

### 1. Data Preprocessing
- Raw MongoDB documents are converted to structured text
- Each document type is processed differently
- Metadata is preserved for context

### 2. Embedding Generation
- Text chunks are converted to vector embeddings
- Uses `all-MiniLM-L6-v2` sentence transformer
- 384-dimensional embeddings for efficient search

### 3. Vector Search
- FAISS index enables fast similarity search
- Cosine similarity for relevance scoring
- Returns top-k most relevant documents

### 4. Context Assembly
- Retrieved documents are formatted as context
- Metadata provides additional information
- Context is passed to the LLM

### 5. Response Generation
- GPT-4 generates analysis based on context
- Responses are data-driven and specific
- Source attribution is provided

## 🎯 Example Queries

The RAG system can handle various types of queries:

### Team Analysis
- "Who are the top 5 teams with most championships?"
- "Compare the Lakers and Celtics performance in the 2020s"
- "Which teams had the best win percentage in 2020?"

### Player Analysis
- "What are LeBron James' career statistics?"
- "Who are the top scorers in NBA history?"
- "Compare Michael Jordan and Kobe Bryant's achievements"

### Historical Analysis
- "How did the NBA change from the 1990s to 2000s?"
- "Which decade had the most competitive teams?"
- "What were the most dominant teams in each era?"

### Statistical Analysis
- "What are the highest scoring games in NBA history?"
- "Which teams have the best home court advantage?"
- "Compare different eras of basketball statistically"

## ⚙️ Configuration

### Vector Store Settings
- **Embedding Model**: `all-MiniLM-L6-v2` (384 dimensions)
- **Similarity Metric**: Cosine similarity
- **Index Type**: FAISS IndexFlatIP

### Retrieval Settings
- **Default k**: 5 documents per query
- **Context Window**: Configurable based on query complexity
- **Relevance Threshold**: Dynamic based on top results

### LLM Settings
- **Model**: GPT-4o
- **Temperature**: 0.3 (for consistent responses)
- **Max Tokens**: 1000
- **Context**: NBA expert persona

## 🔧 Customization

### Adding New Data Sources
1. Extend `NBADataProcessor` class
2. Add new processing method
3. Update `initialize()` method
4. Test with sample queries

### Modifying Embeddings
1. Change embedding model in `NBAVectorStore`
2. Update dimension parameter
3. Rebuild vector index
4. Test performance

### Customizing Prompts
1. Modify `generate_response()` method
2. Update prompt template
3. Adjust temperature and parameters
4. Test with various queries

## 📈 Performance Optimization

### Vector Store
- Use GPU-accelerated FAISS for large datasets
- Implement batch processing for embeddings
- Consider hierarchical indexing for scale

### Retrieval
- Implement query expansion
- Add re-ranking mechanisms
- Use hybrid search (keyword + semantic)

### Generation
- Implement response caching
- Use streaming for long responses
- Add response validation

## 🐛 Troubleshooting

### Common Issues

1. **"RAG system not initialized"**
   - Run `python setup_rag.py`
   - Check MongoDB connection
   - Verify data availability

2. **"No relevant documents found"**
   - Check if data exists in MongoDB
   - Verify embedding generation
   - Try different query phrasing

3. **"OpenAI API error"**
   - Check API key validity
   - Verify rate limits
   - Check network connectivity

4. **"MongoDB connection failed"**
   - Verify MongoDB is running
   - Check connection string
   - Ensure database exists

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🚀 Future Enhancements

### Planned Features
- Real-time data updates
- Multi-modal analysis (images, videos)
- Advanced statistical modeling
- Interactive visualizations
- Query suggestion system

### Performance Improvements
- Caching layer for frequent queries
- Batch processing for large datasets
- Distributed vector search
- Model fine-tuning on NBA data

## 📚 API Reference

### RAG Analysis Endpoint

**POST** `/api/rag-analyze`

**Request Body:**
```json
{
  "query": "Your NBA question here"
}
```

**Response:**
```json
{
  "query": "Your question",
  "analysis": "Generated analysis",
  "sources": [
    {
      "type": "team|player|game|coach",
      "id": "document_id",
      "relevance_score": 0.95,
      "metadata": {...}
    }
  ],
  "timestamp": "2024-01-01T00:00:00"
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Basketball Reference for comprehensive NBA data
- OpenAI for powerful language models
- FAISS for efficient vector search
- Sentence Transformers for embeddings
- The NBA community for inspiration

