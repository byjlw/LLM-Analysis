"""
Pytest configuration and fixtures.
"""

import os
import shutil
import tempfile
from typing import Generator
import pytest

@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """
    Create a temporary directory for test files.
    
    Yields:
        Path to temporary directory
    """
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def test_output_dir(temp_dir: str) -> str:
    """
    Create a test output directory.
    
    Args:
        temp_dir: Temporary directory path
        
    Returns:
        Path to test output directory
    """
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

@pytest.fixture
def sample_json_data() -> dict:
    """
    Provide sample JSON data for testing.
    
    Returns:
        Dictionary containing sample data
    """
    return {
        "frameworks": [
            {"name": "torch", "count": 1},
            {"name": "tensorflow", "count": 2}
        ],
        "models": [
            {"name": "bert-base", "count": 1},
            {"name": "gpt2", "count": 1}
        ]
    }

@pytest.fixture
def sample_ideas_data() -> list:
    """
    Provide sample ideas data for testing.
    
    Returns:
        List containing sample ideas
    """
    return [
        {
            "Product Idea": "AI Assistant",
            "Problem it solves": "Task automation",
            "Software Techstack": ["Python", "FastAPI"],
            "Target hardware expectations": ["Cloud servers"],
            "Company profile": "SaaS",
            "Engineering profile": "Backend developers"
        },
        {
            "Product Idea": "Smart Analytics",
            "Problem it solves": "Data insights",
            "Software Techstack": ["Python", "React"],
            "Target hardware expectations": ["Web browsers"],
            "Company profile": "Enterprise",
            "Engineering profile": "Full-stack developers"
        }
    ]
