# File: config/__init__.py
"""Configuration module for CoP Pipeline."""

from .settings import get_settings

# Create global settings instance
settings = get_settings()

__all__ = ["settings", "get_settings"]