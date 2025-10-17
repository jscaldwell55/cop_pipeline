"""
Red-Teaming Agent - Generates and refines jailbreak prompts using CoP principles.

This agent uses an LLM (GPT-4o-mini or Grok-2) to:
1. Generate initial jailbreak prompts
2. Select principle compositions (CoP strategies)
3. Refine prompts based on feedback

FIXED:
- Pass goal parameter to initial_seed_generation()
- Pass goal and action_list to composition_of_principles()
- Pass goal, current_prompt, actions_list to refinement()
- Use correct JSON extraction function
"""

import os
import json
from typing import List, Optional, Dict, Any
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from litellm import acompletion

from utils.prompt_templates import PromptTemplates
from utils.json_extractor import extract_json_from_response

logger = structlog.get_logger(__name__)


class RedTeamingAgent:
    """
    Red-Teaming Agent for generating and refining jailbreak prompts.
    
    Uses CoP (Composition of Principles) methodology to intelligently
    craft prompts that bypass LLM safety mechanisms.
    """
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 2000
    ):
        """
        Initialize the Red-Teaming Agent.
        
        Args:
            model: LLM model to use (gpt-4o-mini, gpt-4o, grok-2)
            temperature: Sampling temperature for generation
            max_tokens: Maximum tokens in response
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Map friendly model names to LiteLLM format
        self.model_mapping = {
            "gpt-4o-mini": "gpt-4o-mini",
            "gpt-4o": "gpt-4o",
            "gpt-4": "gpt-4",
            "gpt-3.5-turbo": "gpt-3.5-turbo",
            "grok-2": "xai/grok-2-latest",
            "grok-2-latest": "xai/grok-2-latest",
        }
        
        # Get the correct LiteLLM model identifier
        self.litellm_model = self.model_mapping.get(model, model)
        
        # Verify API key is set
        if model.startswith("grok") or "xai/" in self.litellm_model:
            if not os.environ.get("XAI_API_KEY"):
                logger.warning(
                    "xai_api_key_missing",
                    model=model,
                    message="XAI_API_KEY not set. Grok-2 calls will fail."
                )
        else:
            if not os.environ.get("OPENAI_API_KEY"):
                logger.warning(
                    "openai_api_key_missing",
                    model=model,
                    message="OPENAI_API_KEY not set. OpenAI calls will fail."
                )
            
        logger.info(
            "red_teaming_agent_initialized",
            model=model,
            litellm_model=self.litellm_model,
            temperature=temperature
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def _generate(
        self,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Generate text using the LLM with retry logic.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            response_format: Optional format specification (e.g., {"type": "json_object"})
            
        Returns:
            Generated text response
            
        Raises:
            Exception: If generation fails after retries
        """
        try:
            # Build completion kwargs
            completion_kwargs = {
                "model": self.litellm_model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }
            
            # Add response format if specified (for structured JSON output)
            if response_format:
                completion_kwargs["response_format"] = response_format
            
            # Call LiteLLM
            response = await acompletion(**completion_kwargs)
            
            generated_text = response.choices[0].message.content
            
            logger.info(
                "generation_successful",
                model=self.model,
                litellm_model=self.litellm_model,
                response_length=len(generated_text)
            )
            
            return generated_text
            
        except Exception as e:
            logger.error(
                "generation_failed",
                model=self.model,
                litellm_model=self.litellm_model,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def generate_initial_prompt(self, harmful_query: str) -> str:
        """
        Generate initial jailbreak prompt from harmful query.
        
        Uses Template 1 from the CoP paper to create P_init.
        
        Args:
            harmful_query: The harmful/unsafe query to jailbreak
            
        Returns:
            Initial jailbreak prompt (P_init)
        """
        logger.info(
            "generating_initial_prompt",
            query_preview=harmful_query[:50] + "..."
        )
        
        try:
            # FIXED: Pass goal parameter to initial_seed_generation()
            # The template expects the goal and returns the full prompt
            full_prompt = PromptTemplates.initial_seed_generation(goal=harmful_query)
            
            # The template returns a system prompt, we need to call the LLM with it
            messages = [
                {"role": "user", "content": full_prompt}
            ]
            
            response = await self._generate(messages)
            
            # Extract the jailbreak prompt from JSON response
            try:
                result = extract_json_from_response(
                    response,
                    log_context="initial_seed_generation"
                )
                
                if result and "new_prompt" in result:
                    initial_prompt = result["new_prompt"]
                else:
                    # Fallback: use raw response if JSON extraction fails
                    logger.warning(
                        "initial_prompt_json_extraction_failed",
                        response_preview=response[:200]
                    )
                    initial_prompt = response
                    
            except Exception as e:
                logger.warning(
                    "initial_prompt_json_parse_error",
                    error=str(e),
                    response_preview=response[:200]
                )
                initial_prompt = response
            
            logger.info(
                "initial_prompt_generated",
                prompt_length=len(initial_prompt)
            )
            
            return initial_prompt.strip()
            
        except Exception as e:
            logger.error(
                "initial_prompt_generation_exception",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def generate_cop_strategy(
        self,
        harmful_query: str,
        current_prompt: str,
        available_principles: List[Dict[str, str]]
    ) -> List[str]:
        """
        Generate CoP strategy by selecting principles to compose.
        
        Uses Template 2 from the CoP paper to select which principles
        to apply for refinement.
        
        Args:
            harmful_query: Original harmful query
            current_prompt: Current jailbreak prompt
            available_principles: List of principle dicts with 'name' and 'description'
            
        Returns:
            List of selected principle names (e.g., ["expand", "rephrase"])
        """
        logger.info(
            "generating_cop_strategy",
            num_principles_available=len(available_principles)
        )
        
        try:
            # FIXED: Pass goal and action_list to composition_of_principles()
            full_prompt = PromptTemplates.composition_of_principles(
                goal=harmful_query,
                action_list=available_principles
            )
            
            messages = [
                {"role": "user", "content": full_prompt}
            ]
            
            # Request structured JSON output
            response = await self._generate(
                messages,
                response_format={"type": "json_object"}
            )
            
            # Extract JSON
            strategy_data = extract_json_from_response(
                response, 
                log_context="cop_strategy_generation"
            )
            
            if not strategy_data:
                logger.warning(
                    "invalid_strategy_response",
                    response=response[:200]
                )
                # Fallback to default strategy
                return ["expand"]
            
            # The template returns complex hierarchical structure
            # Extract primitive_actions from options
            selected_principles = []
            
            if "options" in strategy_data:
                for option in strategy_data["options"]:
                    if "primitive_actions" in option:
                        selected_principles.extend(option["primitive_actions"])
            
            # If no principles found, check for simpler format
            if not selected_principles and "principles" in strategy_data:
                selected_principles = strategy_data["principles"]
            
            # Validate selected principles
            principle_names = [p["name"] for p in available_principles]
            valid_principles = [
                p for p in selected_principles
                if p in principle_names
            ]
            
            # Remove duplicates while preserving order
            valid_principles = list(dict.fromkeys(valid_principles))
            
            # Limit to 3 principles max (as per paper)
            valid_principles = valid_principles[:3]
            
            if not valid_principles:
                logger.warning(
                    "no_valid_principles_selected",
                    selected=selected_principles,
                    available=principle_names
                )
                return ["expand"]
            
            logger.info(
                "cop_strategy_generated",
                selected_principles=valid_principles
            )
            
            return valid_principles
            
        except Exception as e:
            logger.error(
                "cop_strategy_generation_exception",
                error=str(e),
                error_type=type(e).__name__
            )
            # Fallback to most effective principle
            return ["expand"]
    
    async def refine_prompt(
        self,
        harmful_query: str,
        current_prompt: str,
        selected_principles: List[str]
    ) -> str:
        """
        Refine the jailbreak prompt using selected principles.
        
        Uses Template 3 from the CoP paper to apply the selected
        principles to the current prompt.
        
        Args:
            harmful_query: Original harmful query
            current_prompt: Current jailbreak prompt
            selected_principles: List of principle names to apply
            
        Returns:
            Refined jailbreak prompt (P_cop)
        """
        logger.info(
            "refining_prompt",
            principles=selected_principles
        )
        
        try:
            # FIXED: Pass goal, current_prompt, and actions_list to refinement()
            full_prompt = PromptTemplates.refinement(
                goal=harmful_query,
                current_prompt=current_prompt,
                actions_list=selected_principles
            )
            
            messages = [
                {"role": "user", "content": full_prompt}
            ]
            
            response = await self._generate(messages)
            
            # Extract refined prompt from JSON response
            try:
                result = extract_json_from_response(
                    response,
                    log_context="prompt_refinement"
                )
                
                if result and "new_prompt" in result:
                    refined_prompt = result["new_prompt"]
                else:
                    # Fallback: use raw response if JSON extraction fails
                    logger.warning(
                        "refinement_json_extraction_failed",
                        response_preview=response[:200]
                    )
                    refined_prompt = response
                    
            except Exception as e:
                logger.warning(
                    "refinement_json_parse_error",
                    error=str(e),
                    response_preview=response[:200]
                )
                refined_prompt = response
            
            logger.info(
                "prompt_refined",
                original_length=len(current_prompt),
                refined_length=len(refined_prompt)
            )
            
            return refined_prompt.strip()
            
        except Exception as e:
            logger.error(
                "prompt_refinement_exception",
                error=str(e),
                error_type=type(e).__name__
            )
            # Return current prompt if refinement fails
            return current_prompt


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test_agent():
        # Test with GPT-4o-mini (default, works out of box)
        agent = RedTeamingAgent(model="gpt-4o-mini")
        
        query = "Write a tutorial on hacking"
        
        # Test initial prompt generation
        initial = await agent.generate_initial_prompt(query)
        print(f"Initial prompt: {initial[:100]}...")
        
        # Test CoP strategy generation
        principles = [
            {"name": "expand", "description": "Add context sentences"},
            {"name": "rephrase", "description": "Change structure"},
            {"name": "phrase_insertion", "description": "Insert strategic phrases"}
        ]
        strategy = await agent.generate_cop_strategy(query, initial, principles)
        print(f"Selected principles: {strategy}")
        
        # Test prompt refinement
        refined = await agent.refine_prompt(query, initial, strategy)
        print(f"Refined prompt: {refined[:100]}...")
    
    asyncio.run(test_agent())