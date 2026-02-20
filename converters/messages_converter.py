import json
from typing import List, Dict, Any, Optional


def anthropic_messages_to_openai(
    anthropic_messages: List[Dict[str, Any]],
    system_prompt: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Convertit les messages Anthropic vers format OpenAI.

    Gère:
    - system prompt séparé → message system
    - tool_use content blocks → assistant message avec tool_calls
    - tool_result content blocks → tool message
    """
    openai_messages = []

    # Ajouter system prompt en premier
    if system_prompt:
        openai_messages.append({
            "role": "system",
            "content": system_prompt
        })

    for msg in anthropic_messages:
        role = msg.get("role")
        content = msg.get("content")

        if role not in ["user", "assistant"]:
            continue

        # Si content est une string simple
        if isinstance(content, str):
            openai_messages.append({
                "role": role,
                "content": content
            })
            continue

        # Si content est une liste de blocks
        if isinstance(content, list):
            # Séparer les différents types de blocks
            tool_uses = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]
            tool_results = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_result"]
            text_blocks = [b for b in content if isinstance(b, dict) and b.get("type") == "text"]

            # Assistant message avec tool calls
            if tool_uses and role == "assistant":
                tool_calls = []
                for tu in tool_uses:
                    # Convert ID: toolu_ABC → call_ABC
                    openai_id = tu["id"].replace("toolu_", "call_", 1)
                    tool_calls.append({
                        "id": openai_id,
                        "type": "function",
                        "function": {
                            "name": tu["name"],
                            "arguments": json.dumps(tu["input"])
                        }
                    })

                # Si il y a aussi du texte, l'inclure
                text_content = None
                if text_blocks:
                    text_content = " ".join([b.get("text", "") for b in text_blocks])

                openai_messages.append({
                    "role": "assistant",
                    "content": text_content,
                    "tool_calls": tool_calls
                })

            # Tool results → tool messages
            elif tool_results and role == "user":
                for tr in tool_results:
                    # Convert ID: toolu_ABC → call_ABC
                    openai_id = tr["tool_use_id"].replace("toolu_", "call_", 1)

                    # Get content as string
                    tr_content = tr.get("content", "")
                    if not isinstance(tr_content, str):
                        tr_content = json.dumps(tr_content)

                    openai_messages.append({
                        "role": "tool",
                        "tool_call_id": openai_id,
                        "content": tr_content
                    })

            # Regular text message
            elif text_blocks:
                text_content = " ".join([b.get("text", "") for b in text_blocks])
                openai_messages.append({
                    "role": role,
                    "content": text_content
                })

    return openai_messages
