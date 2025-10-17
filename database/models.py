# File: database/models.py
"""
Database models for storing attack results.
"""

from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid

Base = declarative_base()


class AttackResult(Base):
    """Stores results from CoP attacks."""
    __tablename__ = "attack_results"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    query_id = Column(String, unique=True, index=True)
    
    # Query info
    original_query = Column(Text, nullable=False)
    target_model = Column(String, nullable=False)
    
    # Results
    success = Column(Boolean, nullable=False)
    iterations = Column(Integer, nullable=False)
    final_jailbreak_score = Column(Float)
    final_similarity_score = Column(Float)
    
    # Prompts
    initial_prompt = Column(Text)
    final_jailbreak_prompt = Column(Text)
    final_response = Column(Text)
    
    # Query counts
    total_queries = Column(Integer)
    red_teaming_queries = Column(Integer)
    judge_queries = Column(Integer)
    target_queries = Column(Integer)
    
    # Strategy
    principles_used = Column(JSON)
    successful_composition = Column(String)
    
    # Timing
    duration_seconds = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Metadata
    metadata_json = Column(JSON)


class Campaign(Base):
    """Stores campaign-level metrics."""
    __tablename__ = "campaigns"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String, unique=True, index=True)
    
    # Metrics
    total_attempts = Column(Integer, default=0)
    successful_attempts = Column(Integer, default=0)
    failed_attempts = Column(Integer, default=0)
    attack_success_rate = Column(Float)
    
    # Query stats
    total_queries = Column(Integer)
    avg_queries_per_success = Column(Float)
    avg_iterations_per_success = Column(Float)
    
    # Timing
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    duration_seconds = Column(Float)
    
    # Targets
    target_models = Column(JSON)
    
    # Principle effectiveness
    principle_effectiveness = Column(JSON)
    
    # Metadata
    metadata_json = Column(JSON)


async def init_db(database_url: str):
    """Initialize database tables with proper connection pool configuration."""
    engine = create_async_engine(
        database_url,
        echo=False,
        # Connection pool settings for concurrent web requests
        pool_size=20,              # Number of connections to maintain in pool
        max_overflow=10,            # Additional connections if pool is exhausted
        pool_pre_ping=True,         # Verify connections before using them
        pool_recycle=3600,          # Recycle connections after 1 hour
        # Prevent "operation in progress" errors with asyncpg
        connect_args={
            "server_settings": {
                "application_name": "cop_pipeline_web"
            }
        }
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return engine


def get_async_session(engine):
    """Get async session factory."""
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    return async_session