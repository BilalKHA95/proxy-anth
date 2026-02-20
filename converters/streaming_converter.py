import json
from typing import AsyncIterator


async def convert_openai_stream_to_anthropic(
    openai_stream: AsyncIterator[str]
) -> AsyncIterator[str]:
    """
    Convertit le stream OpenAI vers format Anthropic SSE.

    OpenAI format:
    data: {"id":"chatcmpl-...","choices":[{"delta":{"content":"Hello"}}]}
    data: [DONE]

    Anthropic format:
    event: message_start
    data: {"type":"message_start","message":{"id":"msg_..."}}

    event: content_block_delta
    data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"Hello"}}

    event: message_stop
    data: {"type":"message_stop"}
    """
    message_started = False
    content_block_started = False
    message_id = None

    async for line in openai_stream:
        if not line.strip() or line.startswith(":"):
            continue

        if line.startswith("data: "):
            data_str = line[6:]

            # End of stream
            if data_str.strip() == "[DONE]":
                # Envoyer content_block_stop si nécessaire
                if content_block_started:
                    yield f"event: content_block_stop\n"
                    yield f"data: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"

                # Envoyer message_delta (usage finale)
                yield f"event: message_delta\n"
                yield f"data: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': 'end_turn'}, 'usage': {'output_tokens': 0}})}\n\n"

                # Envoyer message_stop
                yield f"event: message_stop\n"
                yield f"data: {json.dumps({'type': 'message_stop'})}\n\n"
                break

            try:
                chunk = json.loads(data_str)

                # Extraire l'ID du message
                if not message_id:
                    message_id = f"msg_{chunk.get('id', 'unknown')}"

                delta = chunk["choices"][0].get("delta", {})
                finish_reason = chunk["choices"][0].get("finish_reason")

                # Premier chunk - envoyer message_start
                if not message_started:
                    yield f"event: message_start\n"
                    yield f"data: {json.dumps({'type': 'message_start', 'message': {'id': message_id, 'type': 'message', 'role': 'assistant', 'content': [], 'model': chunk.get('model', 'unknown'), 'usage': {'input_tokens': 0, 'output_tokens': 0}}})}\n\n"
                    message_started = True

                # Content delta
                if "content" in delta and delta["content"]:
                    # Envoyer content_block_start si c'est le premier
                    if not content_block_started:
                        yield f"event: content_block_start\n"
                        yield f"data: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}})}\n\n"
                        content_block_started = True

                    # Envoyer content_block_delta
                    yield f"event: content_block_delta\n"
                    yield f"data: {json.dumps({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': delta['content']}})}\n\n"

                # Tool calls (simplification - on envoie tool_use complet quand on a l'info)
                if "tool_calls" in delta and delta["tool_calls"]:
                    for tc_delta in delta["tool_calls"]:
                        # Si on a un tool call complet
                        if tc_delta.get("function", {}).get("name"):
                            if not content_block_started:
                                # Start tool_use block
                                tool_use_id = tc_delta.get("id", "").replace("call_", "toolu_", 1)
                                yield f"event: content_block_start\n"
                                yield f"data: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'tool_use', 'id': tool_use_id, 'name': tc_delta['function']['name']}})}\n\n"
                                content_block_started = True

                # Handle finish_reason
                if finish_reason:
                    if content_block_started:
                        yield f"event: content_block_stop\n"
                        yield f"data: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"

                    # Map finish_reason
                    stop_reason_map = {
                        "stop": "end_turn",
                        "tool_calls": "tool_use",
                        "length": "max_tokens",
                        "content_filter": "stop_sequence"
                    }
                    anthropic_stop_reason = stop_reason_map.get(finish_reason, "end_turn")

                    yield f"event: message_delta\n"
                    yield f"data: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': anthropic_stop_reason}, 'usage': {'output_tokens': 0}})}\n\n"

            except (json.JSONDecodeError, KeyError, IndexError) as e:
                # Skip malformed chunks
                continue
