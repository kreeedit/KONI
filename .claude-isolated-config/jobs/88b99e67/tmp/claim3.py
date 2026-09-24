import time, inspect, re, sys
from collections import Counter
sys.path.insert(0, "/home/tamask/github/KONI")
from app import texts, flame_pure as fp

s1 = texts.section_texts("0003", "001")
print("sections:", len(s1))

t0 = time.time()
sigs = []
n_pair = 0
meta = {}
for ev in fp.compare_iter(s1, s1, progress_every=10**9):
    if ev["t"] == "meta":
        meta = ev
    elif ev["t"] == "pair":
        n_pair += 1
        sigs.append(" ".join(fp._core_sequence(
            [b for b in fp._fuzzy_blocks(
                [u for u in []] , [], 0.8, 0)] , [])))
import json
print("meta n_candidates", meta.get("n_candidates"), "n_chosen", meta.get("n_chosen"))
print("pairs", n_pair)
