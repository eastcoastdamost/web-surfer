#!/usr/bin/env python3
"""Launcher for the repo checkout: python3 web_surfer.py [url]

Puts the project root on sys.path so `src` imports work without install.
"""

import sys
from pathlib import Path

# Allow `python3 web_surfer.py` from the repo root without installing.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.main import main

if __name__ == "__main__":
    sys.exit(main())
