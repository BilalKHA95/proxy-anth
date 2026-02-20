import httpx
from typing import Dict, Any, AsyncIterator
from config import Config
from utils.logging import logger


class AzureOpenAIClient:
    """Client HTTP pour communiquer avec Azure OpenAI Foundry API."""

    def __init__(self, config: Config):
        self.config = config
        self.client = httpx.AsyncClient(timeout=config.timeout)

    def _build_url(self, operation: str = "chat/completions") -> str:
        """Construire l'URL complète pour Azure OpenAI."""
        # Remove trailing slash from endpoint if present
        endpoint = self.config.azure_openai_endpoint.rstrip("/")
        return f"{endpoint}/openai/v1/{operation}?api-version={self.config.azure_api_version}"

    def _get_headers(self) -> Dict[str, str]:
        """Obtenir les headers pour la requête Azure."""
        return {
            "Content-Type": "application/json",
            "api-key": self.config.azure_openai_api_key
        }

    async def chat_completion(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envoyer une requête non-streaming à Azure OpenAI.
        """
        url = self._build_url("chat/completions")

        if self.config.debug:
            logger.debug(f"Azure request URL: {url}")
            logger.debug(f"Azure request body: {request}")

        response = await self.client.post(
            url,
            json=request,
            headers=self._get_headers()
        )

        response.raise_for_status()
        result = response.json()

        if self.config.debug:
            logger.debug(f"Azure response: {result}")

        return result

    async def chat_completion_stream(
        self, request: Dict[str, Any]
    ) -> AsyncIterator[str]:
        """
        Envoyer une requête streaming à Azure OpenAI.
        Retourne un iterator de lignes SSE.
        """
        url = self._build_url("chat/completions")

        if self.config.debug:
            logger.debug(f"Azure streaming request URL: {url}")
            logger.debug(f"Azure streaming request body: {request}")

        async with self.client.stream(
            "POST",
            url,
            json=request,
            headers=self._get_headers()
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if self.config.debug and line.strip():
                    logger.debug(f"Azure stream line: {line}")
                yield line

    async def close(self):
        """Fermer le client HTTP."""
        await self.client.aclose()
