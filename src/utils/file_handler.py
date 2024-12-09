"""
File handling utilities for managing output files and directories.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class FileHandler:
    """Handles file operations for the LLM Coding Analysis tool."""
    
    def __init__(self, base_output_dir: str = "output"):
        """
        Initialize the file handler.
        
        Args:
            base_output_dir: Base directory for output files
        """
        self.base_output_dir = base_output_dir
        self.current_output_dir = None
        
    def create_output_directory(self) -> str:
        """
        Create the output directory.
        
        Returns:
            Path to the created directory
        """
        os.makedirs(self.base_output_dir, exist_ok=True)
        self.current_output_dir = self.base_output_dir
        logger.debug(f"Created output directory: {self.base_output_dir}")
        return self.base_output_dir
        
    def get_output_path(self, filename: str) -> str:
        """
        Get the full path for an output file.
        
        Args:
            filename: Name of the output file
            
        Returns:
            Full path to the output file
            
        Raises:
            ValueError: If no output directory has been created
        """
        if not self.current_output_dir:
            logger.error("No output directory has been created")
            raise ValueError("No output directory has been created")
            
        # Ensure we don't duplicate the output directory in the path
        if filename.startswith(self.base_output_dir):
            logger.warning(f"Filename '{filename}' starts with output directory path")
            # Strip the base output directory from the start if it's there
            filename = filename[len(self.base_output_dir):].lstrip('/')
                
        full_path = os.path.join(self.current_output_dir, filename)
        logger.debug(f"Generated output path: {full_path}")
        return full_path
        
    def save_json(self, data: Any, filename: str) -> str:
        """
        Save data as JSON to the output directory.
        
        Args:
            data: Data to save
            filename: Name of the output file
            
        Returns:
            Path to the saved file
        """
        output_path = self.get_output_path(filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            
        logger.debug(f"Saved JSON data to: {output_path}")
        return output_path
        
    def load_json(self, filepath: str) -> Any:
        """
        Load JSON data from a file.
        
        Args:
            filepath: Path to the JSON file
            
        Returns:
            Loaded JSON data
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            json.JSONDecodeError: If the file contains invalid JSON
        """
        # If filepath is relative to output directory, make it absolute
        if not os.path.isabs(filepath) and self.current_output_dir:
            filepath = self.get_output_path(filepath)
            
        logger.debug(f"Loading JSON from: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.debug(f"Successfully loaded JSON data from: {filepath}")
            return data
        except FileNotFoundError:
            logger.error(f"JSON file not found: {filepath}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in file {filepath}: {str(e)}")
            raise
            
    def update_dependencies(self, new_deps: Dict, filename: str = "dependencies.json") -> str:
        """
        Update the dependencies JSON file, incrementing counts for existing items.
        
        Args:
            new_deps: New dependencies to add/update
            filename: Name of the dependencies file
            
        Returns:
            Path to the updated dependencies file
        """
        try:
            filepath = self.get_output_path(filename)
            
            if os.path.exists(filepath):
                logger.debug(f"Loading existing dependencies from: {filepath}")
                current_deps = self.load_json(filepath)
            else:
                logger.debug("No existing dependencies file, creating new one")
                current_deps = {"frameworks": [], "models": []}
                
            # Update frameworks
            for new_framework in new_deps.get("frameworks", []):
                found = False
                for existing in current_deps["frameworks"]:
                    if existing["name"] == new_framework:
                        existing["count"] += 1
                        found = True
                        break
                if not found:
                    current_deps["frameworks"].append({
                        "name": new_framework,
                        "count": 1
                    })
                    
            # Update models
            for new_model in new_deps.get("models", []):
                found = False
                for existing in current_deps["models"]:
                    if existing["name"] == new_model:
                        existing["count"] += 1
                        found = True
                        break
                if not found:
                    current_deps["models"].append({
                        "name": new_model,
                        "count": 1
                    })
                    
            logger.debug(f"Saving updated dependencies to: {filepath}")
            return self.save_json(current_deps, filename)
            
        except Exception as e:
            logger.error(f"Failed to update dependencies: {str(e)}")
            raise ValueError(f"Failed to update dependencies: {str(e)}")
