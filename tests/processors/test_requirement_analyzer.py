"""
Tests for the RequirementAnalyzer processor.
"""

import json
import os
import pytest
from unittest.mock import Mock

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
        "Product Idea": "Test Product",
        "Problem it solves": "Test Problem",
        "Software Techstack": ["Python", "React"],
        "Target hardware expectations": ["Cloud"],
        "Company profile": "Test Company",
        "Engineering profile": "Test Engineers"
    }

def test_format_prompt(requirement_analyzer, sample_idea):
    """Test prompt formatting."""
    template = "Requirements for: {THE_IDEA}"
    formatted = requirement_analyzer._format_prompt(sample_idea, template)
    
    # Verify all idea fields are included in the prompt
    assert "Test Product" in formatted
    assert "Test Problem" in formatted
    assert "Python" in formatted
    assert "React" in formatted
    assert "Cloud" in formatted
    assert "Test Company" in formatted
    assert "Test Engineers" in formatted

def test_analyze_idea_prompt_file_not_found(requirement_analyzer, sample_idea):
    """Test handling of missing prompt file."""
    requirement_analyzer.file_handler.create_output_directory()
    
    with pytest.raises(FileNotFoundError):
        requirement_analyzer.analyze_idea(
            sample_idea,
            prompt_file="nonexistent.txt"
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
