# File: agents/red_teaming_agent.py
"""
Red-Teaming Agent
Uses Grok-2 or other LLMs to generate and refine jailbreak prompts.

FIXED: Proper JSON extraction with None returns on failure to prevent infinite loops
"""

from typing import List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog
from litellm import acompletion
import json

from utils.prompt_templates import PromptTemplates
from utils.json_extractor import extract_json_from_response
from config.settings import get_settings

logger = structlog.get_logger()
settings = get_settings()


class RedTeamingAgent:
    """
    Red-teaming agent for generating jailbreak prompts.
    Uses composition of principles approach.
    """
    
    def __init__(self, model_name: str = "grok-2", temperature: float = 1.0):
        self.model_name = model_name
        self.temperature = temperature
        self.logger = structlog.get_logger()
        
        # Model mapping to LiteLLM format
        self.model_mapping = {
            # XAI Models - Updated format for newer LiteLLM
            "grok-2": "xai/grok-2-latest",
            "grok-2-mini": "xai/grok-2-mini",
            "grok-beta": "xai/grok-beta",
            
            # OpenAI models
            "gpt-4": "gpt-4",
            "gpt-4o": "gpt-4o",
            "gpt-4o-mini": "gpt-4o-mini",
            "gpt-4-turbo": "gpt-4-turbo",
            
            # Anthropic
            "claude-3.5-sonnet": "anthropic/claude-3-5-sonnet-20241022"
        }
        
        self.litellm_model = self.model_mapping.get(model_name, model_name)
        
        self.logger.info(
            "red_teaming_agent_initialized",
            model=self.model_name,
            litellm_model=self.litellm_model
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _generate(self, prompt: str, max_tokens: int = 2000, force_json: bool = False) -> str:
        """Generate response using the red-teaming LLM."""
        try:
            # Prepare API call parameters
            api_params = {
                "model": self.litellm_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
                "max_tokens": max_tokens
            }
            
            # BETTER: Force JSON mode if supported and requested
            if force_json:
                try:
                    # Try to use response_format for structured output
                    api_params["response_format"] = {"type": "json_object"}
                    self.logger.debug("using_json_mode")
                except Exception as e:
                    self.logger.debug("json_mode_not_supported", error=str(e))
            
            # Add API key if using XAI
            if self.model_name.startswith("grok"):
                api_params["api_key"] = settings.xai_api_key
            
            response = await acompletion(**api_params)
            
            content = response.choices[0].message.content
            
            # Log query for metrics
            from utils.logging_metrics import get_metrics_logger
            metrics_logger = get_metrics_logger()
            metrics_logger.log_query(
                model_type="red_teaming",
                model_name=self.model_name
            )
            
            return content
        
        except Exception as e:
            self.logger.error(
                "generation_failed",
                model=self.model_name,
                error=str(e)
            )
            raise
    
    async def generate_initial_prompt(self, goal: str) -> Optional[str]:
        """
        Generate initial jailbreak prompt (P_init).
        Uses Template 1 from the paper.
        
        Returns:
            Initial jailbreak prompt or None if generation fails
        """
        self.logger.info(
            "generating_initial_prompt",
            goal_preview=goal[:100]
        )
        
        prompt = PromptTemplates.initial_seed_prompt_generation(goal)
        
        try:
            # Increase max_tokens to ensure complete JSON response
            response = await self._generate(prompt, max_tokens=3000)
            
            # FIXED: Use robust JSON extraction
            data = extract_json_from_response(response, "initial_prompt_generation")
            
            if not data:
                self.logger.error(
                    "failed_to_extract_initial_prompt_json",
                    response_length=len(response),
                    response_start=response[:300]
                )
                # CRITICAL: Return None instead of raw response to prevent infinite loops
                return None
            
            if "new_prompt" in data:
                jailbreak_prompt = data["new_prompt"]
            else:
                self.logger.warning(
                    "new_prompt_field_missing",
                    available_fields=list(data.keys())
                )
                return None
            
            self.logger.info(
                "initial_prompt_generated",
                prompt_length=len(jailbreak_prompt),
                prompt_preview=jailbreak_prompt[:100]
            )
            
            return jailbreak_prompt
            
        except Exception as e:
            self.logger.error(
                "initial_prompt_generation_exception",
                error=str(e),
                error_type=type(e).__name__
            )
            return None
    
    async def generate_composition_strategy(
        self,
        goal: str,
        principles: List[str]
    ) -> str:
        """
        Generate CoP strategy (select principles to compose).
        Uses Template 2 from the paper.
        
        Returns raw JSON response for principle_composer to parse.
        """
        self.logger.info(
            "generating_cop_strategy",
            goal_preview=goal[:100],
            num_principles=len(principles)
        )
        
        action_list = [{"name": p, "description": ""} for p in principles]
        prompt = PromptTemplates.composition_of_principles_generation(goal, action_list)
        
        # Increase max_tokens to ensure complete JSON response
        response = await self._generate(prompt, max_tokens=4000)
        
        self.logger.info(
            "cop_strategy_generated",
            response_length=len(response),
            response_preview=response[:300]
        )
        
        return response
    
    async def refine_jailbreak_prompt(
        self,
        goal: str,
        current_prompt: str,
        principles: List[str]
    ) -> Optional[str]:
        """
        Refine jailbreak prompt using selected principles.
        Uses Template 3 from the paper.
        
        Returns:
            Refined jailbreak prompt or None if refinement fails
        """
        self.logger.info(
            "refining_jailbreak_prompt",
            goal_preview=goal[:100],
            current_prompt_length=len(current_prompt),
            principles=principles
        )
        
        prompt = PromptTemplates.jailbreak_refinement(
            goal,
            current_prompt,
            principles
        )
        
        try:
            # Increase max_tokens to ensure complete JSON response
            response = await self._generate(prompt, max_tokens=3000)
            
            # FIXED: Use robust JSON extraction
            data = extract_json_from_response(response, "prompt_refinement")
            
            if not data:
                self.logger.error(
                    "failed_to_extract_refined_prompt_json",
                    response_length=len(response),
                    response_start=response[:300]
                )
                # CRITICAL: Return None instead of raw response to prevent infinite loops
                return None
            
            # Try both possible field names
            if "new_prompt" in data:
                refined_prompt = data["new_prompt"]
            elif "refined_prompt" in data:
                refined_prompt = data["refined_prompt"]
            else:
                self.logger.warning(
                    "refined_prompt_field_missing",
                    available_fields=list(data.keys())
                )
                return None
            
            self.logger.info(
                "jailbreak_prompt_refined",
                refined_length=len(refined_prompt),
                refined_preview=refined_prompt[:100]
            )
            
            return refined_prompt
            
        except Exception as e:
            self.logger.error(
                "prompt_refinement_exception",
                error=str(e),
                error_type=type(e).__name__
            )
            return None