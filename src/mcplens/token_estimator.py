import json
from typing import Any, Dict

PUNCTUATION_CHARS = set('{}[]:,' + '"')

def estimate_json_tokens(data: Any) -> int:
    """
    Calibrated token estimation for structured JSON payloads
    simulating Anthropic / OpenAI tokenizer conventions.
    """
    if data is None:
        return 1
    text = json.dumps(data, separators=(',', ':'))
    
    # Subword heuristic calibrated on Tiktoken & Claude tokenizers:
    # - Average alphanumeric words: ~1 token per 4 characters
    # - JSON syntax punctuation: ~1 token each
    tokens = 0
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c in PUNCTUATION_CHARS:
            tokens += 1
            i += 1
        elif c.isspace():
            tokens += 1
            while i < n and text[i].isspace():
                i += 1
        else:
            start = i
            while i < n and (text[i] not in PUNCTUATION_CHARS) and not text[i].isspace():
                i += 1
            chunk = text[start:i]
            tokens += max(1, (len(chunk) + 2) // 4)
    return tokens


def estimate_tool_tokens(tool_name: str, description: str, input_schema: Dict[str, Any]) -> int:
    """
    Estimates total token footprint of an MCP tool in the LLM's system prompt context,
    including tool schema overhead, description, and parameter types.
    """
    overhead = 18
    name_tokens = max(1, (len(tool_name) + 2) // 4)
    desc_tokens = max(1, (len(description) + 2) // 4) if description else 0
    schema_tokens = estimate_json_tokens(input_schema)
    
    return overhead + name_tokens + desc_tokens + schema_tokens
