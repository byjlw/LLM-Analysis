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

def test_clean_json_string(openrouter_client):
    """Test JSON string cleaning."""
    # Test markdown code block
    markdown = "```json\n{\"test\": \"value\"}\n```"
    cleaned = openrouter_client._clean_json_string(markdown)
    assert cleaned == '{"test": "value"}'
    
    # Test with leading text
    text_with_json = 'Here is the JSON: ["item1", "item2"]'
    cleaned = openrouter_client._clean_json_string(text_with_json)
    assert cleaned == '["item1", "item2"]'
    
    # Test with nested JSON object
    nested_json = 'Some text {"data": {"nested": "value"}} more text'
    cleaned = openrouter_client._clean_json_string(nested_json)
    assert cleaned == '{"data": {"nested": "value"}}'

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

@patch('requests.post')
def test_generate_requirements_success(mock_post, openrouter_client):
    """Test successful requirements generation."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": "Test requirements"
            }
        }]
    }
    mock_post.return_value = mock_response
    
    requirements = openrouter_client.generate_requirements("test prompt")
    assert requirements == "Test requirements"

@patch('requests.post')
def test_generate_code_success(mock_post, openrouter_client):
    """Test successful code generation."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": "Test code"
            }
        }]
    }
    mock_post.return_value = mock_response
    
    code = openrouter_client.generate_code("test prompt")
    assert code == "Test code"
