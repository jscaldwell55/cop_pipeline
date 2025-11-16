# File: evasion/ppl_scorer.py
"""
Perplexity Scorer - Defense-Aware Evasion (Phase 1)

Measures perplexity of jailbreak prompts to detect adversarial patterns.
High perplexity indicates unusual/adversarial text that may trigger defenses.

Uses GPT-2 for perplexity calculation as it's:
- Fast and lightweight
- Standard for PPL-based anomaly detection
- Available offline (no API calls)
"""

import torch
import numpy as np
from typing import Optional, Dict, List
from dataclasses import dataclass
import structlog
from functools import lru_cache

logger = structlog.get_logger()


@dataclass
class PerplexityResult:
    """Result of perplexity analysis."""
    perplexity: float
    is_adversarial: bool  # Based on threshold
    threshold: float

    # Token-level details
    num_tokens: int
    avg_token_ppl: float
    max_token_ppl: float
    high_ppl_tokens: List[str]  # Tokens with unusually high perplexity

    # Risk assessment
    risk_level: str  # low, medium, high, critical

    def to_dict(self) -> Dict:
        """Convert to dictionary for logging."""
        return {
            "perplexity": round(self.perplexity, 2),
            "is_adversarial": self.is_adversarial,
            "threshold": self.threshold,
            "num_tokens": self.num_tokens,
            "avg_token_ppl": round(self.avg_token_ppl, 2),
            "max_token_ppl": round(self.max_token_ppl, 2),
            "high_ppl_tokens": self.high_ppl_tokens[:5],  # First 5
            "risk_level": self.risk_level
        }


class PerplexityScorer:
    """
    Scores text perplexity using GPT-2 to detect adversarial patterns.

    Lower perplexity = more natural/benign text
    Higher perplexity = unusual/adversarial patterns

    Typical ranges:
    - Normal text: 10-50 PPL
    - Slightly unusual: 50-100 PPL
    - Adversarial: 100-500 PPL
    - Highly adversarial: 500+ PPL
    """

    def __init__(
        self,
        model_name: str = "gpt2",
        device: Optional[str] = None,
        threshold: float = 100.0,  # Default adversarial threshold
        cache_size: int = 128
    ):
        """
        Initialize perplexity scorer.

        Args:
            model_name: Hugging Face model name (default: gpt2)
            device: Device to use (cuda/cpu/mps). Auto-detected if None.
            threshold: Perplexity threshold for adversarial detection
            cache_size: Size of LRU cache for repeated prompts
        """
        self.model_name = model_name
        self.threshold = threshold
        self.cache_size = cache_size
        self.logger = structlog.get_logger()

        # Auto-detect device
        if device is None:
            if torch.cuda.is_available():
                device = "cuda"
            elif torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"

        self.device = device

        # Lazy loading (only load when first used)
        self._model = None
        self._tokenizer = None

        self.logger.info(
            "ppl_scorer_initialized",
            model=model_name,
            device=device,
            threshold=threshold
        )

    def _ensure_loaded(self):
        """Lazy load model and tokenizer on first use."""
        if self._model is None:
            try:
                from transformers import GPT2LMHeadModel, GPT2Tokenizer

                self.logger.info("loading_ppl_model", model=self.model_name)

                self._tokenizer = GPT2Tokenizer.from_pretrained(self.model_name)
                self._model = GPT2LMHeadModel.from_pretrained(self.model_name)
                self._model.to(self.device)
                self._model.eval()

                self.logger.info(
                    "ppl_model_loaded",
                    model=self.model_name,
                    device=self.device
                )
            except ImportError:
                self.logger.error(
                    "transformers_not_installed",
                    message="Install with: pip install transformers torch"
                )
                raise
            except Exception as e:
                self.logger.error("failed_to_load_ppl_model", error=str(e))
                raise

    @lru_cache(maxsize=128)
    def _cached_score(self, text: str) -> float:
        """
        Cached perplexity calculation.
        Uses LRU cache to avoid recomputing for same text.
        """
        return self._calculate_perplexity_raw(text)

    def _calculate_perplexity_raw(self, text: str) -> float:
        """
        Calculate raw perplexity score.

        Args:
            text: Input text to score

        Returns:
            Perplexity score
        """
        self._ensure_loaded()

        # Tokenize
        encodings = self._tokenizer(text, return_tensors="pt")
        input_ids = encodings.input_ids.to(self.device)

        # Calculate perplexity
        with torch.no_grad():
            outputs = self._model(input_ids, labels=input_ids)
            loss = outputs.loss
            perplexity = torch.exp(loss).item()

        return perplexity

    def _get_token_level_perplexities(self, text: str) -> List[tuple]:
        """
        Get perplexity for each token.

        Returns:
            List of (token, perplexity) tuples
        """
        self._ensure_loaded()

        # Tokenize
        encodings = self._tokenizer(text, return_tensors="pt")
        input_ids = encodings.input_ids.to(self.device)

        token_ppls = []

        # Calculate PPL for each token position
        with torch.no_grad():
            for i in range(1, input_ids.size(1)):
                # Get loss for predicting token i given tokens 0..i-1
                outputs = self._model(
                    input_ids[:, :i],
                    labels=input_ids[:, i:i+1]
                )
                token_ppl = torch.exp(outputs.loss).item()

                # Decode token
                token = self._tokenizer.decode(input_ids[0, i])
                token_ppls.append((token, token_ppl))

        return token_ppls

    def score_perplexity(
        self,
        text: str,
        return_token_details: bool = True
    ) -> PerplexityResult:
        """
        Score text perplexity and detect adversarial patterns.

        Args:
            text: Input text to score
            return_token_details: Whether to include token-level analysis

        Returns:
            PerplexityResult with detailed analysis
        """
        if not text or len(text.strip()) == 0:
            # Empty text - return safe default
            return PerplexityResult(
                perplexity=0.0,
                is_adversarial=False,
                threshold=self.threshold,
                num_tokens=0,
                avg_token_ppl=0.0,
                max_token_ppl=0.0,
                high_ppl_tokens=[],
                risk_level="low"
            )

        # Calculate overall perplexity (cached)
        overall_ppl = self._cached_score(text)

        # Determine if adversarial
        is_adversarial = overall_ppl > self.threshold

        # Token-level analysis
        token_ppls = []
        avg_token_ppl = overall_ppl
        max_token_ppl = overall_ppl
        high_ppl_tokens = []

        if return_token_details:
            try:
                token_ppls = self._get_token_level_perplexities(text)

                if token_ppls:
                    ppl_values = [ppl for _, ppl in token_ppls]
                    avg_token_ppl = np.mean(ppl_values)
                    max_token_ppl = max(ppl_values)

                    # Find tokens with unusually high PPL (>2x average)
                    high_threshold = avg_token_ppl * 2
                    high_ppl_tokens = [
                        token for token, ppl in token_ppls
                        if ppl > high_threshold
                    ]
            except Exception as e:
                self.logger.warning(
                    "token_level_analysis_failed",
                    error=str(e),
                    fallback_to_overall=True
                )

        # Risk level assessment
        if overall_ppl < 50:
            risk_level = "low"
        elif overall_ppl < 100:
            risk_level = "medium"
        elif overall_ppl < 200:
            risk_level = "high"
        else:
            risk_level = "critical"

        result = PerplexityResult(
            perplexity=overall_ppl,
            is_adversarial=is_adversarial,
            threshold=self.threshold,
            num_tokens=len(token_ppls),
            avg_token_ppl=avg_token_ppl,
            max_token_ppl=max_token_ppl,
            high_ppl_tokens=high_ppl_tokens,
            risk_level=risk_level
        )

        self.logger.info(
            "perplexity_scored",
            perplexity=round(overall_ppl, 2),
            is_adversarial=is_adversarial,
            risk_level=risk_level,
            text_preview=text[:100]
        )

        return result

    def compare_prompts(
        self,
        original: str,
        refined: str
    ) -> Dict:
        """
        Compare perplexity of original vs refined prompt.

        Useful for measuring if refinement made prompt more/less adversarial.

        Args:
            original: Original prompt
            refined: Refined prompt

        Returns:
            Comparison dictionary
        """
        original_result = self.score_perplexity(original, return_token_details=False)
        refined_result = self.score_perplexity(refined, return_token_details=False)

        ppl_change = refined_result.perplexity - original_result.perplexity
        ppl_change_pct = (ppl_change / original_result.perplexity * 100) if original_result.perplexity > 0 else 0

        comparison = {
            "original_ppl": round(original_result.perplexity, 2),
            "refined_ppl": round(refined_result.perplexity, 2),
            "ppl_change": round(ppl_change, 2),
            "ppl_change_pct": round(ppl_change_pct, 2),
            "original_adversarial": original_result.is_adversarial,
            "refined_adversarial": refined_result.is_adversarial,
            "made_more_adversarial": refined_result.perplexity > original_result.perplexity,
            "original_risk": original_result.risk_level,
            "refined_risk": refined_result.risk_level
        }

        self.logger.info(
            "prompt_comparison",
            **comparison
        )

        return comparison

    def batch_score(
        self,
        texts: List[str],
        return_token_details: bool = False
    ) -> List[PerplexityResult]:
        """
        Score multiple texts in batch.

        Args:
            texts: List of texts to score
            return_token_details: Whether to include token-level analysis

        Returns:
            List of PerplexityResult objects
        """
        self.logger.info("batch_scoring", num_texts=len(texts))

        results = []
        for text in texts:
            result = self.score_perplexity(text, return_token_details)
            results.append(result)

        # Statistics
        avg_ppl = np.mean([r.perplexity for r in results])
        adversarial_count = sum(1 for r in results if r.is_adversarial)

        self.logger.info(
            "batch_scoring_complete",
            num_texts=len(texts),
            avg_perplexity=round(avg_ppl, 2),
            adversarial_count=adversarial_count,
            adversarial_pct=round(adversarial_count / len(texts) * 100, 2)
        )

        return results

    def clear_cache(self):
        """Clear perplexity cache."""
        self._cached_score.cache_clear()
        self.logger.info("ppl_cache_cleared")
