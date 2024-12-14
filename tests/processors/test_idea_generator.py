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
    return IdeaGenerator(file_handler, Mock())  # Use Mock for OpenRouter client

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
    # Mock OpenRouter client response
    mock_client = Mock()
    mock_client._make_request.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps([sample_idea])
            }
        }]
    }
    idea_generator.openrouter_client = mock_client
    
    result = idea_generator._generate_batch([{"role": "user", "content": "test"}])
    assert result == [sample_idea]

def test_generate_batch_invalid_response(idea_generator):
    """Test batch generation with invalid response."""
    # Mock OpenRouter client response
    mock_client = Mock()
    mock_client._make_request.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps({"invalid": "format"})
            }
        }]
    }
    idea_generator.openrouter_client = mock_client
    
    with pytest.raises(ValueError, match="Expected list of ideas"):
        idea_generator._generate_batch([{"role": "user", "content": "test"}])

@patch('builtins.open', new_callable=mock_open)
@patch('os.path.exists')
def test_generate_success(mock_exists, mock_file, idea_generator, sample_idea):
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
    
    # Mock OpenRouter client responses
    mock_client = Mock()
    mock_client._make_request.side_effect = [
        # Response for initial prompt
        {"choices": [{"message": {"content": "Initial brainstorming"}}]},
        # Response for expand prompt
        {"choices": [{"message": {"content": "Specific ideas"}}]},
        # Response for list prompt
        {"choices": [{"message": {"content": json.dumps([sample_idea])}}]}
    ]
    idea_generator.openrouter_client = mock_client

    result = idea_generator.generate(
        initial_prompt_file="initial_prompt.txt",
        expand_prompt_file="expand_prompt.txt",
        list_prompt_file="list_prompt.txt",
        more_items_prompt_file="more_items_prompt.txt",
        output_file="test_ideas.json",
        num_ideas=1  # Request just one idea to test single batch
    )
    
    assert result is not None
    assert mock_client._make_request.call_count == 3

@patch('builtins.open', new_callable=mock_open)
@patch('os.path.exists')
def test_generate_multiple_batches(mock_exists, mock_file, idea_generator, sample_idea):
    """Test generating multiple batches of ideas."""
    # Set up mocks
    mock_exists.return_value = True
    mock_file.return_value = mock_open(read_data="Test prompt content").return_value
    
    # Mock OpenRouter client responses
    mock_client = Mock()
    mock_client._make_request.side_effect = [
        # Response for initial prompt
        {"choices": [{"message": {"content": "Initial brainstorming"}}]},
        # Response for expand prompt
        {"choices": [{"message": {"content": "Specific ideas"}}]},
        # Response for first batch
        {"choices": [{"message": {"content": json.dumps([sample_idea])}}]},
        # Response for second batch
        {"choices": [{"message": {"content": json.dumps([{
            "Idea": "Another idea",
            "Details": "More details"
        }])}}]}
    ]
    idea_generator.openrouter_client = mock_client

    result = idea_generator.generate(
        initial_prompt_file="initial_prompt.txt",
        expand_prompt_file="expand_prompt.txt",
        list_prompt_file="list_prompt.txt",
        more_items_prompt_file="more_items_prompt.txt",
        output_file="test_ideas.json",
        num_ideas=2
    )
    
    assert result is not None
    assert mock_client._make_request.call_count == 4  # All 4 calls are needed

@patch('builtins.open', new_callable=mock_open)
@patch('os.path.exists')
def test_generate_validation_failure(mock_exists, mock_file, idea_generator):
    """Test idea generation with validation failure."""
    # Set up mocks
    mock_exists.return_value = True
    mock_file.return_value = mock_open(read_data="Test prompt content").return_value
    
    # Mock OpenRouter client responses
    mock_client = Mock()
    mock_client._make_request.side_effect = [
        # Response for initial prompt
        {"choices": [{"message": {"content": "Initial brainstorming"}}]},
        # Response for expand prompt
        {"choices": [{"message": {"content": "Specific ideas"}}]},
        # Response with invalid idea format
        {"choices": [{"message": {"content": json.dumps([{"invalid": "idea"}])}}]}
    ]
    idea_generator.openrouter_client = mock_client

    with pytest.raises(ValueError, match="missing required fields"):
        idea_generator.generate(
            initial_prompt_file="initial_prompt.txt",
            expand_prompt_file="expand_prompt.txt",
            list_prompt_file="list_prompt.txt",
            more_items_prompt_file="more_items_prompt.txt",
            output_file="test_ideas.json"
        )
