"""
Processor for collecting framework dependencies from code files.
"""

import json
import logging
import os
from collections import Counter
from typing import Dict, List, Set, Union, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.utils.file_handler import FileHandler
from src.utils.process_prompts import generate_dependencies

logger = logging.getLogger(__name__)

class DependencyCollector:
    """Collects framework dependencies from code files."""

    def __init__(self, file_handler: FileHandler, openrouter_client=None):
        """Initialize the collector."""
        self.file_handler = file_handler
        self.openrouter_client = openrouter_client

    def analyze_file(self, filepath: str, prompt_file: str) -> Dict[str, Set[str]]:
        """
        Analyze a single file for dependencies.
        
        Args:
            filepath: Path to the file to analyze
            prompt_file: Path to the prompt template file
            
        Returns:
            Dictionary containing frameworks set
            
        Raises:
            FileNotFoundError: If files don't exist
            ValueError: If analysis fails
        """
        logger.debug(f"Analyzing file: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            logger.warning(f"Failed to read {filepath} as UTF-8, skipping")
            return {"frameworks": set()}
        except Exception as e:
            logger.error(f"Error reading {filepath}: {str(e)}")
            return {"frameworks": set()}

        # Read the prompt file
        if not os.path.exists(prompt_file):
            logger.error(f"Prompt file not found: {prompt_file}")
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt = f.read()

        # Use LLM to analyze dependencies
        try:
            if self.openrouter_client:
                result = generate_dependencies(self.openrouter_client, prompt, content)
                # Convert framework names to lowercase
                frameworks = {str(f).lower() for f in result.get("frameworks", [])}
                return {"frameworks": frameworks}
            else:
                logger.warning("No OpenRouter client provided, skipping LLM analysis")
                return {"frameworks": set()}
        except Exception as e:
            logger.error(f"Error analyzing dependencies with LLM: {str(e)}")
            return {"frameworks": set()}

    def analyze_directory(self, directory: str, prompt_file: str, parallel_requests: int = 5) -> Dict[str, Counter]:
        """
        Analyze all code files in a directory.
        
        Args:
            directory: Directory containing code files
            prompt_file: Path to the prompt template file
            parallel_requests: Number of parallel requests to make (default: 5)
            
        Returns:
            Dictionary containing framework counter
        """
        logger.info(f"Analyzing directory: {directory}")
        
        framework_counter = Counter()
        
        try:
            if os.path.exists(directory):
                # Collect all file paths first
                file_paths = []
                for root, _, files in os.walk(directory):
                    for file in files:
                        if file.endswith('.txt'):  # Only process .txt files
                            filepath = os.path.join(root, file)
                            file_paths.append(filepath)
                
                logger.info(f"Found {len(file_paths)} files to analyze")
                
                # Process files in parallel
                with ThreadPoolExecutor(max_workers=parallel_requests) as executor:
                    futures = []
                    
                    # Submit tasks for parallel execution
                    for filepath in file_paths:
                        future = executor.submit(
                            self.analyze_file,
                            filepath=filepath,
                            prompt_file=prompt_file
                        )
                        futures.append((future, filepath))
                    
                    # Wait for all tasks to complete and collect results
                    for future, filepath in futures:
                        try:
                            result = future.result()
                            framework_counter.update(result["frameworks"])
                        except Exception as e:
                            logger.error(f"Error analyzing file {filepath}: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error walking directory {directory}: {str(e)}")
        
        logger.info("Analysis complete:")
        logger.info(f"Total frameworks found: {len(framework_counter)}")
        logger.debug(f"Framework counts: {dict(framework_counter)}")
        
        return {
            "frameworks": framework_counter
        }

    def _normalize_dependency_data(self, data: Dict[str, Counter]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Normalize dependency data into a consistent format with counts.
        
        Args:
            data: Dictionary containing framework counter
            
        Returns:
            Dictionary with frameworks list
        """
        try:
            # Get the Counter object from the data
            framework_counter = data["frameworks"]
            
            # Convert Counter to list of dicts with name and count
            frameworks = [
                {
                    "name": framework,  # Already lowercase from analyze_file
                    "count": count
                }
                for framework, count in framework_counter.items()
            ]
            
            # Sort by name for consistent output
            frameworks.sort(key=lambda x: x["name"])
            
            # Create normalized data structure
            normalized = {
                "frameworks": frameworks
            }
            
            # Log the normalized data for debugging
            logger.debug(f"Normalized dependency data: {json.dumps(normalized, indent=2)}")
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error normalizing dependency data: {str(e)}")
            return {"frameworks": []}

    def _is_valid_code_dir(self, code_dir: str) -> bool:
        """
        Check if a code directory path is valid and safe to create/use.
        
        Args:
            code_dir: Path to check
            
        Returns:
            bool: True if path is valid and safe, False otherwise
        """
        try:
            # Must be within output directory
            if self.file_handler.current_output_dir:
                output_dir = os.path.abspath(self.file_handler.current_output_dir)
                code_dir_abs = os.path.abspath(code_dir)
                return code_dir_abs.startswith(output_dir)
            return False
        except Exception:
            return False

    def collect_all(self, prompt_file: str = None, code_dir: str = None, parallel_requests: int = 5) -> str:
        """
        Collect all dependencies and save to file.
        
        Args:
            prompt_file: Path to the prompt template file
            code_dir: Optional path to code directory. If not provided,
                     will use default path in current output directory.
            parallel_requests: Number of parallel requests to make (default: 5)
        
        Returns:
            Path to the updated dependencies file
            
        Raises:
            ValueError: If prompt_file is not provided or paths are invalid
        """
        if prompt_file is None:
            raise ValueError("prompt_file must be provided")

        if code_dir is None:
            if not self.file_handler.current_output_dir:
                logger.error("No output directory has been created")
                raise ValueError("No output directory has been created")
            
            code_dir = os.path.join(self.file_handler.current_output_dir, "code")
        
        # Validate code directory path
        if not self._is_valid_code_dir(code_dir):
            logger.error(f"Invalid code directory path: {code_dir}")
            raise ValueError(f"Invalid code directory path: {code_dir}")
        
        # Create code directory if it doesn't exist
        try:
            if not os.path.exists(code_dir):
                os.makedirs(code_dir)
        except Exception as e:
            logger.error(f"Error creating code directory {code_dir}: {str(e)}")
            raise ValueError(f"Could not create code directory: {str(e)}")
        
        logger.info(f"Collecting dependencies from: {code_dir}")
        
        try:
            # Analyze code directory with parallel processing
            results = self.analyze_directory(code_dir, prompt_file, parallel_requests)
            
            # Normalize the data into a consistent format
            normalized_data = self._normalize_dependency_data(results)
            
            # Save results
            output_path = self.file_handler.update_dependencies(normalized_data)
            logger.info(f"Updated dependencies file: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error collecting dependencies: {str(e)}")
            # Return a new dependencies file with empty data
            output_path = self.file_handler.update_dependencies({"frameworks": []})
            return output_path
