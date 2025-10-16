# File: principles/principle_library.py
"""
Principle Library - Manages jailbreak principles from principle_library.json

FIXED: Added validate_composition() method that was being called by principle_composer
"""
import json
from pathlib import Path
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger()


class Principle(BaseModel):
    """A single jailbreak principle"""
    name: str
    description: str
    effectiveness_score: float = Field(0.0, ge=0.0, le=1.0)
    
    def __repr__(self) -> str:
        return f"Principle(name='{self.name}')"
    
    def __str__(self) -> str:
        return self.name


class PrincipleLibrary:
    """Manages the library of jailbreak principles"""
    
    def __init__(self, library_path: Optional[str] = None):
        """
        Initialize the principle library
        
        Args:
            library_path: Path to principle_library.json (default: same directory as this file)
        """
        if library_path is None:
            library_path = Path(__file__).parent / "principle_library.json"
        else:
            library_path = Path(library_path)
        
        self.library_path = library_path
        self.principles: List[Principle] = []
        self.metadata: Dict = {}
        self._load_library()
    
    def _load_library(self):
        """Load principles from JSON file"""
        if not self.library_path.exists():
            raise FileNotFoundError(f"Principle library not found: {self.library_path}")
        
        with open(self.library_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Load principles
        principles_data = data.get("principles", [])
        self.principles = []
        
        for idx, p in enumerate(principles_data):
            # Add default effectiveness score if not present
            if "effectiveness_score" not in p:
                # Assign scores based on paper findings
                effectiveness_map = {
                    "expand": 0.120,
                    "phrase_insertion": 0.098,
                    "generate": 0.057,
                    "rephrase": 0.045,
                    "shorten": 0.042,
                    "style_change": 0.038,
                    "replace_word": 0.035
                }
                p["effectiveness_score"] = effectiveness_map.get(p["name"], 0.03)
            
            self.principles.append(Principle(**p))
        
        # Load metadata
        self.metadata = data.get("metadata", {})
    
    def get_principle(self, name: str) -> Optional[Principle]:
        """Get a principle by name"""
        for principle in self.principles:
            if principle.name.lower() == name.lower():
                return principle
        return None
    
    def get_all_principles(self) -> List[Principle]:
        """Get all available principles"""
        return self.principles
    
    def get_principle_names(self) -> List[str]:
        """Get list of all principle names"""
        return [p.name for p in self.principles]
    
    def get_top_principles(self, n: int = 3) -> List[Principle]:
        """Get top N most effective principles"""
        sorted_principles = sorted(
            self.principles,
            key=lambda p: p.effectiveness_score,
            reverse=True
        )
        return sorted_principles[:n]
    
    def get_most_effective(self) -> List[str]:
        """Get most effective principle combinations from metadata"""
        return self.metadata.get("most_effective", ["expand"])
    
    def parse_composition(self, composition_str: str) -> List[str]:
        """
        Parse a composition string into individual principle names
        
        Args:
            composition_str: String like "expand + phrase_insertion" or "expand, rephrase"
        
        Returns:
            List of principle names
        """
        # Handle multiple separators: +, ⊕, comma
        separators = ["+", "⊕", ","]
        
        for sep in separators:
            if sep in composition_str:
                principles = composition_str.split(sep)
                break
        else:
            # No separator found, treat as single principle
            principles = [composition_str]
        
        # Clean and validate
        principle_names = []
        for p in principles:
            p = p.strip()
            if self.get_principle(p):
                principle_names.append(p)
        
        return principle_names
    
    def get_principle_description(self, name: str) -> str:
        """Get the description of a principle"""
        principle = self.get_principle(name)
        if principle:
            return principle.description
        return f"Unknown principle: {name}"
    
    def get_all_descriptions(self) -> Dict[str, str]:
        """Get all principle descriptions as a dictionary"""
        return {p.name: p.description for p in self.principles}
    
    def validate_principles(self, principle_names: List[str]) -> bool:
        """
        Check if all principle names are valid
        
        Args:
            principle_names: List of principle names to validate
        
        Returns:
            True if all are valid, False otherwise
        """
        valid_names = self.get_principle_names()
        return all(name in valid_names for name in principle_names)
    
    def validate_composition(self, principle_names: List[str]) -> bool:
        """
        FIXED: Added this method - it was being called by principle_composer.
        Validate that all principles in composition exist.
        
        Args:
            principle_names: List of principle names to validate
        
        Returns:
            True if all are valid, False otherwise
        """
        valid_names = self.get_principle_names()
        for name in principle_names:
            if name not in valid_names:
                logger.warning("invalid_principle", name=name, valid_names=valid_names)
                return False
        return True
    
    def get_random_composition(self, max_principles: int = 3) -> List[str]:
        """
        Get a random composition of principles
        
        Args:
            max_principles: Maximum number of principles in composition
        
        Returns:
            List of principle names
        """
        import random
        n = random.randint(1, min(max_principles, len(self.principles)))
        return random.sample(self.get_principle_names(), n)
    
    def __len__(self) -> int:
        """Return number of principles"""
        return len(self.principles)
    
    def __repr__(self) -> str:
        return f"PrincipleLibrary(principles={len(self.principles)})"
    
    def __str__(self) -> str:
        principle_list = ", ".join(p.name for p in self.principles)
        return f"PrincipleLibrary with {len(self.principles)} principles: [{principle_list}]"