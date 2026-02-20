import json
from typing import Dict, Any, Optional
from converters.tools_converter import openai_tool_call_to_anthropic


def convert_azure_to_anthropic_response(
    azure_response: Dict[str, Any],
    original_request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convertit une réponse Azure OpenAI vers format Anthropic.
    """
    choice = azure_response["choices"][0]
    message = choice["message"]

    # Construire le content
    content = []

    # Texte régulier
    if message.get("content"):
        content.append({
            "type": "text",
            "text": message["content"]
        })

    # Tool calls → tool_use blocks
    if message.get("tool_calls"):
        for tc in message["tool_calls"]:
            content.append(openai_tool_call_to_anthropic(tc))

    # Mapper finish_reason OpenAI → stop_reason Anthropic
    stop_reason_map = {
        "stop": "end_turn",
        "tool_calls": "tool_use",
        "length": "max_tokens",
        "content_filter": "stop_sequence"
    }

    stop_reason = stop_reason_map.get(
        choice.get("finish_reason", "stop"),
        "end_turn"
    )

    # Construire la réponse Anthropic
    anthropic_response = {
        "id": f"msg_{azure_response['id']}",
        "type": "message",
        "role": "assistant",
        "content": content,
        "model": azure_response.get("model", "unknown"),
        "stop_reason": stop_reason,
        "usage": {
            "input_tokens": azure_response["usage"]["prompt_tokens"],
            "output_tokens": azure_response["usage"]["completion_tokens"]
        }
    }

    return anthropic_response
