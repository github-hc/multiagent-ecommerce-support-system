import json
import re
import logging

logger = logging.getLogger("agents.utils")

def clean_and_parse_json(raw_text: str) -> dict:
    """
    Cleans raw LLM response text by removing markdown wrapper codeblocks,
    inline/block comments, and trailing commas, then parses it as JSON.
    """
    text = raw_text.strip()
    
    # 1. Extract JSON string from markdown code block if present
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    else:
        match_braces = re.search(r"(\{.*\})", text, re.DOTALL)
        if match_braces:
            text = match_braces.group(1).strip()

    # 2. Remove JS/C-style line comments (// ...) and block comments (/* ... */)
    # ignoring comments within double-quoted string literals
    pattern = re.compile(r'("(?:[^"\\]|\\.)*")|(?://.*|/\*[\s\S]*?\*/)')
    def replacer(m):
        group_str = m.group(1)
        if group_str is not None:
            return group_str
        return ""
    text = pattern.sub(replacer, text)

    # 3. Remove trailing commas inside objects and arrays before closing brace/bracket
    text = re.sub(r",\s*([\}\]])", r"\1", text)
    
    # 4. Parse the sanitized text
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse cleaned JSON. Cleaned text was:\n{text}")
        raise e
