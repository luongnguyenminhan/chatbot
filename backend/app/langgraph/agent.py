from datetime import datetime, timezone

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import NodeInterrupt
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from .rag_node import retrieve_knowledge, generate_query, format_docs, should_use_rag
from .state import AgentState
from .tools import tools
from ..models import AnyArgsSchema

load_dotenv()

# Default model when no specific model is specified in config
model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)


def load_chat_model(fully_specified_name: str = None) -> BaseChatModel:
    """Load a chat model based on provider/model specification."""
    if not fully_specified_name:
        return model  # Return default model

    if "/" in fully_specified_name:
        provider, model_name = fully_specified_name.split("/", maxsplit=1)
        try:
            return init_chat_model(model_name, model_provider=provider)
        except:
            print(f"Failed to load model {fully_specified_name}, using default")
            return model
    return model


def should_continue(state):
    """Determine if the agent should continue with tool execution or end."""
    messages = state["messages"]
    last_message = messages[-1]
    if not last_message.tool_calls:
        return END
    else:
        return "tools"


class FrontendTool(BaseTool):
    """Tool implementation for frontend-rendered tools."""

    def __init__(self, name: str):
        super().__init__(name=name, description="", args_schema=AnyArgsSchema)

    def _run(self, *args, **kwargs):
        raise NodeInterrupt("This is a frontend tool call")

    async def _arun(self, *args, **kwargs) -> str:
        raise NodeInterrupt("This is a frontend tool call")


def get_tool_defs(config):
    """Get tool definitions for binding to the model."""
    frontend_tools = [
        {"type": "function", "function": tool}
        for tool in config["configurable"]["frontend_tools"]
    ]
    return tools + frontend_tools


def get_tools(config):
    """Get tool instances for the tool node."""
    frontend_tools = [
        FrontendTool(tool.name) for tool in config["configurable"]["frontend_tools"]
    ]
    return tools + frontend_tools


async def call_model(state, config):
    """Call the language model with the current state and RAG context."""
    thread_id = config.get("configurable", {}).get("thread_id", "unknown")
    print(f"\n[AGENT] Calling model for thread: {thread_id}")

    # Get the system prompt from config
    system = config["configurable"]["system"]

    # Get response model name if specified, otherwise use default
    response_model_name = config.get("configurable", {}).get("response_model")

    # Add RAG context to system prompt if available
    if "retrieved_docs" in state and state["retrieved_docs"]:
        print(f"[AGENT] Using RAG context with {len(state['retrieved_docs'])} documents")
        rag_context = format_docs(state["retrieved_docs"])
        enhanced_system = f"{system}\n\nRelevant information from knowledge base:\n{rag_context}"
    elif "rag_context" in state and state["rag_context"]:
        print(f"[AGENT] Using RAG context with {len(state['rag_context'])} documents")
        rag_context = "\n\n".join(state["rag_context"])
        enhanced_system = f"{system}\n\nRelevant information from knowledge base:\n{rag_context}"
    else:
        print("[AGENT] No RAG context available")
        enhanced_system = system

    # Prepare messages with enhanced system prompt
    messages = [SystemMessage(content=enhanced_system)] + state["messages"]
    print(f"[AGENT] Total messages in context: {len(messages)}")

    # Load the appropriate model
    current_model = load_chat_model(response_model_name)

    # Invoke model with tools
    print(f"[AGENT] Invoking model: {response_model_name or 'default'}")
    model_with_tools = current_model.bind_tools(get_tool_defs(config))
    response = await model_with_tools.ainvoke(
        messages,
        {
            "system_time": datetime.now(tz=timezone.utc).isoformat(),
        }
    )

    # Return the response to be added to the messages
    return {"messages": response}


async def run_tools(input, config, **kwargs):
    """Execute tools based on the model's response."""
    thread_id = config.get("configurable", {}).get("thread_id", "unknown")
    print(f"\n[TOOLS] Running tools for thread: {thread_id}")

    tool_node = ToolNode(get_tools(config))
    response = await tool_node.ainvoke(input, config, **kwargs)

    print(f"[TOOLS] Tool response: {response}")
    return response


# Define the RAG-enabled agent workflow with optional RAG
workflow = StateGraph(AgentState)

# Add nodes for the RAG pipeline and agent
workflow.add_node("rag_decision", should_use_rag)
workflow.add_node("generate_query", generate_query)
workflow.add_node("retrieve", retrieve_knowledge)
workflow.add_node("agent", call_model)
workflow.add_node("tools", run_tools)

# Set up the graph flow with conditional RAG
workflow.set_entry_point("rag_decision")

# Add conditional edges from the RAG decision point
workflow.add_conditional_edges(
    "rag_decision",
    lambda state: "use_rag" if state.get("need_rag", False) else "skip_rag",
    {
        "use_rag": "generate_query",
        "skip_rag": "agent"
    }
)

# Continue with RAG flow if needed
workflow.add_edge("generate_query", "retrieve")
workflow.add_edge("retrieve", "agent")

# Handle tools and end conditions
workflow.add_conditional_edges(
    "agent",
    should_continue,
    ["tools", END],
)
workflow.add_edge("tools", "agent")

# Initialize memory checkpointer to persist conversation state
memory = MemorySaver()
assistant_ui_graph = workflow.compile(checkpointer=memory)


# Helper function to interact with the memory-enabled agent
async def chat_with_memory(messages, conversation_id, system="You are a helpful AI assistant.", frontend_tools=None,
                           use_rag=True):
    """
    Chat with the agent while maintaining conversation history across sessions
    
    Args:
        messages: The messages to send to the agent
        conversation_id: Unique identifier for this conversation
        system: System prompt
        frontend_tools: Any frontend tools to include
        use_rag: Whether to use RAG for this conversation
    """
    if frontend_tools is None:
        frontend_tools = []

    # Extract user_id from conversation_id for document filtering
    user_id = conversation_id.split("-")[0] if "-" in conversation_id else "default_user"

    config = {
        "configurable": {
            "system": system,
            "frontend_tools": frontend_tools,
            "thread_id": conversation_id,
            "user_id": user_id,
            "response_model": "gemini-2.0-flash",  # Default model
            "query_model": "gemini-2.0-flash",  # Default model for query refinement
            "use_rag": use_rag  # Flag to control RAG usage
        }
    }

    # Flag to indicate whether RAG should be used for this query
    initial_state = {"messages": messages, "need_rag": use_rag}

    return await assistant_ui_graph.ainvoke(initial_state, config)
