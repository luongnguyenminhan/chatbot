from typing import Dict, List, Any
from langchain_core.messages import HumanMessage, AIMessage
from ..knowledge.vectordb import query_knowledge_base
from .state import AgentState


async def retrieve_knowledge(state: AgentState, config: Dict[str, Any]) -> Dict:
    """
    LangGraph node for retrieving information from knowledge base.
    This node checks if the latest message from the user needs RAG enhancement.
    """
    print(f"\n[RAG NODE] Starting knowledge retrieval for thread: {config.get('configurable', {}).get('thread_id', 'unknown')}")
    
    messages = state.get("messages", [])
    
    # Only process if there's at least one message and it's from the user
    if not messages or not isinstance(messages[-1], HumanMessage):
        print("[RAG NODE] No user message found, skipping retrieval")
        return {}
    
    # Get the latest user query
    user_query = messages[-1].content
    if isinstance(user_query, list):  # Handle multimodal content
        text_parts = [part.get("text", "") for part in user_query if part.get("type") == "text"]
        user_query = " ".join(text_parts)
    
    print(f"[RAG NODE] User query: {user_query[:100]}...")
    
    try:
        # Query the knowledge base
        print("[RAG NODE] Querying knowledge base...")
        retrieved_docs = query_knowledge_base(user_query)
        print(f"[RAG NODE] Retrieved {len(retrieved_docs)} documents")
        
        if retrieved_docs:
            for i, doc in enumerate(retrieved_docs):
                print(f"[RAG NODE] Doc {i+1} snippet: {doc[:50]}...")
        
        # Add retrieved context to the state
        return {"rag_context": retrieved_docs}
    except Exception as e:
        print(f"[RAG NODE] Error in knowledge retrieval: {str(e)}")
        return {}
