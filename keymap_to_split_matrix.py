#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyyaml",
# ]
# ///
"""
ZMK Keymap to Split Matrix Layout Converter
Converts keymap.json to @split-matrix-layouts.md format for OverKeys
Supports: Glove80 (80 keys), Go60 (60 keys)

Thin wrapper - actual implementation in scripts/
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.convert import main

if __name__ == '__main__':
    main()
