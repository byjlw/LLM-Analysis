"""
Processor for collecting framework and model dependencies from code files.
"""

import json
import logging
import os
import re
from collections import Counter
from typing import Dict, List, Set, Union, Any

from src.utils.file_handler import FileHandler

logger = logging.getLogger(__name__)

class DependencyCollector:
    """Collects framework and model dependencies from code files."""

    def __init__(self, file_handler: FileHandler):
        """Initialize the collector."""
        self.file_handler = file_handler

    def _extract_python_imports(self, content: str, filepath: str) -> Set[str]:
        """Extract Python imports from code."""
        imports = set()
        
        # Match import statements
        import_patterns = [
            r'import\s+(\w+)',  # import torch
            r'from\s+(\w+)\s+import',  # from tensorflow import
            r'import\s+(\w+)\s+as',  # import tensorflow as tf
        ]
        
        for pattern in import_patterns:
            for match in re.finditer(pattern, content):
                module = match.group(1)
                logger.debug(f"Found Python import in {filepath}: {module}")
                imports.add(module)
        
        return imports

    def _extract_js_imports(self, content: str, filepath: str) -> Set[str]:
        """Extract JavaScript/TypeScript imports from code."""
        imports = set()
        
        # Match import statements
        import_patterns = [
            r'from\s+[\'"]@?([^/\'"]+)',  # from '@tensorflow/tfjs'
            r'import\s+.*?[\'"]@?([^/\'"]+)',  # import * from '@tensorflow/tfjs'
            r'require\([\'"]@?([^/\'"]+)',  # require('@tensorflow/tfjs')
        ]
        
        for pattern in import_patterns:
            for match in re.finditer(pattern, content):
                package = match.group(1)
                logger.debug(f"Found JS/TS import in {filepath}: {package}")
                imports.add(package)
        
        return imports

    def _extract_model_references(self, content: str, filepath: str) -> Set[str]:
        """Extract model references from code."""
        models = set()
        
        # Match model loading patterns
        model_patterns = [
            # Python patterns
            r'\.from_pretrained\([\'"]([^\'"]+)[\'"]',  # .from_pretrained("model-name")
            r'\.load_model\([\'"]([^\'"]+)[\'"]',  # .load_model("model-name")
            r'torch\.load\([\'"]([^\'"]+)[\'"]',  # torch.load("model-name")
            r'torch\.hub\.load\([\'"]([^\'"]+)[\'"]',  # torch.hub.load("model-name")
            r'tf\.saved_model\.load\([\'"]([^\'"]+)[\'"]',  # tf.saved_model.load("model-name")
            r'tf\.keras\.models\.load_model\([\'"]([^\'"]+)[\'"]',  # tf.keras.models.load_model("model-name")
            
            # JavaScript patterns
            r'loadLayersModel\([\'"]([^\'"]+)[\'"]',  # loadLayersModel("model-name")
            r'loadGraphModel\([\'"]([^\'"]+)[\'"]',  # loadGraphModel("model-name")
            r'model\.load\([\'"]([^\'"]+)[\'"]',  # model.load("model-name")
        ]
        
        for pattern in model_patterns:
            for match in re.finditer(pattern, content):
                model = match.group(1)
                logger.debug(f"Found model reference in {filepath}: {model}")
                models.add(model)
        
        return models

    def analyze_file(self, filepath: str) -> Dict[str, Set[str]]:
        """Analyze a single file for dependencies."""
        logger.debug(f"Analyzing file: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            logger.warning(f"Failed to read {filepath} as UTF-8, skipping")
            return {"frameworks": set(), "models": set()}
        except Exception as e:
            logger.error(f"Error reading {filepath}: {str(e)}")
            return {"frameworks": set(), "models": set()}
        
        frameworks = set()
        models = set()
        
        # Extract dependencies based on file type
        try:
            if filepath.endswith('.py'):
                frameworks.update(self._extract_python_imports(content, filepath))
            elif filepath.endswith(('.js', '.ts')):
                frameworks.update(self._extract_js_imports(content, filepath))
            
            # Extract model references
            models.update(self._extract_model_references(content, filepath))
            
            # Filter out standard library imports
            frameworks = {f for f in frameworks if f not in {'os', 'sys', 'json', 'typing'}}
            
            logger.debug(f"Found in {filepath}:")
            logger.debug(f"  Frameworks: {frameworks}")
            logger.debug(f"  Models: {models}")
            
            return {
                "frameworks": frameworks,
                "models": models
            }
        except Exception as e:
            logger.error(f"Error analyzing {filepath}: {str(e)}")
            return {"frameworks": set(), "models": set()}

    def analyze_directory(self, directory: str) -> Dict[str, Counter]:
        """Analyze all code files in a directory."""
        logger.info(f"Analyzing directory: {directory}")
        
        framework_counter = Counter()
        model_counter = Counter()
        
        try:
            if os.path.exists(directory):
                for root, _, files in os.walk(directory):
                    for file in files:
                        if file.endswith(('.py', '.js', '.ts')):
                            filepath = os.path.join(root, file)
                            results = self.analyze_file(filepath)
                            framework_counter.update(results["frameworks"])
                            model_counter.update(results["models"])
        except Exception as e:
            logger.error(f"Error walking directory {directory}: {str(e)}")
        
        logger.info("Analysis complete:")
        logger.info(f"  Total frameworks found: {len(framework_counter)}")
        logger.info(f"  Total models found: {len(model_counter)}")
        
        return {
            "frameworks": framework_counter,
            "models": model_counter
        }

    def _normalize_dependency_data(self, data: Dict[str, Counter]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Normalize dependency data into a consistent format with counts.
        """
        normalized = {
            "frameworks": [],
            "models": []
        }
        
        try:
            # Convert Counter objects to lists of dicts with name and count
            for framework, count in data["frameworks"].items():
                normalized["frameworks"].append({
                    "name": framework,
                    "count": count
                })
            
            for model, count in data["models"].items():
                normalized["models"].append({
                    "name": model,
                    "count": count
                })
            
            # Sort by name for consistent output
            normalized["frameworks"].sort(key=lambda x: x["name"])
            normalized["models"].sort(key=lambda x: x["name"])
            
        except Exception as e:
            logger.error(f"Error normalizing dependency data: {str(e)}")
            return {
                "frameworks": [],
                "models": []
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
                "frameworks": [],
                "models": []
            }
            output_path = self.file_handler.update_dependencies(empty_data)
            return output_path
