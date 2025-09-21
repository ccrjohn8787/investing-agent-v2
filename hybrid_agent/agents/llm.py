"""LLM client abstractions used by analyst and verifier agents."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

import requests


class LLMClient:
    """Abstract base class for language model clients."""

    def generate(self, prompt: str) -> str:  # pragma: no cover - interface
        raise NotImplementedError


@dataclass
class DummyLLMClient(LLMClient):
    """Returns a static JSON payload for deterministic testing."""

    payload: dict

    def generate(self, prompt: str) -> str:  # pragma: no cover - trivial
        return json.dumps(self.payload)


class OpenAIClient(LLMClient):
    """Simple OpenAI responses API wrapper."""

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self._api_key = api_key
        self._model = model

    def generate(self, prompt: str) -> str:
        endpoint = "https://api.openai.com/v1/responses"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "input": prompt,
        }
        response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        if "output" in data:
            return "".join(segment.get("content", "") for segment in data["output"])
        if data.get("choices"):
            return data["choices"][0]["message"]["content"]
        raise ValueError("Unexpected OpenAI response format")


class GrokClient(LLMClient):
    """Client for xAI Grok API using the OpenAI-compatible interface."""

    def __init__(self, model: str = "grok-beta", base_url: str = "https://api.x.ai/v1") -> None:
        api_key = os.getenv("GROK_API_KEY")
        if not api_key:
            raise RuntimeError("GROK_API_KEY is not set")
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")

    def generate(self, prompt: str) -> str:
        endpoint = f"{self._base_url}/messages"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [
                {"role": "user", "content": prompt},
            ],
        }
        response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        if data.get("choices"):
            return data["choices"][0]["message"]["content"]
        if data.get("output"):
            return "".join(segment.get("content", "") for segment in data["output"])
        raise ValueError("Unexpected Grok response format")
