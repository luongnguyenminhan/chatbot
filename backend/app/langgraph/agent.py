from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.errors import NodeInterrupt
from langchain_core.tools import BaseTool
from ..models import AnyArgsSchema, FrontendToolCall
from .tools import tools
from .state import AgentState
from .rag_node import retrieve_knowledge
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
import os
load_dotenv()


model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)


def should_continue(state):
    messages = state["messages"]
    last_message = messages[-1]
    if not last_message.tool_calls:
        return END
    else:
        return "tools"


def should_use_rag(state):
    # Check if user query might benefit from RAG
    # In a production system, you'd want a more sophisticated check
    return "rag"


class FrontendTool(BaseTool):
    def __init__(self, name: str):
        super().__init__(name=name, description="", args_schema=AnyArgsSchema)

    def _run(self, *args, **kwargs):
        # Since this is a frontend-only tool, it might not actually execute anything.
        # Raise an interrupt or handle accordingly.
        raise NodeInterrupt("This is a frontend tool call")

    async def _arun(self, *args, **kwargs) -> str:
        # Similarly handle async calls
        raise NodeInterrupt("This is a frontend tool call")


def get_tool_defs(config):
    frontend_tools = [
        {"type": "function", "function": tool}
        for tool in config["configurable"]["frontend_tools"]
    ]
    return tools + frontend_tools


def get_tools(config):
    frontend_tools = [
        FrontendTool(tool.name) for tool in config["configurable"]["frontend_tools"]
    ]
    return tools + frontend_tools


async def call_model(state, config):
    thread_id = config.get("configurable", {}).get("thread_id", "unknown")
    print(f"\n[AGENT] Calling model for thread: {thread_id}")
    
    system = config["configurable"]["system"]
    
    # Add RAG context to system prompt if available
    if "rag_context" in state and state["rag_context"]:
        print(f"[AGENT] Using RAG context with {len(state['rag_context'])} documents")
        rag_context = "\n\n".join(state["rag_context"])
        enhanced_system = f"{system}\n\nRelevant information from knowledge base:\n{rag_context}"
    else:
        print("[AGENT] No RAG context available")
        enhanced_system = system

    messages = [SystemMessage(content=enhanced_system)] + state["messages"]
    print(f"[AGENT] Total messages in context: {len(messages)}")
    
    print("[AGENT] Invoking model with tools...")
    model_with_tools = model.bind_tools(get_tool_defs(config))
    response = await model_with_tools.ainvoke(messages)
    print(f"[AGENT] Model response received: {type(response)}")
    
    # We return a list, because this will get added to the existing list
    return {"messages": response}


async def run_tools(input, config, **kwargs):
    thread_id = config.get("configurable", {}).get("thread_id", "unknown")
    print(f"\n[TOOLS] Running tools for thread: {thread_id}")
    
    tool_node = ToolNode(get_tools(config))
    response = await tool_node.ainvoke(input, config, **kwargs)
    
    print(f"[TOOLS] Tool response: {response}")
    return response


# Define a new graph with RAG capabilities
workflow = StateGraph(AgentState)

workflow.add_node("rag", retrieve_knowledge)
workflow.add_node("agent", call_model)
workflow.add_node("tools", run_tools)

# Set the entry point to RAG for knowledge retrieval
workflow.set_entry_point("rag")
workflow.add_edge("rag", "agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    ["tools", END],
)

workflow.add_edge("tools", "agent")

# Initialize memory checkpointer to persist conversation state
memory = MemorySaver()
assistant_ui_graph = workflow.compile(checkpointer=memory)

# Add helper function to interact with the memory-enabled agent
async def chat_with_memory(messages, conversation_id, system="You are a helpful AI assistant.", frontend_tools=None):
    """
    Chat with the agent while maintaining conversation history across sessions
    
    Args:
        messages: The messages to send to the agent
        conversation_id: Unique identifier for this conversation
        system: System prompt
        frontend_tools: Any frontend tools to include
    """
    if frontend_tools is None:
        frontend_tools = []
    
    config = {
        "configurable": {
            "system": system,
            "frontend_tools": frontend_tools,
            "thread_id": conversation_id
        }
    }
    
    return await assistant_ui_graph.ainvoke({"messages": messages}, config)
