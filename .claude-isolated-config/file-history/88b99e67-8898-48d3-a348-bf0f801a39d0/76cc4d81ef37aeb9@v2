import os, sys, json, time
sys.path.insert(0, os.getcwd())
sys.path.insert(0, "scripts")
from app import flame_pure as F

sigs = json.load(open(os.path.join(os.environ["CLAUDE_JOB_DIR"], "tmp", "sigs.json")))["self"]

real_sketch = F._sketch

t0 = time.time()
fast = F.cluster_pairs(sigs, threshold=0.85)
t_fast = time.time() - t0

# Disable the sketch gate: a fully-saturated sketch ANDs non-zero with anything,
# so the loop falls back to the exact frozenset intersection alone.
F._sketch = lambda s, k=4, bits=4096: (1 << bits) - 1
t0 = time.time()
ref = F.cluster_pairs(sigs, threshold=0.85)
t_ref = time.time() - t0
F._sketch = real_sketch

same_clusters = fast["clusters"] == ref["clusters"]
same_pc = fast["pair_cluster"] == ref["pair_cluster"]
print("fast   : %.2fs  %s" % (t_fast, fast["stats"]))
print("nogate : %.2fs  %s" % (t_ref, ref["stats"]))
print("speedup: %.1fx" % (t_ref / t_fast))
print("clusters identical : %s" % same_clusters)
print("pair_cluster identical: %s" % same_pc)
print("lev_compares identical : %s" % (fast["stats"]["lev_compares"] == ref["stats"]["lev_compares"]))
if not (same_clusters and same_pc):
    print("!! SKETCH GATE IS NOT RECALL-NEUTRAL")
    sys.exit(1)

# And the sketch must never prove-disjoint two strings that actually share a k-gram.
import random, string
random.seed(7)
bad = 0
for _ in range(3000):
    a = "".join(random.choice("αβγδε ζηθικλμνξο") for _ in range(random.randint(3, 40)))
    b = a if random.random() < 0.4 else "".join(random.choice("αβγδε ζηθικλμνξο") for _ in range(random.randint(3, 40)))
    if (F._shingles(a) & F._shingles(b)) and not (F._sketch(a) & F._sketch(b)):
        bad += 1
print("sketch false-disjoints over 3000 random pairs: %d (want 0)" % bad)
sys.exit(1 if bad else 0)
