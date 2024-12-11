"""
Processor for generating code based on requirements.
"""

import json
import logging
import os
import re
from typing import Dict, List, Optional

from src.utils.file_handler import FileHandler
from src.utils.openrouter import OpenRouterClient
from src.utils.process_prompts import generate_code

logger = logging.getLogger(__name__)

class CodeGenerator:
    """Generates code based on requirements."""

    def __init__(self, file_handler: FileHandler, openrouter_client: OpenRouterClient):
        """Initialize the generator."""
        self.file_handler = file_handler
        self.openrouter_client = openrouter_client

    def _normalize_string(self, s: str) -> str:
        """
        Normalize a string for comparison by converting to lowercase and replacing
        spaces/special chars with underscores.
        """
        # Convert to lowercase
        s = s.lower()
        # Replace spaces and special characters with underscores
        s = re.sub(r'[^a-z0-9]+', '_', s)
        # Remove leading/trailing underscores
        s = s.strip('_')
        return s

    def _load_ideas(self, ideas_file: str) -> List[Dict]:
        """Load ideas from JSON file."""
        logger.debug(f"Loading ideas from: {ideas_file}")
        try:
            return self.file_handler.load_json(ideas_file)
        except Exception as e:
            logger.error(f"Failed to load ideas: {str(e)}")
            return []

    def _find_matching_idea(self, ideas: List[Dict], requirements_file: str) -> Optional[Dict]:
        """Find the idea that matches a requirements file name."""
        try:
            # Extract the product name from the requirements file
            # Example: requirements_voice-activated_virtual_assistant_for_seniors.txt
            # -> voice-activated_virtual_assistant_for_seniors
            match = re.search(r'requirements_(.+)\.txt$', requirements_file)
            if not match:
                logger.warning(f"Could not extract product name from: {requirements_file}")
                return None
            
            requirements_product = match.group(1)
            normalized_req_product = self._normalize_string(requirements_product)
            logger.debug(f"Normalized requirements product name: {normalized_req_product}")
            
            # Find matching idea
            for idea in ideas:
                if "Product Idea" in idea:
                    normalized_idea = self._normalize_string(idea["Product Idea"])
                    logger.debug(f"Comparing with normalized idea: {normalized_idea}")
                    if normalized_idea == normalized_req_product:
                        return idea
            
            logger.warning(f"No matching idea found for requirements file: {requirements_file}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding matching idea: {str(e)}")
            return None

    def _generate_code_for_idea(self, idea: Dict, requirements_path: str, prompt_file: str) -> bool:
        """Generate code for a single idea."""
        try:
            # Read requirements
            with open(requirements_path, 'r', encoding='utf-8') as f:
                requirements = f.read()

            # Read prompt template
            if not os.path.exists(prompt_file):
                logger.error(f"Prompt file not found: {prompt_file}")
                raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt = f.read()

            # Combine prompt with requirements
            full_prompt = f"{prompt}\n{requirements}"
            
            # Generate code using process_prompts
            code = generate_code(self.openrouter_client, full_prompt)
            if not code:
                logger.error("Failed to generate code")
                return False
            
            # Create code directory if it doesn't exist
            code_dir = os.path.join(self.file_handler.current_output_dir, "code")
            os.makedirs(code_dir, exist_ok=True)
            
            # Save code to file
            normalized_name = self._normalize_string(idea["Product Idea"])
            code_file = os.path.join(code_dir, f"{normalized_name}.txt")
            
            with open(code_file, 'w', encoding='utf-8') as f:
                f.write(code)
            
            logger.info(f"Generated code saved to: {code_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating code: {str(e)}")
            return False

    def generate(self, prompt_file: str, ideas_file: Optional[str] = None) -> bool:
        """
        Generate code based on requirements.
        
        Args:
            prompt_file: Path to the prompt template file
            ideas_file: Optional path to ideas JSON file. If not provided,
                       will use default path in current output directory.
        
        Returns:
            bool: True if code generation was successful, False otherwise
            
        Raises:
            ValueError: If prompt_file is not provided
        """
        if prompt_file is None:
            raise ValueError("prompt_file must be provided")

        try:
            # Get ideas file path
            if ideas_file is None:
                if not self.file_handler.current_output_dir:
                    logger.error("No output directory has been created")
                    return False
                ideas_file = os.path.join(self.file_handler.current_output_dir, "ideas.json")
            
            # Load ideas
            ideas = self._load_ideas(ideas_file)
            if not ideas:
                logger.error("No ideas found")
                return False
            
            logger.info(f"Loaded {len(ideas)} ideas from {ideas_file}")
            
            # Get requirements directory
            requirements_dir = os.path.join(self.file_handler.current_output_dir, "requirements")
            if not os.path.exists(requirements_dir):
                logger.error(f"Requirements directory not found: {requirements_dir}")
                return False
            
            # Process each requirements file
            success = True
            for filename in os.listdir(requirements_dir):
                if filename.startswith("requirements_") and filename.endswith(".txt"):
                    logger.info(f"Processing requirements for: {filename}")
                    
                    # Find matching idea
                    idea = self._find_matching_idea(ideas, filename)
                    if not idea:
                        logger.debug(f"Available ideas: {[i.get('Product Idea') for i in ideas]}")
                        success = False
                        continue
                    
                    # Generate code
                    requirements_path = os.path.join(requirements_dir, filename)
                    if not self._generate_code_for_idea(idea, requirements_path, prompt_file):
                        success = False
            
            return success
            
        except Exception as e:
            logger.error(f"Error in code generation: {str(e)}")
            return False
