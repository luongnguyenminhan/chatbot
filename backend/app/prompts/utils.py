"""
Utility functions for prompt engineering in the assistant UI LangGraph application.
"""

def generate_prompt(template, examples=None, additional_instructions=None):
    """
    Generate a prompt by combining a template, examples, and additional instructions.
    
    Args:
        template (str): The base prompt template.
        examples (str, optional): Example prompts to guide the model. Defaults to None.
        additional_instructions (str, optional): Additional instructions for the model. Defaults to None.
        
    Returns:
        str: The combined prompt.
    """
    prompt = template
    
    if examples:
        prompt += "\n\n" + examples
        
    if additional_instructions:
        prompt += "\n\n" + additional_instructions
        
    return prompt
