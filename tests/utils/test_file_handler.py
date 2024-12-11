"""
Tests for the FileHandler utility class.
"""

import json
import os
from datetime import datetime
import pytest
from src.utils.file_handler import FileHandler

def test_init_file_handler():
    """Test FileHandler initialization."""
    handler = FileHandler("test_output")
    assert handler.base_output_dir == "test_output"
    assert handler.current_output_dir is None

def test_get_output_path_without_directory():
    """Test get_output_path when no directory has been created."""
    handler = FileHandler("test_output")
    with pytest.raises(ValueError, match="No output directory has been created"):
        handler.get_output_path("test.json")

def test_get_output_path(temp_dir):
    """Test getting output file path."""
    handler = FileHandler(temp_dir)
    handler.create_output_directory()
    
    # Test simple filename
    path = handler.get_output_path("test.json")
    assert path.endswith("test.json")
    assert path.startswith(handler.current_output_dir)
    
    # Test nested path
    path = handler.get_output_path("subdir/test.json")
    assert path.endswith("subdir/test.json")
    assert path.startswith(handler.current_output_dir)

def test_save_json(temp_dir, sample_json_data):
    """Test saving JSON data."""
    handler = FileHandler(temp_dir)
    handler.create_output_directory()
    
    # Save JSON data
    output_path = handler.save_json(sample_json_data, "test.json")
    
    # Verify file exists
    assert os.path.exists(output_path)
    
    # Verify content
    with open(output_path, 'r', encoding='utf-8') as f:
        saved_data = json.load(f)
    assert saved_data == sample_json_data

def test_load_json(temp_dir, sample_json_data):
    """Test loading JSON data."""
    handler = FileHandler(temp_dir)
    handler.create_output_directory()
    
    # Save and then load JSON data
    output_path = handler.save_json(sample_json_data, "test.json")
    loaded_data = handler.load_json(output_path)
    
    assert loaded_data == sample_json_data

def test_load_json_file_not_found(temp_dir):
    """Test loading non-existent JSON file."""
    handler = FileHandler(temp_dir)
    handler.create_output_directory()
    
    with pytest.raises(FileNotFoundError):
        handler.load_json("nonexistent.json")

def test_load_json_invalid_json(temp_dir):
    """Test loading invalid JSON file."""
    handler = FileHandler(temp_dir)
    handler.create_output_directory()
    
    # Create invalid JSON file
    invalid_path = os.path.join(handler.current_output_dir, "invalid.json")
    with open(invalid_path, 'w', encoding='utf-8') as f:
        f.write("invalid json content")
        
    with pytest.raises(json.JSONDecodeError):
        handler.load_json(invalid_path)
