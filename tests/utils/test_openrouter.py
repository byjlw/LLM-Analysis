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

def test_transform_to_array(openrouter_client, sample_idea):
    """Test JSON data transformation to array."""
    # Already an array
    assert openrouter_client._transform_to_array([sample_idea]) == [sample_idea]
    
    # Single item
    assert openrouter_client._transform_to_array(sample_idea) == [sample_idea]
    
    # Nested in data field
    nested_data = {"data": sample_idea}
    assert openrouter_client._transform_to_array(nested_data) == [sample_idea]
    
    # Nested in message field
    message_data = {"message": {"content": sample_idea}}
    assert openrouter_client._transform_to_array(message_data) == [sample_idea]
    
    # Invalid data returns default
    invalid_data = "not json"
    result = openrouter_client._transform_to_array(invalid_data)
    assert len(result) == 1
    assert result[0]["Product Idea"] == "Default Product"

def test_validate_json_structure(openrouter_client, sample_idea):
    """Test JSON structure validation and fixing."""
    # Valid structure
    valid_data = [sample_idea]
    result = openrouter_client._validate_json_structure(valid_data)
    assert result == valid_data
    
    # Missing fields get defaults
    incomplete_data = [{
        "Product Idea": "Test",
        # Missing other fields
    }]
    result = openrouter_client._validate_json_structure(incomplete_data)
    assert len(result) == 1
    assert result[0]["Product Idea"] == "Test"
    assert result[0]["Problem it solves"] == "Unknown Problem"
    assert isinstance(result[0]["Software Techstack"], list)
    
    # Invalid types get converted
    invalid_types = [{
        "Product Idea": ["Should be string"],
        "Problem it solves": "Valid",
        "Software Techstack": "Should be list",
        "Target hardware expectations": ["Valid"],
        "Company profile": 123,
        "Engineering profile": "Valid"
    }]
    result = openrouter_client._validate_json_structure(invalid_types)
    assert len(result) == 1
    assert isinstance(result[0]["Software Techstack"], list)
    assert isinstance(result[0]["Company profile"], str)

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
def test_generate_ideas_success(mock_post, openrouter_client, sample_idea):
    """Test successful idea generation."""
    # Test array response
    mock_response = Mock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps([sample_idea])
            }
        }]
    }
    mock_post.return_value = mock_response
    
    ideas = openrouter_client.generate_ideas("test prompt")
    assert len(ideas) == 1
    assert ideas[0]["Product Idea"] == sample_idea["Product Idea"]
    
    # Test single object response
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps(sample_idea)
            }
        }]
    }
    ideas = openrouter_client.generate_ideas("test prompt")
    assert len(ideas) == 1
    assert ideas[0]["Product Idea"] == sample_idea["Product Idea"]
    
    # Test nested response
    nested_response = {
        "message": "Test prompt received",
        "status": "success",
        "data": sample_idea
    }
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps(nested_response)
            }
        }]
    }
    ideas = openrouter_client.generate_ideas("test prompt")
    assert len(ideas) == 1
    assert ideas[0]["Product Idea"] == sample_idea["Product Idea"]

@patch('requests.post')
def test_generate_ideas_invalid_response(mock_post, openrouter_client):
    """Test idea generation with invalid response."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": "Invalid JSON content"
            }
        }]
    }
    mock_post.return_value = mock_response
    
    ideas = openrouter_client.generate_ideas("test prompt")
    assert len(ideas) == 1
    assert "Error Processing Response" in ideas[0]["Product Idea"]
    assert isinstance(ideas[0]["Software Techstack"], list)

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
def test_generate_requirements_error(mock_post, openrouter_client):
    """Test requirements generation with error."""
    mock_response = Mock()
    mock_response.json.return_value = {"error": "Invalid response"}
    mock_post.return_value = mock_response
    
    requirements = openrouter_client.generate_requirements("test prompt")
    assert "Error generating requirements" in requirements

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

@patch('requests.post')
def test_generate_code_error(mock_post, openrouter_client):
    """Test code generation with error."""
    mock_response = Mock()
    mock_response.json.return_value = {"error": "Invalid response"}
    mock_post.return_value = mock_response
    
    code = openrouter_client.generate_code("test prompt")
    assert "Error generating code" in code
