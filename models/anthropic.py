from typing import List, Optional, Union, Literal, Any, Dict
from pydantic import BaseModel, Field


class TextBlock(BaseModel):
    type: Literal["text"] = "text"
    text: str


class ToolUseBlock(BaseModel):
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: Dict[str, Any]


class ToolResultBlock(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: Union[str, List[Dict[str, Any]]]


ContentBlock = Union[TextBlock, ToolUseBlock, ToolResultBlock]


class AnthropicMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: Union[str, List[Union[TextBlock, ToolUseBlock, ToolResultBlock]]]


class AnthropicTool(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]


class AnthropicRequest(BaseModel):
    model: str
    messages: List[Union[AnthropicMessage, Dict[str, Any]]]
    max_tokens: int = 4096
    system: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    stream: bool = False
    tools: Optional[List[Union[AnthropicTool, Dict[str, Any]]]] = None
    stop_sequences: Optional[List[str]] = None


class AnthropicUsage(BaseModel):
    input_tokens: int
    output_tokens: int


class AnthropicResponse(BaseModel):
    id: str
    type: Literal["message"] = "message"
    role: Literal["assistant"] = "assistant"
    content: List[Union[TextBlock, ToolUseBlock]]
    model: str
    stop_reason: Optional[str] = None
    usage: AnthropicUsage


class AnthropicError(BaseModel):
    type: str
    message: str


class AnthropicErrorResponse(BaseModel):
    type: Literal["error"] = "error"
    error: AnthropicError
