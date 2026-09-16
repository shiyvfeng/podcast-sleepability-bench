"""Shared batch output location; input cache retains stable manifest IDs."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('PODCAST_OUTPUT_DIR', str(ROOT / 'output'))).resolve()
OUT.mkdir(parents=True, exist_ok=True)
