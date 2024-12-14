"""
Processor for generating product ideas using LLM models.
"""

import json
import logging
import os
from typing import Dict, List, Union, Any

from ..utils.openrouter import OpenRouterClient
from ..utils.file_handler import FileHandler
from ..utils.process_prompts import get_raw_json_response, get_text_response

logger = logging.getLogger(__name__)

class IdeaGenerator:
    """Generates product ideas using LLM models."""
    
    def __init__(self, file_handler: FileHandler, openrouter_client: OpenRouterClient):
        """
        Initialize the idea generator.
        
        Args:
            file_handler: File handling utility
            openrouter_client: OpenRouter API client
        """
        self.file_handler = file_handler
        self.openrouter_client = openrouter_client
        self.batch_size = 20
        
    def _validate_and_normalize_response(self, data: Any) -> List[Dict[str, str]]:
        """
        Validate and normalize the LLM response format.
        
        Args:
            data: Raw response data to validate
            
        Returns:
            List of validated idea dictionaries
            
        Raises:
            ValueError: If validation fails
        """
        logger.debug(f"Validating response data:\n{json.dumps(data, indent=2)}")
        
        # Extract ideas array from response
        ideas_array = data
        if isinstance(data, dict):
            # If it's a dict, look for the first value that's a list
            for value in data.values():
                if isinstance(value, list):
                    ideas_array = value
                    break
            
        # Validate it's a list
        if not isinstance(ideas_array, list):
            logger.error(f"Expected list of ideas, got {type(ideas_array)}")
            raise ValueError("Expected list of ideas")
            
        validated = []
        for i, idea in enumerate(ideas_array):
            if not isinstance(idea, dict):
                logger.error(f"Idea {i} is not a dictionary")
                raise ValueError(f"Idea {i} is not a dictionary")
                
            if "Idea" not in idea or "Details" not in idea:
                logger.error(f"Idea {i} missing required fields")
                raise ValueError(f"Idea {i} missing required fields")
                
            if not isinstance(idea["Idea"], str) or not isinstance(idea["Details"], str):
                logger.error(f"Idea {i} has invalid field types")
                raise ValueError(f"Idea {i} has invalid field types")
                
            validated.append(idea)
            logger.debug(f"Idea {i} passed validation:")
            logger.debug(f"  Idea: {idea['Idea']}")
            logger.debug(f"  Details: {idea['Details'][:100]}...")  # Log first 100 chars of details
                
        return validated
        
    def _read_prompt(self, prompt_path: str) -> str:
        """
        Read a prompt file.
        
        Args:
            prompt_path: Path to the prompt file
            
        Returns:
            Content of the prompt file
            
        Raises:
            FileNotFoundError: If the prompt file doesn't exist
        """
        if not os.path.exists(prompt_path):
            logger.error(f"Prompt file not found: {prompt_path}")
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
            
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt = f.read()
            
        logger.debug(f"Read prompt from {prompt_path}:\n{prompt}")
        return prompt
        
    def _generate_batch(self, messages: List[Dict[str, str]], max_retries: int = 3) -> List[Dict[str, str]]:
        """
        Generate and validate a batch of ideas.
        
        Args:
            messages: List of message dictionaries for the LLM
            max_retries: Maximum number of retries for format correction
            
        Returns:
            List of validated ideas
            
        Raises:
            ValueError: If validation fails after max retries
        """
        # Get raw response from LLM
        raw_data = get_raw_json_response(
            self.openrouter_client,
            messages,
            max_retries=max_retries
        )
        
        # Validate and normalize the response
        return self._validate_and_normalize_response(raw_data)
        
    def generate(self, initial_prompt_file: str, expand_prompt_file: str, list_prompt_file: str, 
                more_items_prompt_file: str, output_file: str, num_ideas: int = 15) -> str:
        """
        Generate product ideas using the specified prompt files.
        
        Args:
            initial_prompt_file: Path to initial ideas prompt file
            expand_prompt_file: Path to expand ideas prompt file
            list_prompt_file: Path to list format prompt file
            more_items_prompt_file: Path to more items prompt file
            output_file: Name of the output file to save ideas
            num_ideas: Number of ideas to generate
            
        Returns:
            Path to the generated ideas file
            
        Raises:
            FileNotFoundError: If any prompt file doesn't exist
            ValueError: If idea generation or validation fails
        """
        try:
            # Read all required prompts
            initial_prompt = self._read_prompt(initial_prompt_file)
            expand_prompt = self._read_prompt(expand_prompt_file)
            list_prompt = self._read_prompt(list_prompt_file)
            more_items_prompt = self._read_prompt(more_items_prompt_file)
            
            logger.info("Starting idea generation...")
            all_ideas = []
            remaining_ideas = num_ideas
            
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
            
            initial_response = get_text_response(self.openrouter_client, messages)
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
                    "content": expand_prompt
                }
            ]
            
            specific_response = get_text_response(self.openrouter_client, messages)
            logger.debug(f"Specific response:\n{specific_response}")
            
            # Step 3: Get formatted ideas with initial batch size
            current_format_prompt = list_prompt.replace("{NUM_IDEAS}", str(self.batch_size))
            
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
            
            # Get first batch of ideas
            batch_ideas = self._generate_batch(messages)
            all_ideas.extend(batch_ideas)
            remaining_ideas -= len(batch_ideas)
            
            # Step 4: If we need more ideas, keep requesting them in batches
            while remaining_ideas > 0:
                logger.debug(f"Requesting {self.batch_size} more ideas...")
                
                messages = [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that responds in valid JSON format."
                    },
                    {
                        "role": "assistant",
                        "content": json.dumps(batch_ideas)
                    },
                    {
                        "role": "user",
                        "content": more_items_prompt.replace("{NUM}", str(self.batch_size))
                    }
                ]
                
                # Get next batch of ideas
                batch_ideas = self._generate_batch(messages)
                all_ideas.extend(batch_ideas)
                remaining_ideas -= len(batch_ideas)
            
            logger.info(f"Successfully generated {len(all_ideas)} ideas")
            
            # Save the ideas to the output directory
            output_path = self.file_handler.save_json(all_ideas, output_file)
            logger.info(f"Saved ideas to {output_path}")
            
            # Log a sample of the generated ideas
            logger.debug("Sample of generated ideas:")
            for i, idea in enumerate(all_ideas[:3]):  # Show first 3 ideas
                logger.debug(f"Idea {i + 1}:")
                logger.debug(f"  Idea: {idea['Idea']}")
                logger.debug(f"  Details: {idea['Details'][:100]}...")
                
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to generate ideas: {str(e)}", exc_info=True)
            raise
