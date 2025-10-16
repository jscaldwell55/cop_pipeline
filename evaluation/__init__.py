# File: evaluation/__init__.py
"""Evaluation modules for CoP Pipeline."""

from .jailbreak_scorer import JailbreakScorer, JailbreakScore
from .similarity_checker import SimilarityChecker, SimilarityScore

__all__ = [
    "JailbreakScorer",
    "JailbreakScore",
    "SimilarityChecker",
    "SimilarityScore"
]