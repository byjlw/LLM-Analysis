"""
Processor for generating code based on requirements.
"""

import json
import logging
import os
import re
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

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
            # Extract the name from the requirements file
            # Example: requirements_voice_activated_virtual_assistant.txt
            # -> voice_activated_virtual_assistant
            match = re.search(r'requirements_(.+)\.txt$', requirements_file)
            if not match:
                logger.warning(f"Could not extract name from: {requirements_file}")
                return None
            
            requirements_name = match.group(1)
            normalized_req_name = self._normalize_string(requirements_name)
            logger.debug(f"Normalized requirements name: {normalized_req_name}")
            
            # Find matching idea
            for idea in ideas:
                normalized_idea = self._normalize_string(idea["Idea"])
                if normalized_idea == normalized_req_name:
                    return idea
            
            logger.warning(f"No matching idea found for requirements file: {requirements_file}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding matching idea: {str(e)}")
            return None

    def _generate_code_for_idea(self, idea: Dict, requirements_path: str, initial_prompt_file: str, writer_prompt_file: str, code_dir: str) -> bool:
        """
        Generate code for a single idea.
        
        Args:
            idea: Product idea dictionary
            requirements_path: Path to the requirements file
            initial_prompt_file: Path to the initial prompt template file
            writer_prompt_file: Path to the code writer prompt template file
            code_dir: Directory to save generated code
            
        Returns:
            bool indicating success or failure
        """
        try:
            # Read requirements
            with open(requirements_path, 'r', encoding='utf-8') as f:
                requirements = f.read()

            # Read prompt templates
            if not os.path.exists(initial_prompt_file):
                logger.error(f"Initial prompt file not found: {initial_prompt_file}")
                return False
            if not os.path.exists(writer_prompt_file):
                logger.error(f"Writer prompt file not found: {writer_prompt_file}")
                return False

            with open(initial_prompt_file, 'r', encoding='utf-8') as f:
                initial_prompt = f.read()
            with open(writer_prompt_file, 'r', encoding='utf-8') as f:
                writer_prompt = f.read()
            
            # Generate code using process_prompts
            code = generate_code(
                self.openrouter_client,
                initial_prompt,
                writer_prompt,
                requirements
            )
            if not code:
                logger.error(f"Failed to generate code for {idea['Idea']}")
                return False
            
            # Save code to file
            normalized_name = self._normalize_string(idea["Idea"])
            code_file = os.path.join(code_dir, f"{normalized_name}.txt")
            
            with open(code_file, 'w', encoding='utf-8') as f:
                f.write(code)
            
            logger.info(f"Generated code saved to: {code_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating code for {idea['Idea']}: {str(e)}")
            return False

    def generate(self, initial_prompt_file: str, writer_prompt_file: str, ideas_file: Optional[str] = None, parallel_requests: int = 5) -> bool:
        """
        Generate code based on requirements.
        
        Args:
            initial_prompt_file: Path to the initial prompt template file
            writer_prompt_file: Path to the code writer prompt template file
            ideas_file: Optional path to ideas JSON file. If not provided,
                       will use default path in current output directory.
            parallel_requests: Number of parallel requests to make (default: 5)
        
        Returns:
            bool: True if code generation was successful, False otherwise
            
        Raises:
            ValueError: If prompt files are not provided
        """
        if initial_prompt_file is None or writer_prompt_file is None:
            raise ValueError("Both prompt files must be provided")

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
            
            # Create code directory
            code_dir = os.path.join(self.file_handler.current_output_dir, "code")
            os.makedirs(code_dir, exist_ok=True)
            
            # Process requirements in parallel
            success = True
            with ThreadPoolExecutor(max_workers=parallel_requests) as executor:
                futures = []
                
                # Submit tasks for parallel execution
                for filename in os.listdir(requirements_dir):
                    if filename.startswith("requirements_") and filename.endswith(".txt"):
                        # Find matching idea
                        idea = self._find_matching_idea(ideas, filename)
                        if not idea:
                            logger.debug(f"Available ideas: {[i['Idea'] for i in ideas]}")
                            continue
                        
                        requirements_path = os.path.join(requirements_dir, filename)
                        future = executor.submit(
                            self._generate_code_for_idea,
                            idea=idea,
                            requirements_path=requirements_path,
                            initial_prompt_file=initial_prompt_file,
                            writer_prompt_file=writer_prompt_file,
                            code_dir=code_dir
                        )
                        futures.append((future, idea))
                
                # Wait for all tasks to complete
                for future, idea in futures:
                    try:
                        if not future.result():
                            success = False
                            logger.error(f"Failed to generate code for: {idea['Idea']}")
                    except Exception as e:
                        success = False
                        logger.error(f"Error generating code for {idea['Idea']}: {str(e)}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in code generation: {str(e)}")
            return False
