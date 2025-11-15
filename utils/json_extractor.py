# File: utils/json_extractor.py
"""
JSON Extraction Utilities - Enhanced Production Version

FIXED: Better handling of long responses, nested JSON, and truncation detection
"""

import json
import re
from typing import Optional, Dict, Any
import structlog

logger = structlog.get_logger()


def fix_json_string(text: str) -> str:
    """
    Fix common JSON issues from LLM responses.

    FIXED: Only escapes literal control characters when INSIDE JSON string values.
    Preserves structural whitespace outside strings.

    This is needed when LLMs don't properly escape special characters in JSON values.
    """
    result = []
    in_string = False
    escape_next = False

    i = 0
    while i < len(text):
        char = text[i]

        # Handle escape sequences
        if escape_next:
            result.append(char)
            escape_next = False
            i += 1
            continue

        if char == '\\':
            result.append(char)
            escape_next = True
            i += 1
            continue

        # Track string boundaries
        if char == '"':
            in_string = not in_string
            result.append(char)
            i += 1
            continue

        # Only escape control characters when INSIDE strings
        if in_string:
            if char == '\n':
                result.append('\\n')
            elif char == '\r':
                result.append('\\r')
            elif char == '\t':
                result.append('\\t')
            elif char == '\b':
                result.append('\\b')
            elif char == '\f':
                result.append('\\f')
            else:
                result.append(char)
        else:
            # Outside strings: keep whitespace as-is (it's structural)
            result.append(char)

        i += 1

    return ''.join(result)


def extract_largest_valid_json(response: str) -> Optional[Dict[str, Any]]:
    """
    Extract the largest valid JSON object from response using brace matching.
    
    NEW: Improved algorithm that handles nested objects and finds the best match.
    """
    best_json = None
    best_length = 0
    
    # Find all potential JSON start positions
    for start_idx in range(len(response)):
        if response[start_idx] != '{':
            continue
        
        # Track brace depth
        depth = 0
        in_string = False
        escape_next = False
        
        for i in range(start_idx, len(response)):
            char = response[i]
            
            # Handle string context (quotes can contain braces)
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            # Only count braces outside strings
            if not in_string:
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    
                    # Found complete JSON object
                    if depth == 0:
                        json_str = response[start_idx:i+1]
                        
                        # Try to parse it
                        try:
                            parsed = json.loads(json_str)
                            if len(json_str) > best_length:
                                best_json = parsed
                                best_length = len(json_str)
                        except json.JSONDecodeError:
                            # Try with control char fix
                            try:
                                fixed = fix_json_string(json_str)
                                parsed = json.loads(fixed)
                                if len(json_str) > best_length:
                                    best_json = parsed
                                    best_length = len(json_str)
                            except json.JSONDecodeError:
                                pass
                        
                        break  # Move to next start position
    
    return best_json


def detect_truncation_issues(response: str) -> Dict[str, Any]:
    """
    Detect if response has truncation or formatting issues.
    
    Returns diagnostic information about the response.
    """
    issues = {
        "is_truncated": False,
        "brace_mismatch": False,
        "very_long": False,
        "has_markdown": False,
        "ends_abruptly": False
    }
    
    # Check length
    if len(response) > 5000:
        issues["very_long"] = True
    
    # Check brace balance
    open_braces = response.count('{')
    close_braces = response.count('}')
    if open_braces != close_braces:
        issues["brace_mismatch"] = True
        issues["is_truncated"] = True
    
    # Check for markdown
    if '```' in response:
        issues["has_markdown"] = True
    
    # Check for abrupt ending
    response_end = response[-50:].strip()
    if not response_end.endswith('}') and not response_end.endswith('```'):
        issues["ends_abruptly"] = True
        issues["is_truncated"] = True
    
    return issues


def extract_json_from_response(
    response: str, 
    log_context: str = "json_extraction"
) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from LLM response with automatic control character fixing.
    
    ENHANCED: Better handling of long responses, nested JSON, and truncation.
    
    Args:
        response: Raw response from LLM
        log_context: Context for logging (e.g., "initial_prompt_generation")
        
    Returns:
        Parsed JSON dict or None if extraction fails
    """
    if not response or not isinstance(response, str):
        return None
    
    response = response.strip()
    
    # Detect issues early
    issues = detect_truncation_issues(response)
    
    if issues["very_long"]:
        logger.debug(
            f"{log_context}_long_response",
            length=len(response),
            truncated=issues["is_truncated"]
        )
    
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
    if issues["has_markdown"]:
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
    # Strategy 4: Enhanced brace matching for nested JSON
    # ============================================================
    result = extract_largest_valid_json(response)
    if result:
        logger.debug(
            f"{log_context}_extracted_nested_json",
            response_length=len(response)
        )
        return result
    
    # ============================================================
    # Strategy 5: Try to repair truncated JSON
    # ============================================================
    if issues["is_truncated"] or issues["brace_mismatch"]:
        # Find the last valid complete object
        last_close_brace = response.rfind('}')
        if last_close_brace > 0:
            # Try parsing up to the last closing brace
            truncated = response[:last_close_brace + 1]
            
            try:
                return json.loads(truncated)
            except json.JSONDecodeError:
                pass
            
            try:
                fixed = fix_json_string(truncated)
                result = json.loads(fixed)
                logger.warning(
                    f"{log_context}_repaired_truncated_json",
                    original_length=len(response),
                    repaired_length=len(truncated)
                )
                return result
            except json.JSONDecodeError:
                pass
    
    # ============================================================
    # All strategies failed - provide detailed diagnostics
    # ============================================================
    logger.warning(
        f"{log_context}_extraction_failed",
        response_length=len(response),
        response_preview=response[:300],
        response_end=response[-100:] if len(response) > 100 else response,
        issues=issues,
        has_json_structure='{' in response and '}' in response,
        open_braces=response.count('{'),
        close_braces=response.count('}')
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
        value = data.get(field_name)
        if value:
            return value
        
        # Try common variations
        variations = [
            field_name.lower(),
            field_name.upper(),
            field_name.replace('_', ''),
            field_name.replace('_', '-')
        ]
        
        for var in variations:
            if var in data:
                logger.debug(
                    f"{log_context}_field_name_variation",
                    requested=field_name,
                    found=var
                )
                return data[var]
    
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


def debug_json_extraction(response: str, log_context: str = "debug") -> Dict[str, Any]:
    """
    Debug helper: Extract JSON and return detailed diagnostics.
    
    Use this to troubleshoot extraction issues.
    """
    diagnostics = {
        "response_length": len(response),
        "response_preview": response[:500],
        "response_end": response[-200:] if len(response) > 200 else response,
        "issues": detect_truncation_issues(response),
        "extraction_result": None,
        "extraction_success": False
    }
    
    result = extract_json_from_response(response, log_context)
    
    diagnostics["extraction_result"] = result
    diagnostics["extraction_success"] = result is not None
    
    if result:
        diagnostics["result_keys"] = list(result.keys()) if isinstance(result, dict) else None
        diagnostics["result_type"] = type(result).__name__
    
    return diagnostics