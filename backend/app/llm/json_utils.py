import json
import re
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class JSONExtractError(ValueError):
    """Raised when JSON cannot be extracted or parsed from LLM response text."""

    pass


def extract_balanced_brace(text: str) -> str:
    """
    Find the first balanced outermost curly brace pair {...} in text,
    properly ignoring braces inside quoted strings and escaping.
    """
    start_idx = -1
    depth = 0
    in_string = False
    escape = False

    for i, char in enumerate(text):
        if char == '"' and not escape:
            in_string = not in_string
        elif not in_string:
            if char == "{":
                if depth == 0:
                    start_idx = i
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0 and start_idx != -1:
                    return text[start_idx : i + 1]

        if char == "\\" and not escape:
            escape = True
        else:
            escape = False

    raise JSONExtractError("No balanced JSON object {...} found in response text.")


def clean_trailing_commas(json_str: str) -> str:
    """Clean trailing commas before closing braces/brackets."""
    return re.sub(r",\s*([\]}])", r"\1", json_str)


def extract_json(text: str) -> dict[str, Any]:
    """
    Extract JSON dictionary from text with markdown fence stripping,
    brace matching, and defensive comma repair.
    """
    if not text or not text.strip():
        raise JSONExtractError("Response text is empty.")

    # 1. Strip reasoning think tags if present (e.g. DeepSeek-R1 / Nemotron reasoning)
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # 2. Strip markdown fences if present
    cleaned = re.sub(r"```(?:json)?", "", cleaned).strip()

    # 2. Extract balanced outer braces
    try:
        brace_chunk = extract_balanced_brace(cleaned)
    except JSONExtractError:
        # Fallback to direct string if it starts with { and ends with }
        if cleaned.startswith("{") and cleaned.endswith("}"):
            brace_chunk = cleaned
        else:
            raise

    # 3. Attempt json.loads
    try:
        return json.loads(brace_chunk)
    except json.JSONDecodeError:
        # Try trailing comma fix
        repaired = clean_trailing_commas(brace_chunk)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError as err:
            raise JSONExtractError(f"Failed to parse extracted JSON: {err}") from err


def parse_model(text: str, model_cls: type[T]) -> T:
    """Extract JSON from text and validate against a Pydantic model."""
    data = extract_json(text)
    try:
        return model_cls.model_validate(data)
    except ValidationError as err:
        raise JSONExtractError(
            f"JSON schema validation failed for {model_cls.__name__}: {err}"
        ) from err
