from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import httpx
from contextlib import asynccontextmanager

from models.anthropic import AnthropicRequest
from converters.request_converter import convert_anthropic_to_azure_request
from converters.response_converter import convert_azure_to_anthropic_response
from converters.streaming_converter import convert_openai_stream_to_anthropic
from services.azure_client import AzureOpenAIClient
from config import get_config
from utils.logging import logger


# Global Azure client
azure_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    global azure_client
    config = get_config()
    azure_client = AzureOpenAIClient(config)
    logger.info("Proxy server started")
    logger.info(f"Azure endpoint: {config.azure_openai_endpoint}")
    logger.info(f"Model mapping: {config.model_mapping}")
    yield
    # Cleanup
    if azure_client:
        await azure_client.close()
    logger.info("Proxy server stopped")


app = FastAPI(
    title="Claude Code Router → Azure OpenAI Foundry Proxy",
    description="Proxy to convert Anthropic Messages API format to Azure OpenAI format",
    version="1.0.0",
    lifespan=lifespan
)


@app.post("/v1/messages")
async def messages_endpoint(request: AnthropicRequest):
    """
    Endpoint compatible with Anthropic Messages API.
    Converts requests to Azure OpenAI format and responses back to Anthropic format.
    """
    try:
        config = get_config()

        logger.info(f"Received request for model: {request.model}")
        logger.info(f"Stream: {request.stream}, Max tokens: {request.max_tokens}")

        # 1. Convert Anthropic request → Azure request
        azure_request = convert_anthropic_to_azure_request(request, config)

        # 2. Call Azure OpenAI
        if request.stream:
            # Streaming response
            logger.info("Processing streaming request")
            openai_stream = azure_client.chat_completion_stream(azure_request)
            anthropic_stream = convert_openai_stream_to_anthropic(openai_stream)

            return StreamingResponse(
                anthropic_stream,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        else:
            # Non-streaming response
            logger.info("Processing non-streaming request")
            azure_response = await azure_client.chat_completion(azure_request)

            # 3. Convert Azure response → Anthropic response
            anthropic_response = convert_azure_to_anthropic_response(azure_response)

            logger.info(f"Response ID: {anthropic_response['id']}, Stop reason: {anthropic_response['stop_reason']}")

            return JSONResponse(content=anthropic_response)

    except httpx.HTTPStatusError as e:
        logger.error(f"Azure API error: {e.response.status_code} - {e.response.text}")
        # Convert Azure error to Anthropic error format
        error_response = {
            "type": "error",
            "error": {
                "type": "api_error" if e.response.status_code >= 500 else "invalid_request_error",
                "message": f"Azure API error: {e.response.text}"
            }
        }
        return JSONResponse(
            content=error_response,
            status_code=e.response.status_code
        )

    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        error_response = {
            "type": "error",
            "error": {
                "type": "api_error",
                "message": f"Internal server error: {str(e)}"
            }
        }
        return JSONResponse(
            content=error_response,
            status_code=500
        )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "proxy": "claude-code-router-to-azure",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Claude Code Router → Azure OpenAI Foundry Proxy",
        "version": "1.0.0",
        "endpoints": {
            "messages": "/v1/messages",
            "health": "/health"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
