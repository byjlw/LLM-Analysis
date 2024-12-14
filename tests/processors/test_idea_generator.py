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

def test_validate_and_normalize_response(idea_generator, sample_idea):
    """Test response validation and normalization."""
    # Test valid list of ideas
    valid_ideas = [sample_idea]
    assert idea_generator._validate_and_normalize_response(valid_ideas) == valid_ideas
    
    # Test ideas wrapped in object
    wrapped_ideas = {"ideas": [sample_idea]}
    assert idea_generator._validate_and_normalize_response(wrapped_ideas) == [sample_idea]
    
    # Test invalid root type
    with pytest.raises(ValueError, match="Expected list of ideas"):
        idea_generator._validate_and_normalize_response("not a list")
    
    # Test invalid idea format
    with pytest.raises(ValueError, match="is not a dictionary"):
        idea_generator._validate_and_normalize_response(["not a dict"])
    
    # Test missing required fields
    with pytest.raises(ValueError, match="missing required fields"):
        idea_generator._validate_and_normalize_response([{"Idea": "test"}])
    
    # Test invalid field types
    with pytest.raises(ValueError, match="has invalid field types"):
        idea_generator._validate_and_normalize_response([{
            "Idea": 123,  # Should be string
            "Details": "test"
        }])

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

def test_generate_batch_success(idea_generator, sample_idea):
    """Test successful batch generation."""
    # Mock OpenRouter client
    mock_client = Mock()
    idea_generator.openrouter_client = mock_client
    
    # Mock get_raw_json_response to return valid ideas
    with patch('src.utils.process_prompts.get_raw_json_response', 
              return_value=[sample_idea]):
        result = idea_generator._generate_batch([{"role": "user", "content": "test"}])
        assert result == [sample_idea]

def test_generate_batch_invalid_response(idea_generator):
    """Test batch generation with invalid response."""
    # Mock OpenRouter client
    mock_client = Mock()
    idea_generator.openrouter_client = mock_client
    
    # Mock get_raw_json_response to return invalid format
    with patch('src.utils.process_prompts.get_raw_json_response', 
              return_value={"invalid": "format"}):
        with pytest.raises(ValueError, match="Expected list of ideas"):
            idea_generator._generate_batch([{"role": "user", "content": "test"}])

@patch('src.utils.process_prompts.get_raw_json_response')
@patch('src.utils.process_prompts.get_text_response')
@patch('builtins.open', new_callable=mock_open)
@patch('os.path.exists')
def test_generate_success(mock_exists, mock_file, mock_text_response, mock_json_response, 
                         idea_generator, sample_idea):
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
    
    # Mock text responses
    mock_text_response.side_effect = [
        "Initial brainstorming",  # For initial prompt
        "Specific ideas"          # For expand prompt
    ]
    
    # Mock JSON responses for batches
    mock_json_response.side_effect = [
        [sample_idea]  # First batch
    ]

    # Call generate with all prompt files
    result = idea_generator.generate(
        initial_prompt_file="initial_prompt.txt",
        expand_prompt_file="expand_prompt.txt",
        list_prompt_file="list_prompt.txt",
        more_items_prompt_file="more_items_prompt.txt",
        output_file="test_ideas.json",
        num_ideas=1  # Request just one idea to test single batch
    )

    # Verify the text responses were requested
    assert mock_text_response.call_count == 2
    
    # Verify JSON response was requested for batch
    assert mock_json_response.call_count == 1

@patch('src.utils.process_prompts.get_raw_json_response')
@patch('src.utils.process_prompts.get_text_response')
@patch('builtins.open', new_callable=mock_open)
@patch('os.path.exists')
def test_generate_multiple_batches(mock_exists, mock_file, mock_text_response, mock_json_response,
                                 idea_generator, sample_idea):
    """Test generating multiple batches of ideas."""
    # Set up mocks
    mock_exists.return_value = True
    mock_file.return_value = mock_open(read_data="Test prompt content").return_value
    
    # Mock text responses
    mock_text_response.side_effect = [
        "Initial brainstorming",
        "Specific ideas"
    ]
    
    # Mock JSON responses for batches
    batch1 = [sample_idea]
    batch2 = [{
        "Idea": "Another idea",
        "Details": "More details"
    }]
    mock_json_response.side_effect = [batch1, batch2]

    # Request 2 ideas to test multiple batches
    result = idea_generator.generate(
        initial_prompt_file="initial_prompt.txt",
        expand_prompt_file="expand_prompt.txt",
        list_prompt_file="list_prompt.txt",
        more_items_prompt_file="more_items_prompt.txt",
        output_file="test_ideas.json",
        num_ideas=2
    )

    # Verify both batches were processed
    assert mock_json_response.call_count == 2

@patch('src.utils.process_prompts.get_raw_json_response')
@patch('src.utils.process_prompts.get_text_response')
@patch('builtins.open', new_callable=mock_open)
@patch('os.path.exists')
def test_generate_validation_failure(mock_exists, mock_file, mock_text_response, mock_json_response,
                                   idea_generator):
    """Test idea generation with validation failure."""
    # Set up mocks
    mock_exists.return_value = True
    mock_file.return_value = mock_open(read_data="Test prompt content").return_value
    
    # Mock text responses
    mock_text_response.side_effect = [
        "Initial brainstorming",
        "Specific ideas"
    ]
    
    # Mock JSON response with invalid idea
    mock_json_response.return_value = [{"invalid": "idea"}]

    # Should raise ValueError due to validation failure
    with pytest.raises(ValueError, match="is not a dictionary"):
        idea_generator.generate(
            initial_prompt_file="initial_prompt.txt",
            expand_prompt_file="expand_prompt.txt",
            list_prompt_file="list_prompt.txt",
            more_items_prompt_file="more_items_prompt.txt",
            output_file="test_ideas.json"
        )
