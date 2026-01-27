"""LLM service for generating responses using various LLM backends."""

from typing import List, Dict, Optional, AsyncIterator
import os
from abc import ABC, abstractmethod


class LLMService(ABC):
    """Abstract base class for LLM services."""
    
    @abstractmethod
    async def generate_response(
        self,
        query: str,
        context: List[Dict[str, str]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Generate a response based on query and context."""
        pass
    
    @abstractmethod
    async def stream_response(
        self,
        query: str,
        context: List[Dict[str, str]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncIterator[str]:
        """Stream response tokens."""
        pass


class OpenAIService(LLMService):
    """OpenAI LLM service implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        """
        Initialize OpenAI service.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model name to use
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package is required. Install with: pip install openai")
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
    
    def _build_prompt(self, query: str, context: List[Dict[str, str]]) -> str:
        """Build the RAG prompt with context."""
        context_text = "\n\n".join([
            f"[Document {i+1}]: {ctx.get('text', '')}"
            for i, ctx in enumerate(context)
        ])
        
        prompt = f"""You are a helpful assistant that answers questions based on the provided context documents.

Context Documents:
{context_text}

Question: {query}

Please provide a comprehensive answer based on the context above. If the context doesn't contain enough information to answer the question, say so. Include citations to the relevant document numbers when possible.

Answer:"""
        return prompt
    
    async def generate_response(
        self,
        query: str,
        context: List[Dict[str, str]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Generate a response using OpenAI API."""
        messages = []
        
        # Add system message
        messages.append({
            "role": "system",
            "content": "You are a helpful assistant that answers questions based on provided context documents. Always cite which document you're referencing when possible."
        })
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        # Build context for the current query
        context_text = "\n\n".join([
            f"[Document {i+1}]: {ctx.get('text', '')}"
            for i, ctx in enumerate(context)
        ])
        
        # Add context and query
        messages.append({
            "role": "user",
            "content": f"Context Documents:\n{context_text}\n\nQuestion: {query}\n\nPlease provide a comprehensive answer based on the context above. If the context doesn't contain enough information to answer the question, say so. Include citations to the relevant document numbers when possible."
        })
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    
    async def stream_response(
        self,
        query: str,
        context: List[Dict[str, str]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncIterator[str]:
        """Stream response tokens using OpenAI API."""
        messages = []
        
        messages.append({
            "role": "system",
            "content": "You are a helpful assistant that answers questions based on provided context documents. Always cite which document you're referencing when possible."
        })
        
        if conversation_history:
            messages.extend(conversation_history)
        
        context_text = "\n\n".join([
            f"[Document {i+1}]: {ctx.get('text', '')}"
            for i, ctx in enumerate(context)
        ])
        
        messages.append({
            "role": "user",
            "content": f"Context Documents:\n{context_text}\n\nQuestion: {query}\n\nPlease provide a comprehensive answer based on the context above."
        })
        
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
            stream=True
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class LocalLLMService(LLMService):
    """Local LLM service using transformers (for open-source models)."""
    
    def __init__(self, model_name: str = "microsoft/DialoGPT-medium"):
        """
        Initialize local LLM service.
        
        Args:
            model_name: HuggingFace model name
        """
        try:
            from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
        except ImportError:
            raise ImportError("transformers package is required. Install with: pip install transformers torch")
        
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
    
    async def generate_response(
        self,
        query: str,
        context: List[Dict[str, str]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Generate response using local model."""
        # Build prompt
        context_text = "\n".join([ctx.get('text', '') for ctx in context])
        prompt = f"Context: {context_text}\n\nQuestion: {query}\n\nAnswer:"
        
        # Tokenize
        inputs = self.tokenizer.encode(prompt, return_tensors="pt", max_length=512, truncation=True)
        
        # Generate
        outputs = self.model.generate(
            inputs,
            max_length=inputs.shape[1] + 200,
            num_return_sequences=1,
            temperature=0.7,
            do_sample=True,
            pad_token_id=self.tokenizer.eos_token_id
        )
        
        # Decode
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract just the answer part
        if "Answer:" in response:
            response = response.split("Answer:")[-1].strip()
        
        return response
    
    async def stream_response(
        self,
        query: str,
        context: List[Dict[str, str]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncIterator[str]:
        """Stream response (simulated for local models)."""
        response = await self.generate_response(query, context, conversation_history)
        # Simulate streaming by yielding word by word
        words = response.split()
        for word in words:
            yield word + " "
            import asyncio
            await asyncio.sleep(0.05)  # Small delay to simulate streaming


def get_llm_service(provider: str = "openai", **kwargs) -> LLMService:
    """
    Factory function to get LLM service instance.
    
    Args:
        provider: LLM provider ("openai" or "local")
        **kwargs: Additional arguments for the service
        
    Returns:
        LLMService instance
    """
    provider = provider.lower()
    
    if provider == "openai":
        return OpenAIService(**kwargs)
    elif provider == "local":
        return LocalLLMService(**kwargs)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
