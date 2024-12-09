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

def test_create_output_directory(temp_dir):
    """Test creation of output directory."""
    handler = FileHandler(temp_dir)
    output_dir = handler.create_output_directory()
    
    # Verify directory was created
    assert os.path.exists(output_dir)
    assert os.path.isdir(output_dir)
    
    # Verify timestamp format in directory name
    dir_name = os.path.basename(output_dir)
    try:
        datetime.strptime(dir_name, "%Y%m%d_%H%M%S")
    except ValueError:
        pytest.fail("Output directory name does not match expected timestamp format")
        
    # Verify current_output_dir was set
    assert handler.current_output_dir == output_dir

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

def test_update_dependencies_new_file(temp_dir):
    """Test updating dependencies in new file."""
    handler = FileHandler(temp_dir)
    handler.create_output_directory()
    
    new_deps = {
        "frameworks": ["pytorch"],
        "models": ["bert-base"]
    }
    
    output_path = handler.update_dependencies(new_deps)
    
    # Verify file exists
    assert os.path.exists(output_path)
    
    # Verify content structure
    with open(output_path, 'r', encoding='utf-8') as f:
        saved_data = json.load(f)
        
    assert "frameworks" in saved_data
    assert "models" in saved_data
    assert len(saved_data["frameworks"]) == 1
    assert saved_data["frameworks"][0]["name"] == "pytorch"
    assert saved_data["frameworks"][0]["count"] == 1

def test_update_dependencies_existing_file(temp_dir, sample_json_data):
    """Test updating existing dependencies file."""
    handler = FileHandler(temp_dir)
    handler.create_output_directory()
    
    # Save initial dependencies
    handler.save_json(sample_json_data, "dependencies.json")
    
    # Update with new dependencies
    new_deps = {
        "frameworks": ["torch"],  # Existing framework
        "models": ["gpt3"]  # New model
    }
    
    output_path = handler.update_dependencies(new_deps)
    
    # Verify content
    with open(output_path, 'r', encoding='utf-8') as f:
        updated_data = json.load(f)
        
    # Check torch count increased
    torch_framework = next(f for f in updated_data["frameworks"] if f["name"] == "torch")
    assert torch_framework["count"] == 2
    
    # Check new model was added
    assert any(m["name"] == "gpt3" and m["count"] == 1 for m in updated_data["models"])

def test_path_duplication_prevention(temp_dir):
    """Test prevention of path duplication."""
    handler = FileHandler(temp_dir)
    handler.create_output_directory()
    
    # Test with output directory in path
    path = handler.get_output_path(f"{temp_dir}/test.json")
    assert not path.startswith(f"{temp_dir}/{temp_dir}")
    
    # Test with timestamp directory in path
    timestamp_dir = os.path.basename(handler.current_output_dir)
    path = handler.get_output_path(f"{timestamp_dir}/test.json")
    assert path.count(timestamp_dir) == 1
