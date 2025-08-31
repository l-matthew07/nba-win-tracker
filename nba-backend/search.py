from pymongo import MongoClient
import json

from http.server import BaseHTTPRequestHandler, HTTPServer
from pymongo import MongoClient
from datetime import datetime
import urllib.parse
import json
import logging

hostName = "localhost"
serverPort = 8080

mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["your_database_name"]       # <--- change
collection = db["your_collection_name"]       # <--- change

def search_mongodb(query):
    cursor = collection.find(
        {"$text": {"$search": query}},
        {"score": {"$meta": "textScore"}, "title": 1, "content": 1}
    ).sort([("score", {"$meta": "textScore"})]).limit(10)
    
    results = []
    for doc in cursor:
        snippet = doc.get("content", [""])[0] if "content" in doc and len(doc["content"]) > 0 else ""
        results.append({
            "id": str(doc["_id"]),
            "title": doc.get("title", ""),
            "snippet": snippet
        })
    return results

def get_document(doc_id):
    from bson.objectid import ObjectId
    try:
        doc = collection.find_one({"_id": ObjectId(doc_id)})
        if not doc:
            return None
        # Return full document as JSON
        doc["_id"] = str(doc["_id"])  # convert ObjectId to string
        return doc
    except Exception as e:
        logging.error(f"Error fetching document {doc_id}: {e}")
        return None

class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        logging.info(f"GET request: Path: {self.path}")
        
        if self.path.startswith("/search?q="):
            raw_query = self.path[len("/search?q="):]
            query = urllib.parse.unquote_plus(raw_query)
            
            startTime = datetime.now()
            results = search_mongodb(query)
            duration = (datetime.now() - startTime).total_seconds()
            
            response_json = {
                "query": query,
                "duration_seconds": duration,
                "results": results
            }
            
            response_str = json.dumps(response_json)
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(response_str.encode("utf-8"))
            return
        
        if self.path.startswith("/document?id="):
            raw_id = self.path[len("/document?id="):]
            doc_id = urllib.parse.unquote_plus(raw_id)
            
            doc = get_document(doc_id)
            if doc is None:
                self.send_response(404)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Document not found"}).encode("utf-8"))
                return
            
            response_str = json.dumps(doc)
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(response_str.encode("utf-8"))
            return
        
        # Unknown path
        self.send_response(404)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))
        return

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.info(f"Starting server at http://{hostName}:{serverPort}")
    webServer = HTTPServer((hostName, serverPort), MyServer)
    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass
    webServer.server_close()
    logging.info("Server stopped.")
