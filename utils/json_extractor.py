# File: utils/json_extractor.py
"""
JSON Extraction Utilities - Production Version

Extracts JSON from LLM responses with automatic control character fixing.
Optimized for GPT-4o with JSON mode, but robust fallback for other models.
"""

import json
import re
from typing import Optional, Dict, Any
import structlog

logger = structlog.get_logger()


def fix_json_string(text: str) -> str:
    """
    Fix common JSON issues from LLM responses.
    
    Replaces literal control characters (newlines, tabs) with escaped versions.
    This is needed when LLMs don't properly escape special characters in JSON values.
    """
    fixed = text
    # Handle already-escaped newlines first
    fixed = fixed.replace('\\n', '<<<ESCAPED_NEWLINE>>>')
    fixed = fixed.replace('\\r', '<<<ESCAPED_RETURN>>>')
    fixed = fixed.replace('\\t', '<<<ESCAPED_TAB>>>')
    
    # Fix literal control characters
    fixed = fixed.replace('\n', '\\n')
    fixed = fixed.replace('\r', '\\r')
    fixed = fixed.replace('\t', '\\t')
    fixed = fixed.replace('\b', '\\b')
    fixed = fixed.replace('\f', '\\f')
    
    # Restore already-escaped characters
    fixed = fixed.replace('<<<ESCAPED_NEWLINE>>>', '\\n')
    fixed = fixed.replace('<<<ESCAPED_RETURN>>>', '\\r')
    fixed = fixed.replace('<<<ESCAPED_TAB>>>', '\\t')
    
    return fixed


def extract_json_from_response(
    response: str, 
    log_context: str = "json_extraction"
) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from LLM response with automatic control character fixing.
    
    Handles multiple formats:
    - Raw JSON: {"key": "value"}
    - Markdown: ```json\\n{"key": "value"}\\n```
    - Embedded: "Here is: {"key": "value"} as requested"
    - Control chars: {"key": "value with\\nliteral newlines"}
    
    Args:
        response: Raw response from LLM
        log_context: Context for logging (e.g., "initial_prompt_generation")
        
    Returns:
        Parsed JSON dict or None if extraction fails
    """
    if not response or not isinstance(response, str):
        return None
    
    response = response.strip()
    
    # ============================================================
    # Strategy 1: Raw JSON (fastest - works with GPT-4o JSON mode)
    # ============================================================
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # ============================================================
    # Strategy 2: Fix control characters and retry
    # ============================================================
    try:
        fixed = fix_json_string(response)
        result = json.loads(fixed)
        # Only log at debug level - this is expected with some models
        logger.debug(
            f"{log_context}_fixed_control_chars",
            response_length=len(response)
        )
        return result
    except json.JSONDecodeError:
        pass
    
    # ============================================================
    # Strategy 3: Extract from markdown code blocks
    # ============================================================
    markdown_patterns = [
        r'```json\s*\n(.*?)\n```',
        r'```json\s*(.*?)```',
        r'```\s*\n(.*?)\n```',
        r'```\s*(.*?)```',
    ]
    
    for pattern in markdown_patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
            
            # Try direct parse
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
            
            # Try with control char fix
            try:
                fixed = fix_json_string(json_str)
                return json.loads(fixed)
            except json.JSONDecodeError:
                continue
    
    # ============================================================
    # Strategy 4: Find JSON object in text (brace matching)
    # ============================================================
    brace_count = 0
    start_idx = None
    
    for i, char in enumerate(response):
        if char == '{':
            if start_idx is None:
                start_idx = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and start_idx is not None:
                json_str = response[start_idx:i+1]
                
                # Try direct parse
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
                
                # Try with control char fix
                try:
                    fixed = fix_json_string(json_str)
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    # Reset and keep looking for next JSON object
                    start_idx = None
                    brace_count = 0
                    continue
    
    # ============================================================
    # All strategies failed - log warning only
    # ============================================================
    logger.warning(
        f"{log_context}_extraction_failed",
        response_length=len(response),
        response_preview=response[:300],
        has_json_structure='{' in response and '}' in response
    )
    return None


def extract_json_field(
    response: str, 
    field_name: str, 
    log_context: str = "field_extraction"
) -> Optional[Any]:
    """
    Extract a specific field from JSON in LLM response.
    
    Args:
        response: Raw response from LLM
        field_name: Name of field to extract (e.g., "new_prompt")
        log_context: Context for logging
        
    Returns:
        Field value or None if not found
    """
    data = extract_json_from_response(response, log_context)
    
    if data and isinstance(data, dict):
        return data.get(field_name)
    
    return None


def validate_json_schema(data: Dict[str, Any], required_fields: list[str]) -> bool:
    """
    Validate that JSON contains required fields.
    
    Args:
        data: Parsed JSON dict
        required_fields: List of required field names
        
    Returns:
        True if all required fields present, False otherwise
    """
    if not isinstance(data, dict):
        return False
    
    missing = [f for f in required_fields if f not in data]
    
    if missing:
        logger.debug("json_validation_missing_fields", missing=missing)
        return False
    
    return True


def safe_json_parse(
    response: str, 
    required_fields: Optional[list[str]] = None,
    log_context: str = "json_parse"
) -> Optional[Dict[str, Any]]:
    """
    Safely parse JSON with optional field validation.
    
    Args:
        response: Raw response from LLM
        required_fields: Optional list of required field names
        log_context: Context for logging
        
    Returns:
        Parsed and validated JSON dict or None
    """
    data = extract_json_from_response(response, log_context)
    
    if data and required_fields:
        if validate_json_schema(data, required_fields):
            return data
        return None
    
    return data


def is_json_truncated(response: str) -> bool:
    """
    Quick check if JSON response appears truncated.
    
    Returns:
        True if response looks incomplete
    """
    response = response.strip()
    
    # Unbalanced braces/brackets
    if response.count('{') != response.count('}'):
        return True
    if response.count('[') != response.count(']'):
        return True
    
    # Ends with common truncation patterns
    truncation_patterns = ['...', ' ca', ' th', ' an', ' in', ' to', ' the']
    return any(response.endswith(p) for p in truncation_patterns)