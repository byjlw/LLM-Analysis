"""
Tests for the CodeGenerator processor.
"""

import json
import os
import pytest
from unittest.mock import Mock, patch, mock_open

from src.processors.code_generator import CodeGenerator
from src.utils.file_handler import FileHandler

@pytest.fixture
def code_generator(temp_dir):
    """Create a CodeGenerator instance."""
    file_handler = FileHandler(temp_dir)
    file_handler.create_output_directory()
    return CodeGenerator(file_handler, None)  # No OpenRouter client needed for validation tests

def test_normalize_string(code_generator):
    """Test string normalization for matching."""
    test_cases = [
        ("Voice-Activated Virtual Assistant", "voice_activated_virtual_assistant"),
        ("AI-Powered Chatbot", "ai_powered_chatbot"),
        ("Smart Home System 2.0", "smart_home_system_2_0"),
        ("Machine Learning @ Scale", "machine_learning_scale"),
        ("  Spaces  Around  ", "spaces_around"),
        ("MixedCaseExample", "mixedcaseexample"),
        ("multiple---dashes", "multiple_dashes"),
        ("special!@#$characters", "special_characters"),
    ]
    
    for input_str, expected in test_cases:
        assert code_generator._normalize_string(input_str) == expected

def test_load_ideas_file_not_found(code_generator, temp_dir):
    """Test loading ideas from non-existent file."""
    result = code_generator._load_ideas(os.path.join(temp_dir, "nonexistent.json"))
    assert result == []

def test_load_ideas_invalid_json(code_generator, temp_dir):
    """Test loading ideas from invalid JSON file."""
    # Create invalid JSON file
    ideas_file = os.path.join(temp_dir, "invalid.json")
    with open(ideas_file, "w") as f:
        f.write("invalid json")
    
    result = code_generator._load_ideas(ideas_file)
    assert result == []

def test_load_ideas_success(code_generator, temp_dir):
    """Test successful ideas loading."""
    # Create valid JSON file
    ideas = [{"Idea": "Test", "Details": "Details"}]
    ideas_file = os.path.join(temp_dir, "ideas.json")
    with open(ideas_file, "w") as f:
        json.dump(ideas, f)
    
    result = code_generator._load_ideas(ideas_file)
    assert result == ideas

def test_find_matching_idea(code_generator):
    """Test finding matching ideas from requirements files."""
    # Create test ideas
    ideas = [
        {"Idea": "Voice-Activated Virtual Assistant"},
        {"Idea": "AI-Powered Chatbot"},
        {"Idea": "Smart Home System"}
    ]
    
    # Test exact match
    match = code_generator._find_matching_idea(
        ideas, 
        "requirements_voice_activated_virtual_assistant.txt"
    )
    assert match is not None
    assert match["Idea"] == "Voice-Activated Virtual Assistant"
    
    # Test case insensitive match
    match = code_generator._find_matching_idea(
        ideas, 
        "requirements_AI_POWERED_CHATBOT.txt"
    )
    assert match is not None
    assert match["Idea"] == "AI-Powered Chatbot"
    
    # Test with special characters
    match = code_generator._find_matching_idea(
        ideas, 
        "requirements_smart-home-system.txt"
    )
    assert match is not None
    assert match["Idea"] == "Smart Home System"
    
    # Test no match
    match = code_generator._find_matching_idea(
        ideas, 
        "requirements_nonexistent_product.txt"
    )
    assert match is None

def test_find_matching_idea_invalid_filename(code_generator):
    """Test finding matching idea with invalid filename format."""
    ideas = [{"Idea": "Test"}]
    match = code_generator._find_matching_idea(ideas, "invalid_filename.txt")
    assert match is None

def test_find_matching_idea_empty_ideas(code_generator):
    """Test finding matching idea with empty ideas list."""
    match = code_generator._find_matching_idea([], "requirements_test.txt")
    assert match is None

def test_generate_code_for_idea_missing_requirements(code_generator, temp_dir):
    """Test code generation with missing requirements file."""
    idea = {"Idea": "Test"}
    result = code_generator._generate_code_for_idea(
        idea=idea,
        requirements_path=os.path.join(temp_dir, "nonexistent.txt"),
        initial_prompt_file="initial.txt",
        writer_prompt_file="writer.txt",
        code_dir=temp_dir
    )
    assert not result

def test_generate_code_for_idea_missing_prompts(code_generator, temp_dir):
    """Test code generation with missing prompt files."""
    # Create requirements file
    req_file = os.path.join(temp_dir, "requirements.txt")
    with open(req_file, "w") as f:
        f.write("Test requirements")
    
    idea = {"Idea": "Test"}
    result = code_generator._generate_code_for_idea(
        idea=idea,
        requirements_path=req_file,
        initial_prompt_file="nonexistent_initial.txt",
        writer_prompt_file="nonexistent_writer.txt",
        code_dir=temp_dir
    )
    assert not result

def test_generate_validation_error(code_generator):
    """Test generate with missing prompt files."""
    with pytest.raises(ValueError, match="Both prompt files must be provided"):
        code_generator.generate(None, None)

def test_generate_no_output_dir(code_generator):
    """Test generate without output directory."""
    # Create a new code generator without output directory
    code_generator = CodeGenerator(FileHandler(None), None)
    result = code_generator.generate("initial.txt", "writer.txt")
    assert not result

def test_generate_with_missing_files(code_generator, temp_dir):
    """Test code generation with missing files."""
    # Test with missing ideas file
    result = code_generator.generate(
        initial_prompt_file="initial.txt",
        writer_prompt_file="writer.txt",
        ideas_file="nonexistent.json"
    )
    assert not result
    
    # Test with missing requirements directory
    ideas_file = os.path.join(temp_dir, "ideas.json")
    with open(ideas_file, 'w', encoding='utf-8') as f:
        json.dump([{"Idea": "Test"}], f)
    
    result = code_generator.generate(
        initial_prompt_file="initial.txt",
        writer_prompt_file="writer.txt",
        ideas_file=ideas_file
    )
    assert not result
