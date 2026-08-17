"""
LLM Service using Ollama
"""

from typing import List, Dict, Optional, AsyncIterator
from abc import ABC, abstractmethod
import requests
import json


class LLMService(ABC):

    @abstractmethod
    async def generate_response(
        self,
        query: str,
        context: List[Dict[str, str]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        pass

    @abstractmethod
    async def stream_response(
        self,
        query: str,
        context: List[Dict[str, str]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncIterator[str]:
        pass


class OllamaService(LLMService):

    def __init__(
        self,
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434"
    ):
        self.model = model
        self.base_url = base_url

    def build_prompt(self, query, context):

        context_text = "\n\n".join(
            [
                f"[Document {i+1}]\n{doc.get('text', '')}"
                for i, doc in enumerate(context)
            ]
        )

        return f"""
You are a helpful AI assistant.

Answer ONLY using the provided context.

If the answer is not present in the context, reply:

I don't have enough information.

Context:

{context_text}

Question:

{query}

Answer:
"""

    async def generate_response(
        self,
        query: str,
        context: List[Dict[str, str]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:

        prompt = self.build_prompt(query, context)

        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False
            },
            timeout=300
        )

        response.raise_for_status()

        return response.json()["response"]

    async def stream_response(
        self,
        query: str,
        context: List[Dict[str, str]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncIterator[str]:

        prompt = self.build_prompt(query, context)

        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": True
            },
            stream=True,
            timeout=300
        )

        response.raise_for_status()

        for line in response.iter_lines():

            if not line:
                continue

            try:
                chunk = json.loads(line.decode())

                if "response" in chunk:
                    yield chunk["response"]

            except Exception:
                continue


def get_llm_service(
    provider: str = "ollama",
    **kwargs
) -> LLMService:

    provider = provider.lower()

    if provider in ["ollama", "local"]:
        return OllamaService(
            model=kwargs.get("model", "llama3.2"),
            base_url=kwargs.get(
                "base_url",
                "http://localhost:11434"
            )
        )

    raise ValueError(f"Unsupported provider: {provider}")