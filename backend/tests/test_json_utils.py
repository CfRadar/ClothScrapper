import pytest
from backend.app.llm.json_utils import JSONExtractError, extract_json, parse_model
from pydantic import BaseModel


class SampleModel(BaseModel):
    name: str
    count: int


def test_clean_json_extraction():
    text = '{"name": "oversized tee", "count": 15}'
    data = extract_json(text)
    assert data["name"] == "oversized tee"
    assert data["count"] == 15


def test_markdown_fence_stripping():
    text = """```json
    {
      "name": "acid wash tee",
      "count": 42
    }
    ```"""
    data = extract_json(text)
    assert data["name"] == "acid wash tee"
    assert data["count"] == 42


def test_conversational_wrapping_and_brace_matching():
    text = (
        "Sure! Here is the JSON data you requested:\n"
        "{\n"
        '  "name": "japanese graphic tee",\n'
        '  "count": 10\n'
        "}\n"
        "Hope this helps!"
    )
    data = extract_json(text)
    assert data["name"] == "japanese graphic tee"
    assert data["count"] == 10


def test_trailing_comma_repair():
    text = '{"name": "box tee", "count": 5,}'
    data = extract_json(text)
    assert data["name"] == "box tee"
    assert data["count"] == 5


def test_parse_model_success():
    text = '```{"name": "polo", "count": 20}```'
    obj = parse_model(text, SampleModel)
    assert isinstance(obj, SampleModel)
    assert obj.name == "polo"
    assert obj.count == 20


def test_parse_model_invalid_raises():
    with pytest.raises(JSONExtractError):
        parse_model("Sorry, no JSON here.", SampleModel)
