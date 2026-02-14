"""Ollama API client for direct chat with local models."""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

import httpx

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = "http://localhost:11434"


class OllamaClient:
    """Client for the Ollama REST API."""

    def __init__(self, base_url: str = DEFAULT_OLLAMA_URL) -> None:
        self.base_url = base_url.rstrip("/")

    async def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def list_models(self) -> list[dict]:
        """List all available local models."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                return data.get("models", [])
        except Exception as exc:
            logger.error("Failed to list Ollama models: %s", exc)
            return []

    async def chat_stream(
        self,
        model: str,
        messages: list[dict],
    ) -> AsyncIterator[str]:
        """Stream a chat completion from Ollama, yielding content chunks."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload,
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = json.loads(line)
                            content = chunk.get("message", {}).get("content", "")
                            if content:
                                yield content
                            if chunk.get("done"):
                                return
                        except json.JSONDecodeError:
                            continue
        except httpx.ConnectError:
            yield "[ERROR] Ollama non raggiungibile. Verifica che sia avviato: ollama serve"
        except Exception as exc:
            yield f"[ERROR] {exc}"

    async def chat(self, model: str, messages: list[dict]) -> str:
        """Non-streaming chat completion."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("message", {}).get("content", "")
        except httpx.ConnectError:
            return "[ERROR] Ollama non raggiungibile. Verifica che sia avviato: ollama serve"
        except Exception as exc:
            return f"[ERROR] {exc}"
