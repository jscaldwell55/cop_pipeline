"""
CoP Pipeline - Web UI for Render Deployment
Handles Render-specific environment variables and configurations
"""

import os
import asyncio
from web_ui import CoPWebUI, create_gradio_interface


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
    """
    
    # Parse DATABASE_URL if present
    if "DATABASE_URL" in os.environ:
        db_config = parse_database_url(os.environ["DATABASE_URL"])
        for key, value in db_config.items():
            if key not in os.environ:  # Don't override explicit settings
                os.environ[key] = value
    
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


async def main():
    """Main entry point for Render deployment"""
    
    print("🚀 Starting CoP Red-Teaming Web UI on Render...")
    
    # Setup Render-specific environment
    setup_render_environment()
    
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