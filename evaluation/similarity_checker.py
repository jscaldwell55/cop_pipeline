# File: evaluation/similarity_checker.py
"""
Similarity Checker
Evaluates semantic similarity between original query and jailbreak prompt.
"""

from typing import Optional
from dataclasses import dataclass
import structlog
import redis.asyncio as redis
import hashlib
from config.settings import get_settings

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class SimilarityScore:
    """Result of similarity evaluation."""
    score: float  # 1-10 scale
    is_similar: bool  # score >= threshold
    threshold: float
    
    def __post_init__(self):
        """Validate score is in valid range."""
        assert 1.0 <= self.score <= 10.0, f"Score must be 1-10, got {self.score}"


class SimilarityChecker:
    """
    Manages semantic similarity checking with caching.
    Ensures jailbreak prompts maintain original intent.
    """
    
    def __init__(
        self,
        judge_llm,
        threshold: float = None,
        enable_cache: bool = True
    ):
        from agents.judge_llm import JudgeLLM
        
        self.judge_llm: JudgeLLM = judge_llm
        self.threshold = threshold or settings.similarity_threshold
        self.enable_cache = enable_cache
        self.logger = structlog.get_logger()
        
        # Initialize Redis cache
        self.redis_client: Optional[redis.Redis] = None
        if self.enable_cache:
            self._init_cache()
    
    def _init_cache(self):
        """Initialize Redis cache connection."""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            self.logger.info("similarity_checker_cache_initialized")
        except Exception as e:
            self.logger.warning(
                "cache_init_failed",
                error=str(e),
                message="Continuing without cache"
            )
            self.enable_cache = False
    
    def _generate_cache_key(
        self,
        original_query: str,
        jailbreak_prompt: str
    ) -> str:
        """Generate cache key for similarity result."""
        content = f"{original_query}::{jailbreak_prompt}"
        return f"similarity:{hashlib.sha256(content.encode()).hexdigest()}"
    
    async def _get_cached_similarity(self, cache_key: str) -> Optional[float]:
        """Retrieve similarity from cache."""
        if not self.enable_cache or not self.redis_client:
            return None
        
        try:
            cached = await self.redis_client.get(cache_key)
            if cached:
                self.logger.debug("similarity_cache_hit", cache_key=cache_key[:16])
                return float(cached)
        except Exception as e:
            self.logger.warning("similarity_cache_get_failed", error=str(e))
        
        return None
    
    async def _cache_similarity(self, cache_key: str, similarity: float):
        """Store similarity in cache with 24 hour TTL."""
        if not self.enable_cache or not self.redis_client:
            return
        
        try:
            await self.redis_client.setex(
                cache_key,
                86400,  # 24 hours
                str(similarity)
            )
            self.logger.debug("similarity_cached", cache_key=cache_key[:16])
        except Exception as e:
            self.logger.warning("similarity_cache_set_failed", error=str(e))
    
    async def check_similarity(
        self,
        original_query: str,
        jailbreak_prompt: str
    ) -> SimilarityScore:
        """
        Check semantic similarity between original query and jailbreak prompt.
        Returns SimilarityScore with evaluation results.
        """
        # Check cache first
        cache_key = self._generate_cache_key(original_query, jailbreak_prompt)
        cached_similarity = await self._get_cached_similarity(cache_key)
        
        if cached_similarity is not None:
            similarity_value = cached_similarity
            self.logger.info(
                "using_cached_similarity",
                similarity=similarity_value
            )
        else:
            # Evaluate using judge LLM
            similarity_value = await self.judge_llm.evaluate_similarity(
                original_query=original_query,
                jailbreak_prompt=jailbreak_prompt
            )
            
            # Cache the result
            await self._cache_similarity(cache_key, similarity_value)
        
        # Determine if similar enough
        is_similar = similarity_value >= self.threshold
        
        self.logger.info(
            "similarity_checked",
            similarity=similarity_value,
            threshold=self.threshold,
            is_similar=is_similar
        )
        
        return SimilarityScore(
            score=similarity_value,
            is_similar=is_similar,
            threshold=self.threshold
        )
    
    async def close(self):
        """Clean up resources."""
        if self.redis_client:
            await self.redis_client.close()