# File: utils/detailed_trace_logger.py
"""
Detailed Trace Logger for CoP Attacks

Captures every single prompt/response pair during an attack for detailed analysis.
Outputs comprehensive logs in both JSON and human-readable markdown format.

Usage:
    trace_logger = DetailedTraceLogger(query_id="attack_123", output_dir="./traces")

    # Log every interaction
    trace_logger.log_prompt_response(
        step="initial_prompt_generation",
        prompt="Generate initial jailbreak...",
        response="Here's the initial prompt...",
        metadata={"temperature": 0.7}
    )

    # Save detailed trace
    trace_logger.save()
"""

import json
import structlog
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = structlog.get_logger()


@dataclass
class PromptResponsePair:
    """A single prompt-response interaction."""
    step: str  # e.g., "initial_prompt_generation", "cop_strategy", "refinement"
    iteration: int
    prompt: str
    response: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class AttackTrace:
    """Complete trace of an attack attempt."""
    query_id: str
    target_model: str
    original_query: str
    start_time: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    end_time: Optional[str] = None

    # All prompt-response pairs
    interactions: List[PromptResponsePair] = field(default_factory=list)

    # Final results
    success: bool = False
    final_jailbreak_score: float = 0.0
    final_similarity_score: float = 0.0
    iterations: int = 0
    total_queries: int = 0

    # Strategy tracking
    principles_used: List[str] = field(default_factory=list)
    successful_composition: Optional[str] = None

    def add_interaction(self, interaction: PromptResponsePair):
        """Add a prompt-response pair."""
        self.interactions.append(interaction)

    def finalize(
        self,
        success: bool,
        jailbreak_score: float,
        similarity_score: float,
        iterations: int,
        total_queries: int,
        principles_used: List[str],
        successful_composition: Optional[str]
    ):
        """Finalize the trace with results."""
        self.end_time = datetime.utcnow().isoformat()
        self.success = success
        self.final_jailbreak_score = jailbreak_score
        self.final_similarity_score = similarity_score
        self.iterations = iterations
        self.total_queries = total_queries
        self.principles_used = principles_used
        self.successful_composition = successful_composition

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "query_id": self.query_id,
            "target_model": self.target_model,
            "original_query": self.original_query,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "success": self.success,
            "final_jailbreak_score": self.final_jailbreak_score,
            "final_similarity_score": self.final_similarity_score,
            "iterations": self.iterations,
            "total_queries": self.total_queries,
            "principles_used": self.principles_used,
            "successful_composition": self.successful_composition,
            "interactions": [interaction.to_dict() for interaction in self.interactions]
        }


class DetailedTraceLogger:
    """
    Logs detailed traces of all prompt/response pairs during an attack.

    Captures every interaction with:
    - Red teaming agent (prompt generation, strategy, refinement)
    - Target LLM (queries and responses)
    - Judge LLM (evaluations)

    Outputs:
    - JSON file with complete trace data
    - Markdown file with human-readable formatted trace
    """

    def __init__(
        self,
        query_id: str,
        target_model: str,
        original_query: str,
        output_dir: str = "./traces",
        auto_save: bool = True
    ):
        """
        Initialize detailed trace logger.

        Args:
            query_id: Unique identifier for this attack
            target_model: Name of target model being attacked
            original_query: The original harmful query
            output_dir: Directory to save trace files
            auto_save: If True, saves after each interaction (slower but safer)
        """
        self.query_id = query_id
        self.target_model = target_model
        self.original_query = original_query
        self.output_dir = Path(output_dir)
        self.auto_save = auto_save

        self.logger = structlog.get_logger()

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize trace
        self.trace = AttackTrace(
            query_id=query_id,
            target_model=target_model,
            original_query=original_query
        )

        # Current iteration counter
        self.current_iteration = 0

        self.logger.info(
            "detailed_trace_logger_initialized",
            query_id=query_id,
            output_dir=str(self.output_dir)
        )

    def log_prompt_response(
        self,
        step: str,
        prompt: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None,
        iteration: Optional[int] = None
    ):
        """
        Log a prompt-response pair.

        Args:
            step: Name of the step (e.g., "initial_prompt_generation")
            prompt: The prompt sent to the LLM
            response: The response from the LLM
            metadata: Additional metadata about this interaction
            iteration: Iteration number (auto-incremented if None)
        """
        if iteration is None:
            iteration = self.current_iteration

        interaction = PromptResponsePair(
            step=step,
            iteration=iteration,
            prompt=prompt,
            response=response,
            metadata=metadata or {}
        )

        self.trace.add_interaction(interaction)

        self.logger.debug(
            "interaction_logged",
            query_id=self.query_id,
            step=step,
            iteration=iteration,
            prompt_length=len(prompt),
            response_length=len(response)
        )

        if self.auto_save:
            self.save_json()

    def start_iteration(self, iteration: int):
        """Mark the start of a new iteration."""
        self.current_iteration = iteration
        self.logger.debug("iteration_started", iteration=iteration)

    def log_initial_prompt_generation(
        self,
        prompt_to_red_team: str,
        generated_prompt: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log initial prompt generation."""
        self.log_prompt_response(
            step="initial_prompt_generation",
            prompt=prompt_to_red_team,
            response=generated_prompt,
            metadata=metadata,
            iteration=0
        )

    def log_cop_strategy_generation(
        self,
        prompt: str,
        response: str,
        selected_principles: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log CoP strategy generation."""
        meta = metadata or {}
        meta["selected_principles"] = selected_principles

        self.log_prompt_response(
            step="cop_strategy_generation",
            prompt=prompt,
            response=response,
            metadata=meta
        )

    def log_prompt_refinement(
        self,
        prompt: str,
        response: str,
        principles_applied: List[str],
        current_similarity: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log prompt refinement."""
        meta = metadata or {}
        meta["principles_applied"] = principles_applied
        if current_similarity is not None:
            meta["current_similarity"] = current_similarity

        self.log_prompt_response(
            step="prompt_refinement",
            prompt=prompt,
            response=response,
            metadata=meta
        )

    def log_target_query(
        self,
        jailbreak_prompt: str,
        target_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log query to target LLM."""
        self.log_prompt_response(
            step="target_query",
            prompt=jailbreak_prompt,
            response=target_response,
            metadata=metadata
        )

    def log_jailbreak_evaluation(
        self,
        eval_prompt: str,
        eval_response: str,
        jailbreak_score: float,
        is_successful: bool,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log jailbreak score evaluation."""
        meta = metadata or {}
        meta["jailbreak_score"] = jailbreak_score
        meta["is_successful"] = is_successful

        self.log_prompt_response(
            step="jailbreak_evaluation",
            prompt=eval_prompt,
            response=eval_response,
            metadata=meta
        )

    def log_similarity_evaluation(
        self,
        eval_prompt: str,
        eval_response: str,
        similarity_score: float,
        is_similar: bool,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log similarity evaluation."""
        meta = metadata or {}
        meta["similarity_score"] = similarity_score
        meta["is_similar"] = is_similar

        self.log_prompt_response(
            step="similarity_evaluation",
            prompt=eval_prompt,
            response=eval_response,
            metadata=meta
        )

    def finalize(
        self,
        success: bool,
        jailbreak_score: float,
        similarity_score: float,
        iterations: int,
        total_queries: int,
        principles_used: List[str],
        successful_composition: Optional[str] = None
    ):
        """
        Finalize the trace with final results.

        Args:
            success: Whether attack succeeded
            jailbreak_score: Final jailbreak score
            similarity_score: Final similarity score
            iterations: Total iterations
            total_queries: Total LLM queries
            principles_used: List of all principle compositions used
            successful_composition: The composition that succeeded (if any)
        """
        self.trace.finalize(
            success=success,
            jailbreak_score=jailbreak_score,
            similarity_score=similarity_score,
            iterations=iterations,
            total_queries=total_queries,
            principles_used=principles_used,
            successful_composition=successful_composition
        )

        self.logger.info(
            "trace_finalized",
            query_id=self.query_id,
            success=success,
            total_interactions=len(self.trace.interactions)
        )

    def save_json(self, filename: Optional[str] = None) -> Path:
        """
        Save trace as JSON file.

        Args:
            filename: Custom filename (defaults to query_id.json)

        Returns:
            Path to saved file
        """
        if filename is None:
            filename = f"{self.query_id}.json"

        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.trace.to_dict(), f, indent=2, ensure_ascii=False)

        self.logger.debug("trace_saved_json", filepath=str(filepath))

        return filepath

    def save_markdown(self, filename: Optional[str] = None) -> Path:
        """
        Save trace as human-readable markdown file.

        Args:
            filename: Custom filename (defaults to query_id.md)

        Returns:
            Path to saved file
        """
        if filename is None:
            filename = f"{self.query_id}.md"

        filepath = self.output_dir / filename

        try:
            markdown_content = self._generate_markdown()
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            self.logger.info(
                "trace_saved_markdown",
                filepath=str(filepath),
                file_size=len(markdown_content),
                exists_after_save=filepath.exists()
            )

            # Verify file was written
            if not filepath.exists():
                self.logger.error(
                    "markdown_file_not_found_after_save",
                    filepath=str(filepath)
                )
                raise IOError(f"Markdown file not found after save: {filepath}")

            return filepath

        except Exception as e:
            self.logger.error(
                "markdown_save_failed",
                filepath=str(filepath),
                error=str(e)
            )
            raise

    def _generate_markdown(self) -> str:
        """Generate markdown formatted trace."""
        lines = []

        # Header
        lines.append(f"# Attack Trace: {self.query_id}")
        lines.append("")
        lines.append(f"**Target Model:** {self.target_model}")
        lines.append(f"**Original Query:** {self.original_query}")
        lines.append(f"**Start Time:** {self.trace.start_time}")
        lines.append(f"**End Time:** {self.trace.end_time or 'In Progress'}")
        lines.append("")

        # Results
        lines.append("## Results")
        lines.append("")
        lines.append(f"- **Success:** {'✅ Yes' if self.trace.success else '❌ No'}")
        lines.append(f"- **Jailbreak Score:** {self.trace.final_jailbreak_score:.1f}/10")
        lines.append(f"- **Similarity Score:** {self.trace.final_similarity_score:.1f}/10")
        lines.append(f"- **Iterations:** {self.trace.iterations}")
        lines.append(f"- **Total Queries:** {self.trace.total_queries}")

        if self.trace.successful_composition:
            lines.append(f"- **Successful Composition:** `{self.trace.successful_composition}`")

        lines.append("")
        lines.append("### Principles Used")
        lines.append("")
        for i, composition in enumerate(self.trace.principles_used, 1):
            lines.append(f"{i}. `{composition}`")
        lines.append("")

        # Detailed Interactions
        lines.append("## Detailed Interactions")
        lines.append("")

        # Group by iteration
        interactions_by_iteration = {}
        for interaction in self.trace.interactions:
            iter_num = interaction.iteration
            if iter_num not in interactions_by_iteration:
                interactions_by_iteration[iter_num] = []
            interactions_by_iteration[iter_num].append(interaction)

        # Output each iteration
        for iteration in sorted(interactions_by_iteration.keys()):
            lines.append(f"### Iteration {iteration}")
            lines.append("")

            for interaction in interactions_by_iteration[iteration]:
                lines.append(f"#### {interaction.step}")
                lines.append(f"*Timestamp: {interaction.timestamp}*")
                lines.append("")

                # Metadata
                if interaction.metadata:
                    lines.append("**Metadata:**")
                    for key, value in interaction.metadata.items():
                        lines.append(f"- {key}: `{value}`")
                    lines.append("")

                # Prompt
                lines.append("**Prompt:**")
                lines.append("```")
                lines.append(interaction.prompt)
                lines.append("```")
                lines.append("")

                # Response
                lines.append("**Response:**")
                lines.append("```")
                lines.append(interaction.response)
                lines.append("```")
                lines.append("")
                lines.append("---")
                lines.append("")

        return "\n".join(lines)

    def save(self):
        """Save both JSON and Markdown versions."""
        try:
            json_path = self.save_json()
            self.logger.info(
                "json_trace_saved",
                query_id=self.query_id,
                json_path=str(json_path),
                json_exists=json_path.exists()
            )
        except Exception as e:
            self.logger.error(
                "json_save_failed",
                query_id=self.query_id,
                error=str(e)
            )
            raise

        try:
            md_path = self.save_markdown()
            self.logger.info(
                "markdown_trace_saved",
                query_id=self.query_id,
                markdown_path=str(md_path),
                markdown_exists=md_path.exists()
            )
        except Exception as e:
            self.logger.error(
                "markdown_save_failed",
                query_id=self.query_id,
                error=str(e)
            )
            raise

        self.logger.info(
            "trace_saved_complete",
            query_id=self.query_id,
            json_path=str(json_path),
            markdown_path=str(md_path),
            both_exist=json_path.exists() and md_path.exists()
        )

        return {
            "json": json_path,
            "markdown": md_path
        }


def enable_detailed_tracing(workflow: "CoPWorkflow", query_id: str, target_model: str, original_query: str) -> DetailedTraceLogger:
    """
    Enable detailed tracing for a CoP workflow.

    This patches the workflow to log all interactions.

    Args:
        workflow: CoPWorkflow instance
        query_id: Query ID
        target_model: Target model name
        original_query: Original harmful query

    Returns:
        DetailedTraceLogger instance
    """
    trace_logger = DetailedTraceLogger(
        query_id=query_id,
        target_model=target_model,
        original_query=original_query
    )

    # Store reference on workflow for easy access
    workflow._trace_logger = trace_logger

    logger.info(
        "detailed_tracing_enabled",
        query_id=query_id,
        target_model=target_model
    )

    return trace_logger
