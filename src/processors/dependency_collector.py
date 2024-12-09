"""
Processor for collecting framework dependencies from code files.
"""

import json
import logging
import os
from collections import Counter
from typing import Dict, List, Set, Union, Any

from src.utils.file_handler import FileHandler

logger = logging.getLogger(__name__)

class DependencyCollector:
    """Collects framework dependencies from code files."""

    def __init__(self, file_handler: FileHandler, openrouter_client=None):
        """Initialize the collector."""
        self.file_handler = file_handler
        self.openrouter_client = openrouter_client

    def analyze_file(self, filepath: str) -> Dict[str, Set[str]]:
        """Analyze a single file for dependencies."""
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

        # Get the dependency collection prompt
        try:
            with open(os.path.join("prompts", "4-collect-dependencies.txt"), "r") as f:
                prompt = f.read()
        except Exception as e:
            logger.error(f"Failed to read dependency collection prompt: {str(e)}")
            return {"frameworks": set()}

        # Use LLM to analyze dependencies
        try:
            if self.openrouter_client:
                result = self.openrouter_client.collect_dependencies(content, prompt)
                return {"frameworks": set(result.get("frameworks", []))}
            else:
                logger.warning("No OpenRouter client provided, skipping LLM analysis")
                return {"frameworks": set()}
        except Exception as e:
            logger.error(f"Error analyzing dependencies with LLM: {str(e)}")
            return {"frameworks": set()}

    def analyze_directory(self, directory: str) -> Dict[str, Counter]:
        """Analyze all code files in a directory."""
        logger.info(f"Analyzing directory: {directory}")
        
        framework_counter = Counter()
        
        try:
            if os.path.exists(directory):
                for root, _, files in os.walk(directory):
                    for file in files:
                        if file.endswith('.txt'):  # Only process .txt files
                            filepath = os.path.join(root, file)
                            results = self.analyze_file(filepath)
                            framework_counter.update(results["frameworks"])
        except Exception as e:
            logger.error(f"Error walking directory {directory}: {str(e)}")
        
        logger.info("Analysis complete:")
        logger.info(f"  Total frameworks found: {len(framework_counter)}")
        
        return {
            "frameworks": framework_counter
        }

    def _normalize_dependency_data(self, data: Dict[str, Counter]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Normalize dependency data into a consistent format with counts.
        """
        normalized = {
            "frameworks": []
        }
        
        try:
            # Convert Counter objects to lists of dicts with name and count
            for framework, count in data["frameworks"].items():
                normalized["frameworks"].append({
                    "name": framework,
                    "count": count
                })
            
            # Sort by name for consistent output
            normalized["frameworks"].sort(key=lambda x: x["name"])
            
        except Exception as e:
            logger.error(f"Error normalizing dependency data: {str(e)}")
            return {
                "frameworks": []
            }
        
        return normalized

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

    def collect_all(self, code_dir: str = None) -> str:
        """
        Collect all dependencies and save to file.
        
        Args:
            code_dir: Optional path to code directory. If not provided,
                     will use default path in current output directory.
        
        Returns:
            Path to the updated dependencies file
        """
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
                logger.info(f"Creating code directory: {code_dir}")
                os.makedirs(code_dir)
        except Exception as e:
            logger.error(f"Error creating code directory {code_dir}: {str(e)}")
            raise ValueError(f"Could not create code directory: {str(e)}")
        
        logger.info(f"Collecting dependencies from: {code_dir}")
        
        try:
            # Analyze code directory
            results = self.analyze_directory(code_dir)
            
            # Normalize the data into a consistent format
            normalized_data = self._normalize_dependency_data(results)
            
            # Save results
            output_path = self.file_handler.update_dependencies(normalized_data)
            logger.info(f"Updated dependencies file: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error collecting dependencies: {str(e)}")
            # Return a new dependencies file with empty data
            empty_data = {
                "frameworks": []
            }
            output_path = self.file_handler.update_dependencies(empty_data)
            return output_path
