"""
LinguaSync - Real-Time Voice Translator
=======================================
Main application entry point.

Run:
    python3 main.py
"""

from __future__ import annotations

import sys


def main() -> None:
    try:
        from gui import run_gui

        run_gui()
    except ImportError as e:
        print("\n" + "=" * 60)
        print("❌ LinguaSync Dependency Error:")
        print(f"   {e}")
        print("-" * 60)
        print("💡 Solution:")
        print("   Make sure your virtual environment is active and run:")
        print("   pip install -r requirements.txt")
        print("=" * 60 + "\n")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 LinguaSync terminated by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error starting LinguaSync: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
