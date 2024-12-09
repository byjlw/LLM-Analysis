"""
Tests for the DependencyCollector processor.
"""

import json
import os
from collections import Counter
import pytest
from unittest.mock import Mock
from src.processors.dependency_collector import DependencyCollector
from src.utils.file_handler import FileHandler

@pytest.fixture
def mock_openrouter():
    """Create a mock OpenRouter client."""
    client = Mock()
    client.collect_dependencies.return_value = {"frameworks": ["Flask", "SQLAlchemy"]}
    return client

@pytest.fixture
def dependency_collector(temp_dir, mock_openrouter):
    """Create a DependencyCollector instance."""
    file_handler = FileHandler(temp_dir)
    file_handler.create_output_directory()
    return DependencyCollector(file_handler, mock_openrouter)

def test_analyze_file(dependency_collector, temp_dir):
    """Test analysis of a file using LLM."""
    code = """
from flask import Flask
from sqlalchemy import create_engine

app = Flask(__name__)
engine = create_engine('sqlite:///test.db')
"""
    filepath = os.path.join(temp_dir, "test.txt")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(code)
        
    results = dependency_collector.analyze_file(filepath)
    
    # Test that frameworks are detected via LLM
    assert len(results["frameworks"]) == 2
    assert "Flask" in results["frameworks"]
    assert "SQLAlchemy" in results["frameworks"]

def test_analyze_file_no_llm(temp_dir):
    """Test analysis of a file without LLM client."""
    file_handler = FileHandler(temp_dir)
    file_handler.create_output_directory()
    collector = DependencyCollector(file_handler)  # No OpenRouter client
    
    code = """
from flask import Flask
from sqlalchemy import create_engine

app = Flask(__name__)
engine = create_engine('sqlite:///test.db')
"""
    filepath = os.path.join(temp_dir, "test.txt")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(code)
        
    results = collector.analyze_file(filepath)
    
    # Should return empty set when no LLM client
    assert len(results["frameworks"]) == 0

def test_analyze_directory(dependency_collector, temp_dir):
    """Test analysis of a directory with multiple files."""
    code_dir = os.path.join(temp_dir, "code")
    os.makedirs(code_dir)
    
    # Create multiple files
    files = {
        "app1.txt": """
from flask import Flask
app = Flask(__name__)
""",
        "app2.txt": """
from django.http import HttpResponse
def index(request):
    return HttpResponse("Hello")
""",
        "not_code.log": """
This is a log file that should be ignored
"""
    }
    
    for filename, content in files.items():
        with open(os.path.join(code_dir, filename), 'w', encoding='utf-8') as f:
            f.write(content)
    
    results = dependency_collector.analyze_directory(code_dir)
    
    # Test that analysis finds frameworks across .txt files
    assert len(results["frameworks"]) >= 1
    assert results["frameworks"]["Flask"] > 0
    assert results["frameworks"]["SQLAlchemy"] > 0

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

def test_normalize_dependency_data(dependency_collector):
    """Test normalization of dependency data."""
    counter = Counter({"Flask": 2, "SQLAlchemy": 1})
    data = {"frameworks": counter}
    
    normalized = dependency_collector._normalize_dependency_data(data)
    
    assert len(normalized["frameworks"]) == 2
    assert normalized["frameworks"][0]["name"] == "Flask"
    assert normalized["frameworks"][0]["count"] == 2
    assert normalized["frameworks"][1]["name"] == "SQLAlchemy"
    assert normalized["frameworks"][1]["count"] == 1
