import os
from langchain_qdrant import Qdrant
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
    UnstructuredHTMLLoader
)
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, Filter, FieldCondition, MatchValue
import uuid
from datetime import datetime
import tempfile
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()

if "GOOGLE_API_KEY" not in os.environ:
    print("GOOGLE_API_KEY not found in environment variables. Please set it.")
# Initialize Gemini embeddings
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

# Initialize Qdrant client - use local file storage for development
QDRANT_PATH = os.environ.get("QDRANT_PATH", "./qdrant_data")
COLLECTION_NAME = "knowledge_base"
VECTOR_SIZE = 768  # Gemini embedding size

# Create Qdrant client
qdrant_client = QdrantClient(path=QDRANT_PATH)

# Try to create collection if it doesn't exist
try:
    qdrant_client.get_collection(COLLECTION_NAME)
except Exception:
    qdrant_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )

# Initialize vector store
vector_store = Qdrant(
    client=qdrant_client,
    collection_name=COLLECTION_NAME,
    embeddings=embeddings,
)

# Document metadata store - in-memory for simplicity
# In production, use a database
document_metadata = {}

# Helper functions for document processing
def get_document_loader(file_path, content_type):
    """Returns the appropriate document loader based on file type."""
    if content_type == "application/pdf":
        return PyPDFLoader(file_path)
    elif content_type == "text/plain":
        return TextLoader(file_path)
    elif content_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
        return Docx2txtLoader(file_path)
    elif content_type == "text/html":
        return UnstructuredHTMLLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {content_type}")

def process_and_store_document(file, filename, content_type):
    """Process document and store it in the vector database."""
    print(f"\n[VECTORDB] Processing document: {filename} ({content_type})")
    print(f"[VECTORDB] File size: {len(file)} bytes")
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(file)
        temp_file_path = temp_file.name
    
    try:
        # Load document
        print(f"[VECTORDB] Loading document with appropriate loader...")
        loader = get_document_loader(temp_file_path, content_type)
        documents = loader.load()
        print(f"[VECTORDB] Loaded {len(documents)} document segments")
        
        # Split text into chunks
        print(f"[VECTORDB] Splitting text into chunks...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
        )
        chunks = text_splitter.split_documents(documents)
        print(f"[VECTORDB] Created {len(chunks)} chunks for embedding")
        
        # Generate document ID
        document_id = str(uuid.uuid4())
        print(f"[VECTORDB] Generated document ID: {document_id}")
        
        # Add document ID to metadata for each chunk
        for chunk in chunks:
            if chunk.metadata is None:
                chunk.metadata = {}
            chunk.metadata["document_id"] = document_id
        
        # Store document chunks in vector database
        print(f"[VECTORDB] Storing {len(chunks)} chunks in vector database...")
        vector_store.add_documents(chunks)
        print(f"[VECTORDB] Successfully stored chunks in vector database")
        
        # Store document metadata
        document_metadata[document_id] = {
            "document_id": document_id,
            "name": filename,
            "size": len(file),
            "created_at": datetime.now().isoformat(),
            "content_type": content_type,
            "chunk_count": len(chunks)
        }
        
        print(f"[VECTORDB] Document processing complete: {filename}")
        return document_id
        
    finally:
        # Clean up temporary file
        os.unlink(temp_file_path)

def delete_document(document_id):
    """Delete document from vector database."""
    print(f"\n[VECTORDB] Attempting to delete document: {document_id}")
    
    if document_id in document_metadata:
        # Delete from Qdrant using filter by metadata
        print(f"[VECTORDB] Deleting chunks from vector database...")
        
        # Create a proper filter using Qdrant's models
        filter_condition = Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id)
                )
            ]
        )
        
        # Get point IDs with the specified document_id
        search_result = qdrant_client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=filter_condition,
            limit=10000,  # Adjust based on your expected maximum number of chunks per document
            with_payload=False,
            with_vectors=False
        )
        
        if search_result and search_result[0]:
            point_ids = [point.id for point in search_result[0]]
            if point_ids:
                # Delete points by their IDs
                qdrant_client.delete(
                    collection_name=COLLECTION_NAME,
                    points_selector=qdrant_client.points_selector(points=point_ids)
                )
                
                # Delete metadata
                doc_info = document_metadata[document_id]
                del document_metadata[document_id]
                print(f"[VECTORDB] Successfully deleted document: {doc_info.get('name', document_id)} with {len(point_ids)} chunks")
                return True
        
        print(f"[VECTORDB] No chunks found for document: {document_id}")
        # Clean up metadata even if no chunks were found
        if document_id in document_metadata:
            del document_metadata[document_id]
        return True
        
    print(f"[VECTORDB] Document not found: {document_id}")
    return False

def get_document_list():
    """Get list of documents in the knowledge base."""
    return [
        {
            "document_id": doc["document_id"],
            "name": doc["name"],
            "size": doc["size"],
            "created_at": doc["created_at"],
            "content_type": doc["content_type"]
        }
        for doc in document_metadata.values()
    ]

def query_knowledge_base(query: str, top_k: int = 3) -> List[str]:
    """Query the knowledge base for relevant document chunks."""
    print(f"\n[VECTORDB] Querying knowledge base with: {query[:50]}...")
    print(f"[VECTORDB] Retrieving top {top_k} results")
    
    results = vector_store.similarity_search(query, k=top_k)
    print(f"[VECTORDB] Found {len(results)} results")
    
    for i, doc in enumerate(results):
        metadata_str = ", ".join([f"{k}={v}" for k, v in doc.metadata.items()])
        print(f"[VECTORDB] Result {i+1} metadata: {metadata_str}")
        print(f"[VECTORDB] Result {i+1} snippet: {doc.page_content[:50]}...")
    
    return [doc.page_content for doc in results]
