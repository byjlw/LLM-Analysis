"""
Command line interface for the LLM Analysis tool.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from enum import Enum, IntEnum

from src.processors.code_generator import CodeGenerator
from src.processors.dependency_collector import DependencyCollector
from src.processors.idea_generator import IdeaGenerator
from src.processors.requirement_analyzer import RequirementAnalyzer
from src.utils.file_handler import FileHandler
from src.utils.openrouter import OpenRouterClient

logger = logging.getLogger(__name__)

class ProcessStep(IntEnum):
    """Process steps with integer values for comparison."""
    IDEAS = 1
    REQUIREMENTS = 2
    CODE = 3
    DEPENDENCIES = 4

    @classmethod
    def from_string(cls, step_str: str) -> 'ProcessStep':
        """Convert string to ProcessStep enum."""
        step_map = {
            '1': cls.IDEAS,
            '2': cls.REQUIREMENTS,
            '3': cls.CODE,
            '4': cls.DEPENDENCIES,
            'ideas': cls.IDEAS,
            'requirements': cls.REQUIREMENTS,
            'code': cls.CODE,
            'dependencies': cls.DEPENDENCIES
        }
        if step_str.lower() not in step_map:
            raise ValueError(f"Invalid step: {step_str}. Valid steps are: 1/ideas, 2/requirements, 3/code, 4/dependencies")
        return step_map[step_str.lower()]

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
            logging.FileHandler('llm_analysis.log')
        ]
    )

def load_config(config_path=None):
    """
    Load configuration from JSON file.
    
    Args:
        config_path: Optional path to config file. If not provided, tries config.json
                    then falls back to default_config.json
        
    Returns:
        Dictionary containing configuration
        
    Raises:
        FileNotFoundError: If neither config file exists
        ValueError: If config file is invalid
    """
    if config_path:
        # If specific path provided, use only that
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
        logger.info(f"Loading config from: {config_path}")
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    # Try config.json in current directory first
    if os.path.exists('config.json'):
        logger.info("Loading config from config.json")
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
            
    # Fall back to default_config.json
    default_config = os.path.join(os.path.dirname(__file__), 'config', 'default_config.json')
    if os.path.exists(default_config):
        logger.info("Loading default config")
        with open(default_config, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    raise FileNotFoundError("No config file found. Create config.json or ensure default_config.json exists.")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='LLM Analysis Tool')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Coding dependencies command
    coding_deps = subparsers.add_parser('coding-dependencies', 
                                       help='Analyze code dependencies in LLM outputs')
    
    coding_deps.add_argument(
        '--api-key',
        help='OpenRouter API key',
        default=os.environ.get('OPENROUTER_API_KEY')
    )
    
    coding_deps.add_argument(
        '--output-dir',
        help='Output directory',
        default='output'
    )

    coding_deps.add_argument(
        '--working-dir',
        help='Working directory name (defaults to timestamp)',
        default=None
    )
    
    coding_deps.add_argument(
        '--num-ideas',
        type=int,
        help='Number of ideas to generate',
        default=15
    )
    
    coding_deps.add_argument(
        '--model',
        help='Model to use for generation',
        default='meta-llama/llama-3.3-70b-instruct'
    )
    
    coding_deps.add_argument(
        '--log-level',
        help='Logging level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO'
    )

    coding_deps.add_argument(
        '--start-step',
        help='Step to start from (1/ideas, 2/requirements, 3/code, 4/dependencies)',
        default='1'
    )
    
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
        
    return args

def create_working_dir(base_dir: str, working_dir: str = None) -> str:
    """
    Create a working directory within the base directory.
    
    Args:
        base_dir: Base directory path
        working_dir: Optional working directory name, defaults to timestamp
        
    Returns:
        Path to the created working directory
    """
    # Create base directory if it doesn't exist
    os.makedirs(base_dir, exist_ok=True)
    
    # Create working directory
    if working_dir is None:
        working_dir = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    working_dir_path = os.path.join(base_dir, working_dir)
    os.makedirs(working_dir_path, exist_ok=True)
    
    logger.debug(f"Created working directory: {working_dir_path}")
    return working_dir_path

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
        # Parse starting step
        try:
            start_step = ProcessStep.from_string(args.start_step)
        except ValueError as e:
            logger.error(str(e))
            sys.exit(1)

        # Create working directory
        output_dir = create_working_dir(args.output_dir, args.working_dir)
        
        # Initialize components with the working directory
        file_handler = FileHandler(output_dir)
        openrouter_client = OpenRouterClient(
            api_key=config['openrouter']['api_key'],
            default_model=config['openrouter']['default_model'],
            timeout=config['openrouter']['timeout'],
            max_retries=config['openrouter']['max_retries']
        )
        
        # Create output directory structure
        file_handler.create_output_directory()
        
        # Generate ideas if starting from step 1 or if required files don't exist
        if start_step <= ProcessStep.IDEAS:
            logger.info("Generating ideas...")
            idea_generator = IdeaGenerator(file_handler, openrouter_client)
            ideas_file = idea_generator.generate(
                prompt_file=config["prompts"]["ideas"],
                output_file=config["output"]["ideas_filename"],
                num_ideas=args.num_ideas
            )
            if not ideas_file:
                logger.error("Failed to generate ideas")
                sys.exit(1)
        
        # Generate requirements if starting from step 2 or earlier
        if start_step <= ProcessStep.REQUIREMENTS:
            logger.info("Generating requirements...")
            requirement_analyzer = RequirementAnalyzer(openrouter_client, file_handler)
            requirements = requirement_analyzer.analyze_all(
                prompt_file=config["prompts"]["requirements"]
            )
            if not requirements:
                logger.error("Failed to generate requirements")
                sys.exit(1)
            logger.info(f"Generated {len(requirements)} requirement documents")
        
        # Generate code if starting from step 3 or earlier
        if start_step <= ProcessStep.CODE:
            logger.info("Generating code...")
            code_generator = CodeGenerator(file_handler, openrouter_client)
            if not code_generator.generate(
                prompt_file=config["prompts"]["code"]
            ):
                logger.error("Failed to generate code")
                sys.exit(1)
        
        # Analyze dependencies if starting from step 4 or earlier
        if start_step <= ProcessStep.DEPENDENCIES:
            logger.info("Analyzing dependencies...")
            dependency_collector = DependencyCollector(file_handler, openrouter_client)
            dependencies_file = dependency_collector.collect_all(
                prompt_file=config["prompts"]["dependencies"]
            )
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
