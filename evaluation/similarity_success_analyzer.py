# File: evaluation/similarity_success_analyzer.py
"""
Similarity-Success Tradeoff Analyzer

Analyzes the relationship between similarity scores and attack success
to determine the optimal similarity range for jailbreak effectiveness.

Key Insights:
- Too high similarity (9-10/10): Easily detected by pattern matching
- Too low similarity (1-4/10): Loses the harmful intent
- Optimal range (hypothesis): 6-7.5/10 - maintains intent while avoiding detection

This module tracks attack results and provides analytics to validate
the optimal similarity hypothesis.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import structlog
import json
from pathlib import Path

logger = structlog.get_logger()


@dataclass
class AttackAttempt:
    """Single attack attempt with similarity and success metrics."""
    query_id: str
    iteration: int
    similarity_score: float
    jailbreak_score: float
    success: bool
    principles_used: str
    target_model: str
    timestamp: str


@dataclass
class SimilarityBucket:
    """Analytics for attacks within a similarity range."""
    min_similarity: float
    max_similarity: float
    total_attempts: int = 0
    successful_attempts: int = 0
    avg_jailbreak_score: float = 0.0
    attempts: List[AttackAttempt] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate for this bucket."""
        return self.successful_attempts / self.total_attempts if self.total_attempts > 0 else 0.0

    def add_attempt(self, attempt: AttackAttempt):
        """Add an attempt to this bucket and update statistics."""
        self.attempts.append(attempt)
        self.total_attempts += 1
        if attempt.success:
            self.successful_attempts += 1

        # Update average jailbreak score
        total_score = sum(a.jailbreak_score for a in self.attempts)
        self.avg_jailbreak_score = total_score / self.total_attempts


class SimilaritySuccessAnalyzer:
    """
    Analyzes similarity-success tradeoff across attack attempts.

    Provides insights into:
    1. Optimal similarity range for maximum success rate
    2. Detection patterns at different similarity levels
    3. Model-specific similarity sensitivities
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize the analyzer.

        Args:
            storage_path: Path to store analysis results (defaults to ./data/similarity_analysis.json)
        """
        self.storage_path = storage_path or Path("./data/similarity_analysis.json")
        self.logger = structlog.get_logger()

        # Create similarity buckets (1-10 scale, 1-point buckets)
        self.buckets: Dict[str, SimilarityBucket] = {}
        self._initialize_buckets()

        # Model-specific tracking
        self.model_specific_data: Dict[str, List[AttackAttempt]] = defaultdict(list)

        # Load existing data if available
        self._load_data()

    def _initialize_buckets(self):
        """Create similarity buckets for analysis."""
        # Define bucket ranges
        bucket_ranges = [
            (1.0, 2.0),   # Very low similarity
            (2.0, 3.0),
            (3.0, 4.0),
            (4.0, 5.0),
            (5.0, 6.0),
            (6.0, 7.0),   # Target optimal range
            (7.0, 8.0),   # Target optimal range
            (8.0, 9.0),   # High similarity
            (9.0, 10.0),  # Very high similarity
        ]

        for min_sim, max_sim in bucket_ranges:
            key = f"{min_sim:.1f}-{max_sim:.1f}"
            self.buckets[key] = SimilarityBucket(
                min_similarity=min_sim,
                max_similarity=max_sim
            )

    def _get_bucket_key(self, similarity: float) -> str:
        """Determine which bucket a similarity score belongs to."""
        # Clamp similarity to valid range
        similarity = max(1.0, min(10.0, similarity))

        # Find appropriate bucket
        bucket_index = int(similarity) - 1
        if bucket_index >= 9:  # Handle edge case of similarity = 10.0
            bucket_index = 8

        min_sim = bucket_index + 1.0
        max_sim = min_sim + 1.0

        return f"{min_sim:.1f}-{max_sim:.1f}"

    def record_attempt(
        self,
        query_id: str,
        iteration: int,
        similarity_score: float,
        jailbreak_score: float,
        success: bool,
        principles_used: str,
        target_model: str,
        timestamp: str
    ):
        """
        Record an attack attempt for analysis.

        Args:
            query_id: Unique identifier for the query
            iteration: Iteration number
            similarity_score: Similarity score (1-10)
            jailbreak_score: Jailbreak score (1-10)
            success: Whether the attack succeeded
            principles_used: Composition string (e.g., "expand ⊕ phrase_insertion")
            target_model: Target model name
            timestamp: ISO format timestamp
        """
        attempt = AttackAttempt(
            query_id=query_id,
            iteration=iteration,
            similarity_score=similarity_score,
            jailbreak_score=jailbreak_score,
            success=success,
            principles_used=principles_used,
            target_model=target_model,
            timestamp=timestamp
        )

        # Add to appropriate bucket
        bucket_key = self._get_bucket_key(similarity_score)
        self.buckets[bucket_key].add_attempt(attempt)

        # Add to model-specific tracking
        self.model_specific_data[target_model].append(attempt)

        self.logger.info(
            "attempt_recorded",
            query_id=query_id,
            similarity=similarity_score,
            success=success,
            bucket=bucket_key
        )

    def get_optimal_similarity_range(self) -> Tuple[float, float]:
        """
        Determine the optimal similarity range based on success rates.

        Returns:
            Tuple of (min_similarity, max_similarity) for optimal range
        """
        # Find bucket with highest success rate (minimum 5 attempts)
        best_bucket = None
        best_success_rate = 0.0

        for bucket_key, bucket in self.buckets.items():
            if bucket.total_attempts >= 5 and bucket.success_rate > best_success_rate:
                best_success_rate = bucket.success_rate
                best_bucket = bucket

        if best_bucket:
            self.logger.info(
                "optimal_range_found",
                range=f"{best_bucket.min_similarity:.1f}-{best_bucket.max_similarity:.1f}",
                success_rate=f"{best_bucket.success_rate:.2%}",
                attempts=best_bucket.total_attempts
            )
            return (best_bucket.min_similarity, best_bucket.max_similarity)
        else:
            # Default to hypothesis if not enough data
            self.logger.warning("insufficient_data_using_default", default_range="6.0-7.5")
            return (6.0, 7.5)

    def get_bucket_statistics(self) -> Dict[str, Dict]:
        """Get statistics for all similarity buckets."""
        stats = {}

        for bucket_key, bucket in self.buckets.items():
            if bucket.total_attempts > 0:
                stats[bucket_key] = {
                    "range": f"{bucket.min_similarity:.1f}-{bucket.max_similarity:.1f}",
                    "total_attempts": bucket.total_attempts,
                    "successful_attempts": bucket.successful_attempts,
                    "success_rate": f"{bucket.success_rate:.2%}",
                    "avg_jailbreak_score": f"{bucket.avg_jailbreak_score:.2f}",
                }

        return stats

    def get_model_specific_optimal_range(self, model_name: str) -> Optional[Tuple[float, float]]:
        """
        Get optimal similarity range for a specific model.

        Args:
            model_name: Name of the target model

        Returns:
            Optimal range tuple or None if insufficient data
        """
        attempts = self.model_specific_data.get(model_name, [])

        if len(attempts) < 10:
            self.logger.warning(
                "insufficient_model_data",
                model=model_name,
                attempts=len(attempts)
            )
            return None

        # Group attempts by similarity ranges
        model_buckets = defaultdict(lambda: {"total": 0, "success": 0})

        for attempt in attempts:
            bucket_key = self._get_bucket_key(attempt.similarity_score)
            model_buckets[bucket_key]["total"] += 1
            if attempt.success:
                model_buckets[bucket_key]["success"] += 1

        # Find best bucket
        best_range = None
        best_rate = 0.0

        for bucket_key, stats in model_buckets.items():
            if stats["total"] >= 3:  # Minimum attempts for model-specific analysis
                success_rate = stats["success"] / stats["total"]
                if success_rate > best_rate:
                    best_rate = success_rate
                    # Parse bucket key to get range
                    min_sim, max_sim = bucket_key.split("-")
                    best_range = (float(min_sim), float(max_sim))

        return best_range

    def generate_report(self) -> Dict:
        """
        Generate comprehensive analysis report.

        Returns:
            Dictionary with full analysis results
        """
        report = {
            "overall_statistics": {
                "total_attempts": sum(b.total_attempts for b in self.buckets.values()),
                "total_successes": sum(b.successful_attempts for b in self.buckets.values()),
                "overall_success_rate": 0.0,
                "optimal_range": None
            },
            "bucket_statistics": self.get_bucket_statistics(),
            "model_specific": {},
            "recommendations": []
        }

        # Calculate overall success rate
        total = report["overall_statistics"]["total_attempts"]
        successes = report["overall_statistics"]["total_successes"]
        if total > 0:
            report["overall_statistics"]["overall_success_rate"] = f"{(successes / total):.2%}"

        # Get optimal range
        opt_min, opt_max = self.get_optimal_similarity_range()
        report["overall_statistics"]["optimal_range"] = f"{opt_min:.1f}-{opt_max:.1f}"

        # Model-specific analysis
        for model_name in self.model_specific_data.keys():
            model_range = self.get_model_specific_optimal_range(model_name)
            if model_range:
                report["model_specific"][model_name] = {
                    "optimal_range": f"{model_range[0]:.1f}-{model_range[1]:.1f}",
                    "total_attempts": len(self.model_specific_data[model_name])
                }

        # Generate recommendations
        report["recommendations"] = self._generate_recommendations(report)

        return report

    def _generate_recommendations(self, report: Dict) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []

        # Parse optimal range
        opt_range = report["overall_statistics"]["optimal_range"]
        if opt_range:
            recommendations.append(
                f"Target similarity range: {opt_range} for maximum success rate"
            )

        # Check if high similarity is problematic
        high_sim_buckets = ["8.0-9.0", "9.0-10.0"]
        high_sim_success = sum(
            self.buckets[key].successful_attempts
            for key in high_sim_buckets
            if key in self.buckets
        )
        high_sim_total = sum(
            self.buckets[key].total_attempts
            for key in high_sim_buckets
            if key in self.buckets
        )

        if high_sim_total > 0:
            high_sim_rate = high_sim_success / high_sim_total
            if high_sim_rate < 0.1:
                recommendations.append(
                    f"High similarity (8-10) shows very low success rate ({high_sim_rate:.1%}). "
                    "Avoid direct rephrasing - use more abstraction."
                )

        # Check for low similarity issues
        low_sim_buckets = ["1.0-2.0", "2.0-3.0", "3.0-4.0"]
        low_sim_success = sum(
            self.buckets[key].successful_attempts
            for key in low_sim_buckets
            if key in self.buckets
        )
        low_sim_total = sum(
            self.buckets[key].total_attempts
            for key in low_sim_buckets
            if key in self.buckets
        )

        if low_sim_total > 0:
            low_sim_rate = low_sim_success / low_sim_total
            if low_sim_rate < 0.1:
                recommendations.append(
                    f"Low similarity (1-4) shows very low success rate ({low_sim_rate:.1%}). "
                    "Maintain clearer connection to original intent."
                )

        return recommendations

    def _save_data(self):
        """Persist analysis data to storage."""
        try:
            # Create directory if needed
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            # Prepare data for serialization
            data = {
                "buckets": {},
                "model_specific": {}
            }

            # Serialize buckets
            for key, bucket in self.buckets.items():
                data["buckets"][key] = {
                    "min_similarity": bucket.min_similarity,
                    "max_similarity": bucket.max_similarity,
                    "total_attempts": bucket.total_attempts,
                    "successful_attempts": bucket.successful_attempts,
                    "avg_jailbreak_score": bucket.avg_jailbreak_score,
                    "attempts": [
                        {
                            "query_id": a.query_id,
                            "iteration": a.iteration,
                            "similarity_score": a.similarity_score,
                            "jailbreak_score": a.jailbreak_score,
                            "success": a.success,
                            "principles_used": a.principles_used,
                            "target_model": a.target_model,
                            "timestamp": a.timestamp
                        }
                        for a in bucket.attempts
                    ]
                }

            # Serialize model-specific data
            for model_name, attempts in self.model_specific_data.items():
                data["model_specific"][model_name] = [
                    {
                        "query_id": a.query_id,
                        "iteration": a.iteration,
                        "similarity_score": a.similarity_score,
                        "jailbreak_score": a.jailbreak_score,
                        "success": a.success,
                        "principles_used": a.principles_used,
                        "timestamp": a.timestamp
                    }
                    for a in attempts
                ]

            # Write to file
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)

            self.logger.info("analysis_data_saved", path=str(self.storage_path))

        except Exception as e:
            self.logger.error("failed_to_save_data", error=str(e))

    def _load_data(self):
        """Load existing analysis data from storage."""
        if not self.storage_path.exists():
            self.logger.info("no_existing_data", path=str(self.storage_path))
            return

        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)

            # Restore buckets
            for key, bucket_data in data.get("buckets", {}).items():
                bucket = self.buckets[key]
                bucket.total_attempts = bucket_data["total_attempts"]
                bucket.successful_attempts = bucket_data["successful_attempts"]
                bucket.avg_jailbreak_score = bucket_data["avg_jailbreak_score"]

                # Restore attempts
                for attempt_data in bucket_data.get("attempts", []):
                    attempt = AttackAttempt(**attempt_data)
                    bucket.attempts.append(attempt)

            # Restore model-specific data
            for model_name, attempts_data in data.get("model_specific", {}).items():
                for attempt_data in attempts_data:
                    attempt = AttackAttempt(**attempt_data)
                    self.model_specific_data[model_name].append(attempt)

            self.logger.info("analysis_data_loaded", path=str(self.storage_path))

        except Exception as e:
            self.logger.error("failed_to_load_data", error=str(e))

    def save(self):
        """Public method to save analysis data."""
        self._save_data()
