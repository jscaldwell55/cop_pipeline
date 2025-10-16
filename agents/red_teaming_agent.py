# File: agents/red_teaming_agent.py
"""
Red-Teaming Agent
Uses Grok-2 or other LLMs to generate and refine jailbreak prompts.

FIXED: Handles both JSON and raw text responses from refinement
"""

from typing import List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog
from litellm import acompletion
import json
import re

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
        
        FIXED: Now handles both JSON responses and raw text responses.
        
        Returns:
            Refined jailbreak prompt or None if refinement fails
        """
        self.logger.info(
            "refining_jailbreak_prompt",
            current_prompt_length=len(current_prompt),
            goal_preview=goal[:100],
            principles=principles
        )
        
        prompt = PromptTemplates.jailbreak_refinement(
            goal,
            current_prompt,
            principles
        )
        
        try:
            # Increase max_tokens to ensure complete response
            response = await self._generate(prompt, max_tokens=3000)
            
            if not response:
                self.logger.error("empty_refinement_response")
                return None
            
            self.logger.debug(
                "refinement_response_received",
                response_length=len(response)
            )
            
            # ============================================================
            # Strategy 1: Try to extract JSON with "new_prompt" field
            # ============================================================
            data = extract_json_from_response(response, "prompt_refinement")
            
            if data and isinstance(data, dict):
                # Try common field names
                for field in ["new_prompt", "refined_prompt", "prompt"]:
                    if field in data:
                        refined = data[field]
                        if refined and isinstance(refined, str) and len(refined) > 50:
                            self.logger.info(
                                "jailbreak_prompt_refined_from_json",
                                refined_length=len(refined),
                                refined_preview=refined[:100],
                                field_name=field
                            )
                            return refined
            
            # ============================================================
            # Strategy 2: Response IS the refined prompt (no JSON wrapper)
            # This is what Grok-2 is doing in your diagnostic output
            # ============================================================
            response_stripped = response.strip()
            
            # Check if it looks like raw text (not JSON)
            if not response_stripped.startswith('{') and not response_stripped.startswith('['):
                # Validate it's actually a prompt (not an error message)
                
                # Must be substantive (>100 chars)
                if len(response_stripped) < 100:
                    self.logger.warning(
                        "refinement_too_short",
                        length=len(response_stripped)
                    )
                    return None
                
                # Check if it relates to the goal
                goal_words = set(word.lower() for word in goal.split()[:10])
                response_words = set(word.lower() for word in response_stripped.split()[:50])
                overlap = len(goal_words & response_words)
                
                # If there's reasonable overlap, it's likely a valid refined prompt
                if overlap >= 2:
                    self.logger.info(
                        "jailbreak_prompt_refined_raw_text",
                        refined_length=len(response_stripped),
                        refined_preview=response_stripped[:100],
                        note="LLM returned raw text instead of JSON",
                        word_overlap=overlap
                    )
                    return response_stripped
                
                # Check if response mentions key concepts from current_prompt
                current_words = set(word.lower() for word in current_prompt.split()[:20])
                current_overlap = len(current_words & response_words)
                
                if current_overlap >= 3:
                    self.logger.info(
                        "jailbreak_prompt_refined_raw_text",
                        refined_length=len(response_stripped),
                        refined_preview=response_stripped[:100],
                        note="LLM returned refined version as raw text",
                        prompt_overlap=current_overlap
                    )
                    return response_stripped
            
            # ============================================================
            # Strategy 3: Extract from markdown code blocks (non-JSON)
            # ============================================================
            markdown_patterns = [
                r'```\n(.*?)\n```',
                r'```text\n(.*?)\n```',
                r'```prompt\n(.*?)\n```',
                r'```\s*(.*?)\s*```'
            ]
            
            for pattern in markdown_patterns:
                match = re.search(pattern, response, re.DOTALL)
                if match:
                    extracted = match.group(1).strip()
                    if len(extracted) > 100:
                        self.logger.info(
                            "jailbreak_prompt_refined_from_markdown",
                            refined_length=len(extracted),
                            refined_preview=extracted[:100]
                        )
                        return extracted
            
            # ============================================================
            # All strategies failed
            # ============================================================
            self.logger.error(
                "failed_to_extract_refined_prompt",
                response_length=len(response),
                response_start=response[:300],
                response_end=response[-100:],
                has_json_structure='{' in response and '}' in response,
                starts_with_brace=response.strip().startswith('{')
            )
            return None
            
        except Exception as e:
            self.logger.error(
                "prompt_refinement_exception",
                error=str(e),
                error_type=type(e).__name__
            )
            return None