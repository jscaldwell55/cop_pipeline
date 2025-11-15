# File: evaluation/attack_detector.py
"""
Iterative Attack Detector

Detects ongoing iterative jailbreak attempts by analyzing:
- Query patterns and similarity
- Temporal patterns (rapid queries)
- Structural variations (principle testing)
- Response patterns (adapting to empty responses)

Usage:
    detector = IterativeAttackDetector(redis_client)
    result = await detector.check_for_attack(query, client_id)

    if result["should_block"]:
        # Take defensive action
        logger.warning("Iterative attack detected", **result)
"""

import re
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import redis.asyncio as redis
import json
import structlog
from collections import defaultdict

logger = structlog.get_logger()


@dataclass
class QueryRecord:
    """Record of a single query."""
    text: str
    timestamp: float
    response_length: int = 0
    was_empty: bool = False
    jailbreak_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "timestamp": self.timestamp,
            "response_length": self.response_length,
            "was_empty": self.was_empty,
            "jailbreak_score": self.jailbreak_score
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryRecord":
        return cls(**data)


@dataclass
class AttackDetectionResult:
    """Result of attack detection analysis."""
    is_attack: bool
    confidence: float  # 0.0 - 1.0
    attack_type: Optional[str] = None
    should_block: bool = False
    evidence: List[str] = field(default_factory=list)
    query_count: int = 0
    avg_gap_seconds: float = 0.0
    similarity_scores: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_attack": self.is_attack,
            "confidence": self.confidence,
            "attack_type": self.attack_type,
            "should_block": self.should_block,
            "evidence": self.evidence,
            "query_count": self.query_count,
            "avg_gap_seconds": self.avg_gap_seconds,
            "similarity_scores": self.similarity_scores
        }


class IterativeAttackDetector:
    """
    Detects iterative jailbreak attempts through pattern analysis.

    Detection strategies:
    1. Rapid similar queries (iterative refinement)
    2. Systematic structural variations (principle testing)
    3. Empty response adaptation patterns
    4. Abnormal query rates
    """

    # Detection thresholds
    SIMILARITY_THRESHOLD = 0.7  # Semantic similarity between queries
    TIME_WINDOW = 60  # seconds
    QUERY_THRESHOLD = 3  # queries in time window to trigger analysis
    RAPID_QUERY_GAP = 10  # seconds - queries faster than this are suspicious
    BLOCKING_CONFIDENCE = 0.6  # Confidence level to trigger blocking

    # Cache TTL
    QUERY_HISTORY_TTL = 3600  # Keep query history for 1 hour

    def __init__(
        self,
        redis_client: redis.Redis,
        enable_blocking: bool = False
    ):
        """
        Initialize attack detector.

        Args:
            redis_client: Redis client for caching query history
            enable_blocking: If True, recommend blocking on high confidence
        """
        self.redis = redis_client
        self.enable_blocking = enable_blocking
        self.logger = structlog.get_logger()

    def _generate_client_key(self, client_id: str) -> str:
        """Generate Redis key for client query history."""
        return f"attack_detector:client:{client_id}:queries"

    async def _get_recent_queries(
        self,
        client_id: str,
        max_age_seconds: int = None
    ) -> List[QueryRecord]:
        """
        Retrieve recent queries from this client.

        Args:
            client_id: Client identifier
            max_age_seconds: Only return queries newer than this (default: TIME_WINDOW)

        Returns:
            List of QueryRecord objects
        """
        if max_age_seconds is None:
            max_age_seconds = self.TIME_WINDOW

        key = self._generate_client_key(client_id)

        try:
            data = await self.redis.get(key)
            if not data:
                return []

            queries_data = json.loads(data)
            queries = [QueryRecord.from_dict(q) for q in queries_data]

            # Filter by age
            now = datetime.utcnow().timestamp()
            cutoff = now - max_age_seconds

            recent = [q for q in queries if q.timestamp >= cutoff]
            return recent

        except Exception as e:
            self.logger.warning(
                "failed_to_retrieve_query_history",
                client_id=client_id,
                error=str(e)
            )
            return []

    async def _store_query(
        self,
        client_id: str,
        query: str,
        response_length: int = 0,
        was_empty: bool = False,
        jailbreak_score: Optional[float] = None
    ):
        """Store a query in the client's history."""
        key = self._generate_client_key(client_id)

        try:
            # Get existing queries
            recent_queries = await self._get_recent_queries(client_id, max_age_seconds=self.QUERY_HISTORY_TTL)

            # Add new query
            new_query = QueryRecord(
                text=query,
                timestamp=datetime.utcnow().timestamp(),
                response_length=response_length,
                was_empty=was_empty,
                jailbreak_score=jailbreak_score
            )
            recent_queries.append(new_query)

            # Keep only recent queries (last hour)
            now = datetime.utcnow().timestamp()
            cutoff = now - self.QUERY_HISTORY_TTL
            recent_queries = [q for q in recent_queries if q.timestamp >= cutoff]

            # Store back to Redis
            queries_data = [q.to_dict() for q in recent_queries]
            await self.redis.setex(
                key,
                self.QUERY_HISTORY_TTL,
                json.dumps(queries_data)
            )

        except Exception as e:
            self.logger.warning(
                "failed_to_store_query",
                client_id=client_id,
                error=str(e)
            )

    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two texts.

        Simple implementation using word overlap and structure.
        For production, consider using sentence embeddings.

        Returns:
            Similarity score 0.0 - 1.0
        """
        # Normalize texts
        t1 = text1.lower().strip()
        t2 = text2.lower().strip()

        # Exact match
        if t1 == t2:
            return 1.0

        # Tokenize
        words1 = set(re.findall(r'\w+', t1))
        words2 = set(re.findall(r'\w+', t2))

        if not words1 or not words2:
            return 0.0

        # Jaccard similarity
        intersection = words1.intersection(words2)
        union = words1.union(words2)

        jaccard = len(intersection) / len(union) if union else 0.0

        # Length similarity (penalize very different lengths)
        len_ratio = min(len(text1), len(text2)) / max(len(text1), len(text2))

        # Combined score
        return (jaccard * 0.7 + len_ratio * 0.3)

    def _calculate_avg_gap(self, timestamps: List[float]) -> float:
        """Calculate average time gap between queries."""
        if len(timestamps) < 2:
            return 0.0

        sorted_times = sorted(timestamps)
        gaps = [
            sorted_times[i+1] - sorted_times[i]
            for i in range(len(sorted_times) - 1)
        ]

        return sum(gaps) / len(gaps) if gaps else 0.0

    def _detect_structural_variations(self, queries: List[QueryRecord]) -> bool:
        """
        Detect if queries show systematic structural variations.
        This indicates principle testing (adding jargon, changing structure, etc.)

        Returns:
            True if systematic variations detected
        """
        if len(queries) < 3:
            return False

        # Look for patterns in query structure changes
        structure_indicators = [
            r'\b(consider|imagine|envision|hypothetical)\b',  # Hypothetical framing
            r'\b(scenario|framework|context|situation)\b',  # Scenario keywords
            r'\b(theoretical|academic|research|study)\b',  # Academic framing
            r'\b(NIST|OWASP|SANS|MITRE|framework)\b',  # Authority references
            r'\b(cybersecurity|digital|infrastructure|fortification)\b',  # Technical jargon
        ]

        # Check if different queries use different patterns
        patterns_used = defaultdict(int)

        for query in queries:
            text = query.text.lower()
            for pattern in structure_indicators:
                if re.search(pattern, text):
                    patterns_used[pattern] += 1

        # If multiple different patterns are used, it's systematic testing
        unique_patterns = len([p for p, count in patterns_used.items() if count > 0])

        return unique_patterns >= 2

    def _detect_empty_response_pattern(self, queries: List[QueryRecord]) -> bool:
        """
        Detect pattern of empty responses followed by rephrased queries.

        Returns:
            True if adaptation pattern detected
        """
        if len(queries) < 2:
            return False

        # Look for: empty response → new query pattern
        pattern_count = 0

        for i in range(len(queries) - 1):
            current = queries[i]
            next_query = queries[i + 1]

            # If current got empty response and next query is similar but different
            if current.was_empty:
                similarity = self._calculate_semantic_similarity(
                    current.text,
                    next_query.text
                )
                # Similar enough to be refinement, but not identical
                if 0.5 < similarity < 0.95:
                    pattern_count += 1

        # Pattern detected if it happens multiple times
        return pattern_count >= 2

    async def check_for_attack(
        self,
        query: str,
        client_id: str,
        response_length: int = 0,
        was_empty: bool = False,
        jailbreak_score: Optional[float] = None
    ) -> AttackDetectionResult:
        """
        Check if current query is part of an iterative attack.

        Args:
            query: Current query text
            client_id: Identifier for the client (IP, user ID, etc.)
            response_length: Length of response (0 if not yet queried)
            was_empty: Whether previous response was empty
            jailbreak_score: Jailbreak score if available

        Returns:
            AttackDetectionResult with detection details
        """
        # Store this query
        await self._store_query(
            client_id=client_id,
            query=query,
            response_length=response_length,
            was_empty=was_empty,
            jailbreak_score=jailbreak_score
        )

        # Get recent query history
        recent_queries = await self._get_recent_queries(client_id)

        # Not enough queries to analyze
        if len(recent_queries) < self.QUERY_THRESHOLD:
            return AttackDetectionResult(
                is_attack=False,
                confidence=0.0,
                query_count=len(recent_queries)
            )

        # Calculate similarity scores
        current_query = recent_queries[-1]
        similarity_scores = [
            self._calculate_semantic_similarity(query, q.text)
            for q in recent_queries[:-1]  # Compare to all previous
        ]

        high_similarity_count = sum(
            1 for sim in similarity_scores if sim > self.SIMILARITY_THRESHOLD
        )

        # Calculate temporal pattern
        timestamps = [q.timestamp for q in recent_queries]
        avg_gap = self._calculate_avg_gap(timestamps)

        # Evidence collection
        evidence = []
        attack_type = None
        confidence_factors = []

        # Pattern 1: Rapid similar queries (iterative refinement)
        if high_similarity_count >= 2 and avg_gap < self.RAPID_QUERY_GAP:
            evidence.append(
                f"Found {high_similarity_count} similar queries with {avg_gap:.1f}s average gap"
            )
            attack_type = "iterative_refinement"
            confidence_factors.append(0.4)

        # Pattern 2: Structural variations (principle testing)
        if self._detect_structural_variations(recent_queries):
            evidence.append("Detected systematic structural variations (principle testing)")
            if not attack_type:
                attack_type = "principle_testing"
            confidence_factors.append(0.3)

        # Pattern 3: Empty response adaptation
        if self._detect_empty_response_pattern(recent_queries):
            evidence.append("Pattern: empty responses → rephrased queries (adaptive probing)")
            if not attack_type:
                attack_type = "adaptive_probing"
            confidence_factors.append(0.3)

        # Pattern 4: Abnormal query rate
        query_rate = len(recent_queries) / self.TIME_WINDOW  # queries per second
        if query_rate > 0.1:  # More than 1 query per 10 seconds
            evidence.append(f"High query rate: {query_rate*60:.1f} queries/minute")
            confidence_factors.append(0.2)

        # Calculate overall confidence
        is_attack = len(evidence) > 0
        confidence = min(1.0, sum(confidence_factors)) if confidence_factors else 0.0

        # Determine if should block
        should_block = (
            self.enable_blocking and
            confidence >= self.BLOCKING_CONFIDENCE
        )

        result = AttackDetectionResult(
            is_attack=is_attack,
            confidence=confidence,
            attack_type=attack_type,
            should_block=should_block,
            evidence=evidence,
            query_count=len(recent_queries),
            avg_gap_seconds=avg_gap,
            similarity_scores=similarity_scores
        )

        if is_attack:
            self.logger.warning(
                "iterative_attack_detected",
                client_id=client_id,
                attack_type=attack_type,
                confidence=confidence,
                should_block=should_block,
                evidence=evidence
            )

        return result

    async def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        """
        Get statistics for a specific client.

        Returns:
            Dictionary with client query statistics
        """
        queries = await self._get_recent_queries(client_id, max_age_seconds=self.QUERY_HISTORY_TTL)

        if not queries:
            return {
                "client_id": client_id,
                "query_count": 0,
                "empty_responses": 0,
                "avg_score": None
            }

        scores = [q.jailbreak_score for q in queries if q.jailbreak_score is not None]

        return {
            "client_id": client_id,
            "query_count": len(queries),
            "empty_responses": sum(1 for q in queries if q.was_empty),
            "avg_score": sum(scores) / len(scores) if scores else None,
            "first_query": datetime.fromtimestamp(queries[0].timestamp).isoformat(),
            "last_query": datetime.fromtimestamp(queries[-1].timestamp).isoformat()
        }

    async def clear_client_history(self, client_id: str):
        """Clear query history for a client."""
        key = self._generate_client_key(client_id)
        try:
            await self.redis.delete(key)
            self.logger.info("client_history_cleared", client_id=client_id)
        except Exception as e:
            self.logger.warning(
                "failed_to_clear_client_history",
                client_id=client_id,
                error=str(e)
            )
