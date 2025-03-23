from datetime import datetime, timezone

from app.prompts import get_template, generate_prompt, FINANCIAL_FEW_SHOT_EXAMPLE
from langchain_core.tools import tool


@tool(return_direct=True)
def get_stock_price(stock_symbol: str):
    """Call to get the current stock price and related information for a given stock symbol."""
    # This is a mock implementation
    mock_stock_data = {
        "AAPL": {
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
            "current_price": 173.50,
            "change": 2.35,
            "change_percent": 1.37,
            "volume": 52436789,
            "market_cap": "2.73T",
            "pe_ratio": 28.5,
            "fifty_two_week_high": 198.23,
            "fifty_two_week_low": 124.17,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        # Add more mock data for other symbols as needed
    }

    return mock_stock_data["AAPL"]


@tool(return_direct=True)
def generate_content(prompt_type: str, topic: str, additional_instructions: str = ""):
    """
    Generates content on a given topic using a specified prompt template.

    Args:
        prompt_type (str): The type of prompt to use (e.g., 'base', 'cot', 'financial').
        topic (str): The topic to generate content about.
        additional_instructions (str, optional): Additional instructions for content generation. Defaults to "".

    Returns:
        str: The generated content.
    """
    template = get_template(prompt_type, additional_instructions)
    if prompt_type == "financial":
        example = FINANCIAL_FEW_SHOT_EXAMPLE
    else:
        example = None
    final_prompt = generate_prompt(template, example, f"The topic is: {topic}")
    # In a real application, you would pass the final_prompt to a language model here
    # For this example, we'll just return the prompt itself
    return f"Generated content using {prompt_type} template for topic: {topic}.\nPrompt: {final_prompt}"


@tool(return_direct=True)
def conversation_history_summary():
    """Summarize the conversation history to demonstrate persistent memory capability."""
    return "I can access our complete conversation history because I'm using the MemorySaver checkpointer. This allows me to maintain context across multiple exchanges in this conversation thread."


tools = [get_stock_price, generate_content, conversation_history_summary]
