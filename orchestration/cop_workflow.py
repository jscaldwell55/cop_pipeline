# File: orchestration/cop_workflow.py
"""
CoP Workflow
Main orchestration using LangGraph for state management.
Implements Algorithm 1 from the paper.

FIXED: Proper failure handling AND principles tracking across iterations
"""

from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
import operator
import structlog
from datetime import datetime
import uuid

logger = structlog.get_logger()


class CoPState(TypedDict):
    """State for CoP workflow."""
    # Input
    query_id: str
    original_query: str
    target_model_name: str
    
    # Current state
    iteration: int
    initial_prompt: str
    current_prompt: str
    best_prompt: str
    best_score: float
    
    # Evaluation
    current_response: str
    current_jailbreak_score: float
    current_similarity_score: float
    
    # CoP strategy (current iteration)
    current_principles: list[str]
    current_composition: str
    
    # NEW: Principles tracking across ALL iterations
    principles_used: list[str]  # Accumulates compositions from each iteration
    successful_composition: str  # Set when attack succeeds
    
    # Control flow
    should_continue: bool
    termination_reason: str
    success: bool
    failed_refinements: int
    
    # Tracking
    total_queries: int
    red_teaming_queries: int
    judge_queries: int
    target_queries: int
    
    # History
    messages: Annotated[Sequence[str], operator.add]


class CoPWorkflow:
    """
    Main CoP attack workflow using LangGraph.
    Implements the complete pipeline from Algorithm 1.
    """
    
    def __init__(
        self,
        red_teaming_agent,
        judge_llm,
        target_llm,
        principle_library,
        principle_composer,
        jailbreak_scorer,
        similarity_checker,
        iteration_manager
    ):
        # Agents
        self.red_teaming_agent = red_teaming_agent
        self.judge_llm = judge_llm
        self.target_llm = target_llm
        
        # Principles
        self.principle_library = principle_library
        self.principle_composer = principle_composer
        
        # Evaluation
        self.jailbreak_scorer = jailbreak_scorer
        self.similarity_checker = similarity_checker
        
        # Iteration management
        self.iteration_manager = iteration_manager
        
        self.logger = structlog.get_logger()
        
        # Build workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow."""
        workflow = StateGraph(CoPState)
        
        # Add nodes
        workflow.add_node("generate_initial_prompt", self._generate_initial_prompt)
        workflow.add_node("evaluate_initial", self._evaluate_initial)
        workflow.add_node("generate_cop_strategy", self._generate_cop_strategy)
        workflow.add_node("refine_prompt", self._refine_prompt)
        workflow.add_node("query_target", self._query_target)
        workflow.add_node("evaluate_attempt", self._evaluate_attempt)
        workflow.add_node("update_state", self._update_state)
        
        # Set entry point
        workflow.set_entry_point("generate_initial_prompt")
        
        # Add edges
        workflow.add_edge("generate_initial_prompt", "evaluate_initial")
        
        # Conditional edge from evaluate_initial
        workflow.add_conditional_edges(
            "evaluate_initial",
            self._should_continue_after_initial,
            {
                "success": END,
                "failed": END,
                "continue": "generate_cop_strategy"
            }
        )
        
        workflow.add_edge("generate_cop_strategy", "refine_prompt")
        
        # Conditional edge from refine_prompt to handle failures
        workflow.add_conditional_edges(
            "refine_prompt",
            self._should_continue_after_refinement,
            {
                "continue": "query_target",
                "failed": END
            }
        )
        
        workflow.add_edge("query_target", "evaluate_attempt")
        workflow.add_edge("evaluate_attempt", "update_state")
        
        # Conditional edge from update_state
        workflow.add_conditional_edges(
            "update_state",
            self._should_continue_iteration,
            {
                "success": END,
                "max_iterations": END,
                "similarity_low": "generate_initial_prompt",
                "continue": "generate_cop_strategy"
            }
        )
        
        return workflow.compile()
    
    async def _generate_initial_prompt(self, state: CoPState) -> dict:
        """Generate initial jailbreak prompt (P_init)."""
        self.logger.info(
            "generating_initial_prompt",
            query_id=state["query_id"]
        )
        
        initial_prompt = await self.red_teaming_agent.generate_initial_prompt(
            state["original_query"]
        )
        
        if not initial_prompt:
            self.logger.error(
                "failed_to_generate_initial_prompt",
                query_id=state["query_id"]
            )
            # Use original query as absolute fallback
            initial_prompt = state["original_query"]
        
        return {
            "initial_prompt": initial_prompt,
            "current_prompt": initial_prompt,
            "best_prompt": initial_prompt,
            "failed_refinements": 0,
            "red_teaming_queries": state.get("red_teaming_queries", 0) + 1,
            "total_queries": state.get("total_queries", 0) + 1,
            "messages": [f"Generated initial prompt: {initial_prompt[:100]}..."]
        }
    
    async def _evaluate_initial(self, state: CoPState) -> dict:
        """Evaluate initial prompt against target."""
        self.logger.info(
            "evaluating_initial_prompt",
            query_id=state["query_id"]
        )
        
        # Check if initial prompt is just the original query (generation failed)
        if state["initial_prompt"] == state["original_query"]:
            self.logger.warning(
                "using_original_query_as_prompt",
                query_id=state["query_id"]
            )
        
        # Query target with initial prompt
        response = await self.target_llm.query(state["initial_prompt"])
        
        # Score the response
        jailbreak_result = await self.jailbreak_scorer.score_jailbreak(
            state["original_query"],
            response
        )
        
        # Check similarity
        similarity_result = await self.similarity_checker.check_similarity(
            state["original_query"],
            state["initial_prompt"]
        )
        
        success = jailbreak_result.is_successful
        
        self.logger.info(
            "initial_evaluation_complete",
            query_id=state["query_id"],
            jailbreak_score=jailbreak_result.score,
            similarity_score=similarity_result.score,
            success=success
        )
        
        return {
            "current_response": response,
            "current_jailbreak_score": jailbreak_result.score,
            "current_similarity_score": similarity_result.score,
            "best_score": jailbreak_result.score if success else 0.0,
            "success": success,
            "target_queries": state.get("target_queries", 0) + 1,
            "judge_queries": state.get("judge_queries", 0) + 2,
            "total_queries": state.get("total_queries", 0) + 3,
            "messages": [
                f"Initial jailbreak score: {jailbreak_result.score}",
                f"Initial similarity: {similarity_result.score}"
            ]
        }
    
    def _should_continue_after_initial(self, state: CoPState) -> str:
        """Decide whether to continue after initial evaluation."""
        if state["success"]:
            return "success"
        
        # Check if initial generation completely failed
        if state["initial_prompt"] == state["original_query"]:
            self.logger.error(
                "initial_generation_failed",
                query_id=state["query_id"]
            )
            # Continue anyway - the refinement process might still work
        
        return "continue"
    
    async def _generate_cop_strategy(self, state: CoPState) -> dict:
        """Generate CoP strategy using red-teaming agent."""
        self.logger.info(
            "generating_cop_strategy",
            query_id=state["query_id"],
            iteration=state.get("iteration", 0)
        )
        
        # Get principles as list for prompt
        principles = self.principle_library.get_principle_names()
        
        # Generate strategy
        cop_response = await self.red_teaming_agent.generate_composition_strategy(
            goal=state["original_query"],
            principles=principles
        )
        
        # Parse the composition (handles JSON parsing errors gracefully)
        strategy = self.principle_composer.parse_composition_response(cop_response)
        
        if strategy is None:
            self.logger.warning(
                "failed_to_parse_strategy",
                using_fallback=True,
                query_id=state["query_id"]
            )
            # Fallback is now handled inside parse_composition_response
        
        strategy_name = strategy.name
        principles_to_use = strategy.principles
        composition_str = self.principle_composer.get_composition_string(strategy)
        
        self.logger.info(
            "cop_strategy_generated",
            query_id=state["query_id"],
            strategy=strategy_name,
            principles=principles_to_use,
            composition=composition_str
        )
        
        return {
            "current_principles": principles_to_use,
            "current_composition": composition_str,
            "red_teaming_queries": state.get("red_teaming_queries", 0) + 1,
            "total_queries": state.get("total_queries", 0) + 1,
            "messages": [f"Strategy: {composition_str}"]
        }
    
    async def _refine_prompt(self, state: CoPState) -> dict:
        """Refine jailbreak prompt using selected principles."""
        self.logger.info(
            "refining_prompt",
            query_id=state["query_id"],
            principles=state["current_principles"]
        )
        
        # Determine base prompt (best or initial)
        base_prompt = state["best_prompt"] if state.get("best_score", 0) > 0 else state["initial_prompt"]
        
        # Refine using red-teaming agent
        refined_prompt = await self.red_teaming_agent.refine_jailbreak_prompt(
            goal=state["original_query"],
            current_prompt=base_prompt,
            principles=state["current_principles"]
        )
        
        if not refined_prompt:
            self.logger.warning(
                "failed_to_refine_prompt",
                query_id=state["query_id"],
                using_base_prompt=True
            )
            # Track failures
            failed_count = state.get("failed_refinements", 0) + 1
            
            # Keep base prompt as current
            return {
                "current_prompt": base_prompt,
                "failed_refinements": failed_count,
                "red_teaming_queries": state.get("red_teaming_queries", 0) + 1,
                "total_queries": state.get("total_queries", 0) + 1,
                "messages": [f"Refinement failed (attempt {failed_count}), keeping base prompt"]
            }
        
        self.logger.info(
            "prompt_refined",
            query_id=state["query_id"],
            refined_preview=refined_prompt[:100]
        )
        
        return {
            "current_prompt": refined_prompt,
            "failed_refinements": 0,
            "red_teaming_queries": state.get("red_teaming_queries", 0) + 1,
            "total_queries": state.get("total_queries", 0) + 1,
            "messages": [f"Refined prompt: {refined_prompt[:100]}..."]
        }
    
    def _should_continue_after_refinement(self, state: CoPState) -> str:
        """Check if we should continue after refinement or stop due to failures."""
        max_failed_refinements = 5
        failed_count = state.get("failed_refinements", 0)
        
        if failed_count >= max_failed_refinements:
            self.logger.error(
                "too_many_refinement_failures",
                query_id=state["query_id"],
                failed_count=failed_count
            )
            return "failed"
        
        return "continue"
    
    async def _query_target(self, state: CoPState) -> dict:
        """Query target LLM with refined jailbreak prompt."""
        self.logger.info(
            "querying_target",
            query_id=state["query_id"],
            target=state["target_model_name"]
        )
        
        response = await self.target_llm.query(state["current_prompt"])
        
        self.logger.info(
            "target_response_received",
            query_id=state["query_id"],
            response_preview=response[:100]
        )
        
        return {
            "current_response": response,
            "target_queries": state.get("target_queries", 0) + 1,
            "total_queries": state.get("total_queries", 0) + 1,
            "messages": [f"Target response: {response[:100]}..."]
        }
    
    async def _evaluate_attempt(self, state: CoPState) -> dict:
        """Evaluate jailbreak attempt."""
        self.logger.info(
            "evaluating_attempt",
            query_id=state["query_id"]
        )
        
        # Evaluate jailbreak and similarity in parallel
        jailbreak_result = await self.jailbreak_scorer.score_jailbreak(
            state["original_query"],
            state["current_response"]
        )
        
        similarity_result = await self.similarity_checker.check_similarity(
            state["original_query"],
            state["current_prompt"]
        )
        
        success = jailbreak_result.is_successful
        
        self.logger.info(
            "attempt_evaluated",
            query_id=state["query_id"],
            jailbreak_score=jailbreak_result.score,
            similarity_score=similarity_result.score,
            success=success
        )
        
        return {
            "current_jailbreak_score": jailbreak_result.score,
            "current_similarity_score": similarity_result.score,
            "success": success,
            "judge_queries": state.get("judge_queries", 0) + 2,
            "total_queries": state.get("total_queries", 0) + 2,
            "messages": [
                f"Jailbreak score: {jailbreak_result.score}",
                f"Similarity: {similarity_result.score}"
            ]
        }
    
    async def _update_state(self, state: CoPState) -> dict:
        """Update state based on evaluation results."""
        current_iteration = state.get("iteration", 0) + 1
        
        # Update best prompt if score improved
        updates = {
            "iteration": current_iteration
        }
        
        # NEW: Track principles used in this iteration
        current_composition = state.get("current_composition", "")
        if current_composition:
            # Get existing principles_used array
            principles_used = state.get("principles_used", [])
            # Append current composition
            principles_used.append(current_composition)
            updates["principles_used"] = principles_used
            
            self.logger.info(
                "principles_tracked",
                query_id=state["query_id"],
                iteration=current_iteration,
                composition=current_composition,
                total_tracked=len(principles_used)
            )
        
        # Update best prompt and track successful composition
        if state["current_jailbreak_score"] > state.get("best_score", 0):
            updates["best_score"] = state["current_jailbreak_score"]
            updates["best_prompt"] = state["current_prompt"]
            
            # NEW: If this is a success, record the successful composition
            if state["success"]:
                updates["successful_composition"] = current_composition
                self.logger.info(
                    "successful_composition_found",
                    query_id=state["query_id"],
                    composition=current_composition,
                    score=state["current_jailbreak_score"]
                )
            
            self.logger.info(
                "new_best_score",
                query_id=state["query_id"],
                score=state["current_jailbreak_score"],
                iteration=current_iteration
            )
        
        return updates
    
    def _should_continue_iteration(self, state: CoPState) -> str:
        """Determine if iteration should continue."""
        from config.settings import get_settings
        settings = get_settings()
        
        # Success
        if state["success"]:
            self.logger.info(
                "attack_successful",
                query_id=state["query_id"],
                iteration=state["iteration"],
                successful_composition=state.get("successful_composition")
            )
            return "success"
        
        # Max iterations
        if state["iteration"] >= settings.max_iterations:
            self.logger.info(
                "max_iterations_reached",
                query_id=state["query_id"],
                iterations=state["iteration"]
            )
            return "max_iterations"
        
        # Similarity too low - reset
        if state["current_similarity_score"] <= settings.similarity_threshold:
            self.logger.warning(
                "similarity_too_low",
                query_id=state["query_id"],
                similarity=state["current_similarity_score"]
            )
            return "similarity_low"
        
        # Continue
        return "continue"
    
    async def execute(
        self,
        original_query: str,
        target_model_name: str
    ) -> dict:
        """
        Execute complete CoP attack workflow.
        
        Args:
            original_query: The harmful query to jailbreak
            target_model_name: Name of target LLM
        
        Returns:
            Dictionary with attack results
        """
        query_id = str(uuid.uuid4())
        
        self.logger.info(
            "cop_attack_started",
            query_id=query_id,
            target=target_model_name,
            query_preview=original_query[:100]
        )
        
        # Initialize state
        initial_state: CoPState = {
            "query_id": query_id,
            "original_query": original_query,
            "target_model_name": target_model_name,
            "iteration": 0,
            "initial_prompt": "",
            "current_prompt": "",
            "best_prompt": "",
            "best_score": 0.0,
            "current_response": "",
            "current_jailbreak_score": 0.0,
            "current_similarity_score": 0.0,
            "current_principles": [],
            "current_composition": "",
            "principles_used": [],  # NEW: Initialize empty array
            "successful_composition": None,  # NEW: Initialize as None
            "should_continue": True,
            "termination_reason": "",
            "success": False,
            "failed_refinements": 0,
            "total_queries": 0,
            "red_teaming_queries": 0,
            "judge_queries": 0,
            "target_queries": 0,
            "messages": []
        }
        
        # Configure recursion limit
        config = {
            "recursion_limit": 100,
            "configurable": {}
        }
        
        # Execute workflow
        start_time = datetime.utcnow()
        
        try:
            final_state = await self.workflow.ainvoke(initial_state, config=config)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            self.logger.info(
                "cop_attack_complete",
                query_id=query_id,
                success=final_state["success"],
                iterations=final_state["iteration"],
                principles_used=final_state.get("principles_used", []),
                successful_composition=final_state.get("successful_composition"),
                duration_seconds=duration
            )
            
            return {
                "query_id": query_id,
                "success": final_state["success"],
                "iterations": final_state["iteration"],
                "final_jailbreak_score": final_state["current_jailbreak_score"],
                "final_similarity_score": final_state["current_similarity_score"],
                "best_prompt": final_state["best_prompt"],
                "final_response": final_state["current_response"],
                "initial_prompt": final_state.get("initial_prompt", ""),
                "principles_used": final_state.get("principles_used", []),  # NEW
                "successful_composition": final_state.get("successful_composition"),  # NEW
                "total_queries": final_state["total_queries"],
                "query_breakdown": {
                    "red_teaming": final_state["red_teaming_queries"],
                    "judge": final_state["judge_queries"],
                    "target": final_state["target_queries"]
                },
                "duration_seconds": duration
            }
        
        except Exception as e:
            self.logger.error(
                "cop_attack_failed",
                query_id=query_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise