"""
Processor for analyzing product ideas and generating requirements.
"""

import os
import logging
from typing import Dict, List

from ..utils.openrouter import OpenRouterClient
from ..utils.file_handler import FileHandler
from ..utils.process_prompts import generate_requirements

logger = logging.getLogger(__name__)

class RequirementAnalyzer:
    """Analyzes product ideas and generates requirements."""
    
    def __init__(self, openrouter_client: OpenRouterClient, file_handler: FileHandler):
        """
        Initialize the requirement analyzer.
        
        Args:
            openrouter_client: OpenRouter API client
            file_handler: File handling utility
        """
        self.openrouter_client = openrouter_client
        self.file_handler = file_handler
        
    def _format_prompt(self, idea: Dict, prompt_template: str) -> str:
        """
        Format the requirements prompt with the product idea.
        
        Args:
            idea: Product idea dictionary
            prompt_template: Template for the requirements prompt
            
        Returns:
            Formatted prompt string
        """
        # Create a formatted string representation of the idea
        idea_str = (
            f"Product Idea: {idea['Product Idea']}\n"
            f"Problem it solves: {idea['Problem it solves']}\n"
            f"Software Techstack: {', '.join(idea['Software Techstack'])}\n"
            f"Target hardware: {', '.join(idea['Target hardware expectations'])}\n"
            f"Company profile: {idea['Company profile']}\n"
            f"Engineering profile: {idea['Engineering profile']}"
        )
        
        # Replace the placeholder in the template
        return prompt_template.replace("{THE_IDEA}", idea_str)
        
    def analyze_idea(self, idea: Dict, prompt_file: str, output_dir: str = None) -> str:
        """
        Generate requirements for a single product idea.
        
        Args:
            idea: Product idea dictionary
            prompt_file: Path to the prompt template file
            output_dir: Optional output directory for requirements
            
        Returns:
            Generated requirements string
            
        Raises:
            FileNotFoundError: If the prompt file doesn't exist
            ValueError: If requirement generation fails
        """
        # Read the prompt template
        if not os.path.exists(prompt_file):
            logger.error(f"Prompt file not found: {prompt_file}")
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
            
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
            
        # Format the prompt with the idea
        prompt = self._format_prompt(idea, prompt_template)
        logger.debug(f"Using prompt:\n{prompt}")
        
        # Generate requirements using process_prompts
        requirements = generate_requirements(self.openrouter_client, prompt)
        logger.debug(f"Generated requirements:\n{requirements}")
        
        # Save requirements to file if output directory is specified
        if output_dir:
            filename = f"requirements_{idea['Product Idea'].lower().replace(' ', '_')}.txt"
            filepath = os.path.join(output_dir, filename)
            os.makedirs(output_dir, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(requirements)
            logger.info(f"Saved requirements to: {filepath}")
                
        return requirements
        
    def analyze_all(self, ideas_file: str = "ideas.json", prompt_file: str = None) -> List[str]:
        """
        Generate requirements for all ideas in the ideas file.
        
        Args:
            ideas_file: Path to the JSON file containing ideas
            prompt_file: Path to the prompt template file
            
        Returns:
            List of generated requirements strings
            
        Raises:
            FileNotFoundError: If required files don't exist
            ValueError: If requirement generation fails
        """
        if prompt_file is None:
            raise ValueError("prompt_file must be provided")

        # Use the ideas file from the current output directory
        if not self.file_handler.current_output_dir:
            logger.error("No output directory has been created")
            raise ValueError("No output directory has been created")
            
        ideas_path = os.path.join(self.file_handler.current_output_dir, ideas_file)
        logger.debug(f"Loading ideas from: {ideas_path}")
        
        # Load the ideas file
        ideas = self.file_handler.load_json(ideas_path)
        logger.info(f"Loaded {len(ideas)} ideas from {ideas_path}")
        
        # Create requirements directory in the current output directory
        requirements_dir = os.path.join(self.file_handler.current_output_dir, "requirements")
        os.makedirs(requirements_dir, exist_ok=True)
        logger.info(f"Created requirements directory: {requirements_dir}")
        
        # Generate requirements for each idea
        requirements = []
        for i, idea in enumerate(ideas):
            logger.info(f"Generating requirements for idea {i + 1}: {idea['Product Idea']}")
            req = self.analyze_idea(idea, prompt_file, requirements_dir)
            requirements.append(req)
            logger.debug(f"Generated requirements for idea {i + 1}")
            
        logger.info(f"Generated requirements for {len(requirements)} ideas")
        return requirements
