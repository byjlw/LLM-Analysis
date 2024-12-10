"""
Tests for the CodeGenerator processor.
"""

import json
import os
import pytest
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

def test_find_matching_idea(code_generator):
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
