"""
Tests for the IdeaGenerator processor.
"""

import json
import os
import pytest
from unittest.mock import Mock

from src.processors.idea_generator import IdeaGenerator
from src.utils.file_handler import FileHandler

@pytest.fixture
def sample_idea():
    """Sample idea data for testing."""
    return {
        "Product Idea": "Test Product",
        "Problem it solves": "Test Problem",
        "Software Techstack": ["Python", "React"],
        "Target hardware expectations": ["Cloud"],
        "Company profile": "Test Company",
        "Engineering profile": "Test Engineers"
    }

@pytest.fixture
def idea_generator(temp_dir):
    """Create an IdeaGenerator instance."""
    file_handler = FileHandler(temp_dir)
    file_handler.create_output_directory()
    return IdeaGenerator(file_handler, None)  # No OpenRouter client needed for validation tests

def test_validate_ideas_success(idea_generator, sample_idea):
    """Test successful idea validation."""
    assert idea_generator._validate_ideas([sample_idea]) is True

def test_validate_ideas_invalid_root(idea_generator):
    """Test validation with invalid root type."""
    assert idea_generator._validate_ideas({"not": "a list"}) is False

def test_validate_ideas_missing_field(idea_generator, sample_idea):
    """Test validation with missing required field."""
    invalid_idea = sample_idea.copy()
    del invalid_idea["Problem it solves"]
    assert idea_generator._validate_ideas([invalid_idea]) is False

def test_validate_ideas_invalid_techstack(idea_generator, sample_idea):
    """Test validation with invalid techstack type."""
    invalid_idea = sample_idea.copy()
    invalid_idea["Software Techstack"] = "Not a list"
    assert idea_generator._validate_ideas([invalid_idea]) is False

def test_validate_ideas_invalid_hardware(idea_generator, sample_idea):
    """Test validation with invalid hardware expectations type."""
    invalid_idea = sample_idea.copy()
    invalid_idea["Target hardware expectations"] = "Not a list"
    assert idea_generator._validate_ideas([invalid_idea]) is False
