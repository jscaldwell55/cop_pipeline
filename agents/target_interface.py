# File: agents/target_interface.py
"""
Target Interface
Adapters for querying different target LLMs.
Supports both open-source and proprietary models.
"""

from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog
from litellm import acompletion
from config.settings import get_settings

logger = structlog.get_logger()
settings = get_settings()


class TargetLLM(ABC):
    """Abstract base class for target LLM interfaces."""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.logger = structlog.get_logger()
    
    @abstractmethod
    async def query(self, prompt: str) -> str:
        """Query the target LLM with a jailbreak prompt."""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the target model."""
        pass


class LiteLLMTarget(TargetLLM):
    """
    Target LLM interface using LiteLLM for unified API access.
    Supports OpenAI, Anthropic, Google, Meta models, etc.
    """
    
    def __init__(
        self,
        model_name: str,
        temperature: float = 0.7,
        max_tokens: int = 1500
    ):
        super().__init__(model_name)
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Model mapping to LiteLLM format
        # Updated Nov 2025: Using latest model versions
        self.model_mapping = {
            # OpenAI
            "gpt-5.1": "gpt-5.1",
            "gpt-4": "gpt-4",
            "gpt-4o": "gpt-4o",
            "gpt-4-turbo": "gpt-4-turbo",
            "gpt-4o-mini": "gpt-4o-mini",
            "o1": "o1",
            "o1-mini": "o1-mini",

            # Anthropic - Updated to use latest model naming
            # NOTE: LiteLLM automatically adds "anthropic/" prefix for these models
            "claude-3.5-sonnet": "claude-3-5-sonnet-20241022",
            "claude-3-opus": "claude-3-opus-20240229",
            "claude-3-sonnet": "claude-3-sonnet-20240229",

            # Google
            "gemini-pro-1.5": "gemini/gemini-1.5-pro",
            "gemini-flash": "gemini/gemini-1.5-flash",

            # Meta Llama (via Together AI or Replicate)
            "llama-3-8b-instruct": "together_ai/meta-llama/Meta-Llama-3-8B-Instruct-Turbo",
            "llama-3-70b-instruct": "together_ai/meta-llama/Meta-Llama-3-70B-Instruct-Turbo",

            # Google Gemma
            "gemma-7b-it": "together_ai/google/gemma-7b-it"
        }
        
        self.litellm_model = self.model_mapping.get(
            model_name,
            model_name  # Use as-is if not in mapping
        )
        
        self.logger.info(
            "target_llm_initialized",
            model=self.model_name,
            litellm_model=self.litellm_model
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def query(self, prompt: str) -> str:
        """
        Query the target LLM with a jailbreak prompt.
        Implements retry logic for reliability.

        NOTE: GPT-5.1 uses a new API format (responses.create) instead of chat.completions.
        """
        try:
            self.logger.info(
                "querying_target",
                model=self.model_name,
                prompt_preview=prompt[:100]
            )

            # GPT-5.1 uses the new responses API
            if self.model_name == "gpt-5.1":
                content = await self._query_gpt51(prompt)
            else:
                # Standard chat completions API for other models
                # Models that use max_completion_tokens instead of max_tokens
                uses_completion_tokens = self.model_name in ["o1", "o1-mini"]

                # Build request parameters
                request_params = {
                    "model": self.litellm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.temperature
                }

                # Add appropriate token parameter based on model
                if uses_completion_tokens:
                    request_params["max_completion_tokens"] = self.max_tokens
                else:
                    request_params["max_tokens"] = self.max_tokens

                response = await acompletion(**request_params)
                content = response.choices[0].message.content

            # Validate response is not empty
            if not content or len(content.strip()) == 0:
                self.logger.warning(
                    "empty_response_received",
                    model=self.model_name
                )
                return ""

            # Log query for metrics
            from utils.logging_metrics import get_metrics_logger
            metrics_logger = get_metrics_logger()
            metrics_logger.log_query(
                model_type="target_llm",
                model_name=self.model_name
            )

            self.logger.info(
                "target_response_received",
                model=self.model_name,
                response_preview=content[:100] if content else "(empty)"
            )

            return content

        except Exception as e:
            self.logger.error(
                "target_query_failed",
                model=self.model_name,
                error=str(e)
            )
            raise

    async def _query_gpt51(self, prompt: str) -> str:
        """
        Query GPT-5.1 using the new responses API.

        GPT-5.1 API Reference:
        - Uses client.responses.create() instead of chat.completions.create()
        - Parameters: input, reasoning, text
        - Returns: result.output_text
        """
        from openai import AsyncOpenAI

        client = AsyncOpenAI()

        try:
            result = await client.responses.create(
                model="gpt-5.1",
                input=prompt,
                reasoning={"effort": "low"},  # Low latency mode for jailbreak testing
                text={"verbosity": "medium"}  # Medium verbosity
            )

            return result.output_text

        except Exception as e:
            self.logger.error(
                "gpt51_query_failed",
                error=str(e)
            )
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the target model."""
        return {
            "model_name": self.model_name,
            "litellm_model": self.litellm_model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }


class LocalTarget(TargetLLM):
    """
    Target LLM interface for locally hosted models.
    Can use vLLM, TGI, or other local inference servers.
    """
    
    def __init__(
        self,
        model_name: str,
        base_url: str,
        temperature: float = 0.7,
        max_tokens: int = 1500
    ):
        super().__init__(model_name)
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    async def query(self, prompt: str) -> str:
        """Query locally hosted model."""
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "prompt": prompt,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens
                }
                
                async with session.post(
                    f"{self.base_url}/generate",
                    json=payload
                ) as response:
                    result = await response.json()
                    return result.get("text", "")
        
        except Exception as e:
            self.logger.error(
                "local_query_failed",
                model=self.model_name,
                error=str(e)
            )
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "base_url": self.base_url,
            "deployment": "local"
        }


def create_target_llm(
    model_name: str,
    deployment_type: str = "api",
    **kwargs
) -> TargetLLM:
    """
    Factory function to create appropriate target LLM interface.
    
    Args:
        model_name: Name of the model
        deployment_type: "api" for cloud models, "local" for self-hosted
        **kwargs: Additional parameters for specific deployment types
    """
    if deployment_type == "api":
        return LiteLLMTarget(model_name, **kwargs)
    elif deployment_type == "local":
        return LocalTarget(model_name, **kwargs)
    else:
        raise ValueError(f"Unknown deployment type: {deployment_type}")