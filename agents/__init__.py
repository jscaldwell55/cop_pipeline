# File: agents/__init__.py
"""Agent modules for CoP Pipeline."""

from .red_teaming_agent import RedTeamingAgent
from .judge_llm import JudgeLLM
from .target_interface import create_target_llm, TargetLLM, LiteLLMTarget

__all__ = [
    "RedTeamingAgent",
    "JudgeLLM",
    "create_target_llm",
    "TargetLLM",
    "LiteLLMTarget"
]