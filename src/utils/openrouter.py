"""
OpenRouter API client for interacting with LLM models.
"""

import json
import logging
import os
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
        
        logger.debug(f"Request data:\n{json.dumps(data, indent=2)}")
        
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
