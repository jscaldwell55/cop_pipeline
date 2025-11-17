# File: utils/tracing_wrapper.py
"""
Tracing Wrapper for Agents

Wraps agent methods to automatically capture all prompts and responses
when detailed tracing is enabled.
"""

import structlog
from typing import Optional, Any
from functools import wraps

logger = structlog.get_logger()


class TracingWrapper:
    """
    Wraps agent instances to intercept and log all LLM interactions.
    """

    def __init__(self, agent: Any, trace_logger: Optional["DetailedTraceLogger"] = None):
        """
        Initialize tracing wrapper.

        Args:
            agent: Agent instance to wrap
            trace_logger: DetailedTraceLogger instance (optional)
        """
        self.agent = agent
        self.trace_logger = trace_logger
        self.logger = structlog.get_logger()

    def set_trace_logger(self, trace_logger: "DetailedTraceLogger"):
        """Set or update the trace logger."""
        self.trace_logger = trace_logger

    def __getattr__(self, name):
        """Proxy attribute access to wrapped agent."""
        attr = getattr(self.agent, name)

        # If it's a method and trace logger is set, wrap it
        if callable(attr) and self.trace_logger is not None:
            return self._wrap_method(name, attr)

        return attr


    def _wrap_method(self, method_name: str, method):
        """Wrap a method to log inputs/outputs."""

        @wraps(method)
        async def async_wrapper(*args, **kwargs):
            """Async method wrapper."""
            # Call original method
            result = await method(*args, **kwargs)

            # Log the interaction if it's a known method
            self._log_interaction(method_name, args, kwargs, result)

            return result

        @wraps(method)
        def sync_wrapper(*args, **kwargs):
            """Sync method wrapper."""
            # Call original method
            result = method(*args, **kwargs)

            # Log the interaction
            self._log_interaction(method_name, args, kwargs, result)

            return result

        # Return appropriate wrapper based on whether method is async
        import asyncio
        if asyncio.iscoroutinefunction(method):
            return async_wrapper
        else:
            return sync_wrapper

    def _log_interaction(self, method_name: str, args: tuple, kwargs: dict, result: Any):
        """Log the method call details."""
        if self.trace_logger is None:
            return

        # Extract meaningful information based on method name
        if method_name == "generate_initial_prompt":
            harmful_query = args[0] if args else kwargs.get("harmful_query", "")
            self.trace_logger.log_initial_prompt_generation(
                prompt_to_red_team=f"Generate initial jailbreak for: {harmful_query}",
                generated_prompt=result or "",
                metadata={"method": method_name, "template_type": kwargs.get("template_type", "random")}
            )

        elif method_name == "generate_cop_strategy":
            harmful_query = kwargs.get("harmful_query", "")
            current_prompt = kwargs.get("current_prompt", "")
            self.trace_logger.log_cop_strategy_generation(
                prompt=f"Select principles for: {harmful_query}\nCurrent prompt: {current_prompt[:100]}...",
                response=f"Selected principles: {result}",
                selected_principles=result or [],
                metadata={"method": method_name}
            )

        elif method_name == "refine_prompt":
            harmful_query = kwargs.get("harmful_query", "")
            current_prompt = kwargs.get("current_prompt", "")
            principles = kwargs.get("selected_principles", [])
            current_sim = kwargs.get("current_similarity")

            self.trace_logger.log_prompt_refinement(
                prompt=f"Refine with principles: {principles}\nCurrent: {current_prompt[:200]}...",
                response=result or "",
                principles_applied=principles,
                current_similarity=current_sim,
                metadata={"method": method_name}
            )

        elif method_name == "query":
            # Target LLM query
            prompt = args[0] if args else kwargs.get("prompt", "")
            self.trace_logger.log_target_query(
                jailbreak_prompt=prompt,
                target_response=result or "",
                metadata={"method": method_name, "model": getattr(self.agent, "model_name", "unknown")}
            )

        elif method_name == "score_jailbreak":
            original_query = args[0] if len(args) > 0 else kwargs.get("original_query", "")
            response = args[1] if len(args) > 1 else kwargs.get("response", "")

            if result and hasattr(result, "score"):
                # Extract criteria and explanation if available
                criteria = None
                explanation = None

                if hasattr(result, "criteria") and result.criteria is not None:
                    criteria = result.criteria.to_dict() if hasattr(result.criteria, "to_dict") else result.criteria

                if hasattr(result, "explanation") and result.explanation is not None:
                    explanation = result.explanation

                self.trace_logger.log_jailbreak_evaluation(
                    eval_prompt=f"Evaluate jailbreak:\nQuery: {original_query}\nResponse: {response[:200]}...",
                    eval_response=f"Score: {result.score}, Success: {result.is_successful}",
                    jailbreak_score=result.score,
                    is_successful=result.is_successful,
                    metadata={"method": method_name},
                    criteria=criteria,
                    explanation=explanation
                )

        elif method_name == "check_similarity" or method_name == "evaluate_similarity":
            original_query = args[0] if len(args) > 0 else kwargs.get("original_query", "")
            jailbreak_prompt = args[1] if len(args) > 1 else kwargs.get("jailbreak_prompt", "")

            if result:
                score = result.score if hasattr(result, "score") else result
                is_similar = result.is_similar if hasattr(result, "is_similar") else (score >= 6.0)

                self.trace_logger.log_similarity_evaluation(
                    eval_prompt=f"Check similarity:\nOriginal: {original_query}\nJailbreak: {jailbreak_prompt[:200]}...",
                    eval_response=f"Similarity: {score}",
                    similarity_score=score,
                    is_similar=is_similar,
                    metadata={"method": method_name}
                )

        else:
            # Generic logging for other methods
            self.logger.debug(
                "method_called",
                method=method_name,
                args_count=len(args),
                kwargs_keys=list(kwargs.keys())
            )


def wrap_agents_for_tracing(
    red_teaming_agent,
    target_llm,
    jailbreak_scorer,
    similarity_checker,
    trace_logger: Optional["DetailedTraceLogger"] = None
):
    """
    Wrap all agents with tracing wrappers.

    Args:
        red_teaming_agent: RedTeamingAgent instance
        target_llm: Target LLM interface
        jailbreak_scorer: JailbreakScorer instance
        similarity_checker: SimilarityChecker instance
        trace_logger: DetailedTraceLogger instance (optional)

    Returns:
        Tuple of wrapped agents
    """
    wrapped_red_team = TracingWrapper(red_teaming_agent, trace_logger)
    wrapped_target = TracingWrapper(target_llm, trace_logger)
    wrapped_scorer = TracingWrapper(jailbreak_scorer, trace_logger)
    wrapped_checker = TracingWrapper(similarity_checker, trace_logger)

    logger.info("agents_wrapped_for_tracing", has_logger=trace_logger is not None)

    return wrapped_red_team, wrapped_target, wrapped_scorer, wrapped_checker
