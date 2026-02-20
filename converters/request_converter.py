from typing import Dict, Any
from models.anthropic import AnthropicRequest
from converters.messages_converter import anthropic_messages_to_openai
from converters.tools_converter import anthropic_tool_to_openai
from config import Config


def convert_anthropic_to_azure_request(
    anthropic_request: AnthropicRequest,
    config: Config
) -> Dict[str, Any]:
    """
    Convertit une requête Anthropic complète vers format Azure OpenAI.
    """
    # 1. Mapper le modèle Claude → Azure deployment
    model = anthropic_request.model
    azure_deployment = config.model_mapping.get(model, "gpt-4o-mini")

    # 2. Convertir les messages
    # Extraire la liste de messages (peut être des objets Pydantic ou des dicts)
    messages_list = []
    for msg in anthropic_request.messages:
        if hasattr(msg, "model_dump"):
            messages_list.append(msg.model_dump())
        else:
            messages_list.append(msg)

    openai_messages = anthropic_messages_to_openai(
        messages_list,
        anthropic_request.system
    )

    # 3. Convertir les tools
    openai_tools = None
    if anthropic_request.tools:
        openai_tools = []
        for tool in anthropic_request.tools:
            if hasattr(tool, "model_dump"):
                tool_dict = tool.model_dump()
            else:
                tool_dict = tool
            openai_tools.append(anthropic_tool_to_openai(tool_dict))

    # 4. Construire la requête Azure
    azure_request = {
        "model": azure_deployment,
        "messages": openai_messages,
        "max_tokens": anthropic_request.max_tokens,
        "stream": anthropic_request.stream,
    }

    # Paramètres optionnels
    if anthropic_request.temperature is not None:
        azure_request["temperature"] = anthropic_request.temperature

    if anthropic_request.top_p is not None:
        azure_request["top_p"] = anthropic_request.top_p

    if openai_tools:
        azure_request["tools"] = openai_tools
        azure_request["tool_choice"] = "auto"

    if anthropic_request.stop_sequences:
        azure_request["stop"] = anthropic_request.stop_sequences

    return azure_request
