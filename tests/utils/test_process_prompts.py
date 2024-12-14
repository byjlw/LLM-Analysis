"""
Tests for process_prompts utilities.
"""

import json
import pytest
from unittest.mock import Mock, patch

from src.utils.process_prompts import (
    clean_response,
    get_raw_json_response,
    get_text_response,
    generate_requirements,
    generate_code,
    generate_dependencies
)

def test_clean_response():
    """Test cleaning response content."""
    # Test with no code blocks
    content = "plain text"
    assert clean_response(content) == content
    
    # Test with JSON code block
    content = "```json\n{\"test\": true}\n```"
    assert clean_response(content) == "{\"test\": true}"
    
    # Test with leading/trailing whitespace
    content = "  \n```json\n{\"test\": true}\n```\n  "
    assert clean_response(content) == "{\"test\": true}"
    
    # Test with incomplete markers
    content = "```json\n{\"test\": true}"
    assert clean_response(content) == "{\"test\": true}"
    
    content = "{\"test\": true}\n```"
    assert clean_response(content) == "{\"test\": true}"

def test_get_raw_json_response_success():
    """Test successful JSON response processing."""
    mock_client = Mock()
    mock_client._make_request.return_value = {
        "choices": [{
            "message": {
                "content": '{"test": true}'
            }
        }]
    }
    
    result = get_raw_json_response(mock_client, [{"role": "user", "content": "test"}])
    assert result == {"test": True}

def test_get_raw_json_response_invalid_json():
    """Test handling of invalid JSON response."""
    mock_client = Mock()
    mock_client._make_request.return_value = {
        "choices": [{
            "message": {
                "content": "not json"
            }
        }]
    }
    
    # Should return raw string on final attempt
    result = get_raw_json_response(mock_client, [{"role": "user", "content": "test"}])
    assert result == "not json"

def test_get_raw_json_response_retry():
    """Test JSON response retry logic."""
    mock_client = Mock()
    mock_client._make_request.side_effect = [
        # First attempt returns invalid JSON
        {
            "choices": [{
                "message": {
                    "content": "not json"
                }
            }]
        },
        # Second attempt returns valid JSON
        {
            "choices": [{
                "message": {
                    "content": '{"test": true}'
                }
            }]
        }
    ]
    
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "error prompt"
        result = get_raw_json_response(mock_client, [{"role": "user", "content": "test"}])
        assert result == {"test": True}

def test_get_raw_json_response_max_retries():
    """Test JSON response max retries."""
    mock_client = Mock()
    mock_client._make_request.return_value = {
        "choices": [{
            "message": {
                "content": "not json"
            }
        }]
    }
    
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "error prompt"
        # Should return raw string after max retries
        result = get_raw_json_response(
            mock_client,
            [{"role": "user", "content": "test"}],
            max_retries=1
        )
        assert result == "not json"

def test_get_text_response_success():
    """Test successful text response."""
    mock_client = Mock()
    mock_client._make_request.return_value = {
        "choices": [{
            "message": {
                "content": "test response"
            }
        }]
    }
    
    result = get_text_response(mock_client, [{"role": "user", "content": "test"}])
    assert result == "test response"

def test_get_text_response_invalid_structure():
    """Test handling of invalid response structure."""
    mock_client = Mock()
    mock_client._make_request.return_value = {"invalid": "structure"}
    
    with pytest.raises(ValueError, match="Invalid response structure"):
        get_text_response(mock_client, [{"role": "user", "content": "test"}])

def test_generate_requirements_message_format():
    """Test requirements generation message format."""
    mock_client = Mock()
    mock_client._make_request.return_value = {
        "choices": [{
            "message": {
                "content": "test requirements"
            }
        }]
    }
    
    result = generate_requirements(mock_client, "test prompt")
    assert result == "test requirements"
    
    # Verify message format
    messages = mock_client._make_request.call_args[0][0]
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "test prompt"

def test_generate_code_message_format():
    """Test code generation message format."""
    mock_client = Mock()
    mock_client._make_request.return_value = {
        "choices": [{
            "message": {
                "content": "test code"
            }
        }]
    }
    
    result = generate_code(
        mock_client,
        initial_prompt="initial",
        writer_prompt="writer",
        requirements="requirements"
    )
    assert result == "test code"
    
    # Verify message format for both steps
    calls = mock_client._make_request.call_args_list
    assert len(calls) == 2
    
    # First step messages
    messages = calls[0][0][0]
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "initial" in messages[1]["content"]
    assert "requirements" in messages[1]["content"]
    
    # Second step messages
    messages = calls[1][0][0]
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "assistant"
    assert messages[2]["role"] == "user"
    assert messages[2]["content"] == "writer"

def test_generate_dependencies_message_format():
    """Test dependencies generation message format."""
    mock_client = Mock()
    mock_client._make_request.return_value = {
        "choices": [{
            "message": {
                "content": '["test"]'
            }
        }]
    }
    
    result = generate_dependencies(mock_client, "prompt {DETAILS}", "code")
    assert result == {"frameworks": ["test"]}
    
    # Verify message format
    messages = mock_client._make_request.call_args[0][0]
    assert messages[0]["role"] == "system"
    assert "production engineer" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "prompt code"

def test_generate_dependencies_error():
    """Test dependencies generation error handling."""
    mock_client = Mock()
    mock_client._make_request.side_effect = Exception("test error")
    
    result = generate_dependencies(mock_client, "prompt", "code")
    assert result == {"frameworks": []}
