"""
Tests for the RequirementAnalyzer processor.
"""

import json
import os
import pytest
from unittest.mock import Mock

from src.processors.requirement_analyzer import RequirementAnalyzer
from src.utils.openrouter import OpenRouterClient
from src.utils.file_handler import FileHandler

@pytest.fixture
def mock_openrouter():
    """Create a mock OpenRouter client."""
    mock = Mock(spec=OpenRouterClient)
    mock.generate_requirements.return_value = "Test requirements content"
    return mock

@pytest.fixture
def requirement_analyzer(mock_openrouter, temp_dir):
    """Create a RequirementAnalyzer instance with mocked dependencies."""
    file_handler = FileHandler(temp_dir)
    return RequirementAnalyzer(mock_openrouter, file_handler)

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
    template = "Requirements for: THE IDEA"
    formatted = requirement_analyzer._format_prompt(sample_idea, template)
    
    # Verify all idea fields are included in the prompt
    assert "Test Product" in formatted
    assert "Test Problem" in formatted
    assert "Python" in formatted
    assert "React" in formatted
    assert "Cloud" in formatted
    assert "Test Company" in formatted
    assert "Test Engineers" in formatted

def test_analyze_idea_success(requirement_analyzer, sample_idea, temp_dir):
    """Test successful requirement generation for a single idea."""
    # Create output directory
    requirement_analyzer.file_handler.create_output_directory()
    
    # Create a test prompt file
    prompt_file = os.path.join(temp_dir, "test_prompt.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write("Requirements for: THE IDEA")
    
    # Create output directory for requirements
    output_dir = os.path.join(temp_dir, "requirements")
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate requirements
    requirements = requirement_analyzer.analyze_idea(
        sample_idea,
        prompt_file=prompt_file,
        output_dir=output_dir
    )
    
    assert requirements == "Test requirements content"
    
    # Verify file was created
    expected_filename = f"requirements_test_product.txt"
    expected_path = os.path.join(output_dir, expected_filename)
    assert os.path.exists(expected_path)
    
    # Verify file content
    with open(expected_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert content == "Test requirements content"

def test_analyze_idea_prompt_file_not_found(requirement_analyzer, sample_idea):
    """Test handling of missing prompt file."""
    requirement_analyzer.file_handler.create_output_directory()
    
    with pytest.raises(FileNotFoundError):
        requirement_analyzer.analyze_idea(
            sample_idea,
            prompt_file="nonexistent.txt"
        )

def test_analyze_idea_api_error(requirement_analyzer, sample_idea, temp_dir):
    """Test handling of API errors."""
    requirement_analyzer.file_handler.create_output_directory()
    
    # Create a test prompt file
    prompt_file = os.path.join(temp_dir, "test_prompt.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write("Requirements for: THE IDEA")
    
    # Mock API error
    requirement_analyzer.openrouter_client.generate_requirements.side_effect = ValueError("API error")
    
    with pytest.raises(ValueError, match="API error"):
        requirement_analyzer.analyze_idea(sample_idea, prompt_file=prompt_file)

def test_analyze_all_success(requirement_analyzer, sample_idea, temp_dir):
    """Test successful analysis of all ideas."""
    # Create output directory
    requirement_analyzer.file_handler.create_output_directory()
    
    # Create ideas.json
    ideas = [sample_idea, {**sample_idea, "Product Idea": "Test Product 2"}]
    ideas_path = os.path.join(requirement_analyzer.file_handler.current_output_dir, "ideas.json")
    with open(ideas_path, "w", encoding="utf-8") as f:
        json.dump(ideas, f)
    
    # Create prompt file
    prompt_file = os.path.join(temp_dir, "test_prompt.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write("Requirements for: THE IDEA")
    
    # Generate requirements
    requirements = requirement_analyzer.analyze_all(
        ideas_file="ideas.json",
        prompt_file=prompt_file
    )
    
    assert len(requirements) == 2
    assert all(req == "Test requirements content" for req in requirements)
    
    # Verify files were created
    requirements_dir = os.path.join(requirement_analyzer.file_handler.current_output_dir, "requirements")
    assert os.path.exists(requirements_dir)
    assert len(os.listdir(requirements_dir)) == 2

def test_analyze_all_ideas_file_not_found(requirement_analyzer, temp_dir):
    """Test handling of missing ideas file."""
    requirement_analyzer.file_handler.create_output_directory()
    
    # Create prompt file
    prompt_file = os.path.join(temp_dir, "test_prompt.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write("Requirements for: THE IDEA")
    
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
        f.write("Requirements for: THE IDEA")
    
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
        f.write("Requirements for: THE IDEA")
    
    with pytest.raises(ValueError, match="No output directory has been created"):
        requirement_analyzer.analyze_all(
            ideas_file="ideas.json",
            prompt_file=prompt_file
        )
