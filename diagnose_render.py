#!/usr/bin/env python3
"""
Diagnostic script for Render deployment issues
Run this on Render to check environment variables and connectivity
"""

import os
import sys
from urllib.parse import urlparse


def diagnose_environment():
    """Check environment variables on Render"""

    print("=" * 70)
    print("RENDER ENVIRONMENT DIAGNOSTIC")
    print("=" * 70)
    print()

    # Check DATABASE_URL
    print("🔍 DATABASE CONFIGURATION:")
    print("-" * 70)
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        print("✅ DATABASE_URL is set")
        parsed = urlparse(database_url)
        print(f"   Hostname: {parsed.hostname}")
        print(f"   Port: {parsed.port}")
        print(f"   Database: {parsed.path[1:] if parsed.path else 'N/A'}")
        print(f"   Username: {parsed.username}")
        print(f"   Password: {'***' if parsed.password else 'NOT SET'}")
    else:
        print("❌ DATABASE_URL is NOT set")
        print("   This is required for Render deployment!")
        print()
        print("   Individual components:")
        print(f"   POSTGRES_HOST: {os.environ.get('POSTGRES_HOST', 'NOT SET')}")
        print(f"   POSTGRES_PORT: {os.environ.get('POSTGRES_PORT', 'NOT SET')}")
        print(f"   POSTGRES_DB: {os.environ.get('POSTGRES_DB', 'NOT SET')}")
        print(f"   POSTGRES_USER: {os.environ.get('POSTGRES_USER', 'NOT SET')}")
        print(f"   POSTGRES_PASSWORD: {'***' if os.environ.get('POSTGRES_PASSWORD') else 'NOT SET'}")

    print()

    # Check REDIS_URL
    print("🔍 REDIS CONFIGURATION:")
    print("-" * 70)
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        print("✅ REDIS_URL is set")
        parsed = urlparse(redis_url)
        print(f"   Hostname: {parsed.hostname}")
        print(f"   Port: {parsed.port}")
        print(f"   Password: {'***' if parsed.password else 'NOT SET'}")
    else:
        print("❌ REDIS_URL is NOT set")
        print("   This is required for Render deployment!")
        print()
        print("   Individual components:")
        print(f"   REDIS_HOST: {os.environ.get('REDIS_HOST', 'NOT SET')}")
        print(f"   REDIS_PORT: {os.environ.get('REDIS_PORT', 'NOT SET')}")
        print(f"   REDIS_PASSWORD: {'***' if os.environ.get('REDIS_PASSWORD') else 'NOT SET'}")

    print()

    # Check API keys
    print("🔍 API KEYS:")
    print("-" * 70)
    api_keys = {
        "XAI_API_KEY": os.environ.get("XAI_API_KEY"),
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY"),
        "GOOGLE_API_KEY": os.environ.get("GOOGLE_API_KEY"),
        "TOGETHER_API_KEY": os.environ.get("TOGETHER_API_KEY"),
    }

    for key, value in api_keys.items():
        if value and value != "your_key_here":
            print(f"✅ {key}: Set (***{value[-4:]})")
        else:
            print(f"⚠️  {key}: Not set or placeholder")

    print()

    # Check other settings
    print("🔍 OTHER SETTINGS:")
    print("-" * 70)
    print(f"PORT: {os.environ.get('PORT', 'NOT SET (default: 7860)')}")
    print(f"PYTHON_VERSION: {os.environ.get('PYTHON_VERSION', 'NOT SET')}")
    print(f"LOG_LEVEL: {os.environ.get('LOG_LEVEL', 'NOT SET (default: INFO)')}")

    print()
    print("=" * 70)

    # Summary
    print()
    print("SUMMARY:")
    print("-" * 70)

    issues = []
    if not database_url:
        issues.append("❌ DATABASE_URL is not set - database connection will fail")
    if not redis_url:
        issues.append("⚠️  REDIS_URL is not set - caching may not work")

    missing_keys = [k for k, v in api_keys.items() if not v or v == "your_key_here"]
    if missing_keys:
        issues.append(f"⚠️  Missing API keys: {', '.join(missing_keys)}")

    if issues:
        print("ISSUES FOUND:")
        for issue in issues:
            print(f"  {issue}")
        print()
        print("NEXT STEPS:")
        print("1. Go to your Render dashboard")
        print("2. Select your service 'cop-redteam-ui'")
        print("3. Check that the PostgreSQL database 'cop-postgres' is created")
        print("4. Check that the Redis service 'cop-redis' is created")
        print("5. Verify environment variables are being populated")
        print("6. If services don't exist, deploy using the render.yaml blueprint")
        return 1
    else:
        print("✅ All required environment variables are set!")
        print("   If you're still experiencing issues, check network connectivity")
        print("   and service availability in the Render dashboard.")
        return 0


if __name__ == "__main__":
    sys.exit(diagnose_environment())
