"""
Process and validate prompts and responses from LLM models.
"""

import json
import logging
import os
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def clean_response(content: str) -> str:
    """
    Clean response by removing markdown code block markers if present.
    
    Args:
        content: Raw content that may contain markdown code blocks
        
    Returns:
        Content with markdown code blocks removed if present,
        otherwise returns original content
    """
    content = content.strip()
    
    # Handle case with both markers
    if content.startswith("```json") and content.endswith("```"):
        content = content[7:-3]  # Remove ```json prefix and ``` suffix
    # Handle case with only opening marker
    elif content.startswith("```json"):
        content = content[7:]  # Remove ```json prefix
    # Handle case with only closing marker
    elif content.endswith("```"):
        content = content[:-3]  # Remove ``` suffix
        
    return content.strip()

def get_raw_json_response(client, messages: List[Dict[str, str]], max_retries: int = 3, model: str = None, max_tokens: int = 2000) -> Any:
    """
    Get raw JSON response from LLM with retry logic.
    
    Args:
        client: OpenRouterClient instance
        messages: List of message dictionaries
        max_retries: Maximum retries for format correction
        model: Optional model override
        max_tokens: Maximum tokens to generate
        
    Returns:
        Raw parsed JSON data
        
    Raises:
        ValueError: If JSON parsing fails after max retries
        RuntimeError: If API request fails
    """
    for attempt in range(max_retries):
        try:
            # Get response from LLM
            response = client._make_request(messages, model, max_tokens)
            content = response["choices"][0]["message"]["content"]
            logger.debug(f"Raw content from API:\n{content}")
            
            # Clean response by removing markdown code blocks if present
            content = clean_response(content)
            logger.debug(f"Cleaned content:\n{content}")
            
            # Try to parse JSON
            try:
                data = json.loads(content)
                logger.debug(f"Parsed JSON:\n{json.dumps(data, indent=2)}")
                return data
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON: {str(e)}")
                # If it's not JSON, return the raw string
                if attempt == max_retries - 1:
                    return content.strip()
            
        except Exception as e:
            error_msg = f"Attempt {attempt + 1}/{max_retries}: Response processing failed: {str(e)}"
            logger.warning(error_msg)
            
            if attempt == max_retries - 1:
                raise ValueError(f"Failed to get valid response after {max_retries} attempts")
            
            # Add assistant's response to conversation history
            messages.append({
                "role": "assistant",
                "content": content
            })
            
            # Read the error correction prompt from file
            error_prompt_path = os.path.join("prompts", "e1-wrong_format.txt")
            try:
                with open(error_prompt_path, "r") as f:
                    error_message = f.read().strip()
                # Add error message to conversation history
                messages.append({
                    "role": "user",
                    "content": error_message
                })
                logger.debug("Added format correction prompt to conversation")
            except IOError as e:
                logger.error(f"Failed to read error prompt file: {str(e)}")
                raise RuntimeError(f"Failed to read error prompt file: {str(e)}")

def get_text_response(client, messages: List[Dict[str, str]], model: str = None, max_tokens: int = 10000) -> str:
    """
    Get a text response from the LLM.
    
    Args:
        client: OpenRouterClient instance
        messages: List of message dictionaries
        model: Optional model override
        max_tokens: Maximum tokens to generate
        
    Returns:
        Text response from LLM
        
    Raises:
        RuntimeError: If API request fails
    """
    response = client._make_request(messages, model, max_tokens)
    try:
        return response["choices"][0]["message"]["content"]
    except KeyError as e:
        error_msg = f"Invalid response structure: missing key {str(e)}\nFull response:\n{json.dumps(response, indent=2)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

def generate_requirements(client, prompt: str, model: str = None, max_tokens: int = 2000) -> str:
    """
    Generate requirements based on a product idea.
    
    Args:
        client: OpenRouterClient instance
        prompt: The prompt containing the product idea
        model: Optional model override
        max_tokens: Maximum number of tokens to generate
        
    Returns:
        String containing the generated requirements
        
    Raises:
        RuntimeError: If API request fails
    """
    logger.info("Starting requirements generation...")
    messages = [
        {
            "role": "system",
            "content": "You are a helpful Assistant."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
    return get_text_response(client, messages, model, max_tokens)

def generate_code(client, initial_prompt: str, writer_prompt: str, requirements: str, model: str = None, max_tokens: int = 10000) -> str:
    """
    Generate code based on requirements with a two-step process.
    
    Args:
        client: OpenRouterClient instance
        initial_prompt: The initial prompt for code generation
        writer_prompt: The prompt for detailed code writing
        requirements: The requirements to implement
        model: Optional model override
        max_tokens: Maximum number of tokens to generate
        
    Returns:
        Generated code string
        
    Raises:
        RuntimeError: If API request fails
    """
    logger.info("Starting code generation...")
    
    # Step 1: Initial code planning
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant"
        },
        {
            "role": "user",
            "content": f"{initial_prompt}\n\n{requirements}"
        }
    ]
    
    # Get initial response
    initial_response = get_text_response(client, messages, model, max_tokens)
    logger.debug(f"Initial code response:\n{initial_response}")
    
    # Step 2: Detailed code writing
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "assistant",
            "content": initial_response
        },
        {
            "role": "user",
            "content": writer_prompt
        }
    ]
    
    # Get final code
    return get_text_response(client, messages, model, max_tokens)

def generate_dependencies(client, prompt: str, code: str, model: str = None, max_tokens: int = 2000) -> Dict[str, List[str]]:
    """
    Analyze code to collect framework dependencies using LLM.
    
    Args:
        client: OpenRouterClient instance
        prompt: The prompt template for dependency collection
        code: The code content to analyze
        model: Optional model override
        max_tokens: Maximum number of tokens to generate
        
    Returns:
        Dictionary containing frameworks list
        
    Raises:
        RuntimeError: If API request fails
    """
    logger.info("Starting dependency collection...")
    
    # Combine prompt template with code
    full_prompt = prompt.replace("{DETAILS}", code)
    
    messages = [
        {
            "role": "system",
            "content": "You are a production engineer that analyzes code dependencies."
        },
        {
            "role": "user",
            "content": full_prompt
        }
    ]
    
    try:
        # Get raw response from LLM
        raw_data = get_raw_json_response(client, messages, max_retries=3, model=model, max_tokens=max_tokens)
        return {"frameworks": raw_data}
    except Exception as e:
        logger.error(f"Failed to collect dependencies: {str(e)}")
        return {"frameworks": []}
