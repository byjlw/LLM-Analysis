"""
Command line interface for the LLM Coding Analysis tool.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime

from src.processors.code_generator import CodeGenerator
from src.processors.dependency_collector import DependencyCollector
from src.processors.idea_generator import IdeaGenerator
from src.processors.requirement_analyzer import RequirementAnalyzer
from src.utils.file_handler import FileHandler
from src.utils.openrouter import OpenRouterClient

logger = logging.getLogger(__name__)

def setup_logging(log_level="INFO"):
    """Set up logging configuration."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
        
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('llm_coding_analysis.log')
        ]
    )

def load_config(config_path=None):
    """
    Load configuration from JSON file.
    
    Args:
        config_path: Optional path to config file. If not provided, uses default.
        
    Returns:
        Dictionary containing configuration
    """
    if not config_path:
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'default_config.json')
        
    if not os.path.exists(config_path):
        logger.warning(f"Config file not found at {config_path}, using defaults")
        return {
            "openrouter": {
                "api_key": "",
                "default_model": "meta-llama/llama-3.3-70b-instruct",
                "timeout": 120,
                "max_retries": 3
            },
            "output": {
                "base_dir": "output"
            }
        }
        
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='LLM Coding Analysis Tool')
    
    parser.add_argument(
        '--api-key',
        help='OpenRouter API key',
        default=os.environ.get('OPENROUTER_API_KEY')
    )
    
    parser.add_argument(
        '--output-dir',
        help='Output directory',
        default='output'
    )
    
    parser.add_argument(
        '--num-ideas',
        type=int,
        help='Number of ideas to generate',
        default=15
    )
    
    parser.add_argument(
        '--model',
        help='Model to use for generation',
        default='meta-llama/llama-3.3-70b-instruct'
    )
    
    parser.add_argument(
        '--log-level',
        help='Logging level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO'
    )
    
    return parser.parse_args()

def create_timestamped_dir(base_dir: str) -> str:
    """
    Create a timestamped directory within the base directory.
    
    Args:
        base_dir: Base directory path
        
    Returns:
        Path to the created timestamped directory
    """
    # Create base directory if it doesn't exist
    os.makedirs(base_dir, exist_ok=True)
    
    # Create timestamped directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_dir = os.path.join(base_dir, timestamp)
    os.makedirs(timestamped_dir, exist_ok=True)
    
    logger.debug(f"Created timestamped directory: {timestamped_dir}")
    return timestamped_dir

def main():
    """Main entry point."""
    # Parse arguments
    args = parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    
    # Load configuration
    config = load_config()
    
    # Override config with command line arguments
    config['openrouter']['api_key'] = args.api_key
    if args.model:
        config['openrouter']['default_model'] = args.model
    
    # Check API key
    if not config['openrouter']['api_key']:
        logger.error("No API key provided. Set OPENROUTER_API_KEY environment variable or use --api-key")
        sys.exit(1)
    
    try:
        # Create timestamped output directory
        output_dir = create_timestamped_dir(args.output_dir)
        
        # Initialize components with the timestamped directory
        file_handler = FileHandler(output_dir)
        openrouter_client = OpenRouterClient(
            api_key=config['openrouter']['api_key'],
            default_model=config['openrouter']['default_model'],
            timeout=config['openrouter']['timeout'],
            max_retries=config['openrouter']['max_retries']
        )
        
        # Create output directory structure
        file_handler.create_output_directory()
        
        # Generate ideas
        logger.info("Generating ideas...")
        idea_generator = IdeaGenerator(file_handler, openrouter_client)
        ideas_file = idea_generator.generate(args.num_ideas)
        if not ideas_file:
            logger.error("Failed to generate ideas")
            sys.exit(1)
        
        # Generate requirements
        logger.info("Generating requirements...")
        requirement_analyzer = RequirementAnalyzer(openrouter_client, file_handler)
        requirements = requirement_analyzer.analyze_all()
        if not requirements:
            logger.error("Failed to generate requirements")
            sys.exit(1)
        logger.info(f"Generated {len(requirements)} requirement documents")
        
        # Generate code
        logger.info("Generating code...")
        code_generator = CodeGenerator(file_handler, openrouter_client)
        if not code_generator.generate():
            logger.error("Failed to generate code")
            sys.exit(1)
        
        # Analyze dependencies
        logger.info("Analyzing dependencies...")
        dependency_collector = DependencyCollector(file_handler)
        dependencies_file = dependency_collector.collect_all()
        if not dependencies_file:
            logger.error("Failed to analyze dependencies")
            sys.exit(1)
        
        logger.info("Processing complete")
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    main()
