#!/usr/bin/env python3
"""
Run Web UI for Pipeline 3-LLM
Usage: python run_web_ui.py [--port 5000]
"""
import os
import sys
import argparse

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web_ui.app import app

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pipeline 3-LLM Web UI')
    parser.add_argument('--port', type=int, default=5001, help='Port to run on (default: 5001)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to run on (default: 0.0.0.0)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()

    print("=" * 70)
    print("🎮 PIPELINE 3-LLM Web UI")
    print("=" * 70)
    print(f"🌐 Buka: http://localhost:{args.port}")
    print(f"📍 Listening on {args.host}:{args.port}")
    print("=" * 70)
    print()

    try:
        app.run(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
