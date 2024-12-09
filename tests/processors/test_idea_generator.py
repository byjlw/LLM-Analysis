"""
Tests for the IdeaGenerator processor.
"""

import json
import os
import pytest
from unittest.mock import Mock, patch

from src.processors.idea_generator import IdeaGenerator
from src.utils.openrouter import OpenRouterClient
from src.utils.file_handler import FileHandler

@pytest.fixture
def sample_idea():
    """Sample idea data for testing."""
    return {
        "Product Idea": "Test Product",
        "Problem it solves": "Test Problem",
        "Software Techstack": ["Python", "React"],
        "Target hardware expectations": ["Cloud"],
        "Company profile": "Test Company",
        "Engineering profile": "Test Engineers"
    }

@pytest.fixture
def mock_openrouter(sample_idea):
    """Create a mock OpenRouter client."""
    mock = Mock(spec=OpenRouterClient)
    # Return a proper list of dictionaries that can be JSON serialized
    mock.generate_ideas.return_value = [sample_idea]
    return mock

@pytest.fixture
def idea_generator(mock_openrouter, temp_dir):
    """Create an IdeaGenerator instance with mocked dependencies."""
    file_handler = FileHandler(temp_dir)
    file_handler.create_output_directory()
    return IdeaGenerator(mock_openrouter, file_handler)

def test_validate_ideas_success(idea_generator, sample_idea):
    """Test successful idea validation."""
    assert idea_generator._validate_ideas([sample_idea]) is True

def test_validate_ideas_invalid_root(idea_generator):
    """Test validation with invalid root type."""
    assert idea_generator._validate_ideas({"not": "a list"}) is False

def test_validate_ideas_missing_field(idea_generator, sample_idea):
    """Test validation with missing required field."""
    invalid_idea = sample_idea.copy()
    del invalid_idea["Problem it solves"]
    assert idea_generator._validate_ideas([invalid_idea]) is False

def test_validate_ideas_invalid_techstack(idea_generator, sample_idea):
    """Test validation with invalid techstack type."""
    invalid_idea = sample_idea.copy()
    invalid_idea["Software Techstack"] = "Not a list"
    assert idea_generator._validate_ideas([invalid_idea]) is False

def test_validate_ideas_invalid_hardware(idea_generator, sample_idea):
    """Test validation with invalid hardware expectations type."""
    invalid_idea = sample_idea.copy()
    invalid_idea["Target hardware expectations"] = "Not a list"
    assert idea_generator._validate_ideas([invalid_idea]) is False

def test_generate_success(idea_generator, temp_dir, sample_idea):
    """Test successful idea generation."""
    # Create a test prompt file
    prompt_file = os.path.join(temp_dir, "test_prompt.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write("Test prompt")
    
    # Generate ideas
    output_path = idea_generator.generate(prompt_file=prompt_file)
    
    # Verify the output file exists
    assert os.path.exists(output_path)
    
    # Verify the content
    with open(output_path, "r", encoding="utf-8") as f:
        generated_ideas = json.load(f)
    
    assert len(generated_ideas) == 1
    assert generated_ideas[0]["Product Idea"] == sample_idea["Product Idea"]
    assert isinstance(generated_ideas[0]["Software Techstack"], list)

def test_generate_prompt_file_not_found(idea_generator):
    """Test handling of missing prompt file."""
    with pytest.raises(FileNotFoundError):
        idea_generator.generate(prompt_file="nonexistent.txt")

def test_generate_validation_failure(idea_generator, temp_dir):
    """Test handling of validation failure."""
    # Create a test prompt file
    prompt_file = os.path.join(temp_dir, "test_prompt.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write("Test prompt")
    
    # Mock OpenRouter to return invalid ideas
    idea_generator.openrouter_client.generate_ideas.return_value = [{"invalid": "structure"}]
    
    with pytest.raises(ValueError, match="Generated ideas failed validation"):
        idea_generator.generate(prompt_file=prompt_file)

def test_generate_file_write_error(idea_generator, temp_dir, sample_idea):
    """Test handling of file write errors."""
    # Create a test prompt file
    prompt_file = os.path.join(temp_dir, "test_prompt.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write("Test prompt")
    
    # Mock FileHandler's save_json to raise an error
    idea_generator.file_handler.save_json = Mock(side_effect=OSError("Test error"))
    
    with pytest.raises(OSError, match="Test error"):
        idea_generator.generate(prompt_file=prompt_file)

def test_generate_openrouter_error(idea_generator, temp_dir):
    """Test handling of OpenRouter API errors."""
    # Create a test prompt file
    prompt_file = os.path.join(temp_dir, "test_prompt.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write("Test prompt")
    
    # Mock OpenRouter to raise an error
    idea_generator.openrouter_client.generate_ideas.side_effect = ValueError("API error")
    
    with pytest.raises(ValueError, match="API error"):
        idea_generator.generate(prompt_file=prompt_file)
