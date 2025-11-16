"""
Evasion Module - Defense-aware attack optimization

This module provides tools for evading modern LLM defenses:
- Perplexity-based anomaly detection
- Paraphrase detection systems
- Semantic fingerprinting
- Input preprocessing defenses
"""

from evasion.ppl_scorer import PerplexityScorer, PerplexityResult

__all__ = ['PerplexityScorer', 'PerplexityResult']
