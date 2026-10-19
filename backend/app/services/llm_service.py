"""
LLM Service using Ollama
"""

from typing import List, Dict, Optional, AsyncIterator
from abc import ABC, abstractmethod
import json
import httpx


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
        model: str = "llama3.2:latest",
        base_url: str = "http://localhost:11434"
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def build_prompt(
        self,
        query: str,
        context: List[Dict[str, str]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:

        context_text = "\n\n".join(
            f"[Document {i + 1}]\n{doc.get('text', '')}"
            for i, doc in enumerate(context)
            if doc.get("text")
        )

        history_text = ""
        if conversation_history:
            history_text = "\n\nConversation history:\n" + "\n".join(
                f"{message.get('role', 'user')}: "
                f"{message.get('content', message.get('text', ''))}"
                for message in conversation_history
            )

        if not context_text.strip():
            context_text = "(No relevant document context was retrieved.)"

        return f"""You are a helpful document question-answering assistant.

Answer the question using only the provided document context.
Do not invent facts or use outside knowledge.
If the answer is not available in the context, say:
"I don't have enough information."

Document context:
{context_text}
{history_text}

Question:
{query}

Answer:"""

    async def generate_response(
        self,
        query: str,
        context: List[Dict[str, str]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:

        prompt = self.build_prompt(
            query, context, conversation_history
        )

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            data = response.json()

        return data.get("response", "").strip()

    async def stream_response(
        self,
        query: str,
        context: List[Dict[str, str]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncIterator[str]:

        prompt = self.build_prompt(
            query, context, conversation_history
        )

        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True
                }
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        chunk = json.loads(line)
                        text = chunk.get("response", "")
                        if text:
                            yield text

                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue


def get_llm_service(
    provider: str = "ollama",
    **kwargs
) -> LLMService:

    provider = provider.lower()

    if provider in ["ollama", "local"]:
        return OllamaService(
            model=kwargs.get("model", "llama3.2:latest"),
            base_url=kwargs.get(
                "base_url",
                "http://localhost:11434"
            )
        )

    raise ValueError(f"Unsupported provider: {provider}")