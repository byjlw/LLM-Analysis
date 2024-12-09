"""
Tests for the DependencyCollector processor.
"""

import json
import os
from collections import Counter
import pytest
from src.processors.dependency_collector import DependencyCollector
from src.utils.file_handler import FileHandler

@pytest.fixture
def dependency_collector(temp_dir):
    """Create a DependencyCollector instance."""
    file_handler = FileHandler(temp_dir)
    file_handler.create_output_directory()
    return DependencyCollector(file_handler)

def test_extract_python_imports(dependency_collector, temp_dir):
    """Test extraction of Python imports."""
    code = """
import torch
import tensorflow as tf
from transformers import AutoModel
import os
import sys
"""
    filepath = os.path.join(temp_dir, "test.py")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(code)
        
    imports = dependency_collector._extract_python_imports(code, filepath)
    
    # Test core functionality: extracting base module names
    assert len(imports) >= 3  # Should find at least torch, tensorflow, transformers
    assert "torch" in imports
    assert "tensorflow" in imports
    assert "transformers" in imports

def test_extract_js_imports(dependency_collector, temp_dir):
    """Test extraction of JavaScript imports."""
    code = """
import { model } from '@tensorflow/tfjs';
import '@tensorflow/tfjs-backend-webgl';
const someLib = require('some-lib');
"""
    filepath = os.path.join(temp_dir, "test.js")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(code)
        
    imports = dependency_collector._extract_js_imports(code, filepath)
    
    # Test core functionality: extracting package names
    assert len(imports) >= 2  # Should find tensorflow and some-lib
    assert "tensorflow" in imports
    assert "some-lib" in imports

def test_extract_model_references(dependency_collector, temp_dir):
    """Test extraction of model references."""
    code = """
# Python model loading patterns
model = AutoModel.from_pretrained("test-model-1")
model = load_model("test-model-2")
model = tf.keras.models.load_model("test-model-3")
model = torch.load("test-model-4")

# JavaScript model loading patterns
model = await tf.loadLayersModel("test-model-5")
const model2 = await tf.loadGraphModel("test-model-6")
model.load("test-model-7")
"""
    filepath = os.path.join(temp_dir, "test.py")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(code)
        
    models = dependency_collector._extract_model_references(code, filepath)
    
    # Test that model references are detected
    assert len(models) >= 3  # Should find multiple test models
    assert any("test-model" in model for model in models)

def test_analyze_file_python(dependency_collector, temp_dir):
    """Test analysis of a Python file."""
    code = """
import torch
import tensorflow as tf
from transformers import AutoModel

model = AutoModel.from_pretrained("test-model-1")
model = tf.keras.models.load_model("test-model-2")
model = torch.load("test-model-3")
"""
    filepath = os.path.join(temp_dir, "test.py")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(code)
        
    results = dependency_collector.analyze_file(filepath)
    
    # Test that both frameworks and models are detected
    assert len(results["frameworks"]) >= 2  # Should find multiple frameworks
    assert len(results["models"]) >= 2  # Should find multiple models
    assert "torch" in results["frameworks"]
    assert "tensorflow" in results["frameworks"]
    assert any("test-model" in model for model in results["models"])

def test_analyze_file_javascript(dependency_collector, temp_dir):
    """Test analysis of a JavaScript file."""
    code = """
import * as tf from '@tensorflow/tfjs';
const model = await tf.loadLayersModel('test-model-1');
const model2 = await tf.loadGraphModel('test-model-2');
model.load('test-model-3');

// Additional model loading patterns
const model3 = await tf.loadGraphModel('test-model-4');
await model.load('test-model-5');
"""
    filepath = os.path.join(temp_dir, "test.js")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(code)
        
    results = dependency_collector.analyze_file(filepath)
    
    # Test that frameworks and models are detected in JS
    assert len(results["frameworks"]) >= 1  # Should find tensorflow
    assert len(results["models"]) >= 2  # Should find multiple models
    assert "tensorflow" in results["frameworks"]
    assert any("test-model" in model for model in results["models"])

def test_analyze_directory(dependency_collector, temp_dir):
    """Test analysis of a directory with multiple files."""
    code_dir = os.path.join(temp_dir, "code")
    os.makedirs(code_dir)
    
    # Create multiple files with different patterns
    files = {
        "model1.py": """
import torch
model = torch.load("test-model-1")
model = torch.hub.load("test-model-2")
""",
        "model2.py": """
import tensorflow as tf
model = tf.keras.models.load_model("test-model-3")
model = tf.saved_model.load("test-model-4")
""",
        "model3.js": """
import * as tf from '@tensorflow/tfjs';
const model = await tf.loadLayersModel('test-model-5');
const model2 = await tf.loadGraphModel('test-model-6');
await model.load('test-model-7');
"""
    }
    
    for filename, content in files.items():
        with open(os.path.join(code_dir, filename), 'w', encoding='utf-8') as f:
            f.write(content)
    
    results = dependency_collector.analyze_directory(code_dir)
    
    # Test that analysis finds frameworks and models across files
    assert len(results["frameworks"]) >= 2  # Should find multiple frameworks
    assert len(results["models"]) >= 4  # Should find multiple models
    assert results["frameworks"]["tensorflow"] > 0  # Common framework across files
    assert any("test-model" in model for model in results["models"])

def test_collect_all_no_output_dir(dependency_collector):
    """Test handling of missing output directory."""
    dependency_collector.file_handler.current_output_dir = None
    
    with pytest.raises(ValueError, match="No output directory has been created"):
        dependency_collector.collect_all()

def test_collect_all_invalid_code_dir(dependency_collector):
    """Test handling of invalid code directory path."""
    # Try to use a path outside the output directory
    invalid_dir = "/path/that/does/not/exist"
    
    with pytest.raises(ValueError, match="Invalid code directory path"):
        dependency_collector.collect_all(invalid_dir)

def test_collect_all_empty_directory(dependency_collector):
    """Test handling of empty code directory."""
    # Create a code directory within the output directory
    code_dir = os.path.join(dependency_collector.file_handler.current_output_dir, "code")
    
    output_path = dependency_collector.collect_all(code_dir)
    
    with open(output_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    assert len(data["frameworks"]) == 0
    assert len(data["models"]) == 0
