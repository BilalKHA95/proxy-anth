import json
from typing import Dict, Any


def anthropic_tool_to_openai(anthropic_tool: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convertit un tool Anthropic vers format OpenAI.

    Anthropic:
    {
      "name": "...",
      "description": "...",
      "input_schema": {...}
    }

    OpenAI:
    {
      "type": "function",
      "function": {
        "name": "...",
        "description": "...",
        "parameters": {...}
      }
    }
    """
    return {
        "type": "function",
        "function": {
            "name": anthropic_tool.get("name"),
            "description": anthropic_tool.get("description", ""),
            "parameters": anthropic_tool.get("input_schema", {})
        }
    }


def openai_tool_call_to_anthropic(tool_call: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convertit un tool_call OpenAI vers tool_use Anthropic.

    OpenAI tool_call:
    {
      "id": "call_ABC",
      "type": "function",
      "function": {
        "name": "get_weather",
        "arguments": "{\"location\":\"Paris\"}"
      }
    }

    Anthropic tool_use:
    {
      "type": "tool_use",
      "id": "toolu_ABC",
      "name": "get_weather",
      "input": {"location": "Paris"}
    }
    """
    # Convert ID format: call_ABC → toolu_ABC
    anthropic_id = tool_call["id"].replace("call_", "toolu_", 1)

    # Parse arguments JSON string to dict
    arguments_str = tool_call["function"]["arguments"]
    try:
        input_dict = json.loads(arguments_str) if arguments_str else {}
    except json.JSONDecodeError:
        input_dict = {}

    return {
        "type": "tool_use",
        "id": anthropic_id,
        "name": tool_call["function"]["name"],
        "input": input_dict
    }
