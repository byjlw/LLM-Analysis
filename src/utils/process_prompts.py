"""
Process and validate prompts and responses from LLM models.
"""

import json
import logging
import os
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def handle_json_response(client, messages: List[Dict[str, str]], model: str, max_tokens: int, max_retries: int) -> Any:
    """
    Handle JSON response from LLM with retry logic for format errors.
    
    Args:
        client: OpenRouterClient instance
        messages: List of message dictionaries
        model: Optional model override
        max_tokens: Maximum tokens to generate
        max_retries: Maximum retries for format correction
        
    Returns:
        Parsed JSON data
        
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
            
            # Try to parse JSON
            try:
                data = json.loads(content)
                logger.debug(f"Parsed JSON:\n{json.dumps(data, indent=2)}")
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse error: {str(e)}\nContent:\n{content}")
                raise ValueError(f"JSON parse error: {str(e)}")
            
            # Handle wrapped ideas
            if isinstance(data, dict) and "ideas" in data:
                logger.debug("Found ideas wrapper, extracting ideas array")
                data = data["ideas"]
            
            # Validate it's a list
            if not isinstance(data, list):
                logger.warning(f"Expected list, got {type(data)}\nContent:\n{json.dumps(data, indent=2)}")
                raise ValueError("Expected list")
            
            # Validate each item has required fields
            for item in data:
                if not isinstance(item, dict):
                    logger.warning(f"Expected dict, got {type(item)}\nItem:\n{json.dumps(item, indent=2)}")
                    raise ValueError("Expected dict")
                if "Idea" not in item or "Details" not in item:
                    logger.warning(f"Missing required fields\nItem:\n{json.dumps(item, indent=2)}")
                    raise ValueError("Missing required fields")
                if not isinstance(item["Idea"], str) or not isinstance(item["Details"], str):
                    logger.warning(f"Invalid field types\nItem:\n{json.dumps(item, indent=2)}")
                    raise ValueError("Invalid field types")
            
            return data
            
        except Exception as e:
            error_msg = f"Attempt {attempt + 1}/{max_retries}: Format validation failed: {str(e)}"
            logger.warning(error_msg)
            
            if attempt == max_retries - 1:
                raise ValueError(f"Failed to get valid JSON format after {max_retries} attempts")
            
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

def generate_ideas(client, initial_prompt: str, second_prompt: str, format_prompt: str, num_ideas: int = 15, model: str = None, max_format_retries: int = 3, max_tokens: int = 10000, more_items_prompt: str = None) -> List:
    """
    Generate and validate product ideas.
    
    Args:
        client: OpenRouterClient instance
        initial_prompt: The initial prompt for generating ideas
        second_prompt: The prompt for getting more specific ideas
        format_prompt: The prompt for setting format and batch size
        num_ideas: Number of ideas to generate (default: 15)
        model: Optional model override
        max_format_retries: Maximum retries for format correction
        max_tokens: Maximum number of tokens to generate
        more_items_prompt: The prompt template for requesting more items
        
    Returns:
        List of validated ideas
        
    Raises:
        ValueError: If validation fails after max retries
        RuntimeError: If API request fails
    """
    logger.info("Starting idea generation...")
    
    # Initialize list to store all ideas
    all_ideas = []
    remaining_ideas = num_ideas
    
    if more_items_prompt is None:
        raise ValueError("more_items_prompt must be provided")
    
    # Step 1: Get initial broad ideas (text response)
    messages = [
        {
            "role": "system",
            "content": "You are a helpful Assistant."
        },
        {
            "role": "user",
            "content": initial_prompt
        }
    ]
    
    # Get initial text response
    initial_response = get_text_response(client, messages, model, max_tokens)
    logger.debug(f"Initial response:\n{initial_response}")
    
    # Step 2: Get more specific ideas (text response)
    messages = [
        {
            "role": "system",
            "content": "You are a helpful Assistant."
        },
        {
            "role": "assistant",
            "content": initial_response
        },
        {
            "role": "user",
            "content": second_prompt
        }
    ]
    
    # Get more specific text response
    specific_response = get_text_response(client, messages, model, max_tokens)
    logger.debug(f"Specific response:\n{specific_response}")
    
    # Step 3: Get formatted ideas with initial batch size
    batch_size = min(25, remaining_ideas)
    current_format_prompt = format_prompt.replace("{NUM_IDEAS}", str(batch_size))
    
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that provides responses in valid JSON format."
        },
        {
            "role": "assistant",
            "content": specific_response
        },
        {
            "role": "user",
            "content": current_format_prompt
        }
    ]
    
    # Get formatted ideas (now we start JSON validation)
    formatted_ideas = handle_json_response(client, messages, model, max_tokens, max_format_retries)
    all_ideas.extend(formatted_ideas)
    remaining_ideas -= len(formatted_ideas)
    
    # Step 4: If we need more ideas, keep requesting them in batches
    while remaining_ideas > 0:
        batch_size = min(25, remaining_ideas)
        logger.debug(f"Requesting {batch_size} more ideas...")
        
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that responds in valid JSON format."
            },
            {
                "role": "assistant",
                "content": json.dumps(formatted_ideas)
            },
            {
                "role": "user",
                "content": more_items_prompt.replace("{NUM}", str(batch_size))
            }
        ]
        
        # Get next batch of ideas
        batch_ideas = handle_json_response(client, messages, model, max_tokens, max_format_retries)
        all_ideas.extend(batch_ideas)
        remaining_ideas -= len(batch_ideas)
        formatted_ideas = batch_ideas
    
    logger.info(f"Successfully generated {len(all_ideas)} ideas")
    return all_ideas

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
        # Get parsed JSON data
        data = handle_json_response(client, messages, model, max_tokens, max_retries=3)
        return {"frameworks": data}
    except Exception as e:
        logger.error(f"Failed to collect dependencies: {str(e)}")
        return {"frameworks": []}
