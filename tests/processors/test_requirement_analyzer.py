"""
Tests for the RequirementAnalyzer processor.
"""

import json
import os
import pytest
from unittest.mock import Mock, patch

from src.processors.requirement_analyzer import RequirementAnalyzer
from src.utils.file_handler import FileHandler

@pytest.fixture
def requirement_analyzer(temp_dir):
    """Create a RequirementAnalyzer instance."""
    file_handler = FileHandler(temp_dir)
    return RequirementAnalyzer(None, file_handler)  # No OpenRouter client needed for validation tests

@pytest.fixture
def sample_idea():
    """Provide a sample idea for testing."""
    return {
        "Idea": "Test Product",
        "Details": "A test product that solves test problems"
    }

def test_format_prompt(requirement_analyzer, sample_idea):
    """Test prompt formatting."""
    template = "Requirements for: {THE_IDEA}"
    formatted = requirement_analyzer._format_prompt(sample_idea, template)
    assert formatted == f"Requirements for: {sample_idea['Details']}"

def test_format_prompt_missing_placeholder(requirement_analyzer, sample_idea):
    """Test prompt formatting without placeholder."""
    template = "Requirements without placeholder"
    formatted = requirement_analyzer._format_prompt(sample_idea, template)
    assert formatted == template

def test_format_prompt_multiple_placeholders(requirement_analyzer, sample_idea):
    """Test prompt formatting with multiple placeholders."""
    template = "{THE_IDEA} and {THE_IDEA} again"
    formatted = requirement_analyzer._format_prompt(sample_idea, template)
    assert formatted == f"{sample_idea['Details']} and {sample_idea['Details']} again"

def test_analyze_idea_prompt_file_not_found(requirement_analyzer, sample_idea):
    """Test handling of missing prompt file."""
    requirement_analyzer.file_handler.create_output_directory()
    
    with pytest.raises(FileNotFoundError):
        requirement_analyzer.analyze_idea(
            sample_idea,
            prompt_file="nonexistent.txt"
        )

def test_analyze_idea_invalid_idea(requirement_analyzer, temp_dir):
    """Test analyzing idea with missing required fields."""
    # Create prompt file
    prompt_file = os.path.join(temp_dir, "prompt.txt")
    with open(prompt_file, "w") as f:
        f.write("Test prompt")
    
    invalid_idea = {"Idea": "Test"}  # Missing Details field
    with pytest.raises(KeyError):
        requirement_analyzer.analyze_idea(invalid_idea, prompt_file)

def test_process_idea_parallel_error(requirement_analyzer, temp_dir):
    """Test parallel processing with error."""
    # Create prompt file
    prompt_file = os.path.join(temp_dir, "prompt.txt")
    with open(prompt_file, "w") as f:
        f.write("Test prompt")
    
    # Test with invalid idea
    invalid_idea = {"Idea": "Test"}  # Missing Details field
    args = (invalid_idea, prompt_file, temp_dir)
    result = requirement_analyzer._process_idea_parallel(args)
    assert result == ""

def test_analyze_all_no_prompt_file(requirement_analyzer):
    """Test analyze_all without prompt file."""
    with pytest.raises(ValueError, match="prompt_file must be provided"):
        requirement_analyzer.analyze_all(prompt_file=None)

def test_analyze_all_no_output_dir(requirement_analyzer, temp_dir):
    """Test handling of missing output directory."""
    # Create prompt file
    prompt_file = os.path.join(temp_dir, "test_prompt.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write("Requirements for: {THE_IDEA}")
    
    with pytest.raises(ValueError, match="No output directory has been created"):
        requirement_analyzer.analyze_all(
            ideas_file="ideas.json",
            prompt_file=prompt_file
        )

def test_analyze_all_ideas_file_not_found(requirement_analyzer, temp_dir):
    """Test handling of missing ideas file."""
    requirement_analyzer.file_handler.create_output_directory()
    
    # Create prompt file
    prompt_file = os.path.join(temp_dir, "test_prompt.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write("Requirements for: {THE_IDEA}")
    
    with pytest.raises(FileNotFoundError):
        requirement_analyzer.analyze_all(
            ideas_file="nonexistent.json",
            prompt_file=prompt_file
        )

def test_analyze_all_invalid_ideas_json(requirement_analyzer, temp_dir):
    """Test handling of invalid ideas JSON."""
    requirement_analyzer.file_handler.create_output_directory()
    
    # Create invalid ideas.json
    ideas_path = os.path.join(requirement_analyzer.file_handler.current_output_dir, "ideas.json")
    with open(ideas_path, "w", encoding="utf-8") as f:
        f.write("invalid json")
    
    # Create prompt file
    prompt_file = os.path.join(temp_dir, "test_prompt.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write("Requirements for: {THE_IDEA}")
    
    with pytest.raises(json.JSONDecodeError):
        requirement_analyzer.analyze_all(
            ideas_file="ideas.json",
            prompt_file=prompt_file
        )

def test_analyze_all_empty_ideas(requirement_analyzer, temp_dir):
    """Test analyzing empty ideas list."""
    requirement_analyzer.file_handler.create_output_directory()
    
    # Create empty ideas.json
    ideas_path = os.path.join(requirement_analyzer.file_handler.current_output_dir, "ideas.json")
    with open(ideas_path, "w", encoding="utf-8") as f:
        json.dump([], f)
    
    # Create prompt file
    prompt_file = os.path.join(temp_dir, "test_prompt.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write("Requirements for: {THE_IDEA}")
    
    result = requirement_analyzer.analyze_all(
        ideas_file="ideas.json",
        prompt_file=prompt_file
    )
    assert result == []
