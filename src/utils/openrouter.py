"""
OpenRouter API client for interacting with LLM models.
"""

import json
import logging
import re
import time
from typing import Dict, Optional, Any
import requests
from requests.exceptions import RequestException, Timeout

logger = logging.getLogger(__name__)

class OpenRouterClient:
    """Client for interacting with the OpenRouter API."""
    
    def __init__(self, api_key: str, default_model: str = "meta-llama/llama-3.3-70b-instruct",
                 timeout: int = 30, max_retries: int = 3):
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
        
    def _make_request(self, prompt: str, model: Optional[str] = None) -> Dict:
        """
        Make a request to the OpenRouter API with retry logic.
        
        Args:
            prompt: The prompt to send to the model
            model: Optional model override
            
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
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that provides responses in valid JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
            "response_format": {"type": "json_object"}
        }
        
        logger.info(f"Making request to OpenRouter API with model: {model or self.default_model}")
        logger.debug(f"Request data: {json.dumps(data, indent=2)}")
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Attempt {attempt + 1}/{self.max_retries}")
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=self.timeout
                )
                
                if response.status_code == 401:
                    raise ValueError("Invalid OpenRouter API key")
                    
                response.raise_for_status()
                response_data = response.json()
                logger.info(f"Full API Response:\n{json.dumps(response_data, indent=2)}")
                return response_data
                
            except Timeout:
                error_msg = f"Request timed out after {self.timeout} seconds"
                logger.error(error_msg)
                if attempt == self.max_retries - 1:
                    raise RuntimeError(error_msg)
                time.sleep(2 ** attempt)
                
            except requests.exceptions.HTTPError as e:
                error_msg = f"HTTP error occurred: {e.response.text}"
                logger.error(error_msg)
                if attempt == self.max_retries - 1:
                    raise RuntimeError(error_msg)
                time.sleep(2 ** attempt)
                
            except RequestException as e:
                error_msg = f"Request error occurred: {str(e)}"
                logger.error(error_msg)
                if attempt == self.max_retries - 1:
                    raise RuntimeError(error_msg)
                time.sleep(2 ** attempt)
                
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
            logger.info(f"Validating item {i}:\n{json.dumps(item, indent=2)}")
                
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
            
    def generate_ideas(self, prompt: str, model: Optional[str] = None) -> list:
        """
        Generate product ideas using the specified prompt.
        
        Args:
            prompt: The prompt for generating ideas
            model: Optional model override
            
        Returns:
            List of generated ideas
            
        Raises:
            ValueError: If the response format is invalid
            RuntimeError: If the API request fails
        """
        logger.info("Starting idea generation...")
        response = self._make_request(prompt, model)
        
        try:
            # Extract the content from the response
            content = response["choices"][0]["message"]["content"]
            logger.info(f"Raw content from API:\n{content}")
            
            # Clean and extract JSON content
            json_content = self._clean_json_string(content)
            logger.info(f"Cleaned JSON content:\n{json_content}")
            
            # Parse the JSON content
            data = json.loads(json_content)
            logger.info(f"Parsed JSON data:\n{json.dumps(data, indent=2)}")
            
            # Validate and ensure correct structure
            validated_data = self._validate_json_structure(data)
            logger.info(f"Successfully processed {len(validated_data)} ideas")
            
            return validated_data
                
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON response: {str(e)}\nRaw content:\n{content}"
            logger.error(error_msg)
            raise ValueError(error_msg)
                
        except KeyError as e:
            error_msg = f"Invalid response structure: missing key {str(e)}\nFull response:\n{json.dumps(response, indent=2)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
    def generate_requirements(self, prompt: str, model: Optional[str] = None) -> str:
        """
        Generate requirements based on a product idea.
        
        Args:
            prompt: The prompt containing the product idea
            model: Optional model override
            
        Returns:
            String containing the generated requirements
            
        Raises:
            RuntimeError: If the API request fails
            ValueError: If the response is invalid
        """
        logger.info("Starting requirements generation...")
        response = self._make_request(prompt, model)
        try:
            return response["choices"][0]["message"]["content"]
        except KeyError as e:
            error_msg = f"Invalid response structure: missing key {str(e)}\nFull response:\n{json.dumps(response, indent=2)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
    def generate_code(self, prompt: str, model: Optional[str] = None) -> str:
        """
        Generate code based on requirements.
        
        Args:
            prompt: The prompt containing the requirements
            model: Optional model override
            
        Returns:
            String containing the generated code
            
        Raises:
            RuntimeError: If the API request fails
            ValueError: If the response is invalid
        """
        logger.info("Starting code generation...")
        response = self._make_request(prompt, model)
        try:
            return response["choices"][0]["message"]["content"]
        except KeyError as e:
            error_msg = f"Invalid response structure: missing key {str(e)}\nFull response:\n{json.dumps(response, indent=2)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
