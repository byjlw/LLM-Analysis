"""
Tests for prompt processing utilities.
"""

import pytest
from src.utils.process_prompts import clean_response

def test_clean_response():
    """Test cleaning response with markdown code blocks."""
    # Test JSON with ```json ``` block
    markdown_json = '```json\n{"test": "value"}\n```'
    assert clean_response(markdown_json) == '{"test": "value"}'
    
    # Test with extra whitespace
    markdown_whitespace = '```json\n\n  {"test": "value"}  \n\n```'
    assert clean_response(markdown_whitespace) == '{"test": "value"}'
    
    # Test array JSON
    markdown_array = '```json\n[\n    {"test": "value1"},\n    {"test": "value2"}\n]\n```'
    assert clean_response(markdown_array) == '[\n    {"test": "value1"},\n    {"test": "value2"}\n]'
    
    # Test non-markdown content
    plain_json = '{"test": "value"}'
    assert clean_response(plain_json) == '{"test": "value"}'
    
    # Test empty content
    assert clean_response('') == ''
    
    # Test content with no JSON blocks
    no_blocks = 'This is just text'
    assert clean_response(no_blocks) == 'This is just text'
    
    # Test content with ```json but no closing ```
    unclosed_block = '```json\n{"test": "value"}'
    assert clean_response(unclosed_block) == '{"test": "value"}'
    
    # Test content with just ```
    just_markers = '```\n```'
    assert clean_response(just_markers) == ''
    
    # Test content with nested backticks
    nested_backticks = '```json\n{"code": "```example```"}\n```'
    assert clean_response(nested_backticks) == '{"code": "```example```"}'
