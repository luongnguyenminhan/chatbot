import re
from typing import Dict, List, Any

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_core.pydantic_v1 import BaseModel

from .state import AgentState
from ..knowledge.vectordb import make_retriever


class SearchQuery(BaseModel):
    """Search the indexed documents for a query."""
    query: str


def get_message_text(msg):
    """Extract text content from various message formats."""
    content = msg.content
    if isinstance(content, str):
        return content
    elif isinstance(content, dict):
        return content.get("text", "")
    else:
        texts = [c if isinstance(c, str) else (c.get("text") or "") for c in content]
        return "".join(texts).strip()


def format_docs(docs: List[Document]) -> str:
    """Format documents as XML for inclusion in prompts."""
    if not docs:
        return "<documents></documents>"

    formatted_docs = []
    for doc in docs:
        metadata = doc.metadata or {}
        meta_str = "".join(f" {k}={v!r}" for k, v in metadata.items())
        if meta_str:
            meta_str = f" {meta_str}"
        formatted_docs.append(f"<document{meta_str}>\n{doc.page_content}\n</document>")

    return f"<documents>\n{''.join(formatted_docs)}\n</documents>"


async def should_use_rag(state: AgentState, config: Dict[str, Any]) -> Dict:
    """
    Determine if RAG should be used for this query based on configuration and query content.
    
    This node decides whether to route the query through the RAG pipeline or directly to the agent.
    """
    thread_id = config.get('configurable', {}).get('thread_id', 'unknown')
    print(f"\n[RAG DECISION] Evaluating if RAG is needed for thread: {thread_id}")

    # Check if RAG is explicitly disabled in config
    use_rag = config.get('configurable', {}).get('use_rag', True)
    if not use_rag:
        print("[RAG DECISION] RAG explicitly disabled in configuration")
        return {"need_rag": False}

    # Get the latest message
    messages = state.get("messages", [])
    if not messages or not isinstance(messages[-1], HumanMessage):
        print("[RAG DECISION] No user message found, skipping RAG")
        return {"need_rag": False}

    # Extract the user query
    user_query = get_message_text(messages[-1])
    print(f"[RAG DECISION] Evaluating query: {user_query[:100]}...")

    # Simple heuristic: Look for knowledge-based question patterns
    knowledge_indicators = [
        r"what is",
        r"how (do|does|can|to)",
        r"explain",
        r"tell me about",
        r"describe",
        r"who (is|was|are|were)",
        r"when (is|was|did)",
        r"where (is|was|did)",
        r"why (is|was|did)",
        r"definition of",
        r"information (on|about)"
    ]

    # Check if the query matches knowledge-seeking patterns
    for pattern in knowledge_indicators:
        if re.search(pattern, user_query.lower()):
            print(f"[RAG DECISION] Query matches knowledge pattern: {pattern}")
            return {"need_rag": True}

    # If no patterns match, default based on configuration
    default_use_rag = config.get('configurable', {}).get('default_use_rag', False)
    print(f"[RAG DECISION] No knowledge patterns matched, using default: {default_use_rag}")
    return {"need_rag": default_use_rag}


async def generate_query(state: AgentState, config: Dict[str, Any]) -> Dict:
    """Generate an optimized search query based on user input."""
    thread_id = config.get('configurable', {}).get('thread_id', 'unknown')
    print(f"\n[QUERY NODE] Generating search query for thread: {thread_id}")

    messages = state.get("messages", [])

    # Only process if there's at least one message and it's from the user
    if not messages or not isinstance(messages[-1], HumanMessage):
        print("[QUERY NODE] No user message found, skipping query generation")
        return {}

    # Extract the user query
    human_input = get_message_text(messages[-1])
    print(f"[QUERY NODE] User query: {human_input[:100]}...")

    # For now, we'll use the raw query directly
    # In future could be enhanced with LLM-based query refinement
    queries = state.get("queries", [])
    queries.append(human_input)

    return {"queries": queries}


async def retrieve_knowledge(state: AgentState, config: Dict[str, Any]) -> Dict:
    """Retrieve relevant documents based on the query."""
    thread_id = config.get('configurable', {}).get('thread_id', 'unknown')
    print(f"\n[RAG NODE] Starting knowledge retrieval for thread: {thread_id}")

    # Check if we have queries
    queries = state.get("queries", [])
    if not queries:
        print("[RAG NODE] No queries available, skipping retrieval")
        return {}

    # Use the most recent query
    user_query = queries[-1]
    print(f"[RAG NODE] Using query: {user_query[:100]}...")

    try:
        # Use the context manager to get a retriever
        with make_retriever(config) as retriever:
            # Retrieve documents
            doc_objects = await retriever(user_query)
            print(f"[RAG NODE] Retrieved {len(doc_objects)} documents")

            if doc_objects:
                # Extract content for system prompt
                rag_context = [doc.page_content for doc in doc_objects]

                # Return both raw content and document objects
                return {
                    "rag_context": rag_context,
                    "retrieved_docs": doc_objects
                }
            else:
                print("[RAG NODE] No relevant documents found")
                return {}
    except Exception as e:
        print(f"[RAG NODE] Error in knowledge retrieval: {str(e)}")
        return {}
