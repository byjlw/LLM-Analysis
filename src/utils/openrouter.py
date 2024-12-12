"""
OpenRouter API client for interacting with LLM models.
"""

import json
import logging
import os
import re
from typing import Dict, Optional, Any, List
import requests
from requests.exceptions import RequestException, Timeout

logger = logging.getLogger(__name__)

class OpenRouterClient:
    """Client for interacting with the OpenRouter API."""
    
    def __init__(self, api_key: str, default_model: str = "meta-llama/llama-3.3-70b-instruct",
                 timeout: int = 60, max_retries: int = 3):
        """
        Initialize the OpenRouter client.
        
        Args:
            api_key: OpenRouter API key
            default_model: Default model to use for requests
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.api_key = api_key
        self.default_model = default_model
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_url = "https://openrouter.ai/api/v1"
        logger.info(f"Initialized OpenRouter client with model: {default_model}")
        
    def _make_request(self, messages: List[Dict[str, str]], model: Optional[str] = None, max_tokens: int = 2000) -> Dict:
        """
        Make a request to the OpenRouter API with retry logic.
        
        Args:
            messages: List of message dictionaries with role and content
            model: Optional model override
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            Dict containing the API response
            
        Raises:
            RequestException: If the request fails after all retries
            ValueError: If the API key is invalid or missing
            RuntimeError: If the API returns an unexpected response
        """
        if not self.api_key:
            raise ValueError("OpenRouter API key is missing")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/jessewhite/llm-coding-analysis",
            "X-Title": "LLM Coding Analysis"
        }
        
        data = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": max_tokens
        }
        
        logger.debug(f"Request data: {json.dumps(data, indent=2)}")
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Attempt {attempt + 1}/{self.max_retries}")
                
                # Use increasing timeout for retries
                current_timeout = self.timeout * (attempt + 1)
                logger.debug(f"Using timeout of {current_timeout} seconds")
                
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=current_timeout
                )
                
                if response.status_code == 401:
                    raise ValueError("Invalid OpenRouter API key")
                    
                response.raise_for_status()
                response_data = response.json()
                logger.debug(f"API Response:\n{json.dumps(response_data, indent=2)}")
                return response_data
                
            except Timeout as e:
                error_msg = f"Request timed out after {current_timeout} seconds"
                logger.warning(error_msg)
                last_error = e
                
            except requests.exceptions.HTTPError as e:
                error_msg = f"HTTP error occurred: {e.response.text}"
                logger.warning(error_msg)
                last_error = e
                
            except RequestException as e:
                error_msg = f"Request error occurred: {str(e)}"
                logger.warning(error_msg)
                last_error = e
        
        # If we've exhausted all retries, raise the last error
        if isinstance(last_error, Timeout):
            raise RuntimeError(f"Request timed out after {self.max_retries} attempts")
        elif isinstance(last_error, requests.exceptions.HTTPError):
            raise RuntimeError(f"HTTP error persisted after {self.max_retries} attempts: {str(last_error)}")
        else:
            raise RuntimeError(f"Request failed after {self.max_retries} attempts: {str(last_error)}")
                
    def _clean_json_string(self, content: str) -> str:
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

    def _validate_json_structure(self, data: Any) -> list:
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
            
    def generate_ideas(self, prompt: str, model: Optional[str] = None, max_format_retries: int = 3, max_tokens: int = 10000) -> list:
        """
        Generate product ideas using the specified prompt.
        
        Args:
            prompt: The prompt for generating ideas
            model: Optional model override
            max_format_retries: Maximum number of retries for format correction
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            List of generated ideas
            
        Raises:
            ValueError: If the response format is invalid after all retries
            RuntimeError: If the API request fails
        """
        logger.info("Starting idea generation...")
        
        # Initialize conversation with system message and user prompt
        messages = [
            {
                "role": "system",
                "content": "You are a Product Manager that provides responses in valid JSON format."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        for attempt in range(max_format_retries):
            try:
                response = self._make_request(messages, model, max_tokens)
                content = response["choices"][0]["message"]["content"]
                logger.debug(f"Raw content from API:\n{content}")
                
                # Clean and extract JSON content
                json_content = self._clean_json_string(content)
                logger.debug(f"Cleaned JSON content:\n{json_content}")
                
                # Parse the JSON content
                data = json.loads(json_content)
                logger.debug(f"Parsed JSON data:\n{json.dumps(data, indent=2)}")
                
                # Validate and ensure correct structure
                validated_data = self._validate_json_structure(data)
                return validated_data
                
            except (json.JSONDecodeError, ValueError) as e:
                error_msg = f"Attempt {attempt + 1}/{max_format_retries}: Format validation failed: {str(e)}"
                logger.warning(error_msg)
                
                if attempt == max_format_retries - 1:
                    raise ValueError(f"Failed to get valid JSON format after {max_format_retries} attempts")
                
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
                
        raise ValueError(f"Failed to get valid JSON format after {max_format_retries} attempts")
            
    def generate_requirements(self, prompt: str, model: Optional[str] = None, max_tokens: int = 2000) -> str:
        """
        Generate requirements based on a product idea.
        
        Args:
            prompt: The prompt containing the product idea
            model: Optional model override
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            String containing the generated requirements
            
        Raises:
            RuntimeError: If the API request fails
            ValueError: If the response is invalid
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
        response = self._make_request(messages, model, max_tokens)
        try:
            return response["choices"][0]["message"]["content"]
        except KeyError as e:
            error_msg = f"Invalid response structure: missing key {str(e)}\nFull response:\n{json.dumps(response, indent=2)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
    def generate_code(self, prompt: str, model: Optional[str] = None, max_tokens: int = 10000) -> str:
        """
        Generate code based on requirements.
        
        Args:
            prompt: The prompt containing the requirements
            model: Optional model override
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            String containing the generated code
            
        Raises:
            RuntimeError: If the API request fails
            ValueError: If the response is invalid
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
        response = self._make_request(messages, model, max_tokens)
        try:
            return response["choices"][0]["message"]["content"]
        except KeyError as e:
            error_msg = f"Invalid response structure: missing key {str(e)}\nFull response:\n{json.dumps(response, indent=2)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def collect_dependencies(self, code: str, prompt: str, model: Optional[str] = None, max_tokens: int = 2000) -> Dict[str, List[str]]:
        """
        Analyze code to collect framework dependencies using LLM.
        
        Args:
            code: The code content to analyze
            prompt: The prompt template for dependency collection
            model: Optional model override
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            Dictionary containing frameworks list
            
        Raises:
            RuntimeError: If the API request fails
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
            response = self._make_request(messages, model, max_tokens)
            content = response["choices"][0]["message"]["content"]
            logger.debug(f"LLM Response:\n{content}")
            
            # Clean and extract JSON content
            json_content = self._clean_json_string(content)
            # Parse the JSON content
            frameworks = json.loads(json_content)
            
            # Ensure expected structure
            if not isinstance(frameworks, list):
                logger.error("Expected list response")
                logger.error(f"Got: {json_content}")
                return {"frameworks": []}
            if not all(isinstance(x, str) for x in frameworks):
                logger.error("All frameworks must be strings")
                logger.error(f"Got: {json_content}")
                return {"frameworks": []}
                
            # Return frameworks in expected format
            return {"frameworks": frameworks}
            
        except Exception as e:
            logger.error(f"Failed to collect dependencies: {str(e)}")
            logger.error(f"LLM Response:\n{content if 'content' in locals() else 'No response received'}")
            return {"frameworks": []}
