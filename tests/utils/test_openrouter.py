"""
Tests for the OpenRouter API client.
"""

import json
import pytest
import requests
from unittest.mock import Mock, patch, PropertyMock

from src.utils.openrouter import OpenRouterClient

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
def openrouter_client():
    """Create an OpenRouter client for testing."""
    return OpenRouterClient(
        api_key="test_key",
        default_model="test-model",
        timeout=10,
        max_retries=2
    )

@patch('requests.post')
def test_make_request_success(mock_post, openrouter_client):
    """Test successful API request."""
    mock_response = Mock()
    mock_response.json.return_value = {"choices": [{"message": {"content": "test"}}]}
    mock_post.return_value = mock_response
    
    response = openrouter_client._make_request("test prompt")
    assert response["choices"][0]["message"]["content"] == "test"

@patch('requests.post')
def test_make_request_retry(mock_post, openrouter_client):
    """Test request retry on failure."""
    # Create mock responses
    mock_fail = Mock()
    mock_fail_response = Mock()
    type(mock_fail_response).text = PropertyMock(return_value='{"error": "timeout"}')
    mock_fail.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_fail_response)
    
    mock_success = Mock()
    mock_success.json.return_value = {"choices": [{"message": {"content": "test"}}]}
    
    # Set up mock post to fail first, then succeed
    mock_post.side_effect = [mock_fail, mock_success]
    
    response = openrouter_client._make_request("test prompt")
    assert response["choices"][0]["message"]["content"] == "test"
    assert mock_post.call_count == 2
