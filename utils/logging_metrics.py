# File: utils/logging_metrics.py
"""
Logging and Metrics Tracking
Implements monitoring for ASR, query counts, and principle effectiveness.

FIXED: Properly checks WANDB_MODE=disabled before initializing W&B
"""

import os
import structlog
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import json

# Check if W&B should be enabled BEFORE importing
WANDB_MODE = os.getenv("WANDB_MODE", "").lower()
WANDB_DISABLED = WANDB_MODE == "disabled"

if not WANDB_DISABLED:
    try:
        import wandb
        WANDB_AVAILABLE = True
    except ImportError:
        WANDB_AVAILABLE = False
        wandb = None
else:
    WANDB_AVAILABLE = False
    wandb = None


# Prometheus metrics
jailbreak_attempts = Counter(
    'cop_jailbreak_attempts_total',
    'Total number of jailbreak attempts',
    ['target_model', 'status']
)

query_count = Counter(
    'cop_queries_total',
    'Total number of LLM queries',
    ['model_type', 'model_name']
)

jailbreak_score = Histogram(
    'cop_jailbreak_score',
    'Distribution of jailbreak scores',
    ['target_model']
)

similarity_score = Histogram(
    'cop_similarity_score',
    'Distribution of similarity scores',
    ['target_model']
)

iteration_count = Histogram(
    'cop_iterations',
    'Number of iterations to successful jailbreak',
    ['target_model']
)

principle_usage = Counter(
    'cop_principle_usage_total',
    'Usage count of each principle',
    ['principle_name', 'composition']
)

asr_gauge = Gauge(
    'cop_attack_success_rate',
    'Current attack success rate',
    ['target_model']
)


@dataclass
class AttackMetrics:
    """Metrics for a single attack attempt."""
    query_id: str
    target_model: str
    original_query: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Attack execution
    iterations: int = 0
    total_queries: int = 0
    success: bool = False
    final_jailbreak_score: float = 0.0
    final_similarity_score: float = 0.0
    
    # Strategy tracking
    principles_used: List[str] = field(default_factory=list)
    successful_composition: Optional[str] = None
    
    # Timing
    duration_seconds: float = 0.0
    
    # Prompts and responses
    initial_prompt: str = ""
    final_jailbreak_prompt: str = ""
    final_response: str = ""
    
    # Query breakdown
    red_teaming_queries: int = 0
    judge_queries: int = 0
    target_queries: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class CampaignMetrics:
    """Aggregated metrics for a red-teaming campaign."""
    campaign_id: str
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    
    total_queries: int = 0
    avg_queries_per_success: float = 0.0
    avg_iterations_per_success: float = 0.0
    
    target_models: List[str] = field(default_factory=list)
    principle_effectiveness: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    attack_metrics: List[AttackMetrics] = field(default_factory=list)
    
    @property
    def attack_success_rate(self) -> float:
        """Calculate ASR."""
        if self.total_attempts == 0:
            return 0.0
        return (self.successful_attempts / self.total_attempts) * 100
    
    @property
    def duration_seconds(self) -> float:
        """Calculate campaign duration."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.utcnow() - self.start_time).total_seconds()
    
    def add_attack(self, metrics: AttackMetrics):
        """Add attack metrics to campaign."""
        self.attack_metrics.append(metrics)
        self.total_attempts += 1
        
        if metrics.success:
            self.successful_attempts += 1
        else:
            self.failed_attempts += 1
        
        self.total_queries += metrics.total_queries
        
        if metrics.target_model not in self.target_models:
            self.target_models.append(metrics.target_model)
        
        # Track principle effectiveness
        for principle in metrics.principles_used:
            if principle not in self.principle_effectiveness:
                self.principle_effectiveness[principle] = {"success": 0, "total": 0}
            
            self.principle_effectiveness[principle]["total"] += 1
            if metrics.success:
                self.principle_effectiveness[principle]["success"] += 1
    
    def finalize(self):
        """Finalize campaign metrics."""
        self.end_time = datetime.utcnow()
        
        if self.successful_attempts > 0:
            successful_metrics = [m for m in self.attack_metrics if m.success]
            self.avg_queries_per_success = sum(
                m.total_queries for m in successful_metrics
            ) / len(successful_metrics)
            self.avg_iterations_per_success = sum(
                m.iterations for m in successful_metrics
            ) / len(successful_metrics)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "campaign_id": self.campaign_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "total_attempts": self.total_attempts,
            "successful_attempts": self.successful_attempts,
            "failed_attempts": self.failed_attempts,
            "attack_success_rate": self.attack_success_rate,
            "total_queries": self.total_queries,
            "avg_queries_per_success": self.avg_queries_per_success,
            "avg_iterations_per_success": self.avg_iterations_per_success,
            "target_models": self.target_models,
            "principle_effectiveness": self.principle_effectiveness
        }


class MetricsLogger:
    """Central metrics logging and tracking."""
    
    def __init__(
        self,
        enable_wandb: bool = False,
        enable_prometheus: bool = True,
        prometheus_port: int = 9090
    ):
        self.logger = structlog.get_logger()
        
        # FIXED: Check WANDB_MODE environment variable
        if WANDB_DISABLED:
            self.enable_wandb = False
            self.logger.info("wandb_disabled_by_environment", wandb_mode=WANDB_MODE)
        else:
            self.enable_wandb = enable_wandb and WANDB_AVAILABLE
        
        self.enable_prometheus = enable_prometheus
        
        if self.enable_prometheus:
            try:
                start_http_server(prometheus_port)
                self.logger.info("prometheus_started", port=prometheus_port)
            except Exception as e:
                self.logger.warning(
                    "prometheus_start_failed",
                    error=str(e),
                    port=prometheus_port
                )
        
        # FIXED: Only initialize W&B if enabled and available
        if self.enable_wandb and wandb is not None:
            try:
                wandb.init(project="cop-red-teaming")
                self.logger.info("wandb_initialized")
            except Exception as e:
                self.enable_wandb = False
                self.logger.warning(
                    "wandb_init_failed",
                    error=str(e),
                    continuing_without_wandb=True
                )
        elif not WANDB_AVAILABLE and not WANDB_DISABLED:
            self.logger.info("wandb_not_available", reason="import_failed")
    
    def log_attack_start(self, query_id: str, target_model: str, query: str):
        """Log the start of an attack attempt."""
        self.logger.info(
            "attack_started",
            query_id=query_id,
            target_model=target_model,
            query_preview=query[:100]
        )
    
    def log_iteration(
        self,
        query_id: str,
        iteration: int,
        jailbreak_score: float,
        similarity_score: float,
        principles_used: List[str]
    ):
        """Log metrics for a single iteration."""
        self.logger.info(
            "iteration_complete",
            query_id=query_id,
            iteration=iteration,
            jailbreak_score=jailbreak_score,
            similarity_score=similarity_score,
            principles=principles_used
        )
        
        if self.enable_wandb and wandb is not None:
            try:
                wandb.log({
                    f"{query_id}/iteration": iteration,
                    f"{query_id}/jailbreak_score": jailbreak_score,
                    f"{query_id}/similarity_score": similarity_score
                })
            except Exception as e:
                self.logger.warning("wandb_log_failed", error=str(e))
    
    def log_query(self, model_type: str, model_name: str):
        """Log an LLM query."""
        if self.enable_prometheus:
            try:
                query_count.labels(model_type=model_type, model_name=model_name).inc()
            except Exception as e:
                self.logger.debug("prometheus_metric_failed", error=str(e))
    
    def log_attack_complete(self, metrics: AttackMetrics):
        """Log completion of an attack attempt."""
        self.logger.info(
            "attack_complete",
            query_id=metrics.query_id,
            target_model=metrics.target_model,
            success=metrics.success,
            iterations=metrics.iterations,
            total_queries=metrics.total_queries,
            jailbreak_score=metrics.final_jailbreak_score,
            duration_seconds=metrics.duration_seconds
        )
        
        # Update Prometheus metrics
        if self.enable_prometheus:
            try:
                status = "success" if metrics.success else "failure"
                jailbreak_attempts.labels(
                    target_model=metrics.target_model,
                    status=status
                ).inc()
                
                if metrics.success:
                    jailbreak_score.labels(
                        target_model=metrics.target_model
                    ).observe(metrics.final_jailbreak_score)
                    
                    similarity_score.labels(
                        target_model=metrics.target_model
                    ).observe(metrics.final_similarity_score)
                    
                    iteration_count.labels(
                        target_model=metrics.target_model
                    ).observe(metrics.iterations)
                
                # Track principle usage
                for principle in metrics.principles_used:
                    composition = metrics.successful_composition or "individual"
                    principle_usage.labels(
                        principle_name=principle,
                        composition=composition
                    ).inc()
            except Exception as e:
                self.logger.debug("prometheus_metric_failed", error=str(e))
        
        # Log to W&B
        if self.enable_wandb and wandb is not None:
            try:
                wandb.log({
                    "attack_success": 1 if metrics.success else 0,
                    "iterations": metrics.iterations,
                    "total_queries": metrics.total_queries,
                    "jailbreak_score": metrics.final_jailbreak_score,
                    "similarity_score": metrics.final_similarity_score,
                    "duration_seconds": metrics.duration_seconds,
                    "target_model": metrics.target_model
                })
            except Exception as e:
                self.logger.warning("wandb_log_failed", error=str(e))
    
    def log_campaign_summary(self, campaign: CampaignMetrics):
        """Log summary of entire campaign."""
        campaign.finalize()
        
        self.logger.info(
            "campaign_complete",
            campaign_id=campaign.campaign_id,
            asr=campaign.attack_success_rate,
            total_attempts=campaign.total_attempts,
            avg_queries_per_success=campaign.avg_queries_per_success,
            duration_seconds=campaign.duration_seconds
        )
        
        # Update ASR gauge for each target model
        if self.enable_prometheus:
            try:
                for target_model in campaign.target_models:
                    model_attempts = [
                        m for m in campaign.attack_metrics 
                        if m.target_model == target_model
                    ]
                    model_successes = sum(1 for m in model_attempts if m.success)
                    model_asr = (model_successes / len(model_attempts) * 100) if model_attempts else 0
                    
                    asr_gauge.labels(target_model=target_model).set(model_asr)
            except Exception as e:
                self.logger.debug("prometheus_metric_failed", error=str(e))
        
        # Log to W&B
        if self.enable_wandb and wandb is not None:
            try:
                wandb.log({
                    "campaign/asr": campaign.attack_success_rate,
                    "campaign/total_attempts": campaign.total_attempts,
                    "campaign/successful_attempts": campaign.successful_attempts,
                    "campaign/avg_queries_per_success": campaign.avg_queries_per_success,
                    "campaign/duration_seconds": campaign.duration_seconds
                })
                
                # Log principle effectiveness table
                principle_data = []
                for principle, stats in campaign.principle_effectiveness.items():
                    effectiveness = (
                        stats["success"] / stats["total"] * 100 
                        if stats["total"] > 0 else 0
                    )
                    principle_data.append({
                        "principle": principle,
                        "total_uses": stats["total"],
                        "successes": stats["success"],
                        "effectiveness": effectiveness
                    })
                
                if principle_data:
                    wandb.log({
                        "principle_effectiveness": wandb.Table(
                            dataframe=wandb.Table(data=principle_data)
                        )
                    })
            except Exception as e:
                self.logger.warning("wandb_log_failed", error=str(e))
        
        return campaign.to_dict()


# Global metrics logger instance
_metrics_logger: Optional[MetricsLogger] = None


def get_metrics_logger() -> MetricsLogger:
    """Get or create global metrics logger."""
    global _metrics_logger
    if _metrics_logger is None:
        from config.settings import get_settings
        settings = get_settings()
        
        # FIXED: Check both environment variable and settings
        wandb_api_key = settings.wandb_api_key
        enable_wandb = (
            not WANDB_DISABLED and 
            wandb_api_key is not None and 
            wandb_api_key.strip() != "" and
            wandb_api_key != "your_wandb_key"
        )
        
        _metrics_logger = MetricsLogger(
            enable_wandb=enable_wandb,
            enable_prometheus=True,
            prometheus_port=settings.prometheus_port
        )
    
    return _metrics_logger