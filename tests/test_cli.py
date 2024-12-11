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
            "ideas": "prompts/1-spawn_ideas.txt",
            "requirements": "prompts/2-idea-to-requirements.txt",
            "code": "prompts/3-write-code.txt",
            "dependencies": "prompts/4-collect-dependencies.txt",
            "error_format": "prompts/e1-wrong_format.txt"
        },
        "logging": {
            "level": "DEBUG",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    }

@pytest.fixture
def mock_idea_generator():
    """Create a mock IdeaGenerator."""
    mock = Mock()
    mock.generate.return_value = "/test/output/ideas.json"
    return mock

@pytest.fixture
def mock_requirement_analyzer():
    """Create a mock RequirementAnalyzer."""
    mock = Mock()
    mock.analyze_all.return_value = ["Test requirements"]
    return mock

@pytest.fixture
def mock_code_generator():
    """Create a mock CodeGenerator."""
    mock = Mock()
    mock.generate_all.return_value = {"test": ["/test/output/test.py"]}
    return mock

@pytest.fixture
def mock_dependency_collector():
    """Create a mock DependencyCollector."""
    mock = Mock()
    mock.collect_all.return_value = "/test/output/dependencies.json"
    return mock

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
@patch('src.cli.load_config')
def test_main_config_override(
    mock_load_config,
    mock_idea_cls,
    mock_file_cls,
    mock_openrouter_cls
):
    """Test configuration override through command line arguments."""
    # Set up configuration
    base_config = {
        "openrouter": {
            "api_key": "",
            "default_model": "test-model",
            "timeout": 120,
            "max_retries": 3
        },
        "output": {
            "base_dir": "output"
        }
    }
    mock_load_config.return_value = base_config
    
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
    
    # Verify OpenRouter client was created with overridden config
    mock_openrouter_cls.assert_called_once_with(
        api_key='test-key',
        default_model='custom-model',
        timeout=120,
        max_retries=3
    )

@patch('sys.argv', ['llm-analysis', 'coding-dependencies', '--api-key', 'test-key', '--log-level', 'DEBUG'])
@patch('src.cli.setup_logging')
def test_main_log_level_config(mock_setup_logging):
    """Test log level configuration."""
    with patch('sys.exit'):
        main()
    mock_setup_logging.assert_called_with('DEBUG')
