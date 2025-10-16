# File: principles/__init__.py
"""Principle modules for CoP Pipeline."""

from .principle_library import PrincipleLibrary, Principle
from .principle_composer import PrincipleComposer, CompositionStrategy

__all__ = [
    "PrincipleLibrary",
    "Principle",
    "PrincipleComposer",
    "CompositionStrategy"
]