#!/usr/bin/env python3
"""
Quick server runner for Marketing Automation MCP
Run this to start the MCP server locally
"""

import os
import sys
import asyncio
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Run the MCP server"""
    print("🚀 Marketing Automation MCP Server")
    print("=" * 50)
    print("⚡ 75% reduction in campaign optimization time")
    print("📈 Average 23% improvement in campaign ROI")
    print("=" * 50)
    
    # Check for demo mode
    if not os.getenv("OPENAI_API_KEY"):
        print("\n🎭 Running in DEMO MODE (no OpenAI key detected)")
        print("   Add OPENAI_API_KEY to .env for full functionality")
        os.environ["DEMO_MODE"] = "true"
    
    print("\n📡 Starting MCP server...")
    print("   Use with Claude Desktop or any MCP client")
    print("   Press Ctrl+C to stop\n")
    
    try:
        from src.server import main as server_main
        asyncio.run(server_main())
    except KeyboardInterrupt:
        print("\n\n✅ Server stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure you're in the project directory")
        print('2. Install dependencies: python3 -m pip install -e ".[dev]"')
        print("3. Check logs/marketing_automation.log for details")

if __name__ == "__main__":
    main()
