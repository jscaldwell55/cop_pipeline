# File: cli.py
"""
Command-line interface for CoP Pipeline.
"""

import asyncio
import click
import json
from pathlib import Path
from typing import List
import sys

from main import CoPPipeline
from utils.logging_metrics import CampaignMetrics


@click.group()
def cli():
    """CoP Pipeline - Composition of Principles Agentic Red-Teaming."""
    pass


@cli.command()
@click.option(
    '--query',
    '-q',
    required=True,
    help='Harmful query to jailbreak'
)
@click.option(
    '--target',
    '-t',
    required=True,
    help='Target model name (e.g., llama-2-7b-chat, gpt-4)'
)
@click.option(
    '--max-iterations',
    '-i',
    default=10,
    help='Maximum number of iterations'
)
@click.option(
    '--red-teaming-agent',
    default='grok-2',
    help='Red-teaming agent model'
)
@click.option(
    '--judge-llm',
    default='gpt-4o',
    help='Judge LLM model'
)
@click.option(
    '--output',
    '-o',
    type=click.Path(),
    help='Output file for results (JSON)'
)
def attack(query, target, max_iterations, red_teaming_agent, judge_llm, output):
    """Execute a single CoP attack."""
    async def run():
        pipeline = CoPPipeline(
            red_teaming_agent_model=red_teaming_agent,
            judge_llm_model=judge_llm,
            enable_database=True
        )
        
        await pipeline.initialize_database()
        
        try:
            click.echo(f"Starting CoP attack on {target}...")
            click.echo(f"Query: {query[:100]}...")
            
            result = await pipeline.attack_single(
                query=query,
                target_model=target,
                max_iterations=max_iterations
            )
            
            click.echo("\n" + "="*60)
            click.echo("ATTACK RESULTS")
            click.echo("="*60)
            click.echo(f"Success: {result.success}")
            click.echo(f"Jailbreak Score: {result.final_jailbreak_score:.2f}/10")
            click.echo(f"Similarity Score: {result.final_similarity_score:.2f}/10")
            click.echo(f"Iterations: {result.iterations}")
            click.echo(f"Total Queries: {result.total_queries}")
            click.echo(f"  - Red-teaming: {result.red_teaming_queries}")
            click.echo(f"  - Judge: {result.judge_queries}")
            click.echo(f"  - Target: {result.target_queries}")
            click.echo(f"Duration: {result.duration_seconds:.2f}s")
            click.echo("\nFinal Jailbreak Prompt:")
            click.echo("-" * 60)
            click.echo(result.final_jailbreak_prompt)
            click.echo("-" * 60)
            
            if output:
                with open(output, 'w') as f:
                    json.dump(result.to_dict(), f, indent=2)
                click.echo(f"\nResults saved to: {output}")
        
        finally:
            await pipeline.close()
    
    asyncio.run(run())


@cli.command()
@click.option(
    '--queries-file',
    '-f',
    required=True,
    type=click.Path(exists=True),
    help='File containing queries (one per line)'
)
@click.option(
    '--targets',
    '-t',
    multiple=True,
    required=True,
    help='Target models (can specify multiple)'
)
@click.option(
    '--max-concurrent',
    '-c',
    default=5,
    help='Maximum concurrent attacks'
)
@click.option(
    '--red-teaming-agent',
    default='grok-2',
    help='Red-teaming agent model'
)
@click.option(
    '--judge-llm',
    default='gpt-4o',
    help='Judge LLM model'
)
@click.option(
    '--output',
    '-o',
    type=click.Path(),
    help='Output file for campaign results (JSON)'
)
def campaign(queries_file, targets, max_concurrent, red_teaming_agent, judge_llm, output):
    """Execute a batch campaign of CoP attacks."""
    async def run():
        # Load queries
        with open(queries_file, 'r') as f:
            queries = [line.strip() for line in f if line.strip()]
        
        click.echo(f"Loaded {len(queries)} queries from {queries_file}")
        click.echo(f"Targeting {len(targets)} models: {', '.join(targets)}")
        click.echo(f"Max concurrent attacks: {max_concurrent}")
        
        pipeline = CoPPipeline(
            red_teaming_agent_model=red_teaming_agent,
            judge_llm_model=judge_llm,
            enable_database=True
        )
        
        await pipeline.initialize_database()
        
        try:
            click.echo("\nStarting campaign...")
            
            campaign = await pipeline.attack_batch(
                queries=queries,
                target_models=list(targets),
                max_concurrent=max_concurrent
            )
            
            click.echo("\n" + "="*60)
            click.echo("CAMPAIGN RESULTS")
            click.echo("="*60)
            click.echo(f"Total Attempts: {campaign.total_attempts}")
            click.echo(f"Successful: {campaign.successful_attempts}")
            click.echo(f"Failed: {campaign.failed_attempts}")
            click.echo(f"Attack Success Rate: {campaign.attack_success_rate:.2f}%")
            click.echo(f"Total Queries: {campaign.total_queries}")
            click.echo(f"Avg Queries per Success: {campaign.avg_queries_per_success:.2f}")
            click.echo(f"Avg Iterations per Success: {campaign.avg_iterations_per_success:.2f}")
            click.echo(f"Duration: {campaign.duration_seconds:.2f}s")
            
            click.echo("\nPrinciple Effectiveness:")
            for principle, stats in campaign.principle_effectiveness.items():
                effectiveness = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
                click.echo(f"  {principle}: {effectiveness:.1f}% ({stats['success']}/{stats['total']})")
            
            if output:
                with open(output, 'w') as f:
                    json.dump(campaign.to_dict(), f, indent=2)
                click.echo(f"\nCampaign results saved to: {output}")
        
        finally:
            await pipeline.close()
    
    asyncio.run(run())


@cli.command()
@click.option(
    '--target',
    '-t',
    required=True,
    help='Target model name'
)
@click.option(
    '--limit',
    '-l',
    default=10,
    help='Number of recent results to show'
)
def history(target, limit):
    """View attack history for a target model."""
    async def run():
        from database.models import init_db, get_async_session
        from database.repository import AttackRepository
        from config.settings import get_settings
        
        settings = get_settings()
        engine = await init_db(settings.database_url)
        async_session_factory = get_async_session(engine)
        
        try:
            async with async_session_factory() as session:
                repo = AttackRepository(session)
                results = await repo.get_attacks_by_target(target, limit)
                
                if not results:
                    click.echo(f"No attack history found for {target}")
                    return
                
                click.echo(f"\nRecent attacks on {target}:")
                click.echo("="*80)
                
                for result in results:
                    success_icon = "✓" if result.success else "✗"
                    click.echo(f"\n{success_icon} Query ID: {result.query_id}")
                    click.echo(f"  Query: {result.original_query[:60]}...")
                    click.echo(f"  Score: {result.final_jailbreak_score:.1f}/10")
                    click.echo(f"  Iterations: {result.iterations}")
                    click.echo(f"  Queries: {result.total_queries}")
                    click.echo(f"  Date: {result.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        finally:
            await engine.dispose()
    
    asyncio.run(run())


@cli.command()
def list_models():
    """List available target models."""
    models = {
        "OpenAI": ["gpt-4", "gpt-4o", "gpt-4-turbo", "o1", "o1-mini"],
        "Anthropic": ["claude-3.5-sonnet", "claude-3-opus"],
        "Google": ["gemini-pro-1.5", "gemini-flash"],
        "Meta Llama": [
            "llama-2-7b-chat",
            "llama-2-13b-chat",
            "llama-2-70b-chat",
            "llama-3-8b-instruct",
            "llama-3-70b-instruct"
        ],
        "Google Gemma": ["gemma-7b-it"]
    }
    
    click.echo("Available Target Models:")
    click.echo("="*60)
    
    for provider, model_list in models.items():
        click.echo(f"\n{provider}:")
        for model in model_list:
            click.echo(f"  • {model}")


@cli.command()
def check_setup():
    """Check if environment is properly configured."""
    from config.settings import get_settings
    import redis
    
    click.echo("Checking CoP Pipeline setup...\n")
    
    # Check settings
    try:
        settings = get_settings()
        click.echo("✓ Settings loaded successfully")
    except Exception as e:
        click.echo(f"✗ Failed to load settings: {e}")
        return
    
    # Check API keys
    if settings.xai_api_key:
        click.echo("✓ XAI API key configured")
    else:
        click.echo("✗ XAI API key missing")
    
    if settings.openai_api_key:
        click.echo("✓ OpenAI API key configured")
    else:
        click.echo("✗ OpenAI API key missing")
    
    # Check Redis
    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
        click.echo("✓ Redis connection successful")
    except Exception as e:
        click.echo(f"✗ Redis connection failed: {e}")
    
    # Check database
    try:
        import asyncpg
        async def check_db():
            conn = await asyncpg.connect(
                host=settings.postgres_host,
                port=settings.postgres_port,
                user=settings.postgres_user,
                password=settings.postgres_password,
                database=settings.postgres_db
            )
            await conn.close()
        
        asyncio.run(check_db())
        click.echo("✓ Database connection successful")
    except Exception as e:
        click.echo(f"✗ Database connection failed: {e}")
    
    click.echo("\nSetup check complete!")


if __name__ == '__main__':
    cli()