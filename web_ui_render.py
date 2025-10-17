"""
CoP Pipeline - Web UI for Render Deployment
Handles Render-specific environment variables and configurations

CRITICAL FIX: Apply nest_asyncio at the VERY TOP before any other imports
"""

import os

# ============================================================================
# CRITICAL: Apply nest_asyncio BEFORE any other imports that use asyncio
# This MUST be the first thing after os import
# ============================================================================
import nest_asyncio
nest_asyncio.apply()
print("✅ nest_asyncio applied in web_ui_render.py")

import asyncio


def parse_database_url(database_url: str) -> dict:
    """Parse Render's DATABASE_URL into components"""
    # Format: postgresql://user:password@host:port/database
    from urllib.parse import urlparse
    
    result = urlparse(database_url)
    
    return {
        "POSTGRES_HOST": result.hostname,
        "POSTGRES_PORT": str(result.port or 5432),
        "POSTGRES_USER": result.username,
        "POSTGRES_PASSWORD": result.password,
        "POSTGRES_DB": result.path[1:]  # Remove leading /
    }


def parse_redis_url(redis_url: str) -> dict:
    """Parse Render's REDIS_URL into components"""
    # Format: redis://default:password@host:port
    from urllib.parse import urlparse
    
    result = urlparse(redis_url)
    
    return {
        "REDIS_HOST": result.hostname,
        "REDIS_PORT": str(result.port or 6379),
        "REDIS_PASSWORD": result.password or ""
    }


def setup_render_environment():
    """
    Convert Render environment variables to format expected by CoP Pipeline
    Render provides DATABASE_URL and REDIS_URL, we need to parse them
    IMPORTANT: This must run BEFORE importing any config/settings
    """
    
    print("🔍 Checking environment variables...")
    print(f"   DATABASE_URL present: {'DATABASE_URL' in os.environ}")
    print(f"   REDIS_URL present: {'REDIS_URL' in os.environ}")
    
    # Parse DATABASE_URL if present
    if "DATABASE_URL" in os.environ:
        print(f"   DATABASE_URL value: {os.environ['DATABASE_URL'][:50]}...")
        db_config = parse_database_url(os.environ["DATABASE_URL"])
        for key, value in db_config.items():
            if key not in os.environ:  # Don't override explicit settings
                os.environ[key] = value
                print(f"   Set {key}: {value if key != 'POSTGRES_PASSWORD' else '***'}")
    
    # Parse REDIS_URL if present
    if "REDIS_URL" in os.environ:
        redis_config = parse_redis_url(os.environ["REDIS_URL"])
        for key, value in redis_config.items():
            if key not in os.environ:  # Don't override explicit settings
                os.environ[key] = value
    
    # Set default port for Render (they set PORT env var)
    if "PORT" not in os.environ:
        os.environ["PORT"] = "7860"
    
    print("✅ Render environment configured")
    print(f"   Database: {os.environ.get('POSTGRES_HOST', 'not configured')}")
    print(f"   Redis: {os.environ.get('REDIS_HOST', 'not configured')}")
    print(f"   Port: {os.environ.get('PORT', '7860')}")


# Setup environment BEFORE importing anything else
setup_render_environment()

# NOW we can import after environment is set up
# web_ui.py will also apply nest_asyncio, but that's okay - it's idempotent
from web_ui import CoPWebUI, create_gradio_interface
from config.settings import get_settings


async def clear_redis_cache():
    """
    Clear Redis cache if CLEAR_CACHE_ON_START environment variable is set to 'true'
    
    Usage in Render:
    1. Set environment variable: CLEAR_CACHE_ON_START=true
    2. Deploy (cache gets cleared)
    3. Set it back to: CLEAR_CACHE_ON_START=false
    4. Deploy again (normal operation)
    """
    import redis.asyncio as aioredis
    
    try:
        settings = get_settings()
        redis_client = await aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        
        await redis_client.flushall()
        await redis_client.close()
        
        print("🗑️  Redis cache cleared successfully!")
        return True
        
    except Exception as e:
        print(f"⚠️  Failed to clear Redis cache: {str(e)}")
        print("   Continuing with startup anyway...")
        return False


async def main():
    """Main entry point for Render deployment"""
    
    print("🚀 Starting CoP Red-Teaming Web UI on Render...")
    print("✅ nest_asyncio active - event loops patched")
    
    # Environment already set up at module import time
    
    # Check if cache clearing is requested
    if os.environ.get("CLEAR_CACHE_ON_START", "").lower() == "true":
        print("\n" + "="*60)
        print("🗑️  CLEAR_CACHE_ON_START=true detected")
        print("   Clearing Redis cache before startup...")
        print("="*60 + "\n")
        
        await clear_redis_cache()
        
        print("\n" + "="*60)
        print("💡 TIP: Set CLEAR_CACHE_ON_START=false to disable this")
        print("="*60 + "\n")
    
    # Initialize UI
    ui = CoPWebUI()
    await ui.initialize()
    print("✅ Pipeline initialized")
    
    # Create interface
    interface = create_gradio_interface(ui)
    print("✅ Gradio interface created")
    
    # Get port from environment (Render sets this)
    port = int(os.environ.get("PORT", 7860))
    
    # Launch configuration for Render
    print("\n" + "="*60)
    print(f"🌐 Web UI starting on port {port}")
    print("="*60 + "\n")
    
    interface.launch(
        server_name="0.0.0.0",  # Bind to all interfaces (required for Render)
        server_port=port,
        share=False,
        show_error=True,
        # Render handles HTTPS, so we don't need share links
        # Optional: Add authentication by uncommenting below
        # auth=("admin", os.environ.get("UI_PASSWORD", "changeme"))
    )


if __name__ == "__main__":
    asyncio.run(main())