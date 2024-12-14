"""
Tests for the CLI module.
"""

import json
import os
import pytest
from unittest.mock import Mock, patch, create_autospec

from src.cli import main, load_config, setup_logging
from src.utils.openrouter import OpenRouterClient
from src.utils.file_handler import FileHandler

@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    return {
        "openrouter": {
            "api_key": "test-key",
            "default_model": "test-model",
            "timeout": 120,
            "max_retries": 3
        },
        "output": {
            "base_dir": "output",
            "ideas_filename": "ideas.json",
            "dependencies_filename": "dependencies.json"
        },
        "prompts": {
            "ideas": "prompts/find-deps/1-spawn_ideas.txt",
            "ideas_expand": "prompts/find-deps/1-spawn_ideas-b.txt",
            "ideas_list": "prompts/find-deps/1-spawn_ideas-c.txt",
            "requirements": "prompts/find-deps/2-idea-to-requirements.txt",
            "code": "prompts/find-deps/3-write-code.txt",
            "code_writer": "prompts/find-deps/3-write-code-b.txt",
            "dependencies": "prompts/find-deps/4-collect-dependencies.txt",
            "error_format": "prompts/e1-wrong_format.txt",
            "more_items": "prompts/m1-num_more_items.txt"
        },
        "logging": {
            "level": "DEBUG",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    }

def test_setup_logging():
    """Test logging setup."""
    with patch('logging.FileHandler') as mock_handler:
        setup_logging("DEBUG")
        mock_handler.assert_called()

def test_default_config_exists():
    """Test that default_config.json exists."""
    default_config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src', 'config', 'default_config.json')
    assert os.path.exists(default_config_path), "default_config.json must exist"

@patch('sys.argv', ['llm-analysis'])
def test_main_no_command():
    """Test main function without a command."""
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1

@patch('sys.argv', ['llm-analysis', 'coding-dependencies'])
def test_main_missing_api_key():
    """Test main function without API key."""
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1

@patch('sys.argv', ['llm-analysis', 'coding-dependencies', '--api-key', 'test-key', '--model', 'custom-model'])
@patch('src.cli.OpenRouterClient', autospec=True)
@patch('src.cli.FileHandler', autospec=True)
@patch('src.cli.IdeaGenerator', autospec=True)
@patch('src.cli.RequirementAnalyzer', autospec=True)
@patch('src.cli.CodeGenerator', autospec=True)
@patch('src.cli.DependencyCollector', autospec=True)
@patch('src.cli.load_config')
def test_main_config_override(
    mock_load_config,
    mock_dependency_cls,
    mock_code_cls,
    mock_requirement_cls,
    mock_idea_cls,
    mock_file_cls,
    mock_openrouter_cls,
    mock_config
):
    """Test configuration override through command line arguments."""
    # Set up configuration
    mock_load_config.return_value = mock_config
    
    # Set up mock file handler
    mock_file_handler = Mock()
    mock_file_handler.current_output_dir = "/test/output"
    mock_file_cls.return_value = mock_file_handler
    
    # Set up mock processors
    mock_idea_generator = Mock()
    mock_idea_generator.generate.return_value = "/test/output/ideas.json"
    mock_idea_cls.return_value = mock_idea_generator
    
    mock_requirement_analyzer = Mock()
    mock_requirement_analyzer.analyze_all.return_value = ["Test requirements"]
    mock_requirement_cls.return_value = mock_requirement_analyzer
    
    mock_code_generator = Mock()
    mock_code_generator.generate.return_value = True
    mock_code_cls.return_value = mock_code_generator
    
    mock_dependency_collector = Mock()
    mock_dependency_collector.collect_all.return_value = "/test/output/dependencies.json"
    mock_dependency_cls.return_value = mock_dependency_collector
    
    # Run main function
    with patch('sys.exit'):
        main()
    
    # Verify OpenRouter client was created with overridden config
    mock_openrouter_cls.assert_called_once_with(
        api_key='test-key',
        default_model='custom-model',
        timeout=120,
        max_retries=3
    )

    # Verify processors were called with correct arguments
    mock_idea_generator.generate.assert_called_once_with(
        initial_prompt_file=mock_config["prompts"]["ideas"],
        expand_prompt_file=mock_config["prompts"]["ideas_expand"],
        list_prompt_file=mock_config["prompts"]["ideas_list"],
        more_items_prompt_file=mock_config["prompts"]["more_items"],
        output_file=mock_config["output"]["ideas_filename"],
        num_ideas=15
    )
    
    mock_requirement_analyzer.analyze_all.assert_called_once_with(
        prompt_file=mock_config["prompts"]["requirements"],
        parallel_requests=5
    )
    
    mock_code_generator.generate.assert_called_once_with(
        initial_prompt_file=mock_config["prompts"]["code"],
        writer_prompt_file=mock_config["prompts"]["code_writer"],
        parallel_requests=5
    )
    
    mock_dependency_collector.collect_all.assert_called_once_with(
        prompt_file=mock_config["prompts"]["dependencies"]
    )

@patch('sys.argv', ['llm-analysis', 'coding-dependencies', '--api-key', 'test-key', '--num-ideas', '20'])
@patch('src.cli.OpenRouterClient', autospec=True)
@patch('src.cli.FileHandler', autospec=True)
@patch('src.cli.IdeaGenerator', autospec=True)
@patch('src.cli.load_config')
def test_main_num_ideas_override(
    mock_load_config,
    mock_idea_cls,
    mock_file_cls,
    mock_openrouter_cls,
    mock_config
):
    """Test num_ideas override through command line arguments."""
    # Set up configuration
    mock_load_config.return_value = mock_config
    
    # Set up mock file handler
    mock_file_handler = Mock()
    mock_file_handler.current_output_dir = "/test/output"
    mock_file_cls.return_value = mock_file_handler
    
    # Set up mock idea generator
    mock_idea_generator = Mock()
    mock_idea_generator.generate.return_value = "/test/output/ideas.json"
    mock_idea_cls.return_value = mock_idea_generator
    
    # Run main function
    with patch('sys.exit'):
        main()
    
    # Verify idea generator was called with overridden num_ideas
    mock_idea_generator.generate.assert_called_once_with(
        initial_prompt_file=mock_config["prompts"]["ideas"],
        expand_prompt_file=mock_config["prompts"]["ideas_expand"],
        list_prompt_file=mock_config["prompts"]["ideas_list"],
        more_items_prompt_file=mock_config["prompts"]["more_items"],
        output_file=mock_config["output"]["ideas_filename"],
        num_ideas=20
    )

@patch('sys.argv', ['llm-analysis', 'coding-dependencies', '--api-key', 'test-key', '--log-level', 'DEBUG'])
@patch('src.cli.setup_logging')
def test_main_log_level_config(mock_setup_logging):
    """Test log level configuration."""
    with patch('sys.exit'):
        main()
    mock_setup_logging.assert_called_with('DEBUG')
