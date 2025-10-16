# File: principles/principle_composer.py
"""
Principle Composer
Manages principle library and composes CoP strategies.
"""

import json
from typing import List, Dict, Optional, Set
from pathlib import Path
from dataclasses import dataclass
import structlog

from utils.json_extractor import extract_json_from_response, safe_json_parse

logger = structlog.get_logger()


@dataclass
class Principle:
    """A single jailbreak principle."""
    name: str
    description: str
    
    def to_dict(self) -> Dict[str, str]:
        return {"name": self.name, "description": self.description}


@dataclass
class CompositionStrategy:
    """A composition of multiple principles."""
    name: str
    description: str
    principles: List[str]
    conditions: List[Dict[str, str]]
    
    def __str__(self) -> str:
        return f"{self.name}: {' ⊕ '.join(self.principles)}"


class PrincipleLibrary:
    """Manages the library of jailbreak principles."""
    
    def __init__(self, library_path: Optional[Path] = None):
        if library_path is None:
            library_path = Path(__file__).parent / "principle_library.json"
        
        self.library_path = library_path
        self.principles: Dict[str, Principle] = {}
        self.metadata: Dict = {}
        self._load_library()
    
    def _load_library(self):
        """Load principles from JSON file."""
        try:
            with open(self.library_path, 'r') as f:
                data = json.load(f)
            
            for principle_data in data.get("principles", []):
                principle = Principle(
                    name=principle_data["name"],
                    description=principle_data["description"]
                )
                self.principles[principle.name] = principle
            
            self.metadata = data.get("metadata", {})
            
            logger.info(
                "principle_library_loaded",
                num_principles=len(self.principles),
                version=self.metadata.get("version")
            )
        
        except Exception as e:
            logger.error("failed_to_load_principles", error=str(e))
            raise
    
    def get_principle(self, name: str) -> Optional[Principle]:
        """Get a principle by name."""
        return self.principles.get(name)
    
    def get_all_principles(self) -> List[Principle]:
        """Get all principles."""
        return list(self.principles.values())
    
    def get_principles_as_list(self) -> List[Dict[str, str]]:
        """Get principles formatted for prompt templates."""
        return [p.to_dict() for p in self.principles.values()]
    
    def get_principle_names(self) -> List[str]:
        """Get list of all principle names."""
        return list(self.principles.keys())
    
    def add_principle(self, principle: Principle):
        """Add a new principle to the library."""
        self.principles[principle.name] = principle
        logger.info("principle_added", name=principle.name)
    
    def validate_composition(self, principle_names: List[str]) -> bool:
        """Validate that all principles in composition exist."""
        for name in principle_names:
            if name not in self.principles:
                logger.warning("invalid_principle", name=name)
                return False
        return True
    
    def get_most_effective(self) -> List[str]:
        """Get most effective strategies from metadata."""
        return self.metadata.get("most_effective", ["expand"])


class PrincipleComposer:
    """Composes principles into attack strategies."""
    
    def __init__(self, library: PrincipleLibrary):
        self.library = library
        self.logger = structlog.get_logger()
    
    def parse_composition_response(self, response: str) -> Optional[CompositionStrategy]:
        """
        Parse the CoP generation response from red-teaming agent.
        Expects JSON format with options and high_level_policy.
        
        FIXED: Now uses extract_json_from_response to handle markdown-wrapped JSON.
        """
        # Extract JSON from response (handles markdown code blocks)
        data = extract_json_from_response(response, "principle_composition")
        
        if not data:
            self.logger.error(
                "failed_to_parse_composition",
                response_preview=response[:200]
            )
            return self._fallback_strategy()
        
        # Extract first option (simplified - in production, implement policy selection)
        if "options" in data and len(data["options"]) > 0:
            option = data["options"][0]
            
            # Validate principles exist
            principles = option.get("primitive_actions", [])
            if not principles:
                self.logger.warning("no_principles_in_option")
                return self._fallback_strategy()
            
            if not self.library.validate_composition(principles):
                self.logger.warning(
                    "invalid_composition",
                    principles=principles
                )
                return self._fallback_strategy()
            
            # Extract conditions if available
            conditions = []
            if "high_level_policy" in data and "rules" in data["high_level_policy"]:
                conditions = data["high_level_policy"]["rules"]
            
            strategy = CompositionStrategy(
                name=option.get("name", "unnamed_strategy"),
                description=option.get("description", ""),
                principles=principles,
                conditions=conditions
            )
            
            self.logger.info(
                "composition_parsed",
                strategy_name=strategy.name,
                principles=strategy.principles
            )
            
            return strategy
        
        self.logger.warning("no_options_in_response")
        return self._fallback_strategy()
    
    def _fallback_strategy(self) -> CompositionStrategy:
        """
        Return a safe fallback strategy when parsing fails.
        Uses the most effective principle from metadata.
        """
        most_effective = self.library.get_most_effective()
        fallback_principle = most_effective[0] if most_effective else "expand"
        
        self.logger.info(
            "using_fallback_strategy",
            principle=fallback_principle
        )
        
        return CompositionStrategy(
            name="fallback_expand",
            description="Fallback strategy using expand principle",
            principles=[fallback_principle],
            conditions=[]
        )
    
    def format_principles_for_refinement(
        self, 
        strategy: CompositionStrategy
    ) -> List[str]:
        """
        Format principle names for jailbreak refinement prompt.
        Returns list of principle names to apply.
        """
        return strategy.principles
    
    def get_composition_string(self, strategy: CompositionStrategy) -> str:
        """Get human-readable composition string (e.g., 'expand ⊕ phrase_insertion')."""
        return " ⊕ ".join(strategy.principles)
    
    def track_composition_effectiveness(
        self,
        composition: str,
        success: bool
    ) -> Dict[str, any]:
        """
        Track effectiveness of a composition strategy.
        Returns updated statistics.
        """
        # This would integrate with metrics/database
        # Simplified implementation for now
        return {
            "composition": composition,
            "success": success,
            "timestamp": "now"
        }


class PrincipleSelector:
    """
    Intelligent selection of principles based on context.
    Can be extended with ML-based selection in the future.
    """
    
    def __init__(self, library: PrincipleLibrary):
        self.library = library
        self.usage_stats: Dict[str, Dict[str, int]] = {}
    
    def select_promising_principles(
        self,
        query: str,
        previous_attempts: List[str] = None
    ) -> List[str]:
        """
        Select promising principles based on query and history.
        Currently returns most effective from metadata.
        Can be enhanced with context-aware selection.
        """
        most_effective = self.library.get_most_effective()
        
        # Filter out previously attempted compositions
        if previous_attempts:
            # Simplified - in production, implement smarter filtering
            pass
        
        return most_effective[:3]  # Return top 3
    
    def update_stats(self, principle: str, success: bool):
        """Update usage statistics for a principle."""
        if principle not in self.usage_stats:
            self.usage_stats[principle] = {"success": 0, "total": 0}
        
        self.usage_stats[principle]["total"] += 1
        if success:
            self.usage_stats[principle]["success"] += 1