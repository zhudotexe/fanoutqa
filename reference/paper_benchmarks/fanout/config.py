import os
from pathlib import Path

if cache_dir := os.getenv("WIKI_CACHE_DIR"):
    CACHE_DIR = Path(cache_dir)
else:
    CACHE_DIR = Path(__file__).parent / "../../ccbqa-processing/.wikicache"
CACHE_DIR.mkdir(exist_ok=True)
