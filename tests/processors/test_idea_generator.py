"""
Tests for the IdeaGenerator processor.
"""

import json
import os
import pytest
from unittest.mock import Mock, patch, mock_open

from src.processors.idea_generator import IdeaGenerator
from src.utils.file_handler import FileHandler

@pytest.fixture
def sample_idea():
    """Sample idea data for testing."""
    return {
        "Idea": "Dynamic Path Planning for Robots",
        "Details": "Develop an AI module that enables robots to autonomously plan and adjust routes in real-time to avoid obstacles and optimize travel time. Use sensor data such as LiDAR, cameras, or ultrasonic sensors to detect obstacles and implement reinforcement learning for continuous improvement."
    }

@pytest.fixture
def idea_generator(temp_dir):
    """Create an IdeaGenerator instance."""
    file_handler = FileHandler(temp_dir)
    file_handler.create_output_directory()
    return IdeaGenerator(file_handler, None)  # No OpenRouter client needed for validation tests

def test_validate_ideas_success(idea_generator, sample_idea):
    """Test successful idea validation."""
    assert idea_generator._validate_ideas([sample_idea]) is True

def test_validate_ideas_invalid_root(idea_generator):
    """Test validation with invalid root type."""
    assert idea_generator._validate_ideas({"not": "a list"}) is False

def test_validate_ideas_missing_idea(idea_generator, sample_idea):
    """Test validation with missing Idea field."""
    invalid_idea = sample_idea.copy()
    del invalid_idea["Idea"]
    assert idea_generator._validate_ideas([invalid_idea]) is False

def test_validate_ideas_missing_details(idea_generator, sample_idea):
    """Test validation with missing Details field."""
    invalid_idea = sample_idea.copy()
    del invalid_idea["Details"]
    assert idea_generator._validate_ideas([invalid_idea]) is False

def test_validate_ideas_not_dict(idea_generator):
    """Test validation with non-dictionary item."""
    assert idea_generator._validate_ideas(["not a dict"]) is False

def test_read_prompt_file_not_found(idea_generator):
    """Test reading non-existent prompt file."""
    with pytest.raises(FileNotFoundError):
        idea_generator._read_prompt("nonexistent.txt")

@patch('builtins.open', new_callable=mock_open, read_data="Test prompt content")
def test_read_prompt_success(mock_file, idea_generator):
    """Test successful prompt file reading."""
    with patch('os.path.exists', return_value=True):
        content = idea_generator._read_prompt("test_prompt.txt")
        assert content == "Test prompt content"
        mock_file.assert_called_once_with("test_prompt.txt", "r", encoding="utf-8")

@patch('src.utils.process_prompts.generate_ideas')
@patch('builtins.open', new_callable=mock_open)
@patch('os.path.exists')
def test_generate_success(mock_exists, mock_file, mock_generate_ideas, idea_generator, sample_idea):
    """Test successful idea generation."""
    # Set up mock prompt contents
    prompts = {
        "initial_prompt.txt": "Initial prompt content",
        "expand_prompt.txt": "Expand prompt content",
        "list_prompt.txt": "List prompt content",
        "more_items_prompt.txt": "More items prompt content"
    }
    
    # Configure mock file to return different content based on filename
    def mock_read_data(*args, **kwargs):
        filename = args[0]
        return mock_open(read_data=prompts.get(filename, "")).return_value
    mock_file.side_effect = mock_read_data
    
    # Configure path exists check
    mock_exists.return_value = True
    
    # Mock generate_ideas to return a valid idea
    mock_generate_ideas.return_value = [sample_idea]

    # Call generate with all prompt files
    result = idea_generator.generate(
        initial_prompt_file="initial_prompt.txt",
        expand_prompt_file="expand_prompt.txt",
        list_prompt_file="list_prompt.txt",
        more_items_prompt_file="more_items_prompt.txt",
        output_file="test_ideas.json"
    )

    # Verify generate_ideas was called with correct prompts
    mock_generate_ideas.assert_called_once()
    call_args = mock_generate_ideas.call_args[0]
    assert call_args[1] == prompts["initial_prompt.txt"]  # initial_prompt
    assert call_args[2] == prompts["expand_prompt.txt"]   # expand_prompt
    assert call_args[3] == prompts["list_prompt.txt"]     # list_prompt
    assert call_args[-1] == prompts["more_items_prompt.txt"]  # more_items_prompt

@patch('src.utils.process_prompts.generate_ideas')
@patch('builtins.open', new_callable=mock_open)
@patch('os.path.exists')
def test_generate_validation_failure(mock_exists, mock_file, mock_generate_ideas, idea_generator):
    """Test idea generation with validation failure."""
    # Set up mocks
    mock_exists.return_value = True
    mock_file.return_value = mock_open(read_data="Test prompt content").return_value
    
    # Mock generate_ideas to return an invalid idea
    mock_generate_ideas.return_value = [{"invalid": "idea"}]

    # Call generate with all prompt files
    with pytest.raises(ValueError, match="Generated ideas failed validation"):
        idea_generator.generate(
            initial_prompt_file="initial_prompt.txt",
            expand_prompt_file="expand_prompt.txt",
            list_prompt_file="list_prompt.txt",
            more_items_prompt_file="more_items_prompt.txt",
            output_file="test_ideas.json"
        )
