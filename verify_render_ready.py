#!/usr/bin/env python3
"""
Render Deployment Readiness Verification
Checks that all RuntimeError fixes are properly integrated for Render deployment.
"""

import sys
import os
from pathlib import Path


def check_file_exists(filepath: str, description: str) -> bool:
    """Check if a file exists"""
    if Path(filepath).exists():
        print(f"  ✅ {description}: {filepath}")
        return True
    else:
        print(f"  ❌ {description}: {filepath} NOT FOUND")
        return False


def check_import_chain() -> bool:
    """Verify the complete import chain works"""
    print("\n🔍 Checking Import Chain...")

    try:
        # This simulates what happens on Render startup
        print("  Testing: web_ui_render imports...")

        # Temporarily set env vars to avoid validation errors
        os.environ.setdefault('ANTHROPIC_API_KEY', 'test-key')
        os.environ.setdefault('OPENAI_API_KEY', 'test-key')
        os.environ.setdefault('XAI_API_KEY', 'test-key')
        os.environ.setdefault('DATABASE_URL', 'postgresql://user:pass@localhost:5432/db')

        import web_ui_render
        print("  ✅ web_ui_render imports successfully")

        from web_ui import CoPWebUI, create_gradio_interface, gradio_error_handler
        print("  ✅ web_ui imports successfully")
        print("  ✅ gradio_error_handler decorator available")

        from agents.judge_llm import JudgeLLM
        print("  ✅ JudgeLLM imports successfully")

        # Check that JudgeLLM has fallback attributes
        judge = JudgeLLM(model="claude-3.5-sonnet")
        assert hasattr(judge, 'fallback_models'), "JudgeLLM missing fallback_models"
        assert hasattr(judge, 'fallback_mapping'), "JudgeLLM missing fallback_mapping"
        print(f"  ✅ JudgeLLM has fallback system: {judge.fallback_models}")

        return True

    except Exception as e:
        print(f"  ❌ Import chain failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_render_config() -> bool:
    """Check render.yaml configuration"""
    print("\n🔍 Checking Render Configuration...")

    try:
        with open('render.yaml', 'r') as f:
            content = f.read()

        # Check for updated DEFAULT_JUDGE_LLM
        if 'DEFAULT_JUDGE_LLM' in content:
            if 'claude-3.5-sonnet' in content:
                print("  ✅ DEFAULT_JUDGE_LLM set to claude-3.5-sonnet")
            else:
                print("  ⚠️  DEFAULT_JUDGE_LLM not set to claude-3.5-sonnet")
                return False
        else:
            print("  ❌ DEFAULT_JUDGE_LLM not found in render.yaml")
            return False

        # Check for required services
        required = ['cop-redteam-ui', 'cop-postgres', 'cop-redis']
        for service in required:
            if service in content:
                print(f"  ✅ Service configured: {service}")
            else:
                print(f"  ❌ Service missing: {service}")
                return False

        return True

    except FileNotFoundError:
        print("  ❌ render.yaml not found")
        return False


def check_error_handlers() -> bool:
    """Check that all Gradio handlers have error wrapper"""
    print("\n🔍 Checking Error Handlers...")

    try:
        with open('web_ui.py', 'r') as f:
            content = f.read()

        # Check for decorator definition
        if '@gradio_error_handler' in content:
            count = content.count('@gradio_error_handler')
            print(f"  ✅ Found @gradio_error_handler decorator ({count} uses)")

            if count >= 6:  # We applied it to 6 functions
                print("  ✅ All expected handlers decorated")
                return True
            else:
                print(f"  ⚠️  Expected 6+ decorations, found {count}")
                return False
        else:
            print("  ❌ @gradio_error_handler not found")
            return False

    except FileNotFoundError:
        print("  ❌ web_ui.py not found")
        return False


def check_model_mappings() -> bool:
    """Check that model mappings are updated"""
    print("\n🔍 Checking Model Mappings...")

    try:
        with open('agents/judge_llm.py', 'r') as f:
            content = f.read()

        # Check for fallback_mapping
        if 'fallback_mapping' in content:
            print("  ✅ fallback_mapping defined")
        else:
            print("  ❌ fallback_mapping not found")
            return False

        # Check for updated model names (without anthropic/ prefix)
        if 'claude-3-5-sonnet-20241022' in content:
            print("  ✅ Claude 3.5 Sonnet model mapping found")
        else:
            print("  ⚠️  Claude 3.5 Sonnet mapping not found")

        # Check for fallback models
        if 'gpt-4o' in content:
            print("  ✅ GPT-4o fallback found")
        else:
            print("  ⚠️  GPT-4o fallback not found")

        return True

    except FileNotFoundError:
        print("  ❌ agents/judge_llm.py not found")
        return False


def check_nest_asyncio() -> bool:
    """Check that nest_asyncio is applied in web_ui_render.py"""
    print("\n🔍 Checking nest_asyncio...")

    try:
        with open('web_ui_render.py', 'r') as f:
            lines = f.readlines()

        # Check that nest_asyncio is imported early (within first 20 lines)
        early_lines = ''.join(lines[:20])

        if 'import nest_asyncio' in early_lines:
            print("  ✅ nest_asyncio imported early")
        else:
            print("  ❌ nest_asyncio not imported early")
            return False

        if 'nest_asyncio.apply()' in early_lines:
            print("  ✅ nest_asyncio.apply() called early")
        else:
            print("  ❌ nest_asyncio.apply() not called early")
            return False

        return True

    except FileNotFoundError:
        print("  ❌ web_ui_render.py not found")
        return False


def main():
    """Run all verification checks"""
    print("="*60)
    print("🚀 RENDER DEPLOYMENT READINESS CHECK")
    print("="*60)

    checks = [
        ("Required Files", lambda: all([
            check_file_exists("web_ui_render.py", "Render entry point"),
            check_file_exists("web_ui.py", "Web UI module"),
            check_file_exists("agents/judge_llm.py", "Judge LLM module"),
            check_file_exists("render.yaml", "Render config"),
            check_file_exists("Dockerfile.render", "Render Dockerfile"),
            check_file_exists("requirements.txt", "Python dependencies"),
        ])),
        ("Import Chain", check_import_chain),
        ("Render Config", check_render_config),
        ("Error Handlers", check_error_handlers),
        ("Model Mappings", check_model_mappings),
        ("Async Handling", check_nest_asyncio),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} check failed with exception: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "="*60)
    print("📊 VERIFICATION SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nResults: {passed}/{total} checks passed")

    if passed == total:
        print("\n" + "="*60)
        print("🎉 ALL CHECKS PASSED!")
        print("="*60)
        print("\n✅ Your application is READY for Render deployment!")
        print("\nNext steps:")
        print("1. Commit and push changes to git")
        print("2. Deploy to Render (will auto-deploy if configured)")
        print("3. Set API keys in Render dashboard:")
        print("   - ANTHROPIC_API_KEY")
        print("   - OPENAI_API_KEY")
        print("   - XAI_API_KEY")
        print("4. Monitor logs for successful startup")
        print("5. Test single attack in UI")
        print("\n📚 See RENDER_VERIFICATION.md for detailed deployment guide")
        return 0
    else:
        print("\n" + "="*60)
        print("⚠️  SOME CHECKS FAILED")
        print("="*60)
        print("\n❌ Please fix the issues above before deploying to Render.")
        print("\n📚 See RENDER_VERIFICATION.md for troubleshooting")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
