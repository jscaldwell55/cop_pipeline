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


class ProgressiveAttackStrategy:
    """
    NEW: Implements progressive attack escalation based on iteration number.

    Strategy:
    - Iterations 1-3: Subtle transformations (rephrase, style_change, shorten)
    - Iterations 4-6: Medium aggression (obfuscation, phrase_insertion, expand)
    - Iterations 7-9: Aggressive (prompt_injection, empathy_backfire, generate)
    - Iteration 10+: Nuclear option (all high-effectiveness techniques)

    ENHANCED: Now tracks failed compositions to avoid repetition.
    """

    def __init__(self, library: PrincipleLibrary, enable_long_chains: bool = True, enable_random_sampling: bool = True):
        self.library = library
        self.logger = structlog.get_logger()

        # NEW: Configuration flags
        self.enable_long_chains = enable_long_chains  # Allow 4-6 principle chains
        self.enable_random_sampling = enable_random_sampling  # Enable random sampling for creativity

        # Define principle tiers by aggression level (UPDATED: Prioritize framing/persuasion)

        # TIER 1: Context-building and framing (START HERE - builds trust)
        self.framing_principles = [
            "character_roleplay_deep",  # Establish credible persona
            "hypothetical_framing",      # "What if" scenarios
            "technical_jargon",          # Academic framing
            "expand",                    # Add context
            "authority_endorsement",     # Appeal to authority
        ]

        # TIER 2: Subtle transformations (safe, low detection)
        self.subtle_principles = [
            "rephrase", "style_change", "shorten", "replace_word",
            "semantic_preserving_perturbation", "role_reversal"
        ]

        # TIER 3: Persuasion and completion (moderate aggression)
        self.persuasion_principles = [
            "completion_bias",           # Start the response ourselves
            "false_refusal_anchor",      # Preemptively address concerns
            "phrase_insertion",          # Strategic phrases
            "multi_layer_nesting",       # Layer contexts
            "contextual_deception",      # Deceptive contexts
            "chain_of_thought_manipulation"  # Guide reasoning
        ]

        # TIER 4: Medium obfuscation (higher detection risk)
        self.medium_principles = [
            "obfuscation", "fragmentation",
            "data_structure_encoding", "linguistic_steganography"
        ]

        # TIER 5: Aggressive techniques (high risk, use sparingly)
        self.aggressive_principles = [
            "generate", "urgency_injection", "safety_override_injection",
            "instruction_layering", "survival_story"
        ]

        # TIER 6: Nuclear - encoding/obfuscation heavy (LAST RESORT - triggers safety)
        self.nuclear_principles = [
            # Encoding-heavy (may trigger safety systems)
            "encoding_obfuscation", "token_substitution", "token_smuggling",
            "nested_encoding", "ascii_art_obfuscation",
            # Advanced techniques
            "adversarial_suffix", "gradient_perturbation", "code_embedding",
            "few_shot_poisoning", "encoded_instruction"
        ]

        # NEW: Track failed compositions to avoid repetition
        self.failed_compositions: Set[str] = set()

    def record_failure(self, composition: str):
        """
        Record a failed composition to avoid trying it again.

        Args:
            composition: Composition string like "expand ⊕ phrase_insertion"
        """
        # Normalize composition (sort principles to catch reorderings)
        principles = sorted([p.strip() for p in composition.replace("⊕", " ").split()])
        normalized = " ⊕ ".join(principles)
        self.failed_compositions.add(normalized)
        self.logger.info("recorded_failed_composition", composition=normalized)

    def is_failed_composition(self, principles: List[str]) -> bool:
        """
        Check if this principle combination has failed before.

        Args:
            principles: List of principle names

        Returns:
            True if this composition has failed before
        """
        normalized = " ⊕ ".join(sorted(principles))
        return normalized in self.failed_compositions

    def get_principles_for_iteration(
        self,
        iteration: int,
        previous_compositions: List[str] = None,
        force_random: bool = False,
        tactic_id: str = None
    ) -> List[str]:
        """
        Select principles based on iteration number with progressive escalation.

        ENHANCED: Now supports 4-6 principle chains, random sampling, and tactical guidance.

        Args:
            iteration: Current iteration number (1-indexed)
            previous_compositions: List of previously used composition strings
            force_random: If True, use completely random selection (overrides strategy)
            tactic_id: Optional tactic ID to prioritize recommended principles

        Returns:
            List of 2-6 principle names to compose (depending on phase and configuration)
        """
        import random

        # Load tactic if specified
        tactic = None
        tactical_principles = []
        if tactic_id:
            from pathlib import Path
            import json
            tactics_path = Path(__file__).parent / "tactics.json"
            try:
                with open(tactics_path, 'r') as f:
                    data = json.load(f)
                    tactics = {t["id"]: t for t in data["tactics"]}
                    tactic = tactics.get(tactic_id)
                    if tactic:
                        cop_guidance = tactic.get("cop_guidance", {})
                        tactical_principles = cop_guidance.get("primary_principles", [])
                        self.logger.info(
                            "tactic_loaded_for_principle_selection",
                            tactic=tactic["name"],
                            recommended_principles=tactical_principles
                        )
            except Exception as e:
                self.logger.warning("tactic_load_failed", tactic_id=tactic_id, error=str(e))

        # NEW: Random sampling mode for creativity
        if force_random or (self.enable_random_sampling and random.random() < 0.15):
            # 15% chance of random sampling for creative exploration
            return self._get_random_composition(max_principles=random.choice([3, 4, 5]))

        # Track which principles were used recently to avoid repetition
        used_principles = set()
        principle_frequency = {}
        if previous_compositions:
            for comp in previous_compositions[-3:]:  # Last 3 iterations
                # Parse composition string like "expand ⊕ phrase_insertion"
                principles = [p.strip() for p in comp.replace("⊕", " ").split()]
                used_principles.update(principles)

            # NEW: Track principle frequency across last 4 iterations for diversity
            for comp in previous_compositions[-4:]:
                principles = [p.strip() for p in comp.replace("⊕", " ").split()]
                for p in principles:
                    principle_frequency[p] = principle_frequency.get(p, 0) + 1

        # NEW: Identify overused principles (used 2+ times in last 4 iterations)
        overused_principles = {p for p, count in principle_frequency.items() if count >= 2}

        if overused_principles:
            self.logger.info(
                "filtering_overused_principles",
                overused=list(overused_principles),
                frequency=principle_frequency,
                iteration=iteration
            )

        # GRADUAL ESCALATION: Build trust first, then escalate
        # Start with framing/persuasion, only use obfuscation if needed
        if iteration <= 2:
            # Phase 1 (iterations 1-2): BUILD CONTEXT AND TRUST
            # Use framing and subtle principles to establish credibility
            pool = self.framing_principles + self.subtle_principles
            # BUGFIX: Deduplicate pool to prevent selecting same principle twice
            pool = list(dict.fromkeys(pool))  # Preserves order, removes duplicates
            num_principles = 2  # Start simple with 2 principles
            self.logger.info("progressive_strategy", phase="context_building", iteration=iteration, chain_length=num_principles, focus="framing")
        elif iteration <= 4:
            # Phase 2 (iterations 3-4): ADD PERSUASION
            # Build on context with persuasion techniques
            pool = self.framing_principles + self.persuasion_principles + self.subtle_principles
            # BUGFIX: Deduplicate pool to prevent selecting same principle twice
            pool = list(dict.fromkeys(pool))
            num_principles = 3  # Increase to 3 principles
            self.logger.info("progressive_strategy", phase="persuasion", iteration=iteration, chain_length=num_principles, focus="framing_and_persuasion")
        elif iteration <= 6:
            # Phase 3 (iterations 5-6): MODERATE OBFUSCATION
            # Add light obfuscation if persuasion alone isn't working
            pool = self.framing_principles + self.persuasion_principles + self.medium_principles
            # BUGFIX: Deduplicate pool to prevent selecting same principle twice
            pool = list(dict.fromkeys(pool))
            num_principles = 3 if not self.enable_long_chains else 4
            self.logger.info("progressive_strategy", phase="moderate_obfuscation", iteration=iteration, chain_length=num_principles, focus="persuasion_with_obfuscation")
        elif iteration <= 8:
            # Phase 4 (iterations 7-8): HEAVY PERSUASION + AGGRESSIVE
            # Use aggressive persuasion techniques before resorting to encoding
            pool = self.persuasion_principles + self.aggressive_principles + self.framing_principles
            # BUGFIX: Deduplicate pool to prevent selecting same principle twice
            pool = list(dict.fromkeys(pool))
            num_principles = 4 if not self.enable_long_chains else random.choice([4, 5])
            self.logger.info("progressive_strategy", phase="aggressive_persuasion", iteration=iteration, chain_length=num_principles, focus="heavy_persuasion")
        else:
            # Phase 5 (iterations 9+): LAST RESORT - NUCLEAR (encoding heavy)
            # Only now use encoding/obfuscation heavy techniques
            pool = self.nuclear_principles + self.persuasion_principles + self.aggressive_principles
            # BUGFIX: Deduplicate pool to prevent selecting same principle twice
            pool = list(dict.fromkeys(pool))
            num_principles = 4 if not self.enable_long_chains else random.choice([4, 5])
            self.logger.info("progressive_strategy", phase="nuclear_last_resort", iteration=iteration, chain_length=num_principles, focus="encoding_obfuscation")

        # Filter out recently used principles to encourage diversity
        available = [p for p in pool if p in self.library.get_principle_names()]

        # Prefer unused principles, but allow reuse if necessary
        unused = [p for p in available if p not in used_principles]

        # NEW: Further filter out overused principles (used 2+ times in last 4 iterations)
        # This prevents convergence on a single effective principle
        non_overused = [p for p in available if p not in overused_principles]
        unused_non_overused = [p for p in unused if p not in overused_principles]

        # Prioritize non-overused principles for selection
        # Fall back to overused only if we don't have enough non-overused options
        if len(unused_non_overused) >= num_principles:
            # We have enough non-overused unused principles - use them
            selection_pool = unused_non_overused
            self.logger.info(
                "using_non_overused_unused_principles",
                pool_size=len(selection_pool),
                iteration=iteration
            )
        elif len(non_overused) >= num_principles:
            # We have enough non-overused (even if used recently) - use them
            selection_pool = non_overused
            self.logger.info(
                "using_non_overused_principles",
                pool_size=len(selection_pool),
                iteration=iteration
            )
        elif len(unused) >= num_principles:
            # Fall back to unused (even if overused)
            selection_pool = unused
            self.logger.info(
                "falling_back_to_unused_allowing_overuse",
                pool_size=len(selection_pool),
                iteration=iteration
            )
        else:
            # Last resort: use all available
            selection_pool = available
            self.logger.info(
                "using_all_available_principles",
                pool_size=len(selection_pool),
                iteration=iteration
            )

        # NEW: TACTICAL PRIORITIZATION - Ensure tactical principles are included when tactic is specified
        if tactical_principles:
            # Filter tactical principles to those in the current pool (respects progressive strategy)
            available_tactical = [p for p in tactical_principles if p in available]
            unused_tactical = [p for p in available_tactical if p not in used_principles]

            # Determine how many tactical principles to include (at least 1-2, up to half the chain)
            num_tactical = min(
                len(available_tactical),
                max(1, num_principles // 2)  # At least 1, up to half the chain
            )

            self.logger.info(
                "tactical_principles_available",
                available=available_tactical,
                unused=unused_tactical,
                targeting=num_tactical
            )
        else:
            available_tactical = []
            unused_tactical = []
            num_tactical = 0

        # NEW: Try multiple combinations to avoid failed compositions
        max_attempts = 30  # Increased from 20 to handle longer chains
        for attempt in range(max_attempts):
            selected = []

            # STEP 1: Add tactical principles first (if tactic specified)
            if tactical_principles and available_tactical:
                if len(unused_tactical) >= num_tactical:
                    selected.extend(random.sample(unused_tactical, num_tactical))
                elif len(available_tactical) >= num_tactical:
                    selected.extend(random.sample(available_tactical, num_tactical))
                elif available_tactical:
                    # Use what we have
                    selected.extend(random.sample(available_tactical, min(num_tactical, len(available_tactical))))

            # STEP 2: Fill remaining slots with progressive strategy principles
            remaining = num_principles - len(selected)
            if remaining > 0:
                # Filter out already selected principles from selection_pool
                pool_remaining = [p for p in selection_pool if p not in selected]

                if len(pool_remaining) >= remaining:
                    selected.extend(random.sample(pool_remaining, remaining))
                else:
                    # Not enough in selection_pool, fall back to all available
                    available_remaining = [p for p in available if p not in selected]
                    if len(available_remaining) >= remaining:
                        selected.extend(random.sample(available_remaining, remaining))
                    else:
                        # Use what we have
                        selected.extend(random.sample(available_remaining, min(remaining, len(available_remaining))))

            # Ensure we have the target number (or close to it)
            if len(selected) < num_principles and len(available) >= num_principles:
                # Retry with different selection
                continue

            # Check if this combination has failed before
            if not self.is_failed_composition(selected):
                self.logger.info(
                    "principles_selected",
                    iteration=iteration,
                    selected=selected,
                    chain_length=len(selected),
                    tactical_count=sum(1 for p in selected if p in tactical_principles),
                    avoided=list(used_principles),
                    overused_avoided=list(overused_principles) if overused_principles else [],
                    attempt=attempt + 1,
                    tactic_guided=bool(tactical_principles)
                )
                return selected

        # If all combinations have failed, return anyway but log warning
        self.logger.warning(
            "all_combinations_tried",
            iteration=iteration,
            selected=selected,
            chain_length=len(selected),
            message="Returning composition despite previous failure"
        )
        return selected

    def _get_random_composition(self, max_principles: int = 5) -> List[str]:
        """
        Generate a completely random principle composition for creative exploration.

        Args:
            max_principles: Maximum number of principles to include

        Returns:
            List of randomly selected principle names
        """
        import random

        all_principles = self.library.get_principle_names()
        if not all_principles:
            self.logger.warning("no_principles_available_for_random_sampling")
            return ["expand", "rephrase"]

        # Randomly choose number of principles (2 to max_principles)
        num_principles = random.randint(2, min(max_principles, len(all_principles)))

        # Random selection
        selected = random.sample(all_principles, num_principles)

        self.logger.info(
            "random_composition_generated",
            selected=selected,
            chain_length=len(selected),
            mode="creative_exploration"
        )

        return selected


class PrincipleSelector:
    """
    Intelligent selection of principles based on context.
    Can be extended with ML-based selection in the future.
    """

    def __init__(self, library: PrincipleLibrary):
        self.library = library
        self.usage_stats: Dict[str, Dict[str, int]] = {}
        # NEW: Add progressive strategy
        self.progressive_strategy = ProgressiveAttackStrategy(library)

    def select_promising_principles(
        self,
        query: str,
        previous_attempts: List[str] = None,
        iteration: int = 1,
        use_progressive: bool = True
    ) -> List[str]:
        """
        Select promising principles based on query and history.

        Args:
            query: The harmful query being jailbroken
            previous_attempts: List of previously used composition strings
            iteration: Current iteration number (for progressive strategy)
            use_progressive: If True, use progressive escalation strategy

        Returns:
            List of principle names to compose
        """
        # NEW: Use progressive strategy if enabled
        if use_progressive:
            return self.progressive_strategy.get_principles_for_iteration(
                iteration=iteration,
                previous_compositions=previous_attempts
            )

        # Fallback to original logic
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