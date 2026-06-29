"""Build (or refresh) the PerseusDL/canonical-greekLit Greek-edition map.

Maps every (author_id, work_id) in the repo to its Greek TEI filename, so the
reader can fetch clean text for works that are on Perseus but NOT in the modern
CTS inventory (e.g. TLG 4029 Procopius). The map auto-builds on first server
start if missing; run this manually to refresh after Perseus updates the repo.

    python scripts/build_repo_map.py
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from app import repo  # noqa: E402

m = repo.build_map()
print(f"Indexed {len(m)} Perseus Greek works -> {repo.MAP_PATH.relative_to(REPO)}")
for k in ("4029_001", "4029_002", "0012_001", "0014_002", "0007_001"):
    print(f"  {k}: {m.get(k)}")