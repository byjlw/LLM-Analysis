"""
Tests for the DependencyCollector processor.
"""

import json
import os
import pytest
from unittest.mock import Mock, patch
from collections import Counter

from src.processors.dependency_collector import DependencyCollector
from src.utils.file_handler import FileHandler

@pytest.fixture
def dependency_collector(temp_dir):
    """Create a DependencyCollector instance."""
    file_handler = FileHandler(temp_dir)
    return DependencyCollector(file_handler, None)  # No OpenRouter client needed for basic tests

@pytest.fixture
def sample_code():
    """Sample code content for testing."""
    return """
    import tensorflow as tf
    import numpy as np
    import pandas as pd
    
    def train_model():
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(128, activation='relu'),
            tf.keras.layers.Dense(1, activation='sigmoid')
        ])
        return model
    """

def test_validate_dependency_response(dependency_collector):
    """Test dependency response validation."""
    # Test single string
    assert dependency_collector._validate_dependency_response("tensorflow") == ["tensorflow"]
    
    # Test list of strings
    assert dependency_collector._validate_dependency_response(
        ["tensorflow", "numpy", "pandas"]
    ) == ["tensorflow", "numpy", "pandas"]
    
    # Test list of dicts with name field
    assert dependency_collector._validate_dependency_response([
        {"name": "tensorflow"},
        {"name": "numpy"}
    ]) == ["tensorflow", "numpy"]
    
    # Test wrapped in frameworks field
    assert dependency_collector._validate_dependency_response({
        "frameworks": ["tensorflow", "numpy"]
    }) == ["tensorflow", "numpy"]
    
    # Test list of strings
    assert dependency_collector._validate_dependency_response(
        ["tensorflow", "numpy"]
    ) == ["tensorflow", "numpy"]
    
    # Test invalid formats
    with pytest.raises(ValueError):
        dependency_collector._validate_dependency_response(123)

def test_analyze_file_no_client(dependency_collector, temp_dir, sample_code):
    """Test analyzing file without OpenRouter client."""
    # Create test code file
    code_file = os.path.join(temp_dir, "test_code.txt")
    with open(code_file, "w", encoding="utf-8") as f:
        f.write(sample_code)
        
    # Create test prompt file
    prompt_file = os.path.join(temp_dir, "test_prompt.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write("Test prompt")
        
    # Test without OpenRouter client
    result = dependency_collector.analyze_file(code_file, prompt_file)
    assert result == {"frameworks": set()}

def test_analyze_file_with_client(dependency_collector, temp_dir, sample_code):
    """Test analyzing file with OpenRouter client."""
    # Create test code file
    code_file = os.path.join(temp_dir, "test_code.txt")
    with open(code_file, "w", encoding="utf-8") as f:
        f.write(sample_code)
        
    # Create test prompt file
    prompt_file = os.path.join(temp_dir, "test_prompt.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write("Test prompt")
        
    # Mock OpenRouter client
    mock_client = Mock()
    mock_client._make_request.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps(["tensorflow", "numpy", "pandas"])
            }
        }]
    }
    dependency_collector.openrouter_client = mock_client
    
    result = dependency_collector.analyze_file(code_file, prompt_file)
    assert result == {"frameworks": {f.lower() for f in ["tensorflow", "numpy", "pandas"]}}

def test_analyze_directory(dependency_collector, temp_dir, sample_code):
    """Test analyzing directory of code files."""
    # Create test code files
    code_dir = os.path.join(temp_dir, "code")
    os.makedirs(code_dir)
    
    for i in range(3):
        with open(os.path.join(code_dir, f"test_{i}.txt"), "w", encoding="utf-8") as f:
            f.write(sample_code)
            
    # Create test prompt file
    prompt_file = os.path.join(temp_dir, "test_prompt.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write("Test prompt")
        
    # Mock OpenRouter client
    mock_client = Mock()
    mock_client._make_request.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps(["tensorflow", "numpy", "pandas"])
            }
        }]
    }
    dependency_collector.openrouter_client = mock_client
    
    result = dependency_collector.analyze_directory(code_dir, prompt_file)
    expected_counter = Counter({f.lower(): 3 for f in ["tensorflow", "numpy", "pandas"]})
    assert result == {"frameworks": expected_counter}

def test_normalize_dependency_data(dependency_collector):
    """Test normalizing dependency data."""
    # Create test data with framework counts
    counter = Counter({
        "tensorflow": 3,
        "numpy": 2,
        "pandas": 1
    })
    data = {
        "frameworks": counter
    }
    
    # Expected normalized format
    expected = {
        "frameworks": [
            {"name": "numpy", "count": 2},
            {"name": "pandas", "count": 1},
            {"name": "tensorflow", "count": 3}
        ]
    }
    
    result = dependency_collector._normalize_dependency_data(data)
    assert result == expected

def test_collect_all(dependency_collector, temp_dir, sample_code):
    """Test collecting all dependencies."""
    # Create test code directory
    code_dir = os.path.join(temp_dir, "code")
    os.makedirs(code_dir)
    
    # Create test code file
    with open(os.path.join(code_dir, "test.txt"), "w", encoding="utf-8") as f:
        f.write(sample_code)
        
    # Create test prompt file
    prompt_file = os.path.join(temp_dir, "test_prompt.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write("Test prompt")
        
    # Set up output directory
    dependency_collector.file_handler.create_output_directory()
    
    # Mock OpenRouter client
    mock_client = Mock()
    mock_client._make_request.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps(["tensorflow", "numpy", "pandas"])
            }
        }]
    }
    dependency_collector.openrouter_client = mock_client
    
    output_path = dependency_collector.collect_all(prompt_file)
    
    # Verify output file exists and contains correct data
    assert os.path.exists(output_path)
    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data == {
            "frameworks": [
                {"name": "numpy", "count": 1},
                {"name": "pandas", "count": 1},
                {"name": "tensorflow", "count": 1}
            ]
        }

def test_analyze_file_with_invalid_response(dependency_collector, temp_dir, sample_code):
    """Test analyzing file with invalid response format."""
    # Create test code file
    code_file = os.path.join(temp_dir, "test_code.txt")
    with open(code_file, "w", encoding="utf-8") as f:
        f.write(sample_code)
        
    # Create test prompt file
    prompt_file = os.path.join(temp_dir, "test_prompt.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write("Test prompt")
        
    # Mock OpenRouter client with invalid response
    mock_client = Mock()
    mock_client._make_request.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps({"invalid": "format"})
            }
        }]
    }
    dependency_collector.openrouter_client = mock_client
    
    # Should handle invalid format gracefully
    result = dependency_collector.analyze_file(code_file, prompt_file)
    assert result == {"frameworks": set()}
