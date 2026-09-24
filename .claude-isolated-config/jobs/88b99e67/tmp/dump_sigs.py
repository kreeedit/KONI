import os, sys, json
sys.path.insert(0, os.getcwd())
from app import flame_pure as F, texts

CACHE = os.path.join(os.environ["CLAUDE_JOB_DIR"], "tmp", "sigs.json")
out = {}
PAIRS = {
    "self": ("0003.001", "0003.001"),
    "reuse": ("0009.001", "0003.001"),
}
for key, (a, b) in PAIRS.items():
    s1 = texts.section_texts(*a.split("."))
    s2 = texts.section_texts(*b.split("."))
    if not s1 or not s2:
        print(key, "no text", flush=True)
        continue
    sigs = []
    for ev in F.compare_iter(s1, s2, progress_every=10**9):
        if ev["t"] == "pair":
            sigs.append(ev["pair"]["core_text"])
    out[key] = sigs
    print(key, len(sigs), flush=True)
json.dump(out, open(CACHE, "w"))
print("wrote", CACHE, flush=True)
