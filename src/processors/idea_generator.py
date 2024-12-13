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
        required_fields = {
            "Product Idea",
            "Problem it solves",
            "Software Techstack",
            "Target hardware expectations",
            "Company profile",
            "Engineering profile"
        }
        
        if not isinstance(ideas, list):
            logger.error(f"Expected ideas to be a list, got {type(ideas)}")
            return False
            
        logger.debug(f"Validating {len(ideas)} ideas")
        
        for i, idea in enumerate(ideas):
            try:
                if not isinstance(idea, dict):
                    logger.error(f"Idea {i} is not a dictionary: {idea}")
                    return False
                    
                missing_fields = required_fields - set(idea.keys())
                if missing_fields:
                    logger.error(f"Idea {i} is missing required fields: {missing_fields}")
                    return False
                    
                # Validate Software Techstack
                techstack = idea.get("Software Techstack", [])
                if not isinstance(techstack, list):
                    logger.error(f"Idea {i} Software Techstack is not a list: {techstack}")
                    return False
                if not all(isinstance(tech, str) for tech in techstack):
                    logger.error(f"Idea {i} Software Techstack contains non-string values")
                    return False
                    
                # Validate Target hardware expectations
                hardware = idea.get("Target hardware expectations", [])
                if not isinstance(hardware, list):
                    logger.error(f"Idea {i} Target hardware expectations is not a list: {hardware}")
                    return False
                if not all(isinstance(hw, str) for hw in hardware):
                    logger.error(f"Idea {i} Target hardware expectations contains non-string values")
                    return False
                    
                # Log successful validation
                logger.debug(f"Idea {i} passed validation:")
                logger.debug(f"  Product: {idea['Product Idea']}")
                logger.debug(f"  Techstack: {idea['Software Techstack']}")
                logger.debug(f"  Hardware: {idea['Target hardware expectations']}")
                
            except Exception as e:
                logger.error(f"Error validating idea {i}: {str(e)}")
                return False
                
        return True
        
    def generate(self, prompt_file: str, output_file: str, num_ideas: int = 15) -> str:
        """
        Generate product ideas using the specified prompt file.
        
        Args:
            prompt_file: Path to the prompt template file
            output_file: Name of the output file to save ideas
            num_ideas: Number of ideas to generate
            
        Returns:
            Path to the generated ideas file
            
        Raises:
            FileNotFoundError: If the prompt file doesn't exist
            ValueError: If idea generation or validation fails
        """
        # Read the prompt file
        if not os.path.exists(prompt_file):
            logger.error(f"Prompt file not found: {prompt_file}")
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
            
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt = f.read()
            
        logger.debug(f"Using prompt:\n{prompt}")

        # Read the more items prompt from config
        more_items_path = self.file_handler.config.get("prompts", {}).get("more_items")
        if not more_items_path or not os.path.exists(more_items_path):
            logger.error(f"More items prompt file not found: {more_items_path}")
            raise FileNotFoundError(f"More items prompt file not found: {more_items_path}")

        with open(more_items_path, 'r', encoding='utf-8') as f:
            more_items_prompt = f.read()
            
        logger.debug(f"Using more items prompt:\n{more_items_prompt}")
        
        try:
            # Generate ideas using process_prompts.py
            logger.debug(f"Requesting {num_ideas} ideas from OpenRouter API...")
            ideas = generate_ideas(
                self.openrouter_client, 
                prompt, 
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
                logger.debug(f"  Product: {idea['Product Idea']}")
                logger.debug(f"  Problem: {idea['Problem it solves']}")
                logger.debug(f"  Techstack: {idea['Software Techstack']}")
                
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to generate ideas: {str(e)}", exc_info=True)
            raise
