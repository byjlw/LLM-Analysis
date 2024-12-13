"""
Process and validate prompts and responses from LLM models.
"""

import json
import logging
import os
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def clean_json_string(content: str) -> str:
    """
    Clean and extract JSON content from a string.
    
    Args:
        content: String that may contain JSON
        
    Returns:
        Cleaned JSON string
        
    Raises:
        ValueError: If no valid JSON structure is found
    """
    # Remove any markdown code block markers
    content = re.sub(r'```(?:json)?\s*', '', content)
    content = re.sub(r'\s*```', '', content)
    
    # Remove any leading/trailing whitespace and newlines
    content = content.strip()
    
    # Try to find any JSON-like structure (array or object)
    json_pattern = r'(?:\{[\s\S]*\}|\[[\s\S]*\])'
    match = re.search(json_pattern, content)
    if not match:
        logger.error(f"No valid JSON structure found in content:\n{content}")
        raise ValueError("No valid JSON structure found in response")
        
    content = match.group(0)
    logger.debug(f"Cleaned JSON content: {content}")
    return content

def validate_json_structure(data: Any) -> list:
    """
    Validate and ensure correct structure of the JSON data.
    
    Args:
        data: Parsed JSON data
        
    Returns:
        List of validated items
        
    Raises:
        ValueError: If the data structure is invalid
    """
    if not isinstance(data, (list, dict)):
        logger.error(f"Invalid data type received from API:\n{json.dumps(data, indent=2)}")
        raise ValueError(f"Expected list or dict, got {type(data)}")
        
    # Convert to list if it's a dict
    items = [data] if isinstance(data, dict) else data
    
    required_fields = {
        "Product Idea": str,
        "Problem it solves": str,
        "Software Techstack": list,
        "Target hardware expectations": list,
        "Company profile": str,
        "Engineering profile": str
    }
    
    validated_items = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            logger.error(f"Invalid item structure:\n{json.dumps(item, indent=2)}")
            raise ValueError(f"Item {i} is not a dictionary")
            
        # Log the item being validated
        logger.debug(f"Validating item {i}:\n{json.dumps(item, indent=2)}")
            
        # Validate all required fields
        for field, expected_type in required_fields.items():
            if field not in item:
                logger.error(f"Item {i} structure:\n{json.dumps(item, indent=2)}")
                raise ValueError(f"Item {i} missing required field: {field}")
            if not isinstance(item[field], expected_type):
                logger.error(f"Item {i} field '{field}' value:\n{json.dumps(item[field], indent=2)}")
                raise ValueError(f"Item {i} field '{field}' has wrong type: expected {expected_type}, got {type(item[field])}")
            if expected_type == list and not all(isinstance(x, str) for x in item[field]):
                logger.error(f"Item {i} field '{field}' values:\n{json.dumps(item[field], indent=2)}")
                raise ValueError(f"Item {i} field '{field}' contains non-string values")
                
        validated_items.append(item)
        
    if not validated_items:
        raise ValueError("No valid items found in response")
        
    return validated_items

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
        Cleaned and parsed JSON data
        
    Raises:
        ValueError: If JSON parsing fails after max retries
        RuntimeError: If API request fails
    """
    for attempt in range(max_retries):
        try:
            response = client._make_request(messages, model, max_tokens)
            content = response["choices"][0]["message"]["content"]
            logger.debug(f"Raw content from API:\n{content}")
            
            # Clean and extract JSON content
            json_content = clean_json_string(content)
            logger.debug(f"Cleaned JSON content:\n{json_content}")
            
            # Parse and return the JSON content
            return json.loads(json_content)
            
        except (json.JSONDecodeError, ValueError) as e:
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

def generate_ideas(client, prompt: str, num_ideas: int = 15, model: str = None, max_format_retries: int = 3, max_tokens: int = 10000, more_items_prompt: str = None) -> List:
    """
    Generate and validate product ideas.
    
    Args:
        client: OpenRouterClient instance
        prompt: The prompt for generating ideas
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
    
    # Generate initial batch of ideas
    initial_count = min(25, remaining_ideas)
    current_prompt = prompt.replace("{NUM_IDEAS}", str(initial_count))
    logger.debug(f"Using prompt for initial {initial_count} ideas:\n{current_prompt}")
    
    messages = [
        {
            "role": "system",
            "content": "You are a Product Manager that provides responses in valid JSON format."
        },
        {
            "role": "user",
            "content": current_prompt
        }
    ]
    
    # Get initial batch of ideas
    initial_ideas = handle_json_response(client, messages, model, max_tokens, max_format_retries)
    validated_ideas = validate_json_structure(initial_ideas)
    all_ideas.extend(validated_ideas)
    remaining_ideas -= len(validated_ideas)
    
    # If we need more ideas, keep requesting them in batches
    while remaining_ideas > 0:
        batch_size = min(25, remaining_ideas)
        logger.debug(f"Requesting {batch_size} more ideas...")
        
        # Add the previous response to conversation history
        messages.append({
            "role": "assistant",
            "content": json.dumps(validated_ideas)
        })
        
        # Add request for more items
        more_prompt = more_items_prompt.replace("{NUM}", str(batch_size))
        messages.append({
            "role": "user",
            "content": more_prompt
        })
        
        # Get next batch of ideas
        batch_ideas = handle_json_response(client, messages, model, max_tokens, max_format_retries)
        validated_batch = validate_json_structure(batch_ideas)
        all_ideas.extend(validated_batch)
        remaining_ideas -= len(validated_batch)
    
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
        ValueError: If response structure is invalid
    """
    logger.info("Starting requirements generation...")
    messages = [
        {
            "role": "system",
            "content": "You are a helpful Product Manager that provides responses in valid JSON format."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
    response = client._make_request(messages, model, max_tokens)
    try:
        return response["choices"][0]["message"]["content"]
    except KeyError as e:
        error_msg = f"Invalid response structure: missing key {str(e)}\nFull response:\n{json.dumps(response, indent=2)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

def generate_code(client, prompt: str, model: str = None, max_tokens: int = 10000) -> str:
    """
    Generate code based on requirements.
    
    Args:
        client: OpenRouterClient instance
        prompt: The prompt containing the requirements
        model: Optional model override
        max_tokens: Maximum number of tokens to generate
        
    Returns:
        Generated code string
        
    Raises:
        RuntimeError: If API request fails
        ValueError: If response structure is invalid
    """
    logger.info("Starting code generation...")
    messages = [
        {
            "role": "system",
            "content": "You are a helpful software developer that provide only code."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
    response = client._make_request(messages, model, max_tokens)
    try:
        return response["choices"][0]["message"]["content"]
    except KeyError as e:
        error_msg = f"Invalid response structure: missing key {str(e)}\nFull response:\n{json.dumps(response, indent=2)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

def validate_dependencies(data: Any) -> Dict[str, List[str]]:
    """
    Validate and process dependency data.
    
    Args:
        data: Parsed JSON data
        
    Returns:
        Dictionary containing frameworks list
        
    Raises:
        ValueError: If data structure is invalid
    """
    if not isinstance(data, list):
        logger.error("Expected list response")
        logger.error(f"Got: {json.dumps(data, indent=2)}")
        raise ValueError("Expected list response")
        
    if not all(isinstance(x, str) for x in data):
        logger.error("All frameworks must be strings")
        logger.error(f"Got: {json.dumps(data, indent=2)}")
        raise ValueError("All frameworks must be strings")
        
    return {"frameworks": data}

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
        
        # Validate the structure and return
        return validate_dependencies(data)
    except Exception as e:
        logger.error(f"Failed to collect dependencies: {str(e)}")
        return {"frameworks": []}
