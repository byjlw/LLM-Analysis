"""
Processor for generating product ideas using LLM models.
"""

import json
import logging
import os
from typing import Dict, List, Union

from ..utils.openrouter import OpenRouterClient
from ..utils.file_handler import FileHandler
from ..utils.process_prompts import generate_ideas

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
        
    def _validate_ideas(self, ideas: List[Dict]) -> bool:
        """
        Validate the structure of generated ideas.
        
        Args:
            ideas: List of generated ideas
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(ideas, list):
            logger.error(f"Expected ideas to be a list, got {type(ideas)}")
            return False
            
        logger.debug(f"Validating {len(ideas)} ideas")
        
        for i, idea in enumerate(ideas):
            if not isinstance(idea, dict):
                logger.error(f"Idea {i} is not a dictionary")
                return False
                
            if "Idea" not in idea or "Details" not in idea:
                logger.error(f"Idea {i} missing required fields")
                return False
                
            # Log successful validation
            logger.debug(f"Idea {i} passed validation:")
            logger.debug(f"  Idea: {idea['Idea']}")
            logger.debug(f"  Details: {idea['Details'][:100]}...")  # Log first 100 chars of details
                
        return True
        
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
            
            # Generate ideas using process_prompts.py
            logger.debug(f"Requesting {num_ideas} ideas from OpenRouter API...")
            ideas = generate_ideas(
                self.openrouter_client,
                initial_prompt,
                expand_prompt,
                list_prompt,
                num_ideas=num_ideas,
                more_items_prompt=more_items_prompt
            )
            
            # Log the raw ideas for debugging
            logger.debug(f"Received ideas from API:\n{json.dumps(ideas, indent=2)}")
            
            # Validate the generated ideas
            if not self._validate_ideas(ideas):
                logger.error("Ideas validation failed")
                logger.debug(f"Invalid ideas structure:\n{json.dumps(ideas, indent=2)}")
                raise ValueError("Generated ideas failed validation")
                
            # Save the ideas to the output directory
            output_path = self.file_handler.save_json(ideas, output_file)
            logger.info(f"Successfully saved {len(ideas)} ideas to {output_path}")
            
            # Log a sample of the generated ideas
            logger.debug("Sample of generated ideas:")
            for i, idea in enumerate(ideas[:3]):  # Show first 3 ideas
                logger.debug(f"Idea {i + 1}:")
                logger.debug(f"  Idea: {idea['Idea']}")
                logger.debug(f"  Details: {idea['Details'][:100]}...")  # Log first 100 chars of details
                
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to generate ideas: {str(e)}", exc_info=True)
            raise
