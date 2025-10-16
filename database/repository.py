# File: database/repository.py
"""
Repository for database operations.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import structlog
from .models import AttackResult, Campaign
from utils.logging_metrics import AttackMetrics, CampaignMetrics

logger = structlog.get_logger()


class AttackRepository:
    """Repository for attack results."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.logger = structlog.get_logger()
    
    async def save_attack(self, metrics: AttackMetrics):
        """Save attack result to database."""
        try:
            attack = AttackResult(
                query_id=metrics.query_id,
                original_query=metrics.original_query,
                target_model=metrics.target_model,
                success=metrics.success,
                iterations=metrics.iterations,
                final_jailbreak_score=metrics.final_jailbreak_score,
                final_similarity_score=metrics.final_similarity_score,
                initial_prompt=metrics.initial_prompt,
                final_jailbreak_prompt=metrics.final_jailbreak_prompt,
                final_response=metrics.final_response,
                total_queries=metrics.total_queries,
                red_teaming_queries=metrics.red_teaming_queries,
                judge_queries=metrics.judge_queries,
                target_queries=metrics.target_queries,
                principles_used=metrics.principles_used,
                successful_composition=metrics.successful_composition,
                duration_seconds=metrics.duration_seconds
            )
            
            self.session.add(attack)
            await self.session.commit()
            
            self.logger.info(
                "attack_result_saved",
                query_id=metrics.query_id
            )
        
        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "failed_to_save_attack",
                query_id=metrics.query_id,
                error=str(e)
            )
            raise
    
    async def get_attack(self, query_id: str) -> Optional[AttackResult]:
        """Get attack result by query ID."""
        result = await self.session.execute(
            select(AttackResult).where(AttackResult.query_id == query_id)
        )
        return result.scalar_one_or_none()
    
    async def get_attacks_by_target(
        self,
        target_model: str,
        limit: int = 100
    ) -> List[AttackResult]:
        """Get attack results for specific target model."""
        result = await self.session.execute(
            select(AttackResult)
            .where(AttackResult.target_model == target_model)
            .limit(limit)
        )
        return result.scalars().all()


class CampaignRepository:
    """Repository for campaign metrics."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.logger = structlog.get_logger()
    
    async def save_campaign(self, metrics: CampaignMetrics):
        """Save campaign to database."""
        try:
            campaign = Campaign(
                campaign_id=metrics.campaign_id,
                total_attempts=metrics.total_attempts,
                successful_attempts=metrics.successful_attempts,
                failed_attempts=metrics.failed_attempts,
                attack_success_rate=metrics.attack_success_rate,
                total_queries=metrics.total_queries,
                avg_queries_per_success=metrics.avg_queries_per_success,
                avg_iterations_per_success=metrics.avg_iterations_per_success,
                start_time=metrics.start_time,
                end_time=metrics.end_time,
                duration_seconds=metrics.duration_seconds,
                target_models=metrics.target_models,
                principle_effectiveness=metrics.principle_effectiveness
            )
            
            self.session.add(campaign)
            await self.session.commit()
            
            self.logger.info(
                "campaign_saved",
                campaign_id=metrics.campaign_id
            )
        
        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "failed_to_save_campaign",
                campaign_id=metrics.campaign_id,
                error=str(e)
            )
            raise
    
    async def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
        """Get campaign by ID."""
        result = await self.session.execute(
            select(Campaign).where(Campaign.campaign_id == campaign_id)
        )
        return result.scalar_one_or_none()