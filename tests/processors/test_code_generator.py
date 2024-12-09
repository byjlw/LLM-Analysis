"""
Tests for the CodeGenerator processor.
"""

import json
import os
import pytest
from unittest.mock import Mock
from src.processors.code_generator import CodeGenerator
from src.utils.file_handler import FileHandler
from src.utils.openrouter import OpenRouterClient

@pytest.fixture
def code_generator(temp_dir):
    """Create a CodeGenerator instance."""
    file_handler = FileHandler(temp_dir)
    file_handler.create_output_directory()
    openrouter_client = Mock(spec=OpenRouterClient)
    return CodeGenerator(file_handler, openrouter_client)

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

def test_find_matching_idea(code_generator, temp_dir):
    """Test finding matching ideas from requirements files."""
    # Create test ideas
    ideas = [
        {"Product Idea": "Voice-Activated Virtual Assistant"},
        {"Product Idea": "AI-Powered Chatbot"},
        {"Product Idea": "Smart Home System"}
    ]
    
    # Test exact match
    match = code_generator._find_matching_idea(
        ideas, 
        "requirements_voice_activated_virtual_assistant.txt"
    )
    assert match is not None
    assert match["Product Idea"] == "Voice-Activated Virtual Assistant"
    
    # Test case insensitive match
    match = code_generator._find_matching_idea(
        ideas, 
        "requirements_AI_POWERED_CHATBOT.txt"
    )
    assert match is not None
    assert match["Product Idea"] == "AI-Powered Chatbot"
    
    # Test with special characters
    match = code_generator._find_matching_idea(
        ideas, 
        "requirements_smart-home-system.txt"
    )
    assert match is not None
    assert match["Product Idea"] == "Smart Home System"
    
    # Test no match
    match = code_generator._find_matching_idea(
        ideas, 
        "requirements_nonexistent_product.txt"
    )
    assert match is None

def test_generate_with_matching_requirements(code_generator, temp_dir):
    """Test code generation with matching requirements and ideas."""
    # Create test ideas file
    ideas = [
        {
            "Product Idea": "Voice-Activated Virtual Assistant",
            "Problem it solves": "Helps users with voice commands",
            "Software Techstack": ["Python", "Flask"]
        }
    ]
    ideas_file = os.path.join(temp_dir, "ideas.json")
    with open(ideas_file, 'w', encoding='utf-8') as f:
        json.dump(ideas, f)
    
    # Create test requirements file
    requirements_dir = os.path.join(code_generator.file_handler.current_output_dir, "requirements")
    os.makedirs(requirements_dir)
    requirements_file = os.path.join(requirements_dir, "requirements_voice_activated_virtual_assistant.txt")
    with open(requirements_file, 'w', encoding='utf-8') as f:
        f.write("Test requirements")
    
    # Mock code generation
    code_generator.openrouter_client.generate_code.return_value = "Test code"
    
    # Run generation
    success = code_generator.generate(ideas_file)
    assert success
    
    # Verify code file was created
    code_dir = os.path.join(code_generator.file_handler.current_output_dir, "code")
    code_file = os.path.join(code_dir, "voice_activated_virtual_assistant.py")
    assert os.path.exists(code_file)
    
    # Verify file contents
    with open(code_file, 'r', encoding='utf-8') as f:
        content = f.read()
    assert content == "Test code"

def test_generate_with_no_matching_requirements(code_generator, temp_dir):
    """Test code generation with no matching requirements."""
    # Create test ideas file
    ideas = [
        {
            "Product Idea": "Voice-Activated Virtual Assistant",
            "Problem it solves": "Helps users with voice commands",
            "Software Techstack": ["Python", "Flask"]
        }
    ]
    ideas_file = os.path.join(temp_dir, "ideas.json")
    with open(ideas_file, 'w', encoding='utf-8') as f:
        json.dump(ideas, f)
    
    # Create test requirements file with non-matching name
    requirements_dir = os.path.join(code_generator.file_handler.current_output_dir, "requirements")
    os.makedirs(requirements_dir)
    requirements_file = os.path.join(requirements_dir, "requirements_nonexistent_product.txt")
    with open(requirements_file, 'w', encoding='utf-8') as f:
        f.write("Test requirements")
    
    # Run generation
    success = code_generator.generate(ideas_file)
    assert not success  # Should fail because no matching idea was found

def test_generate_with_missing_files(code_generator, temp_dir):
    """Test code generation with missing files."""
    # Test with missing ideas file
    success = code_generator.generate("nonexistent.json")
    assert not success
    
    # Test with missing requirements directory
    ideas_file = os.path.join(temp_dir, "ideas.json")
    with open(ideas_file, 'w', encoding='utf-8') as f:
        json.dump([{"Product Idea": "Test"}], f)
    
    success = code_generator.generate(ideas_file)
    assert not success
